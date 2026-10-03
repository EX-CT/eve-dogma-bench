#!/usr/bin/env python3
"""Mutated suite, EFT part (CONTRACT-MUTATED.md §4). Two checks over the engine's JSONL RPC (`serve-stdio`):

* export: `eft_export {fit, name}` for every case must equal Pyfa's exportEft text (mutated/expected_extra/eft_export.jsonl,
  all options on, after fill(); the T3C extra "[Empty Subsystem slot]" line is accepted as in tools/check_eft_export.py).
* import: `eft_parse {text}` for Pyfa's export of every case plus the hand-written edge texts in mutated/eft/ must give
  the fit Pyfa's importEft gives (mutated/expected_extra/eft_import.jsonl). Compared: ship, modules in order
  (type_id, charge, mutation), drones (type_id, quantity, mutation), implants and boosters (type ids, in order).
  Mutations are compared by their *effective* values (§2: only mutaplasmid attributes, omitted = base value, clamped),
  so an importer may clamp at parse time or leave it to calc. Implant/booster lists are compared after the §3 slot
  rule (first entry per slot wins), so an importer may keep or drop conflicting entries.

  python3 mutated/tools/check_eft.py --rpc-cmd "<engine> serve-stdio --dataset D" --dataset D [--show N]
MIT. Reads the EXCT dataset only (mutaplasmid ranges, base values, implant/booster slots)."""
import argparse, gzip, json, math, pathlib, subprocess

SUITE = pathlib.Path(__file__).resolve().parent.parent


class DS:
    def __init__(self, path):
        d = json.load(gzip.open(path))
        self.T, self.M = d["types"], d["mutaplasmids"]

    def base(self, t, a):
        t = self.T.get(str(t))
        if t is None:
            return None
        return t["mass"] if int(a) == 4 else t["attrs"].get(str(a))

    def effective(self, mu):
        """§2 effective rolled values of a mutation object"""
        if not mu:
            return None
        m = self.M.get(str(mu.get("mutaplasmid_type_id")))
        if m is None:
            return {"base": mu.get("base_type_id"), "muta": mu.get("mutaplasmid_type_id"), "attrs": None}
        given = {str(k): v for k, v in (mu.get("attributes") or {}).items()}
        out = {}
        for a, (lo, hi) in m["attrs"].items():
            bv = self.base(mu["base_type_id"], a)
            if bv is None:
                continue
            v = given.get(a, bv)
            lo, hi = round(lo, 3), round(hi, 3)
            if bv == 0:
                v = 0.0
            elif not (lo <= v / bv <= hi):
                v = min(max(v, min(lo * bv, hi * bv)), max(lo * bv, hi * bv))
            out[a] = v
        return {"base": mu["base_type_id"], "muta": mu["mutaplasmid_type_id"], "attrs": out}

    def slot(self, t, attr):
        v = self.T.get(str(t), {}).get("attrs", {}).get(attr)
        return v

    def first_wins(self, ids, attr):
        seen, out = set(), []
        for t in ids:
            s = self.slot(t, attr)
            if s is not None and s in seen:
                continue
            seen.add(s)
            out.append(t)
        return out


def close(a, b):
    if a is None or b is None:
        return a == b
    if a.keys() != b.keys() or a["base"] != b["base"] or a["muta"] != b["muta"]:
        return False
    if a["attrs"] is None or b["attrs"] is None:
        return a["attrs"] == b["attrs"]
    return a["attrs"].keys() == b["attrs"].keys() and all(
        math.isclose(a["attrs"][k], b["attrs"][k], rel_tol=1e-6, abs_tol=1e-9) for k in a["attrs"])


def tid(x):
    return x["type_id"] if isinstance(x, dict) else x


def canon(ds, fit):
    mods = [(m["type_id"], m.get("charge_type_id"), ds.effective(m.get("mutation"))) for m in fit.get("modules", [])]
    drones = sorted(((d["type_id"], d.get("quantity", 1), ds.effective(d.get("mutation"))) for d in fit.get("drones", [])),
                    key=lambda x: (x[0], x[1], json.dumps(x[2], sort_keys=True)))
    return {"ship": fit.get("ship", {}).get("type_id"), "modules": mods, "drones": drones,
            "implants": ds.first_wins([tid(i) for i in fit.get("implants", [])], "331"),
            "boosters": ds.first_wins([tid(b) for b in fit.get("boosters", [])], "1087")}


def same(a, b):
    if a["ship"] != b["ship"] or a["implants"] != b["implants"] or a["boosters"] != b["boosters"]:
        return False
    for xs, ys in ((a["modules"], b["modules"]), (a["drones"], b["drones"])):
        if len(xs) != len(ys) or any(x[:-1] != y[:-1] or not close(x[-1], y[-1]) for x, y in zip(xs, ys)):
            return False
    return True


def rpc(cmd, reqs, timeout=600):
    inp = "".join(json.dumps({"id": i, "method": m, "params": p}) + "\n" for i, (m, p) in enumerate(reqs))
    r = subprocess.run(cmd, shell=True, input=inp, capture_output=True, text=True, timeout=timeout)
    got = {}
    for line in r.stdout.splitlines():
        try:
            o = json.loads(line)
        except ValueError:
            continue
        if isinstance(o, dict) and "id" in o:
            got[o["id"]] = o.get("result", {"error": o.get("error")})
    return got


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rpc-cmd", required=True)
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--show", type=int, default=0)
    a = ap.parse_args()
    ds = DS(a.dataset)
    exp = [json.loads(l) for l in open(SUITE / "expected_extra/eft_export.jsonl")]
    got = rpc(a.rpc_cmd, [("eft_export", {"fit": e["fit"], "name": e["name"]}) for e in exp])
    ok_e, bad_e = 0, []
    for i, e in enumerate(exp):
        t = got.get(i)
        t = t.get("text") if isinstance(t, dict) else t
        if isinstance(t, str) and (t == e["text"] or t.replace("\n[Empty Subsystem slot]", "", 1) == e["text"]):
            ok_e += 1
        else:
            bad_e.append((e["name"], e["text"], t))
    imp = [json.loads(l) for l in open(SUITE / "expected_extra/eft_import.jsonl")]
    got = rpc(a.rpc_cmd, [("eft_parse", {"text": e["text"]}) for e in imp])
    ok_i, bad_i = 0, []
    for i, e in enumerate(imp):
        want = canon(ds, e["ok"][0])
        g = got.get(i)
        g = g.get("fit", g) if isinstance(g, dict) else g
        try:
            have = canon(ds, g)
        except Exception as ex:  # noqa: BLE001
            have = repr(ex)
        if isinstance(have, dict) and same(want, have):
            ok_i += 1
        else:
            bad_i.append((e["name"], want, have))
    for n, w, h in (bad_e + bad_i)[:a.show]:
        print(f"MISMATCH {n}\n--- pyfa\n{w}\n--- got\n{h}\n")
    edges = [b[0] for b in bad_i if b[0].startswith("eftedge_")]
    print(json.dumps({"export": f"{ok_e}/{len(exp)}", "import": f"{ok_i}/{len(imp)}",
                      "export_failed": [b[0] for b in bad_e][:40], "import_failed": [b[0] for b in bad_i][:40],
                      "import_edges_failed": edges}, indent=1))


if __name__ == "__main__":
    main()
