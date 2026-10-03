"""batch-suite reference semantics (PROVISIONAL batch shape, see CONTRACT-BATCH.md).

Everything an engine's batch answer must equal is derived here from one-by-one FitRequest -> FitStats calls:
  expand(req)                      -> [(label, FitRequest)]        which fits the batch stands for, in order
  expected(req, singles, base)     -> normalized BatchResponse      what the batch answer must be
  compare(expected, got)           -> [mismatch strings]            empty = pass
The request/response *shape* lives in adapter.py; only adapter.py changes when the engine contract lands."""
import copy, json, math

DELTA_ABS_TOL = 1e-6   # deltas: round6(value - base_value) from the emitted (6-dp) values; compared within 1e-6
OPS = {"<": lambda a, b: a < b, "<=": lambda a, b: a <= b, ">": lambda a, b: a > b, ">=": lambda a, b: a >= b,
       "==": lambda a, b: a == b, "!=": lambda a, b: a != b}


# ---------------------------------------------------------------- JSON Patch (RFC 6902 subset: add, remove, replace)
def _parse(ptr):
    if ptr == "":
        return []
    assert ptr.startswith("/"), ptr
    return [p.replace("~1", "/").replace("~0", "~") for p in ptr[1:].split("/")]


def apply_patch(doc, ops):
    doc = copy.deepcopy(doc)
    for op in ops:
        parts = _parse(op["path"])
        parent = doc
        for p in parts[:-1]:
            parent = parent[int(p)] if isinstance(parent, list) else parent[p]
        last = parts[-1]
        o = op["op"]
        if isinstance(parent, list):
            if o == "add":
                parent.insert(len(parent) if last == "-" else int(last), copy.deepcopy(op["value"]))
            elif o == "remove":
                del parent[int(last)]
            elif o == "replace":
                parent[int(last)] = copy.deepcopy(op["value"])
            else:
                raise ValueError(o)
        else:
            if o in ("add", "replace"):
                if o == "replace" and last not in parent:
                    raise KeyError(op["path"])
                parent[last] = copy.deepcopy(op["value"])
            elif o == "remove":
                del parent[last]
            else:
                raise ValueError(o)
    return doc


# ---------------------------------------------------------------- expansion
def expand(req):
    """-> list of (label, FitRequest) in result-index order."""
    if "fits" in req:
        return [(it.get("label"), it["fit"]) for it in req["fits"]]
    base = req["base"]
    if "variants" in req:
        return [(v.get("label"), apply_patch(base, v["patch"])) for v in req["variants"]]
    if "product" in req:
        out = [([], [])]
        for axis in req["product"]["axes"]:
            out = [(labels + [v.get("label")], patch + v["patch"]) for labels, patch in out for v in axis]
        return [("×".join(str(l) for l in labels), apply_patch(base, patch)) for labels, patch in out]
    if "sweep" in req:
        sw = req["sweep"]
        return [(f"{sw['path']}={json.dumps(v)}", apply_patch(base, [{"op": "add", "path": sw["path"], "value": v}]))
                for v in sw["values"]]
    raise ValueError("no fits/variants/product/sweep")


# ---------------------------------------------------------------- projection / reference result
def get_path(stats, dotted):
    cur = stats
    for p in dotted.split("."):
        if isinstance(cur, list):
            if not p.lstrip("-").isdigit() or not -len(cur) <= int(p) < len(cur):
                return None
            cur = cur[int(p)]
        elif isinstance(cur, dict):
            if p not in cur:
                return None
            cur = cur[p]
        else:
            return None
    return cur


def project(stats, fields):
    return stats if fields is None else {f: get_path(stats, f) for f in fields}


def _num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def delta(stats, base_stats, fields):
    return {f: (round(get_path(stats, f) - get_path(base_stats, f), 6)
                if _num(get_path(stats, f)) and _num(get_path(base_stats, f)) else None) for f in fields}


