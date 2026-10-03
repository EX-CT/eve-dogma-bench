#!/usr/bin/env python3
"""Score engines on the capacitor suite (CONTRACT-CAP 0.1).

  python3 cap/run_cap.py --batch-cmd "<engine> --dataset D batch" --name H [--cwd DIR]
  python3 cap/run_cap.py --only A,H [--work-root /path/to/bench/checkout]   # use variants.yaml + already built work/<X>

A case passes when every scored metric of cap/expected/<case>.json is within tolerance (cap/metrics.py).
Writes cap/results/<name>.json and prints a summary (cases passed, per-metric, per-category)."""
import argparse, json, pathlib, subprocess, sys, time
import yaml
ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from metrics import SCORED, REPORT_ONLY, ptr, close  # noqa: E402


def load():
    idx = {r["case"]: r for r in json.loads((ROOT / "index.json").read_text())}
    cases = []
    for p in sorted((ROOT / "cases").glob("*.json")):
        e = ROOT / "expected" / p.name
        if e.exists():
            cases.append((p.stem, json.loads(p.read_text()), json.loads(e.read_text()), idx.get(p.stem, {}).get("category", "?")))
    return cases


def score(name, batch_cmd, cwd, cases, timeout=600):
    inp = "".join(json.dumps(c[1]) + "\n" for c in cases)
    t0 = time.time()
    r = subprocess.run(batch_cmd, shell=True, cwd=cwd, input=inp, capture_output=True, text=True, timeout=timeout)
    wall = time.time() - t0
    outs = r.stdout.splitlines()
    rows, per_metric, per_cat, rep = [], {}, {}, {}
    for i, (cname, req, exp, cat) in enumerate(cases):
        try:
            got = json.loads(outs[i])
        except (IndexError, json.JSONDecodeError):
            got = {}
        fails = {}
        for m, want in exp["values"].items():
            g = ptr(got, SCORED[m])
            ok = close(m, g, want)
            pm = per_metric.setdefault(m, [0, 0])
            pm[0] += ok
            pm[1] += 1
            if not ok:
                fails[m] = {"got": g, "want": want}
        for m, want in exp.get("report_only", {}).items():
            g = ptr(got, REPORT_ONLY[m])
            pr = rep.setdefault(m, [0, 0])
            pr[0] += close(m, g, want)
            pr[1] += 1
        ok = not fails and "error" not in got
        pc = per_cat.setdefault(cat, [0, 0])
        pc[0] += ok
        pc[1] += 1
        rows.append({"case": cname, "category": cat, "ok": ok, "fails": fails, **({"error": got["error"]} if "error" in got else {})})
    res = {"name": name, "cases": len(cases), "cases_ok": sum(r["ok"] for r in rows), "per_metric": per_metric,
           "per_category": per_cat, "report_only": rep, "exit": r.returncode, "wall_s": round(wall, 3), "rows": rows}
    out = ROOT / "results"
    out.mkdir(exist_ok=True)
    (out / f"{name}.json").write_text(json.dumps(res, indent=1) + "\n")
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch-cmd")
    ap.add_argument("--name", default="engine")
    ap.add_argument("--cwd", default=".")
    ap.add_argument("--only")
    ap.add_argument("--work-root", default=str(ROOT.parent))
    ap.add_argument("--variants", default=str(ROOT.parent / "variants.yaml"))
    a = ap.parse_args()
    cases = load()
    jobs = []
    if a.batch_cmd:
        jobs.append((a.name, a.batch_cmd, a.cwd))
    else:
        conf = yaml.safe_load(open(a.variants))
        only = set(a.only.split(",")) if a.only else None
        for v in conf["variants"]:
            if only and v["name"] not in only:
                continue
            d = pathlib.Path(v["path"]) if "path" in v else pathlib.Path(a.work_root) / "work" / v["name"] / v.get("git", {}).get("subdir", "")
            mf = d / v.get("manifest", "bench.yaml")
            if "batch_cmd" not in v and mf.exists():
                v = {**v, **yaml.safe_load(open(mf))}
            if not v.get("batch_cmd"):
                print(f"{v['name']}: no batch_cmd / not built (skipped)")
                continue
            jobs.append((v["name"], v["batch_cmd"].format(dataset=conf["dataset"], bench=a.work_root, dir=d), str(d)))
    for name, cmd, cwd in jobs:
        try:
            r = score(name, cmd, cwd, cases)
        except Exception as e:  # noqa: BLE001
            print(f"{name}: run failed {e!r}")
            continue
        pm = " ".join(f"{m} {v[0]}/{v[1]}" for m, v in r["per_metric"].items())
        print(f"{name}: cases {r['cases_ok']}/{r['cases']} | {pm} | exit {r['exit']} {r['wall_s']}s")


if __name__ == "__main__":
    main()
