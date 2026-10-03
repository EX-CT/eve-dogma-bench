#!/usr/bin/env python3
"""Score a variant against the FORMATS contract (formats/CONTRACT-FORMATS.md, revision 0.1, DRAFT).

usage:
  python3 tools/evaluate_formats.py --rpc "<variant> serve-stdio" --name F [--cwd DIR] [--out DIR] [--only CATS]
  python3 tools/evaluate_formats.py --batch-cmd "<variant> format-batch" --name F

Transports (CONTRACT-FORMATS section 2):
  --rpc        JSONL RPC as in the base contract: {"id","method","params"} -> {"id","result"} per line.
  --batch-cmd  one process, all requests on stdin ({"method","params"} per line), one response per line, in order.
Methods: format_export {fit, name, format, options} -> {"text"} ; format_import {text, format, path?} ->
{"kind","fits"} | {"kind","items"} ; errors {"error": {"code","message"}}.

Rows (all expectations are Pyfa output, see formats/README.md):
  export:<fmt>       formats/expected/export.jsonl      326 bench fits x 10 export variants
  import:<fmt>       formats/expected/import.jsonl      Pyfa's import of its own export (eft, dna, esi, xml)
  edge_export:<fmt>  formats/expected/edge_export.jsonl hand-written export fits (+ their round trips as import)
  edge:<category>    formats/expected/edge.jsonl        hand-written / malformed inputs, auto-detect + forced format

Scoring (CONTRACT-FORMATS section 7): a row passes or fails. Error rows are scored on reject-vs-accept agreement
with Pyfa only; codes are reported ("code ok"), not scored. Rows marked "scored": false (Pyfa crashes, merged
multi-fit EFT pastes, legacy rename) are report-only. Score = mean of the four group pass rates (export,
import, edge_export, edge; 25 % each, per row within a group); total scored rows are reported too. Gate = 100 %
of scored rows. A not-implemented format counts as failed and is marked.
Results: results/formats/<name>/{scorecard.md, scorecard.json, failures.json}.
"""
import argparse, collections, json, os, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXP = os.path.join(ROOT, "formats", "expected")
CONTRACT = "CONTRACT-FORMATS 0.1 (rulings 2026-10-03)"
NOT_IMPL = ("UNKNOWN_METHOD", "UNSUPPORTED_FORMAT", "NOT_IMPLEMENTED")


# ---------------------------------------------------------------- transport
class Rpc:
    def __init__(self, cmd, cwd):
        self.p = subprocess.Popen(cmd, shell=True, cwd=cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL, text=True, bufsize=1, encoding="utf-8")
        self.n = 0

    def run(self, reqs):
        out = []
        for method, params in reqs:
            self.n += 1
            self.p.stdin.write(json.dumps({"id": self.n, "method": method, "params": params}) + "\n")
            self.p.stdin.flush()
            line = self.p.stdout.readline()
            if not line:
                raise RuntimeError("variant closed the RPC pipe")
            r = json.loads(line)
            out.append(r["result"] if "result" in r else {"error": r.get("error", {"code": "NO_RESULT"})})
        return out


class Batch:
    def __init__(self, cmd, cwd):
        self.cmd, self.cwd = cmd, cwd

    def run(self, reqs):
        inp = "".join(json.dumps({"method": m, "params": p}) + "\n" for m, p in reqs)
        r = subprocess.run(self.cmd, shell=True, cwd=self.cwd, input=inp, capture_output=True, text=True,
                           encoding="utf-8")
        out = []
        for line in r.stdout.splitlines():
            try:
                v = json.loads(line)
            except ValueError:
                v = {"error": {"code": "BAD_OUTPUT"}}
            out.append(v.get("result", v) if isinstance(v, dict) else v)
        return out + [{"error": {"code": "NO_RESULT"}}] * (len(reqs) - len(out))


def split(res):
    """-> (result, error dict or None)"""
    if isinstance(res, dict) and isinstance(res.get("error"), dict) and set(res) <= {"error", "kind"}:
        return None, res["error"]
    return res, None


def not_impl(err, fmt):
    return err is not None and str(err.get("code", "")).upper() in NOT_IMPL and fmt != "auto"


# ---------------------------------------------------------------- normalisation (section 5)
def _tid(x):
    return x if isinstance(x, int) else (x or {}).get("type_id")


