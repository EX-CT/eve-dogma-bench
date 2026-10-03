"""Reference price resolver for the batch-suite price cases (eve-fit-docs docs/23 §5–§6, DRAFT 8b1e6cf).
Pure function of: the fit's items, the override layers, the injected table, and SDE metadata (type -> group ->
category, market group tree from dataset r5). L4 (embedded snapshot) is empty in the first implementation (§5.2).

Rulings (eve, 2026-10-03, docs/23):
  - line `source` / `layer` = the highest layer with an entry for the type; `multiplier` = product of all stacked
    multipliers (1 when none); `base_source` = source of the base price (injected, snapshot or a fixed-price
    override; = source when no multiplier applied).
  - charge quantity = floor(module capacity / charge volume) (Pyfa getNumCharges), 1e-9 guard against FP.
  - ship line index 0; module / charge lines index = module index; other sections index = list index.
Bench interpretation (not ruled): a `--prices` file is L4 with `source` "injected" and `layer` "snapshot";
line / block `snapshot_time` = the L4 market_time (null for a plain map file or non-L4 lines)."""
import gzip, json, math, os
from functools import lru_cache

DATASET_R5 = os.environ.get("EVE_DOGMA_DATASET_R5", "/workspace/exct-eve/data/dataset-3569502-r5.json.gz")
SECTIONS = ("ship", "modules", "charges", "drones", "fighters", "implants", "boosters", "cargo")
KIND_SOURCE = {"type_id": "override:type", "market_group_id": "override:market_group", "group_id": "override:group",
               "category_id": "override:category"}


@lru_cache(maxsize=1)
def ds():
    return json.load(gzip.open(DATASET_R5))


def tinfo(t):
    return ds()["types"][str(t)]


def mg_chain(t):
    """market group of type t and its ancestors, deepest first"""
    out, g = [], tinfo(t).get("market_group")
    while g is not None:
        out.append(g)
        g = ds()["market_groups"].get(str(g), {}).get("parent")
    return out


def entry_for(t, layer):
    """most specific entry of an override layer (list) for type t: type > market group (deepest) > group > category"""
    info = tinfo(t)
    for e in layer:
        if e.get("type_id") == t:
            return e
    for g in mg_chain(t):
        for e in layer:
            if e.get("market_group_id") == g:
                return e
    for e in layer:
        if e.get("group_id") == info.get("group"):
            return e
    for e in layer:
        if e.get("category_id") == info.get("category"):
            return e
    return None


def kind(e):
    return next(k for k in KIND_SOURCE if k in e)


def resolve(t, layers):
    """layers: [("variant", [..]), ("request", [..]), ("injected", {tid: isk}), ("snapshot", L4 or None)]
    L4 = {"isk": {tid: isk}, "label": "injected" (--prices file / prices_load) | "snapshot" (embedded), "time": str|None}.
    Rulings (eve, docs/23): source/layer = highest layer with an entry for the type; multiplier = product of all stacked
    multipliers (1 when none); base_source = source of the base price (injected, snapshot or a fixed-price override);
    with no multiplier base_source = source."""
    mult, top, applied = 1.0, None, False

    def done(unit, src, layer, stime=None):
        s0, l0 = top if top else (src, layer)
        return {"unit_isk": mult * unit, "source": s0, "layer": l0, "multiplier": mult,
                "base_source": src, "snapshot_time": stime}
    for name, layer in layers:
        if name == "injected":
            p = (layer or {}).get(str(t))
            if p is not None:
                return done(float(p), "injected", "injected")
            continue
        if name == "snapshot":
            if layer and str(t) in layer["isk"]:
                return done(float(layer["isk"][str(t)]), layer["label"], "snapshot", layer.get("time"))
            continue
        e = entry_for(t, layer)
        if e is None:
            continue
        if top is None:
            top = (KIND_SOURCE[kind(e)], name)
        if "price" in e:
            return done(float(e["price"]), KIND_SOURCE[kind(e)], name)
        mult *= e["multiplier"]
        applied = True
    return {"missing": "multiplier_without_base" if applied else "no_price"}


