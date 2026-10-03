#!/usr/bin/env python3
"""docs/22 suites: sde (embedded SDE version / provenance / --sde), price_inject (price precedence and validation),
price_rule (the updater's pricing rule on synthetic order books).

  python3 d22/run_d22.py --suite sde|price_inject --cmd ENGINE [--name N] [--out FILE]
  python3 d22/run_d22.py --suite price_rule --rule-cmd 'CMD' [--out FILE]      # updater (eve4); see adapter.py
  python3 d22/run_d22.py --suite all --self-test                               # validate the bench's own data

Cases needing an external input (`needs: ["SDE_PACK"]`, a real edp v1 pack from eve-sde-pipeline) are reported
`pending` (not scored) unless the environment variable is set. Output: {"suite", "name", "cases": {id: {"pass",
"pending"?, "first"}}} - the shape tools/check_no_regress.py reads."""
import argparse, base64, hashlib, json, math, os, re, struct, sys
from pathlib import Path

D = Path(__file__).resolve().parent
ROOT = D.parent
sys.path.insert(0, str(ROOT / "batch")); sys.path.insert(0, str(D))
import adapter as A, rule as R, prices as P  # noqa: E402

SDE_BUILD = 3569502
HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
TIME_RE = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
SDE_KEYS = ("engine", "sde_build", "sde_revision", "sde_release", "sde_hash", "sde_source")


def path(p):
    if p == "$SDE_PACK":
        return os.environ["SDE_PACK"]
    return str(ROOT / p) if p.startswith("d22/") else p


def gargs(args):
    return [path(a) for a in args]


def fitfile(cid):
    return json.loads((ROOT / "cases" / f"{cid}.json").read_text())


def strip(out):
    return {k: v for k, v in out.items() if k not in ("provenance", "price", "warnings")} if isinstance(out, dict) else out


# ------------------------------------------------------------------ bench-side validators (self-test + references)
def pack_header(b):
    if len(b) < 64:
        return None
    m, major, minor, build, rev, n, rel, h, _ = struct.unpack("<4sHHIHHq32sQ", b[:64])
    return {"magic": m, "major": major, "build": build, "rev": rev, "count": n, "hash": h}


def pack_ok(b):
    h = pack_header(b)
    if not h or h["magic"] != b"EDPK" or h["major"] != 1 or hashlib.sha256(b[64:]).digest() != h["hash"]:
        return False
    for i in range(h["count"]):
        o = 64 + 24 * i
        if o + 24 > len(b):
            return False
        _, _, off, ln = struct.unpack("<4sIQQ", b[o:o + 24])
        if off + ln > len(b):
            return False
    return True


def snapshot_code(d):
    """bench validation of a --prices file -> None (ok) or the docs/22 §5 code"""
    if not isinstance(d, dict):
        return "BAD_PRICES"
    if "schema" in d or "schema_version" in d:
        if d.get("schema") != "eve-price-snapshot" or d.get("schema_version") != 1:
            return "PRICE_SNAPSHOT_VERSION"
        if P.canonical_hash(d) != d.get("content_hash"):
            return "PRICE_SNAPSHOT_INVALID"
        for e in d["types"].values():
            if not (e["p0"] <= e["price"] <= e["band_max"] and 0 < e["units"] <= e["units_considered"]
                    and 0 < e["orders"] <= e["orders_considered"] <= e["orders_total"]):
                return "PRICE_SNAPSHOT_INVALID"
        return None
    for k, v in d.items():
        if not k.isdigit() or isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0:
            return "BAD_PRICES"
    return None


def load_any(p):
    import gzip
    return json.load(gzip.open(p) if str(p).endswith(".gz") else open(p))