def _num(v):
    return round(float(v), 6)


def mut_key(mu):
    if not mu:
        return None
    return (mu.get("base_type_id"), mu.get("mutaplasmid_type_id"),
            tuple(sorted((str(k), _num(v)) for k, v in (mu.get("attributes") or {}).items())))


def canon(fit):
    racks = collections.defaultdict(list)
    for m in fit.get("modules") or []:
        racks[m.get("slot")].append((m.get("type_id"), m.get("state"), m.get("charge_type_id"), mut_key(m.get("mutation"))))
    q = lambda xs: sorted(((_tid(x), x.get("quantity", x.get("amount", 1))) for x in xs or []), key=str)
    ship = fit.get("ship") or {}
    return {
        "ship": ship.get("type_id"),
        "mode": ship.get("mode_type_id"),
        "modules": dict(sorted(racks.items(), key=lambda kv: str(kv[0]))),
        "drones": q(fit.get("drones")),
        "fighters": q(fit.get("fighters")),
        "implants": sorted(_tid(i) for i in fit.get("implants") or []),
        "boosters": sorted(_tid(b) for b in fit.get("boosters") or []),
        "cargo": q(fit.get("cargo")),
        "name": fit.get("name"),
        # informational
        "drones_active": sorted(((_tid(d), d.get("active")) for d in fit.get("drones") or []), key=str),
        "notes": fit.get("notes"),
    }


SCORED = ("ship", "mode", "modules", "drones", "fighters", "implants", "boosters", "cargo", "name")
INFO = ("drones_active", "notes")


def diff_fits(exp, got):
    """-> (scored differences, informational differences)"""
    if not isinstance(got, list):
        return ["fits_not_a_list"], []
    if len(exp) != len(got):
        return ["fit_count"], []
    core, info = [], []
    for e, g in zip(exp, got):
        if not isinstance(g, dict):
            core.append("fit_not_an_object")
            continue
        ce, cg = canon(e), canon(g)
        for k in SCORED:
            if ce[k] == cg[k]:
                continue
            if k == "mode" and cg[k] is None:
                continue  # null mode = the hull's first mode (base contract); Pyfa sets it explicitly
            core.append(k)
        info += [k for k in INFO if ce[k] != cg[k] and cg[k] is not None]
    return core, info


def items_key(items):
    return [(_tid(i), i.get("amount", i.get("quantity", 1)), mut_key(i.get("mutation"))) for i in items or []]


def judge_import(exp, res, err):
    """-> (ok, reasons, info, code_ok)"""
    if "error" in exp:
        if err is None:
            return False, ["expected_error"], [], False
        return True, [], [], str(err.get("code")) == exp["error"]["code"]
    if err is not None:
        return False, ["error:%s" % err.get("code")], [], None
    if not isinstance(res, dict):
        res = {"fits": res}
    reasons = []
    if exp.get("kind") is not None and res.get("kind") != exp["kind"]:
        reasons.append("kind")
    if "items" in exp:
        if items_key(res.get("items")) != items_key(exp["items"]):
            reasons.append("items")
        return not reasons, reasons, [], None
    core, info = diff_fits(exp["fits"], res.get("fits"))
    reasons += core
    return not reasons, reasons, info, None


def subsystem_divergence(text, want):
    # dataset note (section 5.1): SDE 3569502 gives T3 cruisers maxSubSystems 5, Pyfa's db 4
    return isinstance(text, str) and text.replace("\n[Empty Subsystem slot]", "", 1) == want


def judge_export(exp, res, err, fmt):
    if "error" in exp:
        if err is None:
            return False, ["expected_error"], [], False
        code = exp["error"]["code"] if isinstance(exp["error"], dict) else "EXPORT_ERROR"
        return True, [], [], str(err.get("code")) == code
    if err is not None:
        return False, ["error:%s" % err.get("code")], [], None
    text = res.get("text") if isinstance(res, dict) else res
    if text == exp["text"]:
        return True, [], [], None
    if fmt.startswith("eft") and subsystem_divergence(text, exp["text"]):
        return True, [], ["known_divergence_subsystem_slot"], None
    info = []
    if fmt.startswith("esi"):
        try:
            if json.loads(text) == json.loads(exp["text"]):
                info.append("json_equal_only")
        except Exception:
            pass
    return False, ["text"], info, None