def items(fit):
    """(section, index, type_id, quantity) per priced item, docs/23 §6.2"""
    out = [("ship", 0, fit["ship"]["type_id"], 1)]
    for i, m in enumerate(fit.get("modules", [])):
        t = (m.get("mutation") or {}).get("base_type_id") or m["type_id"]
        out.append(("modules", i, t, 1))
        c = m.get("charge_type_id")
        if c:
            cap, vol = tinfo(m["type_id"]).get("capacity") or 0, tinfo(c).get("volume") or 0
            n = int(math.floor(cap / vol + 1e-9)) if vol else 0
            out.append(("charges", i, c, n))
    for i, d in enumerate(fit.get("drones", [])):         # mutated drones are priced as their base type (F, docs/23 §11.5)
        out.append(("drones", i, (d.get("mutation") or {}).get("base_type_id") or d["type_id"], int(d.get("quantity", 1))))
    for i, d in enumerate(fit.get("fighters", [])):       # no quantity -> squadron max size (attr 2215; F, docs/23 §11.5)
        q = d.get("quantity")
        if q is None:
            q = (tinfo(d["type_id"]).get("attrs") or {}).get("2215") or 1
        out.append(("fighters", i, d["type_id"], int(q)))
    for i, d in enumerate(fit.get("cargo", [])):
        out.append(("cargo", i, d["type_id"], int(d.get("quantity", 1))))
    for sec in ("implants", "boosters"):
        for i, x in enumerate(fit.get(sec, [])):
            out.append((sec, i, x if isinstance(x, int) else x["type_id"], 1))
    return out


def price_block(fit, layers):
    secs, missing, sources = {}, [], {}
    for sec, i, t, q in items(fit):
        r = resolve(t, layers)
        if "missing" in r:
            missing.append({"section": sec, "index": i, "type_id": t, "quantity": q, "reason": r["missing"]})
            continue
        line = dict(index=i, type_id=t, quantity=q, unit_isk=r["unit_isk"], total_isk=r["unit_isk"] * q,
                    source=r["source"], layer=r["layer"], multiplier=r["multiplier"], base_source=r["base_source"],
                    snapshot_time=r["snapshot_time"])
        s = secs.setdefault(sec, {"total_isk": 0.0, "items": []})
        s["items"].append(line)
        s["total_isk"] += line["total_isk"]
        sources[r["source"]] = sources.get(r["source"], 0) + 1
    for sec in SECTIONS:                                  # all eight sections always present (F, docs/23 §11.2)
        secs.setdefault(sec, {"total_isk": 0.0, "items": []})
    secs = {k: secs[k] for k in SECTIONS}
    times = sorted({l["snapshot_time"] for s in secs.values() for l in s["items"] if l["snapshot_time"]})
    return {"total_isk": sum(s["total_isk"] for s in secs.values()), "complete": not missing, "sections": secs,
            "missing": missing, "sources": sources, "snapshot_time": times[0] if times else None}


def layers_for(req_level, variant_level, injected, l4=None):
    """L1 = variant / fit-entry / axis-option overrides, L2 = BatchRequest + FitRequest own overrides,
    L3 = request prices.isk (fit's own table wins per type), L4 = --prices file or embedded snapshot (None = empty)"""
    return [("variant", variant_level or []), ("request", req_level or []), ("injected", injected or {}), ("snapshot", l4)]


REL = 1e-9


def _close(a, b):
    if a is None or b is None:
        return a is None and b is None
    return abs(a - b) <= REL * max(1.0, abs(a), abs(b))


