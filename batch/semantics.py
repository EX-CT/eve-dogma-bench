"""batch-suite reference semantics: eve-fit-docs docs/23 (batch API contract DRAFT, 8b1e6cf), see CONTRACT-BATCH.md.

Everything an engine's batch answer must equal is derived here from one-by-one FitRequest -> FitStats calls:
  expand(req)                      -> [(label, FitRequest)]        which fits the batch stands for, in order
  expected(req, singles, base)     -> normalized BatchResponse      what the batch answer must be
  compare(expected, got)           -> [mismatch strings]            empty = pass
The request/response *shape* lives in adapter.py; only adapter.py changes when the engine contract lands."""
import copy, json, math

DELTA_ABS_TOL = 1e-6   # deltas: round6(value - ref) from the emitted (6-dp) values; delta_pct = round6(delta/|ref|*100); within 1e-6
OPS = {"in": lambda a, b: a in b, "<": lambda a, b: a < b, "<=": lambda a, b: a <= b, ">": lambda a, b: a > b, ">=": lambda a, b: a >= b,
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
        if op["op"] == "swap_type":          # docs/23 §2.2 engine extension: every module with type_id == from
            for m in doc.get("modules", []):
                if m.get("type_id") == op["from"]:
                    m["type_id"] = op["to"]
            continue
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
def _sweep_values(sw):
    if "values" in sw:
        return list(sw["values"])
    out, k = [], 0
    while True:
        v = sw["from"] + k * sw["step"]
        if v > sw["to"] + 1e-9 * abs(sw["step"]):
            return out
        out.append(v)
        k += 1


def _cj(v):
    """sweep id / label value: compact JSON, keys sorted (docs/23 §2.3)"""
    return json.dumps(v, separators=(",", ":"), sort_keys=True)


def _sweep_options(sw):
    return [{"id": f"{sw['path']}={_cj(v)}", "label": f"{sw['path']}={_cj(v)}",
             "patch": [{"op": "add", "path": sw["path"], "value": v}]} for v in _sweep_values(sw)]


def expand3(req):
    """-> list of (id, label, FitRequest) in result-index order (docs/23 §2)."""
    if "fits" in req:
        out = []
        for i, it in enumerate(req["fits"]):
            fid = it.get("id", str(i))
            out.append((fid, it.get("label", fid), it["fit"]))
        return out
    base = req["base"]
    if "variants" in req:
        out = []
        for k, v in enumerate(req["variants"]):
            vid = v.get("id", f"v{k + 1}")
            out.append((vid, v.get("label", vid), apply_patch(base, v.get("patch", []))))
        return out
    axes = req["product"]["axes"] if "product" in req else [{"name": "sweep", "sweep": req["sweep"]}]
    combos = [([], [], [])]
    for ax in axes:
        opts = _sweep_options(ax["sweep"]) if "sweep" in ax else ax["options"]
        combos = [(ids + [o.get("id", str(n))], labels + [o.get("label", o.get("id", str(n)))], patch + o.get("patch", []))
                  for ids, labels, patch in combos for n, o in enumerate(opts)]
    return [("|".join(i), " × ".join(l), apply_patch(base, p)) for i, l, p in combos]


def l1_overrides(req):
    """docs/23 §5.2 L1 per expanded fit: fit entry / variant / axis option price_overrides (axis order)."""
    if "fits" in req:
        return [it.get("price_overrides", []) for it in req["fits"]]
    if "variants" in req:
        return [v.get("price_overrides", []) for v in req["variants"]]
    if "sweep" in req:
        return [[] for _ in _sweep_values(req["sweep"])]
    combos = [[]]
    for ax in req["product"]["axes"]:
        opts = _sweep_options(ax["sweep"]) if "sweep" in ax else ax["options"]
        combos = [c + o.get("price_overrides", []) for c in combos for o in opts]
    return combos


MAX_COMB_DEFAULT, MAX_COMB_CEILING = 2000, 100000


def count(req):
    """expansion size without expanding (docs/23 §2.3 cap)"""
    if "fits" in req:
        return len(req["fits"])
    if "variants" in req:
        return len(req["variants"])
    axes = req["product"]["axes"] if "product" in req else [{"sweep": req["sweep"]}]
    n = 1
    for ax in axes:
        n *= len(_sweep_values(ax["sweep"])) if "sweep" in ax else len(ax["options"])
    return n


def request_error(req):
    """whole-request error the engine must return instead of results, or None (docs/23 §2.3, §5.1, §8)"""
    n, lim = count(req), min(req.get("max_combinations", MAX_COMB_DEFAULT), MAX_COMB_CEILING)
    if n > lim:
        return {"code": "BATCH_TOO_LARGE", "count": n, "limit": lim}
    lists = [req.get("price_overrides", [])]
    lists += [it.get("price_overrides", []) for it in req.get("fits", []) + req.get("variants", [])]
    lists += [it["fit"].get("price_overrides", []) for it in req.get("fits", [])]
    if "base" in req:
        lists.append(req["base"].get("price_overrides", []))
    for ax in (req.get("product") or {}).get("axes", []):
        lists += [o.get("price_overrides", []) for o in ax.get("options", [])]
    targets = ("type_id", "market_group_id", "group_id", "category_id")
    for lst in lists:
        seen = set()
        for e in lst:
            tk = [k for k in targets if k in e]
            vk = [k for k in ("price", "multiplier") if k in e]
            if len(tk) != 1 or len(vk) != 1 or not isinstance(e[vk[0]], (int, float)) or isinstance(e[vk[0]], bool) \
                    or e[vk[0]] < 0 or (tk[0], e[tk[0]]) in seen:
                return {"code": "BAD_PRICE_OVERRIDE"}
            seen.add((tk[0], e[tk[0]]))
    return None


def expand(req):
    return [(label, fit) for _, label, fit in expand3(req)]


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


def _cmp(x):
    """filter / sort value: numbers, booleans as 0/1 (docs/23 §4.3); None otherwise"""
    if isinstance(x, bool):
        return int(x)
    return x if _num(x) else None


def delta(stats, base_stats, fields):
    return {f: (round(get_path(stats, f) - get_path(base_stats, f), 6)
                if _num(get_path(stats, f)) and _num(get_path(base_stats, f)) else None) for f in fields}


def delta_pct(d, base_stats, fields):
    out = {}
    for f in fields:
        ref = get_path(base_stats, f)
        out[f] = round(d[f] / abs(ref) * 100, 6) if d[f] is not None and _num(ref) and ref != 0 else None
    return out


def expected(req, singles, base_single=None):
    """singles: one-by-one engine outputs for expand(req), in order. base_single: output for req['base'] (deltas)."""
    fields = req.get("fields")
    want_delta = bool(req.get("deltas"))
    if want_delta and "fits" in req:      # form 1: reference = the fit with id == delta_ref (docs/23 §4.2)
        ids = [fid for fid, _, _ in expand3(req)]
        base_single = singles[ids.index(req["delta_ref"])]
    rows = []
    for i, ((fid, label, _), out) in enumerate(zip(expand3(req), singles)):
        r = {"index": i, "id": fid, "label": label}
        if isinstance(out, dict) and "error" in out:
            r["error"] = {"code": out["error"].get("code")}
        else:
            r["stats"] = project(out, fields)
            if req.get("price") and "price" in out:
                r["price"] = out["price"]
            if want_delta:
                r["delta"] = delta(out, base_single, fields)
                r["delta_pct"] = delta_pct(r["delta"], base_single, fields)
        rows.append(r)

    def key_val(r, spec):
        if "error" in r:
            return None
        on = spec.get("on", "value")
        src = r["delta"] if on == "delta" else r["delta_pct"] if on == "delta_pct" else r["stats"]
        return _cmp(src.get(spec["field"]) if fields is not None else get_path(src, spec["field"]))

    def raw_val(r, spec):
        if "error" in r:
            return None
        on = spec.get("on", "value")
        src = r["delta"] if on == "delta" else r["delta_pct"] if on == "delta_pct" else r["stats"]
        return src.get(spec["field"]) if fields is not None else get_path(src, spec["field"])

    def passes(r, flt):
        if "error" in r:
            return False
        if flt["op"] == "not_null":
            return raw_val(r, flt) is not None
        if flt["op"] == "in":
            v = raw_val(r, flt)
            return v is not None and any(v == x and isinstance(v, bool) == isinstance(x, bool) for x in flt["value"])
        v = key_val(r, flt)
        return v is not None and OPS[flt["op"]](v, flt["value"])

    for flt in req.get("filter", []):
        rows = [r for r in rows if passes(r, flt)]
    matched = len(rows)
    for spec in reversed(req.get("sort_by", req.get("sort", []))):   # stable multi-key sort; nulls / errors last
        desc = spec.get("order", "asc") == "desc"
        rows.sort(key=lambda r: (0, -key_val(r, spec) if desc else key_val(r, spec)) if key_val(r, spec) is not None else (1, 0))
    n = req.get("top_n", req.get("limit"))
    if n is not None:
        rows = rows[:n]
    resp = {"total": len(singles), "matched": matched, "results": rows}
    if want_delta and "fits" not in req:
        resp["base"] = {"stats": project(base_single, fields)}
        if req.get("price") and "price" in base_single:
            resp["base"]["price"] = base_single["price"]
    return resp


# ---------------------------------------------------------------- comparison
def _close_delta(a, b):
    if a is None or b is None:
        return a is None and b is None
    return abs(a - b) <= DELTA_ABS_TOL


def _noprov(st):
    """provenance is a result-level key (eve's ruling), never part of the stats identity"""
    return {k: v for k, v in st.items() if k != "provenance"} if isinstance(st, dict) else st


def compare(exp, got, limit=8):
    bad = []
    if "request_error" in exp:
        e = exp["request_error"]
        g = (got or {}).get("error") if isinstance(got, dict) else None
        if not isinstance(g, dict) or g.get("code") != e["code"]:
            return [f"expected request error {e['code']}, got {json.dumps(got)[:160]}"]
        det = dict(g, **(g.get("details") or {}), **(g.get("data") or {}))
        return [f"{e['code']}.{k} {det.get(k)} != {e[k]}" for k in ("count", "limit") if k in e and det.get(k) != e[k]]
    if not isinstance(got, dict) or "results" not in got:
        err = got.get("error") if isinstance(got, dict) else None
        return [f"no batch result: {json.dumps(err)[:200] if err else repr(got)[:200]}"]
    for k in ("total", "matched"):
        if got.get(k) != exp[k]:
            bad.append(f"{k} {got.get(k)} != {exp[k]}")
    er, gr = exp["results"], got["results"]
    if [r["index"] for r in gr] != [r["index"] for r in er]:
        bad.append(f"result order/indices {[r['index'] for r in gr][:12]} != {[r['index'] for r in er][:12]}")
    if "base" in exp and json.dumps((got.get("base") or {}).get("stats"), sort_keys=True) != json.dumps(exp["base"]["stats"], sort_keys=True):
        bad.append("base.stats differs from the one-by-one base fit")
    if "price" in exp.get("base", {}):
        import prices
        bad += prices.compare_block(exp["base"]["price"], (got.get("base") or {}).get("price"), "base.price: ")
    gmap = {r["index"]: r for r in gr}
    for e in er:
        g = gmap.get(e["index"])
        if g is None:
            continue
        for k in ("id", "label"):
            if g.get(k) != e[k]:
                bad.append(f"[{e['index']}] {k} {g.get(k)!r} != {e[k]!r}")
        if "error" in e:
            if "error" not in g or g["error"].get("code") != e["error"]["code"]:
                bad.append(f"[{e['index']}] expected error {e['error']['code']}, got {json.dumps(g)[:120]}")
            continue
        if json.dumps(_noprov(g.get("stats")), sort_keys=True) != json.dumps(_noprov(e["stats"]), sort_keys=True):
            if isinstance(e["stats"], dict) and isinstance(g.get("stats"), dict):
                diff = sorted(k for k in set(e["stats"]) | set(g["stats"]) if json.dumps(e["stats"].get(k), sort_keys=True) != json.dumps(g["stats"].get(k), sort_keys=True))
                bad.append(f"[{e['index']}] stats not identical to one-by-one calc (keys {diff[:6]})")
            else:
                bad.append(f"[{e['index']}] stats not identical to one-by-one calc")
        if "price" in e:
            import prices
            bad += prices.compare_block(e["price"], g.get("price"), f"[{e['index']}] price: ")
        if "delta" in e:
            gd = g.get("delta") or {}
            wrong = [k for k in e["delta"] if not _close_delta(e["delta"][k], gd.get(k))]
            if wrong or set(gd) != set(e["delta"]):
                bad.append(f"[{e['index']}] delta wrong for {wrong[:6] or sorted(set(gd) ^ set(e['delta']))[:6]}")
            gp = g.get("delta_pct") or {}
            wrong = [k for k in e["delta_pct"] if not _close_delta(e["delta_pct"][k], gp.get(k))]
            if wrong or set(gp) != set(e["delta_pct"]):
                bad.append(f"[{e['index']}] delta_pct wrong for {wrong[:6] or sorted(set(gp) ^ set(e['delta_pct']))[:6]}")
        if len(bad) >= limit:
            break
    return bad