# ---------------------------------------------------------------- rows
def load_rows(only):
    rows = []
    cases = {}

    def case(c):
        if c not in cases:
            p = os.path.join(ROOT, "cases", c) if not c.startswith("edge_export/") else os.path.join(ROOT, "formats", c)
            cases[c] = json.load(open(p, encoding="utf-8"))
        return cases[c]

    def base_fmt(f):
        return f.replace("_min", "").replace("_formatted", "")

    for line in open(os.path.join(EXP, "export.jsonl"), encoding="utf-8"):
        r = json.loads(line)
        cat = "export:" + r["format"]
        rows.append(dict(cat=cat, id="%s@%s" % (r["case"], cat), kind="export", fmt=r["format"], exp=r,
                         req=("format_export", {"fit": case(r["case"]), "name": r["case"].rsplit(".", 1)[0],
                                                "format": base_fmt(r["format"]), "options": r["options"]})))
    for line in open(os.path.join(EXP, "import.jsonl"), encoding="utf-8"):
        r = json.loads(line)
        cat = "import:" + r["format"]
        if "error" in r and not isinstance(r["error"], dict):
            r["error"] = {"code": "IMPORT_ERROR", "pyfa": r["error"]}
        rows.append(dict(cat=cat, id="%s@%s" % (r["case"], cat), kind="import", fmt=r["format"], exp=r,
                         legal=not r.get("source_overfit"),
                         req=("format_import", {"text": r["input"], "format": r["format"]})))
    for line in open(os.path.join(EXP, "edge_export.jsonl"), encoding="utf-8"):
        r = json.loads(line)
        src = case(r["case"])
        if r["direction"] == "export":
            rows.append(dict(cat="edge_export:" + r["format"], id=r["id"], kind="export", fmt=r["format"], exp=r,
                             req=("format_export", {"fit": src["fit"], "name": src["name"],
                                                    "format": base_fmt(r["format"]), "options": r["options"]})))
        else:
            rows.append(dict(cat="edge_export:import_" + r["format"], id=r["id"], kind="import", fmt=r["format"],
                             exp=r, req=("format_import", {"text": r["input"], "format": r["format"]})))
    for line in open(os.path.join(EXP, "edge.jsonl"), encoding="utf-8"):
        r = json.loads(line)
        with open(os.path.join(ROOT, "formats", "edge", r["file"]), encoding="utf-8", newline="") as fd:
            text = fd.read()
        p = {"text": text, "format": r["format"]}
        if r.get("path"):
            p["path"] = r["path"]
        rows.append(dict(cat="edge:" + r["category"], id=r["id"], kind="import", fmt=r["format"], exp=r,
                         req=("format_import", p)))
    if only:
        rows = [x for x in rows if any(x["cat"].startswith(o) for o in only.split(","))]
    return rows