def compare_block(exp, got, where=""):
    bad = []
    if not isinstance(got, dict):
        return [f"{where}price block missing"]
    if not _close(exp["total_isk"], got.get("total_isk")):
        bad.append(f"{where}total_isk {got.get('total_isk')} != {exp['total_isk']}")
    if got.get("complete") != exp["complete"]:
        bad.append(f"{where}complete {got.get('complete')} != {exp['complete']}")
    gm = sorted((m.get("section"), m.get("index"), m.get("type_id"), m.get("quantity"), m.get("reason")) for m in got.get("missing", []))
    em = sorted((m["section"], m["index"], m["type_id"], m["quantity"], m["reason"]) for m in exp["missing"])
    if gm != em:
        bad.append(f"{where}missing {gm[:4]} != {em[:4]}")
    # docs/23 §6 (eccf455): no block-level snapshot_time / source list; provenance carries them
    gs = got.get("sections") or {}
    for sec in SECTIONS:
        e, g = exp["sections"].get(sec), gs.get(sec)
        if not g:
            bad.append(f"{where}section {sec} missing")
            continue
        if not _close(e["total_isk"], g.get("total_isk")):
            bad.append(f"{where}{sec}.total_isk {g.get('total_isk')} != {e['total_isk']}")
        gl = {(l.get("index"), l.get("type_id")): l for l in g.get("items", [])}
        if len(gl) != len(e["items"]):
            bad.append(f"{where}{sec}: {len(gl)} lines != {len(e['items'])}")
        for l in e["items"]:
            x = gl.get((l["index"], l["type_id"]))
            if x is None:
                bad.append(f"{where}{sec}[{l['index']}] type {l['type_id']} line missing")
                continue
            for k in ("quantity", "source", "layer", "base_source", "snapshot_time"):
                if x.get(k) != l[k]:
                    bad.append(f"{where}{sec}[{l['index']}].{k} {x.get(k)!r} != {l[k]!r}")
            for k in ("unit_isk", "total_isk", "multiplier"):
                if not _close(l[k], x.get(k)):
                    bad.append(f"{where}{sec}[{l['index']}].{k} {x.get(k)} != {l[k]}")
    return bad


def _es_num(x):
    """ECMAScript Number.prototype.toString (JCS / RFC 8785 §3.2.2.3)"""
    from decimal import Decimal
    if isinstance(x, bool) or not math.isfinite(x):
        raise ValueError(f"not a JCS number: {x!r}")
    if x == 0:
        return "0"
    if x < 0:
        return "-" + _es_num(-x)
    t = Decimal(repr(float(x))).normalize().as_tuple() if isinstance(x, float) else Decimal(int(x)).normalize().as_tuple()
    if isinstance(x, int) and abs(x) >= 2 ** 53:
        t = Decimal(repr(float(x))).normalize().as_tuple()
    digits = "".join(map(str, t.digits))
    k, n = len(digits), len(t.digits) + t.exponent
    if k <= n <= 21:
        return digits + "0" * (n - k)
    if 0 < n <= 21:
        return digits[:n] + "." + digits[n:]
    if -6 < n <= 0:
        return "0." + "0" * (-n) + digits
    e = n - 1
    return digits[0] + ("." + digits[1:] if k > 1 else "") + "e" + ("+" if e > 0 else "-") + str(abs(e))


def jcs(v):
    """RFC 8785 canonical JSON (keys sorted by UTF-16 code units, ES number form)"""
    if v is None or isinstance(v, bool):
        return json.dumps(v)
    if isinstance(v, (int, float)):
        return _es_num(v)
    if isinstance(v, str):
        return json.dumps(v, ensure_ascii=False)
    if isinstance(v, list):
        return "[" + ",".join(jcs(x) for x in v) + "]"
    if isinstance(v, dict):
        ks = sorted(v, key=lambda k: k.encode("utf-16-be"))
        return "{" + ",".join(json.dumps(k, ensure_ascii=False) + ":" + jcs(v[k]) for k in ks) + "}"
    raise TypeError(type(v))


def canonical_hash(obj):
    """docs/22 §4.6 (eccf455) content_hash: "sha256:" + SHA-256 of the RFC 8785 JCS form without content_hash"""
    import hashlib
    o = {k: v for k, v in obj.items() if k != "content_hash"}
    return "sha256:" + hashlib.sha256(jcs(o).encode("utf-8")).hexdigest()


def load_l4(path):
    """--prices FILE -> L4 dict: eve-price-snapshot v1 (label injected, time = market_time) or a plain map"""
    d = json.load(gzip.open(path) if str(path).endswith(".gz") else open(path))
    if d.get("schema") == "eve-price-snapshot":
        return {"isk": {k: v["price"] for k, v in d["types"].items()}, "label": "injected", "time": d["market_time"]}
    return {"isk": {k: float(v) for k, v in d.items()}, "label": "injected", "time": None}