def expected(req, singles, base_single=None):
    """singles: one-by-one engine outputs for expand(req), in order. base_single: output for req['base'] (deltas)."""
    fields = req.get("fields")
    want_delta = bool(req.get("deltas"))
    rows = []
    for i, ((label, _), out) in enumerate(zip(expand(req), singles)):
        r = {"index": i, "label": label}
        if isinstance(out, dict) and "error" in out:
            r["error"] = {"code": out["error"].get("code")}
        else:
            r["stats"] = project(out, fields)
            if want_delta:
                r["delta"] = delta(out, base_single, fields)
        rows.append(r)

    def key_val(r, spec):
        if "error" in r:
            return None
        src = r["delta"] if spec.get("on") == "delta" else r["stats"]
        return src.get(spec["field"]) if fields is not None else get_path(src, spec["field"])

    for flt in req.get("filter", []):
        rows = [r for r in rows if _num(key_val(r, flt)) and OPS[flt["op"]](key_val(r, flt), flt["value"])]
    for spec in reversed(req.get("sort", [])):          # stable multi-key sort; nulls / errors last
        desc = spec.get("order", "asc") == "desc"
        rows.sort(key=lambda r: (0, -key_val(r, spec) if desc else key_val(r, spec)) if _num(key_val(r, spec)) else (1, 0))
    if req.get("limit") is not None:
        rows = rows[:req["limit"]]
    resp = {"total": len(singles), "results": rows}
    if want_delta:
        resp["base"] = {"stats": project(base_single, fields)}
    return resp


# ---------------------------------------------------------------- comparison
def _close_delta(a, b):
    if a is None or b is None:
        return a is None and b is None
    return abs(a - b) <= DELTA_ABS_TOL


def compare(exp, got, limit=8):
    bad = []
    if not isinstance(got, dict) or "results" not in got:
        err = got.get("error") if isinstance(got, dict) else None
        return [f"no batch result: {json.dumps(err)[:200] if err else repr(got)[:200]}"]
    if got.get("total") != exp["total"]:
        bad.append(f"total {got.get('total')} != {exp['total']}")
    er, gr = exp["results"], got["results"]
    if [r["index"] for r in gr] != [r["index"] for r in er]:
        bad.append(f"result order/indices {[r['index'] for r in gr][:12]} != {[r['index'] for r in er][:12]}")
    if "base" in exp and json.dumps((got.get("base") or {}).get("stats"), sort_keys=True) != json.dumps(exp["base"]["stats"], sort_keys=True):
        bad.append("base.stats differs from the one-by-one base fit")
    gmap = {r["index"]: r for r in gr}
    for e in er:
        g = gmap.get(e["index"])
        if g is None:
            continue
        if g.get("label") != e["label"]:
            bad.append(f"[{e['index']}] label {g.get('label')!r} != {e['label']!r}")
        if "error" in e:
            if "error" not in g or g["error"].get("code") != e["error"]["code"]:
                bad.append(f"[{e['index']}] expected error {e['error']['code']}, got {json.dumps(g)[:120]}")
            continue
        if json.dumps(g.get("stats"), sort_keys=True) != json.dumps(e["stats"], sort_keys=True):
            if isinstance(e["stats"], dict) and isinstance(g.get("stats"), dict):
                diff = sorted(k for k in set(e["stats"]) | set(g["stats"]) if json.dumps(e["stats"].get(k), sort_keys=True) != json.dumps(g["stats"].get(k), sort_keys=True))
                bad.append(f"[{e['index']}] stats not identical to one-by-one calc (keys {diff[:6]})")
            else:
                bad.append(f"[{e['index']}] stats not identical to one-by-one calc")
        if "delta" in e:
            gd = g.get("delta") or {}
            wrong = [k for k in e["delta"] if not _close_delta(e["delta"][k], gd.get(k))]
            if wrong or set(gd) != set(e["delta"]):
                bad.append(f"[{e['index']}] delta wrong for {wrong[:6] or sorted(set(gd) ^ set(e['delta']))[:6]}")
        if len(bad) >= limit:
            break
    return bad
