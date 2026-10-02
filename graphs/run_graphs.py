#!/usr/bin/env python3
"""Graph scorer (bench round 2, draft): scores any engine implementing graphs/CONTRACT-GRAPHS.md against the Pyfa
graph oracle (graphs/expected/, produced by graphs/tools/make_graph_expected.py).

  python3 graphs/run_graphs.py --name X --batch-cmd "<engine> graph-batch --dataset D"   # JSONL in -> JSONL out
  python3 graphs/run_graphs.py --name X --cmd "<engine> graph --dataset D"               # one request per process
  python3 graphs/run_graphs.py --name X --rpc-cmd "<engine> serve-stdio --dataset D"     # RPC method "graph"
  python3 graphs/run_graphs.py --self-test                                               # expected vs itself

A sample value is correct when |got - want| <= max(1e-3, 1e-4 * |want|) (the corpus tolerance, tools/metrics.py),
or both are null. Series ending in `_charge_type_id` (application_profile) are informational: Pyfa breaks DPS ties
between equal-stat faction charges by set iteration order, so the id is not well defined; they are reported, not scored.
Writes results/graphs-<name>/scorecard.{json,md} and failures.json."""
import argparse, json, pathlib, subprocess, sys, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from metrics import close  # noqa: E402

INFO_SUFFIX = "_charge_type_id"


def load():
    out = []
    for p in sorted((ROOT / "graphs/cases").glob("*.json")):
        e = ROOT / "graphs/expected" / p.name
        if e.exists():
            out.append((p.stem, json.loads(p.read_text()), json.loads(e.read_text())))
    return out


def run_batch(cmd, reqs, cwd, timeout):
    data = "".join(json.dumps(r) + "\n" for r in reqs)
    t0 = time.perf_counter()
    r = subprocess.run(cmd, shell=True, cwd=cwd, input=data, capture_output=True, text=True, timeout=timeout)
    dt = time.perf_counter() - t0
    outs = []
    for l in r.stdout.splitlines():
        try:
            outs.append(json.loads(l))
        except ValueError:
            outs.append(None)
    return outs, dt


def run_rpc(cmd, reqs, cwd, timeout):
    data = "".join(json.dumps({"id": i, "method": "graph", "params": r}) + "\n" for i, r in enumerate(reqs))
    t0 = time.perf_counter()
    r = subprocess.run(cmd, shell=True, cwd=cwd, input=data, capture_output=True, text=True, timeout=timeout)
    dt = time.perf_counter() - t0
    got = {}
    for l in r.stdout.splitlines():
        try:
            o = json.loads(l)
        except ValueError:
            continue
        if isinstance(o, dict) and "id" in o:
            got[o["id"]] = o.get("result", o)
    return [got.get(i) for i in range(len(reqs))], dt


def run_single(cmd, reqs, cwd, timeout):
    outs = []
    t0 = time.perf_counter()
    for r in reqs:
        p = subprocess.run(cmd, shell=True, cwd=cwd, input=json.dumps(r), capture_output=True, text=True, timeout=timeout)
        try:
            outs.append(json.loads(p.stdout))
        except ValueError:
            outs.append(None)
    return outs, time.perf_counter() - t0


def score_case(resp, exp):
    """-> (ok, total, info_ok, info_total, mismatches)"""
    ok = total = iok = itot = 0
    bad = []
    series = (resp or {}).get("series") if isinstance(resp, dict) else None
    for y, want in exp["series"].items():
        got = (series or {}).get(y)
        info = y.endswith(INFO_SUFFIX)
        for i, w in enumerate(want):
            g = got[i] if isinstance(got, list) and i < len(got) else "<missing>"
            good = g != "<missing>" and close(g, w)
            if info:
                itot += 1
                iok += good
            else:
                total += 1
                ok += good
                if not good:
                    bad.append({"y": y, "x": exp["x"][i], "got": g, "want": w})
    return ok, total, iok, itot, bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name")
    ap.add_argument("--cmd")
    ap.add_argument("--batch-cmd")
    ap.add_argument("--rpc-cmd")
    ap.add_argument("--cwd")
    ap.add_argument("--timeout", type=float, default=600)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    cases = load()
    reqs = [c[1] for c in cases]
    if a.self_test:
        outs, dt, name = [c[2] for c in cases], 0.0, "self-test"
    elif a.batch_cmd:
        outs, dt = run_batch(a.batch_cmd, reqs, a.cwd, a.timeout)
        name = a.name
    elif a.rpc_cmd:
        outs, dt = run_rpc(a.rpc_cmd, reqs, a.cwd, a.timeout)
        name = a.name
    elif a.cmd:
        outs, dt = run_single(a.cmd, reqs, a.cwd, a.timeout)
        name = a.name
    else:
        ap.error("one of --cmd/--batch-cmd/--rpc-cmd/--self-test")
    groups, failures = {}, {}
    tot = [0, 0, 0, 0]
    full = 0
    for (cname, req, exp), resp in zip(cases, outs + [None] * (len(cases) - len(outs))):
        ok, t, iok, it, bad = score_case(resp, exp)
        g = groups.setdefault(exp["graph"], [0, 0, 0])
        g[0] += ok; g[1] += t; g[2] += 1
        for k, v in enumerate((ok, t, iok, it)):
            tot[k] += v
        if bad or t == 0:
            failures[cname] = {"error": (resp or {}).get("error") if isinstance(resp, dict) else "no response", "mismatches": bad[:40]}
        else:
            full += 1
    card = {"variant": name, "cases": len(cases), "cases_fully_correct": full, "values_correct": tot[0], "values_total": tot[1],
            "accuracy": tot[0] / tot[1] if tot[1] else 0, "info_charge_ids": {"ok": tot[2], "total": tot[3]},
            "groups": {k: {"ok": v[0], "total": v[1], "cases": v[2]} for k, v in sorted(groups.items())},
            "wall_s": dt, "time": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    out = ROOT / "results" / ("graphs-" + name)
    out.mkdir(parents=True, exist_ok=True)
    (out / "scorecard.json").write_text(json.dumps(card, indent=1))
    (out / "failures.json").write_text(json.dumps(failures, indent=1, default=str))
    md = [f"# Graph scorecard: {name}", "", f"- cases fully correct: **{full}/{len(cases)}**",
          f"- sample values correct: **{tot[0]}/{tot[1]}** ({100 * card['accuracy']:.2f} %)",
          f"- informational charge ids matching Pyfa: {tot[2]}/{tot[3]}", f"- wall time: {dt:.2f} s", "",
          "| graph | cases | ok | total | % |", "|---|---|---|---|---|"]
    for k, v in sorted(groups.items()):
        md.append(f"| {k} | {v[2]} | {v[0]} | {v[1]} | {100 * v[0] / v[1] if v[1] else 0:.1f} |")
    (out / "scorecard.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
