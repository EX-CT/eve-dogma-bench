#!/usr/bin/env python3
"""Check a variant's import/export formats against Pyfa (formats/expected/*.jsonl).

usage: python3 tools/check_formats.py --rpc "<variant> serve-stdio" [--name NAME] [--out results/formats/NAME]

RPC methods used (JSONL {"id","method","params"} -> {"id","result"}; see formats/README.md):
  format_export {fit, name, format, options}   -> {"text": str}     (fallback for eft/eft_min: eft_export {fit,name,options})
  format_import {text, format, path?}           -> {"kind"?: str, "fits": [FitRequest|...]} or a FitRequest / list
                                                   (fallback for eft: eft_parse {text})
An UNKNOWN_METHOD / unsupported-format error marks the format "not implemented" (not a failure of other formats).
"""
import argparse, collections, json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXP = os.path.join(ROOT, "formats", "expected")


class Rpc:
    def __init__(self, cmd):
        self.p = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL, text=True, bufsize=1)
        self.n = 0

    def call(self, method, params):
        self.n += 1
        self.p.stdin.write(json.dumps({"id": self.n, "method": method, "params": params}) + "\n")
        self.p.stdin.flush()
        line = self.p.stdout.readline()
        if not line:
            raise RuntimeError("variant closed the RPC pipe")
        r = json.loads(line)
        res = r.get("result", r)
        if isinstance(res, dict) and "error" in res and len(res) == 1:
            return None, res["error"]
        if "error" in r and "result" not in r:
            return None, r["error"]
        return res, None


def unknown(err):
    s = json.dumps(err).upper()
    return "UNKNOWN_METHOD" in s or "UNSUPPORTED" in s or "NOT_IMPLEMENTED" in s or "UNKNOWN FORMAT" in s


def _tid(x):
    return x if isinstance(x, int) else (x or {}).get("type_id")


def canon(fit):
    """Pyfa-normalised fit or FitRequest -> comparable summary (field -> value)."""
    if fit is None:
        return None
    mods = collections.defaultdict(list)
    for m in fit.get("modules", []):
        if m is None:
            continue
        mu = m.get("mutation")
        if mu:
            mu = (mu.get("base_type_id"), mu.get("mutaplasmid_type_id"),
                  tuple(sorted((str(k), round(float(v), 6)) for k, v in (mu.get("attributes") or {}).items())))
        mods[m.get("slot")].append((m.get("type_id"), m.get("state"), m.get("charge_type_id"), mu))
    ship = fit.get("ship") or {}
    q = lambda xs, k="quantity": sorted((_tid(x), x.get(k, x.get("amount", 1)) if isinstance(x, dict) else 1)
                                       for x in xs or [])
    return {
        "ship": (ship.get("type_id"), ship.get("mode_type_id")),
        "modules": {k: v for k, v in sorted(mods.items(), key=lambda kv: str(kv[0]))},
        "drones": q(fit.get("drones")),
        "drones_active": sorted((_tid(d), d.get("active")) for d in fit.get("drones") or []),
        "fighters": q(fit.get("fighters")),
        "implants": sorted(_tid(i) for i in fit.get("implants") or []),
        "boosters": sorted(_tid(b) for b in fit.get("boosters") or []),
        "cargo": q(fit.get("cargo")),
        "name": fit.get("name"),
    }


CORE = ("ship", "modules", "drones", "fighters", "implants", "boosters", "cargo")


def diff_fits(exp, got):
    """-> list of differing fields (core fields only; name/drones_active reported separately)."""
    if not isinstance(got, list):
        got = [got]
    if len(exp) != len(got):
        return ["fit_count"], []
    core, extra = [], []
    for e, g in zip(exp, got):
        ce, cg = canon(e), canon(g)
        if ce is None or cg is None:
            if ce != cg:
                core.append("none")
            continue
        for k in CORE:
            if ce[k] == cg[k]:
                continue
            if k == "ship" and ce[k][0] == cg[k][0] and cg[k][1] is None:
                # Pyfa sets a T3D's first mode explicitly; a FitRequest may leave it null (= first mode by contract)
                extra.append("mode_left_default")
                continue
            core.append(k)
        extra += [k for k in ("name", "drones_active") if ce[k] != cg[k] and cg[k] is not None]
    return core, extra


