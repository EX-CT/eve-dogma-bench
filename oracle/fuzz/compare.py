#!/usr/bin/env python3
"""Run the Pyfa oracle (bench-1.9.0 oracle/metrics) + engines A and E on fits/*.json; write per-fit diffs.
usage: compare.py FITSDIR OUTDIR [--no-oracle]"""
import json, os, pathlib, subprocess, sys
W = pathlib.Path(__file__).resolve().parent
M19 = W / "m19"  # bench-1.9.0 tools/metrics.py + oracle/pyfa_oracle.py; falls back to this checkout's
if not M19.exists():
    M19 = W.parent.parent
    sys.path.insert(0, str(M19 / "tools")); ORACLE = str(M19 / "oracle/pyfa_oracle.py")
else:
    ORACLE = str(M19 / "pyfa_oracle.py")
sys.path.insert(0, str(M19))
from metrics import from_pyfa, METRICS, extract, close  # noqa
REF = "/workspace/exct-eve/ref"
ENG = {"A": ["/workspace/exct-eve/fz-e/bin/A-e4c42db", "--dataset", "/workspace/exct-eve/data/dataset-3569502.json.gz"],
       "E": ["/workspace/exct-eve/fz-e/bin/E-5867d53", "--dataset", "/workspace/exct-eve/data/dataset-3569502.json.gz"]}
fits, out = pathlib.Path(sys.argv[1]).resolve(), pathlib.Path(sys.argv[2]).resolve()
out.mkdir(parents=True, exist_ok=True)
files = sorted(fits.glob("*.json"))
names = [f.stem for f in files]
if "--no-oracle" not in sys.argv:
    env = dict(os.environ, PYTHONPATH=REF + "/stubs", ORACLE_REPEAT="0", PYFA=REF + "/pyfa")
    with open(out / "oracle.jsonl", "w") as fo:
        for i in range(0, len(files), 25):
            r = subprocess.run([REF + "/pyfa-venv/bin/python", ORACLE, *map(str, files[i:i + 25])],
                               capture_output=True, text=True, cwd=REF + "/pyfa", env=env)
            fo.write("".join(l + "\n" for l in r.stdout.splitlines() if l.startswith("{")))
            if r.returncode:
                print("oracle rc", r.returncode, r.stderr[-500:], file=sys.stderr)
            print("oracle", i + 25, flush=True)
orc = {}
for l in open(out / "oracle.jsonl"):
    j = json.loads(l)
    orc[j["file"][:-5]] = j
res = {}
for e, cmd in ENG.items():
    if not os.path.exists(cmd[0]):
        continue
    for f in files:
        r = subprocess.run(cmd[:1] + ["calc", str(f)] + cmd[1:], capture_output=True, text=True)
        try:
            res.setdefault(e, {})[f.stem] = json.loads(r.stdout)
        except Exception:
            res.setdefault(e, {})[f.stem] = {"error": r.stdout[:300] + r.stderr[:300]}
    with open(out / f"{e}.jsonl", "w") as fo:
        for n in names:
            fo.write(json.dumps({"file": n, "out": res[e][n]}) + "\n")
rep = {}
summary = {"fits": len(names), "oracle_errors": [], "A_diff_fits": 0, "E_diff_fits": 0, "AE_disagree_fits": 0, "values": 0}
for n in names:
    o = orc.get(n)
    if o is None or "error" in o:
        summary["oracle_errors"].append([n, (o or {}).get("error", "missing")]); continue
    want = from_pyfa(o["stats"])
    d = {}
    for k, w in sorted(want.items()):
        if k not in METRICS:
            continue
        summary["values"] += 1
        g = {e: extract(res[e][n], METRICS[k][0]) if "error" not in res[e][n] else "ERR" for e in res}
        if any(not close(g[e], w) for e in g):
            d[k] = {"pyfa": w, **g}
    if d:
        rep[n] = d
        summary["A_diff_fits"] += any(not close(v.get("A"), v["pyfa"]) for v in d.values())
        summary["E_diff_fits"] += any("E" in v and not close(v.get("E"), v["pyfa"]) for v in d.values())
    if "E" in res and "A" in res:
        for k in want:
            if k in METRICS and not close(extract(res["A"][n], METRICS[k][0]), extract(res["E"][n], METRICS[k][0])):
                summary["AE_disagree_fits"] += 1; break
json.dump(rep, open(out / "diffs.json", "w"), indent=1, default=str)
json.dump(summary, open(out / "summary.json", "w"), indent=1)
print(json.dumps(summary)[:2000])
