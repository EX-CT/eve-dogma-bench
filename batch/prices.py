"""Reference price resolver for the batch-suite price cases (eve-fit-docs docs/23 §5–§6, DRAFT 8b1e6cf).
Pure function of: the fit's items, the override layers, the injected table, and SDE metadata (type -> group ->
category, market group tree from dataset r5). L4 (embedded snapshot) is empty in the first implementation (§5.2).

Interpretation points (flagged for F, docs/23 does not spell them out):
  - line `source` / `layer` = the entry that decided the price: the highest layer with an entry for the type (an
    override, else injected). With multipliers, `multiplier` = product of the multipliers on the way down, and
    `base_source` = source of the fixed price they apply to (None when no multiplier applied).
  - charge quantity = floor(module capacity / charge volume) (Pyfa getNumCharges), with a 1e-9 guard against FP.
  - ship line index 0; module / charge lines index = module index; other sections index = list index."""
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
    """layers: [("variant", [...]), ("request", [...]), ("injected", {tid: isk})] -> dict or None (+reason)"""
    mult, top = 1.0, None
    applied = False
    for name, layer in layers:
        if name == "injected":
            p = layer.get(str(t))
            if p is None:
                break
            src = "injected"
            if top is None:
                return {"unit_isk": float(p), "source": src, "layer": "injected", "multiplier": None, "base_source": None}
            return {"unit_isk": mult * p, "source": top[0], "layer": top[1], "multiplier": mult if applied else None,
                    "base_source": src if applied else None}
        e = entry_for(t, layer)
        if e is None:
            continue
        if top is None:
            top = (KIND_SOURCE[kind(e)], name)
        if "price" in e:
            src = KIND_SOURCE[kind(e)]
            return {"unit_isk": mult * e["price"], "source": top[0], "layer": top[1],
                    "multiplier": mult if applied else None, "base_source": src if applied else None}
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
    for sec, key in (("drones", "drones"), ("fighters", "fighters"), ("cargo", "cargo")):
        for i, d in enumerate(fit.get(key, [])):
            out.append((sec, i, d["type_id"], int(d.get("quantity", 1))))
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
                    source=r["source"], layer=r["layer"], multiplier=r["multiplier"], base_source=r["base_source"])
        s = secs.setdefault(sec, {"total_isk": 0.0, "items": []})
        s["items"].append(line)
        s["total_isk"] += line["total_isk"]
        sources[r["source"]] = sources.get(r["source"], 0) + 1
    return {"total_isk": sum(s["total_isk"] for s in secs.values()), "complete": not missing, "sections": secs,
            "missing": missing, "sources": sources}


def layers_for(req_level, variant_level, injected):
    """batch: L1 = variant/fit-entry/axis-option overrides, L2 = BatchRequest + FitRequest own overrides, L3 = injected"""
    return [("variant", variant_level or []), ("request", req_level or []), ("injected", injected or {})]


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
    if {k: v for k, v in (got.get("sources") or {}).items() if v} != exp["sources"]:
        bad.append(f"{where}sources {got.get('sources')} != {exp['sources']}")
    gs = got.get("sections") or {}
    for sec in SECTIONS:
        e, g = exp["sections"].get(sec), gs.get(sec)
        if e is None:
            if g and (g.get("items") or g.get("total_isk")):
                bad.append(f"{where}section {sec} should be empty")
            continue
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
            for k in ("quantity", "source", "layer", "base_source"):
                if x.get(k) != l[k]:
                    bad.append(f"{where}{sec}[{l['index']}].{k} {x.get(k)!r} != {l[k]!r}")
            for k in ("unit_isk", "total_isk", "multiplier"):
                if not _close(l[k], x.get(k)):
                    bad.append(f"{where}{sec}[{l['index']}].{k} {x.get(k)} != {l[k]}")
    return bad