# ------------------------------------------------------------------ sde checks
def version_fields(v, want_source="embedded"):
    bad = []
    if A.err_code(v) or not isinstance(v, dict):
        return [f"version error: {json.dumps(v)[:200]}"]
    if not str(v.get("engine", "")).startswith("eve-dogma"):
        bad.append(f"engine {v.get('engine')!r}")
    if v.get("sde_build") != SDE_BUILD:
        bad.append(f"sde_build {v.get('sde_build')!r} != {SDE_BUILD}")
    if not isinstance(v.get("sde_revision"), int) or isinstance(v.get("sde_revision"), bool) or v.get("sde_revision") < 0:
        bad.append(f"sde_revision {v.get('sde_revision')!r}")
    if not TIME_RE.match(str(v.get("sde_release"))):
        bad.append(f"sde_release {v.get('sde_release')!r}")
    if not HASH_RE.match(str(v.get("sde_hash"))):
        bad.append(f"sde_hash {v.get('sde_hash')!r}")
    if v.get("sde_source") != want_source:
        bad.append(f"sde_source {v.get('sde_source')!r} != {want_source}")
    if want_source == "embedded":
        for k, w in (("pack_format", "1.0"), ("snapshot_schema_version", 1), ("target", "native")):
            if v.get(k) != w:
                bad.append(f"{k} {v.get(k)!r} != {w!r}")
    return bad


def ck_sde(c, eng):
    k = c["check"]
    if k == "version_fields":
        v = A.version(eng) if c["transport"] == "cli" else A.rpc(eng, [("version", {})])[0]
        return version_fields(v)
    if k == "version_rpc_equals_cli":
        a, b = A.version(eng), A.rpc(eng, [("version", {})])[0]
        return [] if a == b and not A.err_code(a) else [f"cli {json.dumps(a)[:120]} != rpc {json.dumps(b)[:120]}"]
    if k == "version_matches_meta":
        v, m = A.version(eng), A.meta(eng)
        if A.err_code(v):
            return [f"version error: {json.dumps(v)[:200]}"]
        bad = [] if v.get("sde_build") == m.get("sde_build") else [f"sde_build {v.get('sde_build')} != meta {m.get('sde_build')}"]
        return bad + ([] if v.get("sde_release") == m.get("sde_release_date") else
                      [f"sde_release {v.get('sde_release')} != meta sde_release_date {m.get('sde_release_date')}"])
    if k == "provenance_calc":
        v = A.version(eng)
        if A.err_code(v):
            return [f"version error: {json.dumps(v)[:200]}"]
        fits = [fitfile(f) for f in c["fits"]]
        outs = [A.calc(eng, f) for f in fits] if c["transport"] == "cli" else A.rpc(eng, [("calc", A.rpc_calc_params(f)) for f in fits])
        bad = []
        for f, o in zip(c["fits"], outs):
            pv = o.get("provenance") if isinstance(o, dict) else None
            if not isinstance(pv, dict):
                bad.append(f"{f}: no provenance")
                continue
            bad += [f"{f}: provenance.{x} {pv.get(x)!r} != version {v.get(x)!r}" for x in SDE_KEYS if pv.get(x) != v.get(x)]
        return bad
    if k == "sde_invalid_cli":
        o = A.calc(eng, fitfile("exct_rifter"), ["--sde", path(c["pack"])])
        code = A.err_code(o)
        if c.get("any_error"):
            return [] if code and code not in ("NO_OUTPUT", "EXIT") else [f"want a structured error JSON, got {code or 'success'}"]
        return [] if code == "SDE_PACK_INVALID" else [f"got {code or 'success'}, want SDE_PACK_INVALID"]
    if k == "sde_invalid_rpc":
        p = path(c["pack"])
        prm = {"pack_b64": base64.b64encode(Path(p).read_bytes()).decode()} if c.get("b64") else {"path": p}
        r = A.rpc(eng, [("sde_override", prm), ("version", {}), ("calc", A.rpc_calc_params(fitfile(c["fit"])))])
        bad = [] if A.err_code(r[0]) == "SDE_PACK_INVALID" else [f"sde_override: got {A.err_code(r[0]) or 'success'}, want SDE_PACK_INVALID"]
        if A.err_code(r[1]) or r[1].get("sde_source") != "embedded":
            bad.append(f"after the failed override version is {json.dumps(r[1])[:120]}")
        if A.err_code(r[2]):
            bad.append(f"calc after the failed override: {A.err_code(r[2])}")
        return bad
    # ---- valid pack (SDE_PACK)
    pk = os.environ["SDE_PACK"]
    hd = pack_header(Path(pk).read_bytes())
    want_hash = "sha256:" + hd["hash"].hex()
    if k == "sde_valid_cli_version":
        v = A.version(eng, ["--sde", pk])
        bad = version_fields(v, "override")
        for x, w in (("sde_override_path", pk), ("sde_hash", want_hash), ("sde_build", hd["build"]), ("sde_revision", hd["rev"])):
            if v.get(x) != w:
                bad.append(f"{x} {v.get(x)!r} != {w!r}")
        return bad
    if k == "sde_valid_cli_identical":
        bad = []
        for f in c["fits"]:
            a, b = A.calc(eng, fitfile(f)), A.calc(eng, fitfile(f), ["--sde", pk])
            if A.err_code(b) or strip(a) != strip(b):
                bad.append(f"{f}: --sde output differs from embedded")
            elif (b.get("provenance") or {}).get("sde_source") != "override":
                bad.append(f"{f}: provenance.sde_source {(b.get('provenance') or {}).get('sde_source')!r}")
        return bad
    if k == "sde_valid_rpc":
        prm = {"pack_b64": base64.b64encode(Path(pk).read_bytes()).decode()} if c.get("b64") else {"path": pk}
        fits = [fitfile(f) for f in c["fits"]]
        calls = [("sde_override", prm)] + [("calc", A.rpc_calc_params(f)) for f in fits] + [("sde_override", {"reset": True}), ("version", {})]
        r = A.rpc(eng, calls)
        bad = version_fields(r[0], "override")
        if r[0].get("sde_hash") != want_hash:
            bad.append(f"override sde_hash {r[0].get('sde_hash')!r} != {want_hash}")
        for f, o in zip(c["fits"], r[1:1 + len(fits)]):
            if A.err_code(o) or strip(o) != strip(A.calc(eng, fitfile(f))):
                bad.append(f"{f}: RPC calc under the override differs from embedded")
        return bad + [f"after reset: {x}" for x in version_fields(r[-1])]
    if k == "embedded_hash":
        v = A.version(eng)
        return [] if v.get("sde_hash") == want_hash else [f"embedded sde_hash {v.get('sde_hash')!r} != pack {want_hash}"]
    raise KeyError(k)


