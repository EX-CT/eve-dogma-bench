#!/usr/bin/env python3
"""No-regression gate: compare a new run of every bench suite (and the docs/19 inventory) against a committed baseline.

  python3 tools/check_no_regress.py --baseline baselines/f.json --run-dir OUT [--inventory 19-pyfa-feature-inventory.csv]
  python3 tools/check_no_regress.py ... --update          # raise the baseline (only if the check passes)
  python3 tools/check_no_regress.py ... --only core,ext   # check just these suites (others in the baseline skipped)

OUT is what tools/run_all_suites.sh writes (core/ graphs/ mutated/ formats/ result dirs, ext.json, ext_rpc.json, batch.json, effects.json,
cap.json, sde.json, price_inject.json, price_rule.json (only with PRICE_RULE_CMD; not in the engine baseline), roots.json with the suite checkouts used to list case ids). Exit 0 = no regression, 1 = regression,
2 = usage / missing input. See baselines/README.md for the rules."""
import argparse, csv, json, os, sys, time
from pathlib import Path

SUITES = ("core", "ext", "ext_rpc", "batch", "effects", "graphs", "cap", "mutated", "formats", "sde", "price_inject", "price_rule")
CASE_GLOBS = {"core": ("cases", "expected"), "mutated": ("mutated/cases", "mutated/expected"),
              "graphs": ("graphs/cases", "graphs/expected")}


def die(msg):
    print("check_no_regress: " + msg, file=sys.stderr)
    sys.exit(2)


def case_ids(root, kind):
    c, e = CASE_GLOBS[kind]
    return {p.stem for p in (Path(root) / c).glob("*.json") if (Path(root) / e / p.name).exists()}


def collect_suite(name, run_dir, roots):
    """-> {"passed": n, "total": n, "passed_ids": [...]} or for formats {"passed", "total", "failing_ids"}"""
    rd = Path(run_dir)
    if name in ("core", "graphs", "mutated"):
        d = rd / name
        if not (d / "scorecard.json").exists():
            return None
        card, fails = json.loads((d / "scorecard.json").read_text()), json.loads((d / "failures.json").read_text())
        ids = case_ids(roots[name], name)
        if len(ids) != card["cases"]:
            die(f"{name}: {len(ids)} case ids under {roots[name]} but scorecard says {card['cases']} cases")
        passed = sorted(ids - set(fails))
        if len(passed) != card["cases_fully_correct"]:
            die(f"{name}: {len(passed)} passing ids but scorecard says {card['cases_fully_correct']}")
        return {"passed": len(passed), "total": len(ids), "passed_ids": passed}
    if name in ("ext", "ext_rpc", "batch", "effects", "sde", "price_inject", "price_rule"):
        p = rd / f"{name}.json"
        if not p.exists():
            return None
        d = json.loads(p.read_text())
        cases = {k: v for k, v in d["cases"].items() if not v.get("pending")}   # d22: pending = needs an input (SDE_PACK)
        passed = sorted(k for k, v in cases.items() if v.get("pass"))
        return {"passed": len(passed), "total": len(cases), "passed_ids": passed}
    if name == "cap":
        p = rd / "cap.json"
        if not p.exists():
            return None
        rows = [r for r in json.loads(p.read_text())["rows"] if not r.get("pending")]
        passed = sorted(r["case"] for r in rows if r["ok"])
        return {"passed": len(passed), "total": len(rows), "passed_ids": passed}
    if name == "formats":
        d = rd / "formats"
        if not (d / "scorecard.json").exists():
            return None
        card = json.loads((d / "scorecard.json").read_text())
        fails = sorted({f["id"] for f in json.loads((d / "failures.json").read_text()) if f.get("scored", True)})
        return {"passed": card["rows_passed"], "total": card["rows"], "failing_ids": fails}
    raise KeyError(name)


def collect_inventory(path):
    """docs/19 CSV (or YAML) -> {column: {"have": n, "ids": [...]}}; parity items only (extra: true not counted,
    same as the docs/19 counts table)."""
    p = Path(path)
    if p.suffix in (".yaml", ".yml"):
        import yaml
        doc = yaml.safe_load(p.read_text())
        items = next(v for v in doc.values() if isinstance(v, list) and v and isinstance(v[0], dict) and "id" in v[0])
        cols = list(doc["columns"])
    else:
        items = list(csv.DictReader(p.open()))
        cols = [c for c in items[0] if c + "_evidence" in items[0]]
    items = [i for i in items if str(i.get("extra") or "").lower() not in ("yes", "true")]
    return {c: {"have": len(ids), "ids": ids} for c in cols
            for ids in [sorted(i["id"] for i in items if i.get(c) == "have")]}


