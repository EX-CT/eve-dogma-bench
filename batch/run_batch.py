#!/usr/bin/env python3
"""Score an engine on the batch suite (PROVISIONAL shape, CONTRACT-BATCH.md).

  python3 batch/run_batch.py --cmd ENGINE [--transport rpc|cli] [--name X] [--out results.json] [--self-test] [cases...]

ENGINE is the eve-fit binary (plus args), e.g. "target/release/eve-fit". For every case:
  1. expand the BatchRequest into its fits (semantics.expand);
  2. compute every fit ONE BY ONE with `ENGINE calc` (one process per distinct fit) and the base fit if deltas are on;
  3. build the expected answer from those outputs (semantics.expected: projection, deltas, filter, sort, limit);
  4. send the batch to the engine through adapter.py and compare (semantics.compare): stats must be byte-identical
     to the one-by-one output (after projection), deltas within 1e-6, order / indices / labels / errors exact.
A case passes when there is no mismatch. An engine without batch support fails every case (0 passed), no crash.
--self-test replaces step 4 with a reference batch assembled from `ENGINE batch` (JSONL) outputs: proves the
generator + comparer accept a correct implementation (should be 44/44 with any engine).
Output JSON: {"name","pass","total","cases":{id:{"pass","kind","fits","ops","first":[...]}}} (same as ext/)."""
import argparse, json, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

SUITE = Path(__file__).resolve().parent
sys.path.insert(0, str(SUITE))
import adapter, semantics  # noqa: E402


def calc_one(engine, fit):
    r = subprocess.run(engine.split() + ["calc"], input=json.dumps(fit), capture_output=True, text=True, timeout=120)
    try:
        return json.loads(r.stdout)
    except ValueError:
        return {"error": {"code": "NO_OUTPUT", "message": r.stderr[-200:]}}


def calc_jsonl(engine, fits):
    r = subprocess.run(engine.split() + ["batch"], input="".join(json.dumps(f) + "\n" for f in fits),
                       capture_output=True, text=True, timeout=600)
    return [json.loads(l) for l in r.stdout.splitlines()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cmd", required=True)
    ap.add_argument("--transport", default="rpc", choices=["rpc", "cli"])
    ap.add_argument("--name", default="engine")
    ap.add_argument("--out")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("cases", nargs="*")
    a = ap.parse_args()
    man = json.loads((SUITE / "MANIFEST.json").read_text())
    ids = a.cases or sorted(man)
    reqs = {c: json.loads((SUITE / "cases" / f"{c}.json").read_text()) for c in ids}
    # one-by-one reference outputs (distinct fits computed once)
    todo = {}
    for r in reqs.values():
        for _, f in semantics.expand(r):
            todo.setdefault(json.dumps(f, sort_keys=True), f)
        if "base" in r:
            todo.setdefault(json.dumps(r["base"], sort_keys=True), r["base"])
    t0 = time.time()
    keys = list(todo)
    with ThreadPoolExecutor(a.jobs) as ex:
        outs = list(ex.map(lambda k: calc_one(a.cmd, todo[k]), keys))
    single = dict(zip(keys, outs))
    t_single = time.time() - t0
    res, t_batch = {}, 0.0
    for c in ids:
        r = reqs[c]
        fits = semantics.expand(r)
        singles = [single[json.dumps(f, sort_keys=True)] for _, f in fits]
        base = single[json.dumps(r["base"], sort_keys=True)] if "base" in r else None
        exp = semantics.expected(r, singles, base)
        t1 = time.time()
        if a.self_test:
            got = semantics.expected(r, calc_jsonl(a.cmd, [f for _, f in fits]), calc_jsonl(a.cmd, [r["base"]])[0] if "base" in r else None)
        else:
            try:
                got = adapter.call(a.cmd, r, a.transport)
            except Exception as e:  # noqa: BLE001
                got = {"error": {"code": "ADAPTER_EXCEPTION", "message": repr(e)[:200]}}
        t_batch += time.time() - t1
        bad = semantics.compare(exp, got)
        m = man[c]
        res[c] = {"pass": not bad, "kind": m["kind"], "fits": m["fits"], "ops": m["ops"], "first": bad[:5]}
    np = sum(v["pass"] for v in res.values())
    by = {}
    for v in res.values():
        p = by.setdefault(v["kind"], [0, 0])
        p[0] += v["pass"]; p[1] += 1
    out = {"name": a.name, "pass": np, "total": len(res), "self_test": a.self_test, "transport": a.transport,
           "one_by_one_s": round(t_single, 2), "batch_s": round(t_batch, 2), "cases": res}
    if a.out:
        Path(a.out).write_text(json.dumps(out, indent=1) + "\n")
    print(f"{a.name}: batch suite {np}/{len(res)} pass" + (" (SELF-TEST: reference batch, not the engine)" if a.self_test else "")
          + "; " + ", ".join(f"{k} {p}/{t}" for k, (p, t) in sorted(by.items())))
    fails = [c for c, v in res.items() if not v["pass"]]
    if fails:
        print("  first failure:", fails[0], res[fails[0]]["first"][:2])


if __name__ == "__main__":
    main()
