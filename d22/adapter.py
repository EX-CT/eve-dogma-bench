"""docs/22 suites adapter: the ONLY place that knows how the engine / updater is called and what the docs/22 output
looks like. Schemas are PROVISIONAL (docs/22 DECIDED 2026-10-03, no engine implementation yet): `version` CLI / RPC,
top-level `provenance`, `--sde FILE` / RPC `sde_override`, `--prices FILE` / RPC `prices_load`, error codes
SDE_LOAD_FAILED {reason} / PRICE_SNAPSHOT_VERSION / PRICE_SNAPSHOT_INVALID / BAD_PRICES.
eve's rulings (2026-10-03): unified `provenance` {sde_build, sde_hash, price_source, snapshot_time}; sde_hash = pack
content_sha256 (docs/22 §2.2); price_source = source of the base price table (request > file > snapshot > none);
any SDE load failure = SDE_LOAD_FAILED with reason not_found | corrupt | hash_mismatch | incompatible_version. When F (engine) or eve4 (updater)
publish their contract, change this file only; the cases and run_d22.py stay.

price_rule transport (updater, provisional): `PRICE_RULE_CMD` reads {"rule": {...}, "orders": [...]} JSON on stdin
and prints the §4.5 entry JSON, or `null` when the type has no price."""
import json, subprocess


def _json(stdout):
    try:
        return json.loads(stdout)
    except ValueError:
        return None


def cli(engine, args, stdin=None, timeout=120):
    """ENGINE <args>; -> parsed JSON or {"error": {...}}"""
    r = subprocess.run(engine.split() + list(args), input=stdin, capture_output=True, text=True, timeout=timeout)
    j = _json(r.stdout)
    if j is None:
        j = _json(r.stderr.strip().splitlines()[-1]) if r.stderr.strip() else None
        if not (isinstance(j, dict) and "error" in j):
            return {"error": {"code": "NO_OUTPUT", "message": f"exit {r.returncode}: {(r.stderr or r.stdout)[-200:]}"}}
    if r.returncode != 0 and not (isinstance(j, dict) and "error" in j):
        return {"error": {"code": "EXIT", "message": f"exit {r.returncode}"}}
    return j


def version(engine, gargs=()):
    return cli(engine, list(gargs) + ["version"])


def calc(engine, fit, gargs=()):
    return cli(engine, list(gargs) + ["calc"], json.dumps(fit))


def meta(engine):
    return cli(engine, ["meta"])


def rpc(engine, calls, gargs=(), timeout=300):
    """one serve-stdio session; calls = [(method, params)] -> [result or {"error"}] in order"""
    lines = "".join(json.dumps({"id": i + 1, "method": m, "params": p}) + "\n" for i, (m, p) in enumerate(calls))
    r = subprocess.run(engine.split() + list(gargs) + ["serve-stdio"], input=lines, capture_output=True, text=True, timeout=timeout)
    got = {}
    for l in r.stdout.splitlines():
        j = _json(l)
        if isinstance(j, dict) and "id" in j:
            got[j["id"]] = j["result"] if "result" in j else {"error": j.get("error")}
    return [got.get(i + 1, {"error": {"code": "NO_RESPONSE", "message": r.stderr[-200:]}}) for i in range(len(calls))]


def rpc_calc_params(fit):
    return fit                                    # eve-fit serve-stdio: params = FitRequest


def err_code(out):
    """error code of an engine answer (top-level error, or RPC result.error), else None"""
    if isinstance(out, dict) and isinstance(out.get("error"), dict):
        return out["error"].get("code")
    return None


def err_reason(out):
    """SDE_LOAD_FAILED reason: error.reason, or under error.details / error.data"""
    e = out.get("error") if isinstance(out, dict) else None
    if not isinstance(e, dict):
        return None
    return e.get("reason") or (e.get("details") or {}).get("reason") or (e.get("data") or {}).get("reason")


def provenance(out):
    return out.get("provenance") if isinstance(out, dict) else None


def warnings(out):
    return list((out or {}).get("warnings") or []) if isinstance(out, dict) else []


def price_rule(cmd, orders, params):
    """-> entry dict, None (no price), or {"error": {"code": "RULE_REJECTED"}} when the command exits non-zero
    (an invalid rule); unparseable output with exit 0 is NO_OUTPUT"""
    r = subprocess.run(cmd, shell=True, input=json.dumps({"rule": params, "orders": orders}), capture_output=True,
                       text=True, timeout=60)
    if r.returncode != 0:
        return {"error": {"code": "RULE_REJECTED", "message": f"exit {r.returncode}: {r.stderr.strip()[-200:]}"}}
    j = _json(r.stdout)
    if j is None and r.stdout.strip() != "null":
        return {"error": {"code": "NO_OUTPUT", "message": f"exit {r.returncode}: {(r.stderr or r.stdout)[-200:]}"}}
    return j
