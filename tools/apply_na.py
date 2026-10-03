#!/usr/bin/env python3
"""Drop a suite's n/a cases (inventory/suites.yaml `na:`) from a graphs-style result: scorecard.json + failures.json.
  python3 tools/apply_na.py --suite mcp-graphs --scorecard S --failures F [--out-scorecard S2 --out-failures F2]
The n/a cases leave `cases` and (if they passed) `cases_fully_correct`; they are listed under `na` with the reason.
Value counts (values_correct/values_total, groups) are recomputed only for the case counts; per-value totals stay as run."""
import argparse, json, os, yaml
HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument("--suite", required=True)
ap.add_argument("--suites", default=os.path.join(HERE, "..", "inventory", "suites.yaml"))
ap.add_argument("--scorecard", required=True)
ap.add_argument("--failures", required=True)
ap.add_argument("--out-scorecard")
ap.add_argument("--out-failures")
a = ap.parse_args()
na = yaml.safe_load(open(a.suites))["suites"][a.suite].get("na") or {}
card, fails = json.load(open(a.scorecard)), json.load(open(a.failures))
failed_na = [c for c in na if c in fails]
card["cases"] -= len(na)
card["cases_fully_correct"] -= len(na) - len(failed_na)
card["na"] = {c: {"reason": r, "result_as_run": "fail" if c in fails else "pass"} for c, r in na.items()}
fails = {k: v for k, v in fails.items() if k not in na}
json.dump(card, open(a.out_scorecard or a.scorecard, "w"), indent=1)
json.dump(fails, open(a.out_failures or a.failures, "w"), indent=1)
print(f"{a.suite}: {card['cases_fully_correct']}/{card['cases']} (n/a {len(na)}: {', '.join(na)})")