# ------------------------------------------------------------------ price_inject checks
def l4_of(fit, files):
    pr = fit.get("prices") or {}
    use = pr.get("use_snapshot", {"replace": False, "override": True}.get(pr.get("mode"), True))
    return None if use is False or not files else P.load_l4(files[-1])


def expected_block(fit, files):
    l2 = list(fit.get("price_overrides", []))
    return P.price_block(fit, P.layers_for(l2, [], dict((fit.get("prices") or {}).get("isk", {})), l4_of(fit, files)))


def check_price_out(o, fit, files, src, embedded):
    """files: --prices / prices_load files in effect (abs paths); embedded: L4 = embedded snapshot (values unknown)"""
    if A.err_code(o) or not isinstance(o, dict):
        return [f"error {json.dumps(o)[:200]}"]
    bad = []
    pv, blk = o.get("provenance") or {}, o.get("price")
    if pv.get("price_source") != src:
        bad.append(f"provenance.price_source {pv.get('price_source')!r} != {src!r}")
    ids = ("price_snapshot_id", "price_time", "price_hash")
    if src == "request":
        bad += [f"provenance.{x} {pv.get(x)!r} != null" for x in ids if pv.get(x) is not None]
    elif files and l4_of(fit, files):
        d = load_any(files[-1])
        if d.get("schema") == "eve-price-snapshot":
            for x, w in zip(ids, (d["snapshot_id"], d["market_time"], d["content_hash"])):
                if pv.get(x) != w:
                    bad.append(f"provenance.{x} {pv.get(x)!r} != {w!r}")
    elif embedded:
        for x in ids:
            if not pv.get(x):
                bad.append(f"provenance.{x} missing (embedded snapshot)")
    if not isinstance(blk, dict):
        return bad + ["no price block"]
    exp = expected_block(fit, files)
    if not embedded:
        return bad + P.compare_block(exp, blk, "price: ")
    # embedded L4: exact for items priced above L4; items the bench cannot price must be snapshot-based or missing
    got = {(s, l.get("index"), l.get("type_id")): l for s, sec in (blk.get("sections") or {}).items() for l in sec.get("items", [])}
    for s, sec in exp["sections"].items():
        for l in sec["items"]:
            g = got.get((s, l["index"], l["type_id"]))
            if not g:
                bad.append(f"{s}[{l['index']}] {l['type_id']}: line missing")
            elif abs(g.get("unit_isk", -1) - l["unit_isk"]) > 1e-6 * max(1, l["unit_isk"]) or g.get("source") != l["source"]:
                bad.append(f"{s}[{l['index']}] {l['type_id']}: {g.get('unit_isk')}/{g.get('source')} != {l['unit_isk']}/{l['source']}")
    for m in exp["missing"]:
        g = got.get((m["section"], m["index"], m["type_id"]))
        if g and (g.get("base_source") or g.get("source")) != "snapshot":
            bad.append(f"{m['section']}[{m['index']}] {m['type_id']}: source {g.get('source')!r}, want snapshot-based")
        if g and g.get("snapshot_time") != pv.get("price_time"):
            bad.append(f"{m['section']}[{m['index']}]: snapshot_time {g.get('snapshot_time')!r} != price_time {pv.get('price_time')!r}")
    return bad