def fits_of(res):
    if isinstance(res, dict) and "fits" in res:
        return res["fits"], res.get("kind")
    return (res if isinstance(res, list) else [res]), None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rpc", required=True)
    ap.add_argument("--name", default="variant")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    rpc = Rpc(a.rpc)
    out = a.out or os.path.join(ROOT, "results", "formats", a.name)
    os.makedirs(out, exist_ok=True)
    cases = {}
    stats = collections.defaultdict(lambda: collections.Counter())
    impl = {}
    fails = []

    def case_req(c):
        if c not in cases:
            cases[c] = json.load(open(os.path.join(ROOT, "cases", c)))
        return cases[c]

    # ---- exports
    for line in open(os.path.join(EXP, "export.jsonl")):
        r = json.loads(line)
        fmt = r["format"]
        key = "export:" + fmt
        if impl.get(key) is False:
            stats[key]["not_implemented"] += 1
            continue
        name = r["case"].rsplit(".", 1)[0]
        params = {"fit": case_req(r["case"]), "name": name, "format": fmt.replace("_min", "").replace("_formatted", ""),
                  "options": r["options"]}
        res, err = rpc.call("format_export", params)
        if err is not None and unknown(err) and fmt in ("eft", "eft_min"):
            res, err = rpc.call("eft_export", {"fit": params["fit"], "name": name, "options": r["options"]})
        if err is not None and unknown(err):
            impl[key] = False
            stats[key]["not_implemented"] += 1
            continue
        impl[key] = True
        text = res.get("text") if isinstance(res, dict) else res
        st = stats[key]
        st["total"] += 1
        if "error" in r:
            ok = err is not None
        elif err is not None:
            ok = False
        else:
            ok = text == r["text"]
            if not ok and fmt.startswith("eft") and isinstance(text, str) and \
                    text.replace("\n[Empty Subsystem slot]", "", 1) == r["text"]:
                # known data divergence (as tools/check_eft_export.py): SDE 3569502 gives T3 cruisers
                # maxSubSystems = 5, Pyfa's eve.db 4 -> one extra empty subsystem line is accepted
                ok = True
                st["known_divergence_subsystem_slot"] += 1
            if not ok and fmt.startswith("esi"):
                try:
                    if json.loads(text) == json.loads(r["text"]):
                        st["json_equal_only"] += 1
                except Exception:
                    pass
        st["pass"] += ok
        if not ok:
            fails.append({"kind": key, "case": r["case"], "expected": r.get("text", r.get("error")),
                          "got": text if err is None else err})

    # ---- round-trip imports
    for line in open(os.path.join(EXP, "import.jsonl")):
        r = json.loads(line)
        fmt = r["format"]
        key = "import:" + fmt
        if impl.get(key) is False:
            stats[key]["not_implemented"] += 1
            continue
        res, err = rpc.call("format_import", {"text": r["input"], "format": fmt})
        if err is not None and unknown(err) and fmt == "eft":
            res, err = rpc.call("eft_parse", {"text": r["input"]})
        if err is not None and unknown(err):
            impl[key] = False
            stats[key]["not_implemented"] += 1
            continue
        impl[key] = True
        st = stats[key]
        st["total"] += 1
        sub = "overfit" if r.get("source_overfit") else "legal"
        st["total_" + sub] += 1
        if "error" in r:
            ok, core, extra = err is not None, [], []
        elif err is not None:
            ok, core, extra = False, ["error"], []
        else:
            got, _ = fits_of(res)
            core, extra = diff_fits(r["fits"], got)
            ok = not core
            for k in extra:
                st["soft_diff_" + k] += 1
        st["pass"] += ok
        st["pass_" + sub] += ok
        for k in core:
            st["diff_" + k] += 1
        if not ok:
            fails.append({"kind": key, "case": r["case"], "fields": core, "error": err})

    # ---- edge cases (Pyfa Port.importAuto)
    for line in open(os.path.join(EXP, "edge.jsonl")):
        r = json.loads(line)
        key = "edge"
        text = open(os.path.join(ROOT, "formats", "edge", r["file"]), encoding="utf-8").read()
        res, err = rpc.call("format_import", {"text": text, "format": "auto", "path": r["file"]})
        st = stats[key]
        if err is not None and unknown(err) and "error" not in r:
            # per-file: one unsupported sub-format does not disable the whole edge category
            st["not_implemented"] += 1
            st["total"] += 1
            fails.append({"kind": key, "file": r["file"], "error": err, "not_implemented": True})
            continue
        st["total"] += 1
        if "error" in r:
            ok = err is not None
        elif err is not None:
            ok = False
        elif "fits" in r:
            got, kind = fits_of(res)
            core, _ = diff_fits(r["fits"], got)
            ok = not core and (kind is None or kind == r["kind"])
        else:
            ok = isinstance(res, dict) and res.get("kind") == r["kind"]
        st["pass"] += ok
        if not ok:
            fails.append({"kind": key, "file": r["file"], "error": err})

    lines = ["# Formats scorecard: %s" % a.name, "", "| check | implemented | pass | total | legal-fit pass | notes |",
             "|---|---|---|---|---|---|"]
    for key in sorted(stats):
        st = stats[key]
        im = "no" if st["not_implemented"] and not st["total"] else "yes"
        legal = "%d/%d" % (st["pass_legal"], st["total_legal"]) if st["total_legal"] else ""
        notes = ", ".join("%s %d" % (k, v) for k, v in sorted(st.items())
                          if k.startswith(("diff_", "soft_diff_", "json_equal", "known_")) or (k == "not_implemented" and st["total"]))
        lines.append("| %s | %s | %d | %d | %s | %s |" % (key, im, st["pass"], st["total"] or st["not_implemented"],
                                                         legal, notes))
    md = "\n".join(lines) + "\n"
    open(os.path.join(out, "scorecard.md"), "w").write(md)
    json.dump({k: dict(v) for k, v in stats.items()}, open(os.path.join(out, "scorecard.json"), "w"), indent=1,
              sort_keys=True)
    json.dump(fails[:2000], open(os.path.join(out, "failures.json"), "w"), indent=1)
    print(md)


if __name__ == "__main__":
    main()
