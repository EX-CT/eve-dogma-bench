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
import prices  # noqa: E402
PRICE_KEYS = ("price_overrides", "prices")


def strip_price(fit):
    """the one-by-one reference fit: price inputs removed (stats must not depend on them)"""
    f = {k: v for k, v in fit.items() if k not in PRICE_KEYS}
    if isinstance(f.get("options"), dict) and "price" in f["options"]:
        f["options"] = {k: v for k, v in f["options"].items() if k != "price"}
    return f


def l4_for(fit, req, engine_args):
    """L4 = the --prices file unless use_snapshot is false (fit's own flag wins over the batch's)"""
    use = (fit.get("prices") or {}).get("use_snapshot", (req.get("prices") or {}).get("use_snapshot", True))
    if "--prices" not in engine_args or use is False:
        return None
    return prices.load_l4(SUITE.parent / engine_args[engine_args.index("--prices") + 1])


def with_price(out, fit, req, l1, engine_args=()):
    """merge the bench reference price block into a one-by-one output (price cases)"""
    if not isinstance(out, dict) or "error" in out:
        return out
    inj = dict((req.get("prices") or {}).get("isk", {}))
    inj.update((fit.get("prices") or {}).get("isk", {}))      # the FitRequest's own table wins per type (docs/23 §5.2)
    l2 = list(fit.get("price_overrides", [])) + list(req.get("price_overrides", []))   # same target: the fit's own wins (§11.4)
    return dict(out, price=prices.price_block(fit, prices.layers_for(l2, l1, inj, l4_for(fit, req, list(engine_args)))))


STRIP_OUT = ("price", "provenance")
SDE_BUILD = 3569502


def expected_prov(req, fit, engine_args):
    """eve's ruling: provenance {sde_build, sde_hash, price_source, snapshot_time}; price_source = the source of the
    base price table only, request > file > snapshot > none (overrides do not count). -> (allowed price_source set,
    snapshot_time check: "null" | "set" | <exact value> | None = unchecked)"""
    isk = dict((req.get("prices") or {}).get("isk") or {})
    isk.update((fit.get("prices") or {}).get("isk") or {})
    pr = dict(req.get("prices") or {}, **(fit.get("prices") or {}))
    use = pr.get("use_snapshot", {"replace": False, "override": True}.get(pr.get("mode"), True)) is not False
    if isk:
        return {"request"}, "null"                        # docs/22 §2.3 (eccf455): null for request / none
    if not use:
        return {"none"}, "null"
    if "--prices" in engine_args:
        f = prices.load_l4(SUITE.parent / engine_args[engine_args.index("--prices") + 1])
        return {"file"}, f["time"] if f["time"] else "null"
    return {"snapshot", "none"}, "by_source"


def check_prov(pv, req, fit, engine_args, where):
    if not isinstance(pv, dict):
        return [f"{where}no provenance"]
    bad = [f"{where}provenance.{k} missing" for k in ("sde_build", "sde_hash", "price_source", "snapshot_time") if k not in pv]
    if pv.get("sde_build") != SDE_BUILD or not str(pv.get("sde_hash", "")).startswith("sha256:"):
        bad.append(f"{where}provenance sde_build/sde_hash {pv.get('sde_build')!r} {pv.get('sde_hash')!r}")
    srcs, st = expected_prov(req, fit, engine_args)
    if pv.get("price_source") not in srcs:
        bad.append(f"{where}provenance.price_source {pv.get('price_source')!r} not in {sorted(srcs)}")
    g = pv.get("snapshot_time")
    if st == "by_source":
        st = "set" if pv.get("price_source") == "snapshot" else "null"
    if st == "null" and g is not None or st == "set" and not g or st not in (None, "null", "set") and g != st:
        bad.append(f"{where}provenance.snapshot_time {g!r} (want {st})")
    return bad