def ck_inject(c, eng):
    k = c["check"]
    if k == "inject_calc":
        args = gargs(c["args"])
        files = [args[i + 1] for i, a in enumerate(args) if a == "--prices"]
        o = A.calc(eng, c["fit"], args)
        bad = check_price_out(o, c["fit"], files, c["price_source"], embedded=not files and c["price_source"] != "request")
        if c.get("warning") and not any(c["warning"] in w for w in A.warnings(o)):
            bad.append(f"warning {c['warning']!r} not in {A.warnings(o)}")
        return bad
    if k == "inject_rpc":
        calls = [(m, dict(p, path=path(p["path"])) if m == "prices_load" and "path" in p else p) for m, p in c["calls"]]
        r = A.rpc(eng, calls)
        bad = [f"prices_load: {json.dumps(r[0])[:160]}"] if A.err_code(r[0]) else []
        return bad + check_price_out(r[-1], c["calls"][-1][1], [path(c["session_file"])], c["price_source"], embedded=False)
    if k == "inject_rpc_isolated":
        r1 = A.rpc(eng, [("prices_load", {"path": path("d22/data/prices/snap-good.json")})])
        if A.err_code(r1[0]):
            return [f"prices_load: {json.dumps(r1[0])[:160]}"]
        o = A.rpc(eng, [("calc", A.rpc_calc_params(c["fit"]))])[0]
        src = ((o or {}).get("provenance") or {}).get("price_source") if isinstance(o, dict) else None
        return [] if src == "embedded" else [f"new process price_source {src!r} != 'embedded'"]
    if k == "inject_error":
        code = A.err_code(A.calc(eng, c["fit"], gargs(c["args"])))
        return [] if code == c["code"] else [f"got {code or 'success'}, want {c['code']}"]
    if k == "inject_rpc_error":
        r = A.rpc(eng, [(m, dict(p, path=path(p["path"])) if "path" in p else p) for m, p in c["calls"]])
        code = A.err_code(r[0])
        return [] if code == c["code"] else [f"got {code or 'success'}, want {c['code']}"]
    raise KeyError(k)


# ------------------------------------------------------------------ price_rule
def ck_rule(c, cmd):
    got = A.price_rule(cmd, c["orders"], dict(R.DEFAULT, **c["params"]))
    exp = c["expected"]
    if exp is None:
        return [] if got is None else [f"want no price (missing), got {json.dumps(got)[:160]}"]
    if not isinstance(got, dict) or A.err_code(got):
        return [f"want {exp}, got {json.dumps(got)[:160]}"]
    bad = []
    for k, w in exp.items():
        g = got.get(k)
        if isinstance(w, float):
            tol = 1e-9 * max(1.0, abs(w)) if k != "price" else 1e-9 * max(1.0, abs(w))
            if not isinstance(g, (int, float)) or abs(g - w) > tol:
                bad.append(f"{k} {g!r} != {w!r}")
        elif g != w:
            bad.append(f"{k} {g!r} != {w!r}")
    return bad


