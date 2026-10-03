#!/usr/bin/env python3
"""Render cap/results/*.json into a markdown table (stdout)."""
import json, pathlib, sys
R = pathlib.Path(__file__).resolve().parent.parent / "results"
names = sys.argv[1:] or sorted(p.stem for p in R.glob("*.json"))
res = {n: json.loads((R / f"{n}.json").read_text()) for n in names}
cats = sorted({c for r in res.values() for c in r["per_category"]})
print("| engine | scored cases | pending (stagger off) | failing scored cases |")
print("|---|---|---|---|")
for n, r in res.items():
    fails = [x["case"] for x in r["rows"] if not x["ok"] and not x.get("pending")]
    print(f"| {n} | **{r['cases_ok']}/{r['cases']}** ({100*r['cases_ok']/r['cases']:.1f} %) | {r['pending_ok']}/{r['pending']} | {', '.join(fails) or '—'} |")
print()
print("| category | " + " | ".join(names) + " |")
print("|---|" + "---|" * len(names))
for c in cats:
    print(f"| {c} | " + " | ".join("{}/{}".format(*res[n]["per_category"].get(c, [0, 0])) for n in names) + " |")