def synth_prov(req, fit, engine_args):
    srcs, st = expected_prov(req, fit, engine_args)
    src = sorted(srcs)[0] if len(srcs) == 1 else "none"
    t = None if st in (None, "null", "by_source") else "2026-10-03T00:00:00Z" if st == "set" else st
    return {"sde_build": SDE_BUILD, "sde_hash": "sha256:" + "0" * 64, "price_source": src, "snapshot_time": t}


def batch_provenance(req, got, engine_args):
    """top-level provenance (batch-level tables) + each result's effective provenance (its own, else the top one)"""
    if not isinstance(got, dict) or "results" not in got:
        return []
    bad = check_prov(got.get("provenance"), req, {}, engine_args, "top: ")
    fits = {i: f for i, (_, f) in enumerate(semantics.expand(req))}
    for r in got["results"]:
        if "error" in r or r.get("index") not in fits:
            continue
        bad += check_prov(r.get("provenance") or got.get("provenance"), req, fits[r["index"]], engine_args, f"[{r['index']}] ")
        if len(bad) > 6:
            break
    return bad


def calc_price_embedded_case(engine, case, self_test):
    """kind calc_price_embedded: calc with no price inputs; structural only (embedded snapshot values unknown):
    every priced line has source / layer snapshot, multiplier 1, base_source snapshot, snapshot_time ==
    provenance.snapshot_time, provenance.price_source snapshot; lines + missing cover every item (docs/22 §3, docs/23 §5)"""
    if self_test:
        return []
    fit = case["fit"]
    got = calc_one(engine, fit)
    if not isinstance(got, dict) or "error" in got:
        return [f"calc error {json.dumps(got)[:160]}"]
    blk, prov = got.get("price"), got.get("provenance") or {}
    if not isinstance(blk, dict):
        return ["no price block without price inputs (embedded snapshot expected)"]
    bad = []
    pt = prov.get("snapshot_time")
    if not pt:
        bad.append("provenance.snapshot_time missing")
    if prov.get("price_source") != "snapshot":
        bad.append(f"provenance.price_source {prov.get('price_source')!r} != 'snapshot'")
    lines = [(sec, l) for sec, s in (blk.get("sections") or {}).items() for l in s.get("items", [])]
    for sec, l in lines:
        for k, v in (("source", "snapshot"), ("layer", "snapshot"), ("base_source", "snapshot"), ("multiplier", 1)):
            if l.get(k) != v:
                bad.append(f"{sec}[{l.get('index')}] {k}={l.get(k)!r} != {v!r}")
        if l.get("snapshot_time") != pt:
            bad.append(f"{sec}[{l.get('index')}] snapshot_time {l.get('snapshot_time')!r} != provenance.snapshot_time {pt!r}")
    want = sorted((sec, i, t, q) for sec, i, t, q in prices.items(fit))
    have = sorted([(sec, l.get("index"), l.get("type_id"), l.get("quantity")) for sec, l in lines]
                  + [(m.get("section"), m.get("index"), m.get("type_id"), m.get("quantity")) for m in blk.get("missing", [])])
    if want != have:
        bad.append(f"lines+missing {len(have)} != items {len(want)}")
    return bad


def calc_price_case(engine, case, engine_args, self_test):
    """kind calc_price: `ENGINE [--prices F] calc` with price inputs; price block vs bench resolver, the rest identical
    to calc without price inputs (price / provenance keys aside)"""
    fit = case["fit"]
    plain = calc_one(engine, strip_price(fit))
    exp = with_price(plain, fit, {}, [], engine_args)
    got = exp if self_test else calc_one(" ".join([engine] + list(engine_args)), fit)
    if not isinstance(got, dict) or "error" in got:
        return [f"calc error {json.dumps(got)[:160]}"]
    bad = []
    a = {k: v for k, v in got.items() if k not in STRIP_OUT}
    b = {k: v for k, v in plain.items() if k not in STRIP_OUT}
    if json.dumps(a, sort_keys=True) != json.dumps(b, sort_keys=True):
        bad.append("calc stats with price inputs differ from calc without them")
    if not self_test:
        bad += check_prov(got.get("provenance"), {}, fit, list(engine_args), "")
    return bad + prices.compare_block(exp["price"], got.get("price"), "price: ")


