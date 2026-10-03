#!/usr/bin/env python3
"""Score an engine on the pending (NOT released, not part of 0.2 scoring) 0.3 probes in graphs/pending/probes-0.3.jsonl.

  python3 graphs/pending/check_pending.py --batch-cmd "<engine> graph-batch --dataset D" [--cwd DIR] [--file F.jsonl]

--file also accepts G2's testdata/oracle-probes.jsonl (same {probe, request, expected} rows).
Tolerance as in run_graphs.py; `*_charge_type_id` series are not scored."""
import argparse, collections, json, pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from metrics import close  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--batch-cmd", required=True)
ap.add_argument("--cwd")
ap.add_argument("--file", default=str(ROOT / "graphs/pending/probes-0.3.jsonl"))
ap.add_argument("-v", action="store_true")
a = ap.parse_args()
rows = [json.loads(l) for l in open(a.file)]
r = subprocess.run(a.batch_cmd, shell=True, cwd=a.cwd, input="".join(json.dumps(x["request"]) + "\n" for x in rows),
                   capture_output=True, text=True)
outs = []
for l in r.stdout.splitlines():
    try:
        outs.append(json.loads(l))
    except ValueError:
        outs.append(None)
by = collections.defaultdict(lambda: [0, 0])
for row, got in zip(rows, outs + [None] * (len(rows) - len(outs))):
    g = by[row.get("item", row["request"]["graph"])]
    series = (got or {}).get("series") or {}
    for k, want in row["expected"]["series"].items():
        if k.endswith("_charge_type_id"):
            continue
        have = series.get(k) or []
        for i, w in enumerate(want):
            v = have[i] if i < len(have) else "<missing>"
            ok = v != "<missing>" and close(v, w)
            g[1] += 1
            g[0] += ok
            if not ok and a.v:
                print(f"  {row['probe']} {k}@{row['expected']['x'][i]}: got {v} want {w}")
tot = [sum(v[0] for v in by.values()), sum(v[1] for v in by.values())]
for k, (ok, n) in sorted(by.items()):
    print(f"{k:12s} {ok}/{n}")
print(f"{'total':12s} {tot[0]}/{tot[1]}  ({len(rows)} probes)")