def compare(base, run, only):
    errs, warns = [], []
    for name, b in base.get("suites", {}).items():
        if only and name not in only:
            continue
        r = run["suites"].get(name)
        if r is None:
            errs.append(f"{name}: no result in this run")
            continue
        if r["passed"] < b["passed"]:
            errs.append(f"{name}: passed {r['passed']}/{r['total']} < baseline {b['passed']}/{b['total']}")
        if "passed_ids" in b:
            rs = set(r["passed_ids"])
            lost = [i for i in b["passed_ids"] if i not in rs]
            if lost:
                errs.append(f"{name}: {len(lost)} previously passing case(s) no longer pass: {', '.join(lost[:20])}"
                            + (" ..." if len(lost) > 20 else ""))
        else:   # formats: rows have no stable id list; a new failing scored row is a regression unless rows were added
            new = sorted(set(r["failing_ids"]) - set(b["failing_ids"]))
            if new:
                (errs if r["total"] <= b["total"] else warns).append(
                    f"{name}: {len(new)} newly failing scored row(s)"
                    + ("" if r["total"] <= b["total"] else f" ({r['total'] - b['total']} rows were added; check they are new)")
                    + ": " + ", ".join(new[:20]))
        if r["passed"] > b["passed"]:
            warns.append(f"{name}: improved {b['passed']} -> {r['passed']} (run --update to raise the baseline)")
    if "inventory" in run:
        for col, b in base.get("inventory", {}).get("columns", {}).items():
            r = run["inventory"].get(col)
            if r is None:
                errs.append(f"inventory {col}: column missing")
                continue
            lost = sorted(set(b["ids"]) - set(r["ids"]))
            if r["have"] < b["have"]:
                errs.append(f"inventory {col}: have {r['have']} < baseline {b['have']}")
            if lost:
                errs.append(f"inventory {col}: no longer have: {', '.join(lost)}")
            if r["have"] > b["have"]:
                warns.append(f"inventory {col}: have {b['have']} -> {r['have']}")
    return errs, warns


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--run-dir")
    ap.add_argument("--inventory", help="docs/19 CSV or YAML (eve-fit-docs)")
    ap.add_argument("--only", help="comma-separated suites to check (default: all in the baseline)")
    ap.add_argument("--update", action="store_true", help="raise the baseline to this run (refused on regression)")
    ap.add_argument("--init", action="store_true", help="write a new baseline from this run (no comparison)")
    ap.add_argument("--note", default="", help="text stored in the baseline on --init/--update")
    a = ap.parse_args()
    only = set(a.only.split(",")) if a.only else None
    run = {"suites": {}}
    if a.run_dir:
        rj = Path(a.run_dir) / "roots.json"
        roots = json.loads(rj.read_text())["roots"] if rj.exists() else {}
        run["refs"] = json.loads(rj.read_text()).get("refs", {}) if rj.exists() else {}
        for s in SUITES:
            if only and s not in only:
                continue
            if s in CASE_GLOBS and s not in roots:
                die(f"{s}: roots.json missing (needed to list case ids)")
            r = collect_suite(s, a.run_dir, roots)
            if r is not None:
                run["suites"][s] = r
    if a.inventory:
        run["inventory"] = collect_inventory(a.inventory)
    if not run["suites"] and "inventory" not in run:
        die("nothing to check (give --run-dir and/or --inventory)")
    bp = Path(a.baseline)
    stamp = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    if a.init:
        if bp.exists():
            die(f"{bp} exists; use --update")
        out = {"schema": "no-regress/1", "note": a.note, "created": stamp, "updated": stamp,
               "suites": {k: dict(v, ref=run.get("refs", {}).get(k)) for k, v in run["suites"].items()}}
        if "inventory" in run:
            out["inventory"] = {"source": os.path.basename(a.inventory), "columns": run["inventory"]}
        bp.write_text(json.dumps(out, indent=1) + "\n")
        print(f"wrote {bp}")
        return
    base = json.loads(bp.read_text())
    errs, warns = compare(base, run, only)
    lines = []
    for s, r in run["suites"].items():
        b = base["suites"].get(s)
        lines.append(f"{s}: {r['passed']}/{r['total']}" + (f" (baseline {b['passed']}/{b['total']})" if b else " (not in baseline)"))
    for c, r in run.get("inventory", {}).items():
        b = base.get("inventory", {}).get("columns", {}).get(c)
        lines.append(f"inventory {c}: have {r['have']}" + (f" (baseline {b['have']})" if b else ""))
    print("\n".join(lines))
    for w in warns:
        print("note: " + w)
    for e in errs:
        print("REGRESSION: " + e)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as f:
            f.write(f"### no-regress gate: {'❌ ' + str(len(errs)) + ' regression(s)' if errs else '✅ no regression'}\n")
            f.write("".join(f"- {l}\n" for l in lines + ["REGRESSION: " + e for e in errs]))
    if errs:
        if a.update:
            print("--update refused: the baseline can only go up")
        sys.exit(1)
    if a.update:
        for s, r in run["suites"].items():
            base["suites"][s] = dict(r, ref=run.get("refs", {}).get(s))
        if "inventory" in run:
            base.setdefault("inventory", {})["columns"] = {**base.get("inventory", {}).get("columns", {}), **run["inventory"]}
            base["inventory"]["source"] = os.path.basename(a.inventory)
        base["updated"] = stamp
        if a.note:
            base["note"] = a.note
        bp.write_text(json.dumps(base, indent=1) + "\n")
        print(f"baseline {bp} updated")
    print("no regression")


if __name__ == "__main__":
    main()