def group(cat):
    return cat.split(":")[0]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--rpc")
    g.add_argument("--batch-cmd")
    ap.add_argument("--name", default="variant")
    ap.add_argument("--cwd")
    ap.add_argument("--out")
    ap.add_argument("--only", help="comma-separated category prefixes, e.g. edge:,import:eft")
    a = ap.parse_args()
    rows = load_rows(a.only)
    tr = Rpc(a.rpc, a.cwd) if a.rpc else Batch(a.batch_cmd, a.cwd)
    t0 = time.time()
    results = tr.run([r["req"] for r in rows])
    wall = time.time() - t0

    st = collections.defaultdict(collections.Counter)
    fails = []
    for row, res in zip(rows, results):
        res, err = split(res)
        scored = row["exp"].get("scored", True)
        c = st[row["cat"]]
        if not scored:
            ok = (err is not None) == ("error" in row["exp"]) if row["kind"] == "import" and "error" in row["exp"] else None
            if ok is None:
                ok = judge_import(row["exp"], res, err)[0] if row["kind"] == "import" else judge_export(row["exp"], res, err, row["fmt"])[0]
            c["unscored_rows"] += 1
            c["unscored_agree"] += bool(ok)
            fails.append({"id": row["id"], "category": row["cat"], "scored": False, "agrees_with_pyfa": bool(ok),
                          "reason": row["exp"].get("unscored_reason")}) if not ok else None
            continue
        c["total"] += 1
        if not_impl(err, row["fmt"]):
            c["not_implemented"] += 1
            fails.append({"id": row["id"], "category": row["cat"], "reasons": ["not_implemented"], "error": err})
            continue
        if row["kind"] == "export":
            ok, reasons, info, code_ok = judge_export(row["exp"], res, err, row["fmt"])
        else:
            ok, reasons, info, code_ok = judge_import(row["exp"], res, err)
        c["pass"] += ok
        if "legal" in row:
            c["legal_total"] += row["legal"]
            c["legal_pass"] += ok and row["legal"]
        if code_ok is not None:
            c["error_rows"] += 1
            c["code_ok"] += bool(code_ok)
        for k in info:
            c["info_" + k] += 1
        for k in reasons:
            c["diff_" + k.split(":")[0]] += 1
        if not ok:
            fails.append({"id": row["id"], "category": row["cat"], "reasons": reasons,
                          "error": err, "expected_error": row["exp"].get("error")})

    groups = collections.defaultdict(collections.Counter)
    for cat, c in st.items():
        groups[group(cat)]["total"] += c["total"]
        groups[group(cat)]["unscored"] += c["unscored_rows"]
        groups[group(cat)]["pass"] += c["pass"]
    tot = sum(c["total"] for c in st.values())
    ok = sum(c["pass"] for c in st.values())
    rates = [g["pass"] / g["total"] for g in groups.values() if g["total"]]
    weighted = 100.0 * sum(rates) / len(rates) if rates else 0.0
    lines = ["# Formats scorecard: %s" % a.name, "",
             "- contract: %s (DRAFT)" % CONTRACT,
             "- **score (4 groups x 25 %%): %.2f %%**" % weighted,
             "- scored rows passed: **%d/%d** (%.2f %%)%s" % (ok, tot, 100.0 * ok / max(tot, 1),
                                                              " - gate PASSED" if ok == tot else " - gate not met"),
             "- error codes matching (informational): %d/%d" % (sum(c["code_ok"] for c in st.values()),
                                                                sum(c["error_rows"] for c in st.values())),
             "- report-only rows (not scored) agreeing with Pyfa: %d/%d" % (
                 sum(c["unscored_agree"] for c in st.values()), sum(c["unscored_rows"] for c in st.values())),
             "- wall time: %.2f s" % wall, "",
             "| group | weight | pass | scored rows | % | report-only rows |", "|---|---|---|---|---|---|"]
    for gname in ("export", "import", "edge_export", "edge"):
        if gname in groups:
            gg = groups[gname]
            lines.append("| %s | 25 %% | %d | %d | %.2f | %d |" % (gname, gg["pass"], gg["total"],
                                                               100.0 * gg["pass"] / max(gg["total"], 1), gg["unscored"]))
    lines += ["", "| category | pass | total | legal-fit pass | error code ok | notes |", "|---|---|---|---|---|---|"]
    for cat in sorted(st):
        c = st[cat]
        legal = "%d/%d" % (c["legal_pass"], c["legal_total"]) if c["legal_total"] else ""
        code = "%d/%d" % (c["code_ok"], c["error_rows"]) if c["error_rows"] else ""
        notes = ", ".join("%s %d" % (k, v) for k, v in sorted(c.items())
                          if k.startswith(("diff_", "info_", "unscored")) or k == "not_implemented")
        lines.append("| %s | %d | %d | %s | %s | %s |" % (cat, c["pass"], c["total"], legal, code, notes))
    md = "\n".join(lines) + "\n"
    out = a.out or os.path.join(ROOT, "results", "formats", a.name)
    os.makedirs(out, exist_ok=True)
    open(os.path.join(out, "scorecard.md"), "w").write(md)
    json.dump({"variant": a.name, "contract": CONTRACT, "rows": tot, "rows_passed": ok, "score_pct": round(weighted, 4),
               "gate": ok == tot, "wall_s": round(wall, 3),
               "groups": {k: dict(v) for k, v in groups.items()},
               "categories": {k: dict(v) for k, v in sorted(st.items())}},
              open(os.path.join(out, "scorecard.json"), "w"), indent=1, sort_keys=True)
    json.dump(fails, open(os.path.join(out, "failures.json"), "w"), indent=1, ensure_ascii=False)
    print(md)
    return 0 if ok == tot else 1


if __name__ == "__main__":
    sys.exit(main())