# ------------------------------------------------------------------ self-test: the bench's own data
def self_check(suite, c):
    if suite == "price_rule":
        return [] if R.rule(c["orders"], c["params"]) == c["expected"] else ["expected != reference rule"]
    if c["check"] in ("sde_invalid_cli", "sde_invalid_rpc"):
        p = Path(path(c["pack"]))
        return [] if not p.exists() or not pack_ok(p.read_bytes()) else ["pack unexpectedly valid"]
    if c["check"] == "inject_error" and c["args"]:
        code = snapshot_code(load_any(path(c["args"][1])))
        return [] if code == c["code"] else [f"bench validator says {code}, case wants {c['code']}"]
    if c["check"] == "inject_rpc_error":
        code = snapshot_code(load_any(path(c["calls"][0][1]["path"])))
        return [] if code == c["code"] else [f"bench validator says {code}"]
    bad = []
    for a in c.get("args", []) + ([c["session_file"]] if c.get("session_file") else []):
        if a.startswith("d22/") and snapshot_code(load_any(path(a))) and "other-build" not in a:
            bad.append(f"{a} invalid")
    return bad


def run(suite, eng, rule_cmd, self_test, only=None):
    man = json.loads((D / "MANIFEST.json").read_text())
    res = {}
    for key, m in sorted(man.items()):
        if m["suite"] != suite or (only and key.split("/")[1] not in only):
            continue
        cid = key.split("/")[1]
        c = json.loads((D / "cases" / suite / f"{cid}.json").read_text())
        if self_test:
            bad = self_check(suite, c)
        elif any(n not in os.environ for n in c.get("needs", [])):
            res[cid] = {"pass": False, "pending": True, "check": m["check"], "first": [f"needs {','.join(c['needs'])}"]}
            continue
        else:
            try:
                bad = ck_rule(c, rule_cmd) if suite == "price_rule" else ck_sde(c, eng) if suite == "sde" else ck_inject(c, eng)
            except Exception as e:  # noqa: BLE001 - an engine crash / odd shape is a failed case, not a runner crash
                bad = [f"runner exception {type(e).__name__}: {str(e)[:160]}"]
        res[cid] = {"pass": not bad, "check": m["check"], "first": bad[:5]}
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", required=True, choices=["sde", "price_inject", "price_rule", "all"])
    ap.add_argument("--cmd", help="engine binary (sde / price_inject)")
    ap.add_argument("--rule-cmd", default=os.environ.get("PRICE_RULE_CMD"), help="updater rule command (price_rule)")
    ap.add_argument("--name", default="run")
    ap.add_argument("--out")
    ap.add_argument("--only", help="comma-separated case ids")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    suites = ["sde", "price_inject", "price_rule"] if a.suite == "all" else [a.suite]
    if not a.self_test and any(s != "price_rule" for s in suites) and not a.cmd:
        ap.error("--cmd is required")
    if not a.self_test and "price_rule" in suites and not a.rule_cmd:
        ap.error("price_rule needs --rule-cmd or PRICE_RULE_CMD")
    rc = 0
    for s in suites:
        res = run(s, a.cmd, a.rule_cmd, a.self_test, set(a.only.split(",")) if a.only else None)
        scored = {k: v for k, v in res.items() if not v.get("pending")}
        n = sum(v["pass"] for v in scored.values())
        pend = len(res) - len(scored)
        tag = " (SELF-TEST: bench data, not the engine)" if a.self_test else ""
        print(f"{a.name}: d22/{s} {n}/{len(scored)} pass" + (f", {pend} pending" if pend else "") + tag)
        fails = [k for k, v in scored.items() if not v["pass"]]
        if fails:
            print(f"  first failure: {fails[0]} {res[fails[0]]['first'][:2]}")
            rc = 1
        if a.out:
            out = a.out if len(suites) == 1 else str(Path(a.out).with_name(f"{s}.json"))
            Path(out).write_text(json.dumps({"suite": s, "name": a.name, "cases": res}, indent=1, sort_keys=True) + "\n")
    sys.exit(rc)


if __name__ == "__main__":
    main()