def semantics_error(r):
    return None if "fit" in r and "batch_version" not in r else semantics.request_error(r)


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
    eargs = {c: [str(SUITE.parent / x) if x.startswith("batch/") else x for x in man[c].get("engine_args", [])] for c in ids}
    special = {c for c in ids if man[c]["kind"].startswith("calc_price") or semantics_error(reqs[c])}
    # one-by-one reference outputs (distinct fits computed once)
    todo = {}
    for c, r in reqs.items():
        if c in special:
            continue
        for _, f in semantics.expand(r):
            f = strip_price(f)
            todo.setdefault(json.dumps(f, sort_keys=True), f)
        if "base" in r:
            b = strip_price(r["base"])
            todo.setdefault(json.dumps(b, sort_keys=True), b)
    t0 = time.time()
    keys = list(todo)
    with ThreadPoolExecutor(a.jobs) as ex:
        outs = list(ex.map(lambda k: calc_one(a.cmd, todo[k]), keys))
    single = dict(zip(keys, outs))
    t_single = time.time() - t0
    res, t_batch = {}, 0.0
    for c in ids:
        r = reqs[c]
        m = man[c]
        if m["kind"] == "calc_price_embedded":
            bad = calc_price_embedded_case(a.cmd, r, a.self_test)
            res[c] = {"pass": not bad, "kind": m["kind"], "fits": 1, "ops": m["ops"], "first": bad[:5]}
            continue
        if m["kind"].startswith("calc_price"):
            bad = calc_price_case(a.cmd, r, eargs[c], a.self_test)
            res[c] = {"pass": not bad, "kind": m["kind"], "fits": 1, "ops": m["ops"], "first": bad[:5]}
            continue
        if semantics_error(r):
            exp = {"request_error": semantics_error(r)}
            got = {"error": exp["request_error"]} if a.self_test else adapter.call(a.cmd, r, a.transport, engine_args=eargs[c])
            bad = semantics.compare(exp, got)
            res[c] = {"pass": not bad, "kind": m["kind"], "fits": m["fits"], "ops": m["ops"], "first": bad[:5]}
            continue
        fits = semantics.expand(r)
        singles = [single[json.dumps(strip_price(f), sort_keys=True)] for _, f in fits]
        base = single[json.dumps(strip_price(r["base"]), sort_keys=True)] if "base" in r else None
        if r.get("price"):
            singles = [with_price(o, f, r, l1, eargs[c]) for o, (_, f), l1 in zip(singles, fits, semantics.l1_overrides(r))]
            base = with_price(base, r["base"], r, [], eargs[c]) if base is not None else None
        exp = semantics.expected(r, singles, base)
        t1 = time.time()
        if a.self_test:
            js = calc_jsonl(a.cmd, [strip_price(f) for _, f in fits])
            jb = calc_jsonl(a.cmd, [strip_price(r["base"])])[0] if "base" in r else None
            if r.get("price"):
                js = [with_price(o, f, r, l1, eargs[c]) for o, (_, f), l1 in zip(js, fits, semantics.l1_overrides(r))]
                jb = with_price(jb, r["base"], r, [], eargs[c]) if jb is not None else None
            got = semantics.expected(r, js, jb)
            got["provenance"] = synth_prov(r, {}, eargs[c])
            fx = dict(enumerate(f for _, f in fits))
            for x in got["results"]:
                p = synth_prov(r, fx[x["index"]], eargs[c])
                if p != got["provenance"]:
                    x["provenance"] = p
        else:
            try:
                got = adapter.call(a.cmd, r, a.transport, engine_args=eargs[c])
            except Exception as e:  # noqa: BLE001
                got = {"error": {"code": "ADAPTER_EXCEPTION", "message": repr(e)[:200]}}
        t_batch += time.time() - t1
        bad = semantics.compare(exp, got)
        bad += batch_provenance(r, got, eargs[c])
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
