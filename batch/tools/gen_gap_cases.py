#!/usr/bin/env python3
"""gap_* and calcprice_* cases for the batch suite (docs/23 §2–§5, docs/22 §3–§4): filter ops `in` / `not_null`,
`delta_ref` (form 1), numeric sweeps from/to/step (int and float), the `swap_type` patch op, BATCH_TOO_LARGE (default
cap, ceiling, a lowered max_combinations), BAD_PRICE_OVERRIDE variants, `--prices FILE` (plain map and an
eve-price-snapshot v1 file), `use_snapshot: false`, and calc's own price block with price inputs (+ an embedded-snapshot
structural check). Writes batch/data/*.json, batch/cases/{gap,calcprice}_*.json and their MANIFEST entries
(kinds gap / gap_error / calc_price / calc_price_embedded; `engine_args` = global engine options before the subcommand).
usage: python3 batch/tools/gen_gap_cases.py (after gen_batch.py and gen_price_cases.py)"""
import copy, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "batch"))
import prices as P, semantics as S  # noqa: E402

OUT, DATA = ROOT / "batch" / "cases", ROOT / "batch" / "data"
BASE = copy.deepcopy(json.loads((ROOT / "cases" / "exct_rifter.json").read_text()))
BASE["cargo"] = [{"type_id": 21898, "quantity": 1000}]
TYPES = sorted({t for _, _, t, _ in P.items(BASE)} | {486, 520})
F = ["offense.total.dps.total", "defense.ehp.total", "navigation.max_velocity", "capacitor.stable"]
PF = F + ["price.total_isk", "price.complete"]


def isk(t, salt=0):
    return float(500 + (t * 7919 + salt * 104729) % 100000 * 10)


# ---- data files: a plain {type: isk} map and an eve-price-snapshot v1 file (different values, so the source shows)
MAP = {str(t): isk(t, 1) for t in TYPES if t != 31015}          # one rig unpriced -> missing
types = {}
for t in TYPES:
    p0 = isk(t, 2)
    types[str(t)] = {"price": round(p0 * 1.02, 2), "p0": p0, "band_max": p0 * 1.05, "units": 120, "orders": 4,
                     "units_considered": 900, "orders_considered": 15, "orders_total": 19}
SNAP = {"schema": "eve-price-snapshot", "schema_version": 1, "snapshot_id": "jita44-20261003T060000Z", "market": "jita44",
        "market_time": "2026-10-03T06:00:00Z", "generated_at": "2026-10-03T06:04:12Z",
        "source": {"kind": "esi", "endpoint": "synthetic (eve-dogma-bench batch/data)", "region_id": 10000002,
                   "location_id": 60003760, "fetched_from": "2026-10-03T05:58:40Z", "fetched_to": "2026-10-03T06:00:00Z"},
        "rule": {"name": "jita_sell_band_weighted", "version": 1, "order_side": "sell", "location_id": 60003760,
                 "min_units": 10, "band": 0.05, "weighting": "units", "exact": True},
        "currency": "ISK", "sde_build": 3569502, "type_count": len(types), "types": types, "missing": [],
        "updater": {"name": "eve-dogma-bench synthetic", "version": "1"}}
SNAP["content_hash"] = P.canonical_hash(SNAP)
DATA.mkdir(exist_ok=True)
(DATA / "prices-map.json").write_text(json.dumps(MAP, sort_keys=True) + "\n")
(DATA / "prices-jita44-20261003T060000Z.json").write_text(json.dumps(SNAP, sort_keys=True) + "\n")
A_MAP, A_SNAP = ["--prices", "batch/data/prices-map.json"], ["--prices", "batch/data/prices-jita44-20261003T060000Z.json"]

cases = {}


def add(cid, req, note, kind="gap", eargs=None, price=False):
    if kind.startswith("gap"):
        req = dict(req, batch_version=1, **({"price": True} if price else {}))
    cases[cid] = (req, note, kind, eargs or [])


one = lambda fid, fit, **kw: dict({"id": fid, "fit": fit}, **kw)  # noqa: E731
SK = lambda n: dict(BASE, character={"skills": {"default_level": n, "levels": {}}, "security_status": None})  # noqa: E731
FITS5 = [one(f"s{n}", SK(n)) for n in (1, 2, 3, 4, 5)]
# ---- filters / delta_ref
add("gap_filter_in", {"fits": FITS5, "fields": F,
                      "filter": [{"field": "capacitor.stable", "op": "in", "value": [True]},
                                 {"field": "navigation.max_velocity", "op": "not_null"}]},
    "filter op in (bool list) + not_null; booleans never equal 1/0")
add("gap_filter_in_numbers", {"fits": FITS5, "fields": F, "deltas": True, "delta_ref": "s5",
                              "filter": [{"field": "offense.total.dps.total", "op": "not_null", "on": "delta"}]},
    "not_null on delta: every fit has a delta against s5 (incl. s5 itself, delta 0)")
add("gap_filter_not_null_drops", {"fits": FITS5 + [one("noship", dict(BASE, modules=[], drones=[]))],
                                  "fields": F + ["offense.drones.dps.total"],
                                  "filter": [{"field": "offense.drones.dps.total", "op": "not_null"}]},
    "not_null drops fits where the field is null/absent")
add("gap_delta_ref", {"fits": FITS5, "fields": F, "deltas": True, "delta_ref": "s3",
                      "sort_by": [{"field": "offense.total.dps.total", "order": "desc", "on": "delta"}]},
    "form 1 delta_ref: deltas against the fit with id s3; no base block")
add("gap_delta_ref_pct_filter", {"fits": FITS5, "fields": F, "deltas": True, "delta_ref": "s1",
                                 "filter": [{"field": "defense.ehp.total", "op": ">", "value": 0, "on": "delta_pct"}]},
    "delta_ref + filter on delta_pct")
# ---- numeric sweeps (from/to/step)
DP = dict(BASE, damage_pattern={"em": 25, "explosive": 25, "kinetic": 25, "thermal": 25})
add("gap_sweep_int", {"base": BASE, "sweep": {"path": "/character/skills/default_level", "from": 1, "to": 5, "step": 2},
                      "fields": F, "deltas": True}, "int sweep 1,3,5")
add("gap_sweep_float", {"base": DP, "sweep": {"path": "/damage_pattern/em", "from": 0, "to": 100, "step": 12.5},
                        "fields": F, "deltas": True}, "float sweep 0..100 step 12.5 (9 values, labels path=value)")
add("gap_sweep_float_inexact", {"base": DP, "sweep": {"path": "/damage_pattern/thermal", "from": 0.1, "to": 0.7, "step": 0.3},
                                "fields": F}, "float sweep with an inexact step: 0.1, 0.4, 0.7 (from + k*step; to inclusive)")
add("gap_product_sweep_axis", {"base": DP, "product": {"axes": [
    {"name": "skills", "sweep": {"path": "/character/skills/default_level", "from": 3, "to": 5, "step": 1}},
    {"name": "em", "sweep": {"path": "/damage_pattern/em", "from": 0, "to": 50, "step": 25}}]},
    "fields": F, "deltas": True, "sort_by": [{"field": "defense.ehp.total", "order": "asc"}]}, "product of two numeric sweep axes")
# ---- swap_type
add("gap_swap_type", {"base": BASE, "variants": [
    {"id": "t1guns", "label": "T1 guns", "patch": [{"op": "swap_type", "from": 2889, "to": 486}]},
    {"id": "t1gyro", "label": "T1 gyro", "patch": [{"op": "swap_type", "from": 519, "to": 520}]},
    {"id": "absent", "label": "no match", "patch": [{"op": "swap_type", "from": 999999, "to": 486}]},
    {"id": "both", "label": "both + skills 4", "patch": [{"op": "swap_type", "from": 2889, "to": 486},
                                                         {"op": "swap_type", "from": 519, "to": 520},
                                                         {"op": "replace", "path": "/character/skills/default_level", "value": 4}]}],
    "fields": F, "deltas": True}, "swap_type replaces every module with type from; no match = unchanged fit")
# ---- request errors
add("gap_too_large_default", {"base": DP, "product": {"axes": [
    {"name": "skills", "sweep": {"path": "/character/skills/default_level", "from": 0, "to": 5, "step": 1}},
    {"name": "em", "sweep": {"path": "/damage_pattern/em", "from": 0, "to": 100, "step": 0.25}}]}, "fields": F},
    "6 x 401 = 2406 > default 2000 -> BATCH_TOO_LARGE {count 2406, limit 2000}", kind="gap_error")
add("gap_too_large_ceiling", {"base": DP, "max_combinations": 1000000,
                              "sweep": {"path": "/damage_pattern/em", "from": 0, "to": 100, "step": 0.0005}, "fields": F},
    "200001 > ceiling 100000 even with max_combinations 1e6 -> limit 100000", kind="gap_error")
add("gap_too_large_lowered", {"fits": FITS5 + FITS5[:1], "max_combinations": 5, "fields": F},
    "6 fits > max_combinations 5 -> BATCH_TOO_LARGE {6, 5}", kind="gap_error")
for cid, ov, note in [
        ("gap_bad_override_two_targets", [{"type_id": 2889, "group_id": 55, "price": 1}], "two targets in one entry"),
        ("gap_bad_override_no_target", [{"price": 1}], "no target"),
        ("gap_bad_override_both_values", [{"type_id": 2889, "price": 1, "multiplier": 2}], "price and multiplier"),
        ("gap_bad_override_no_value", [{"type_id": 2889}], "neither price nor multiplier"),
        ("gap_bad_override_negative", [{"type_id": 2889, "price": -1}], "negative price"),
        ("gap_bad_override_negative_mult", [{"group_id": 55, "multiplier": -0.5}], "negative multiplier"),
        ("gap_bad_override_string", [{"type_id": 2889, "price": "100"}], "non-number price"),
        ("gap_bad_override_duplicate", [{"type_id": 2889, "price": 1}, {"type_id": 2889, "multiplier": 2}], "duplicate target in one list")]:
    add(cid, {"fits": [one("a", BASE)], "price_overrides": ov, "fields": PF}, "BAD_PRICE_OVERRIDE: " + note,
        kind="gap_error", price=True)
add("gap_bad_override_in_variant", {"base": BASE, "variants": [{"label": "ok"}, {"label": "bad", "price_overrides": [{"category_id": 7}]}],
                                    "fields": PF}, "BAD_PRICE_OVERRIDE inside one variant fails the whole batch",
    kind="gap_error", price=True)
# ---- --prices files in batch
add("gap_prices_file_map", {"fits": [one("a", BASE), one("b", SK(3))], "fields": PF},
    "--prices plain map = L4 source injected; one rig unpriced -> missing", eargs=A_MAP, price=True)
add("gap_prices_file_snapshot", {"base": BASE, "variants": [{"label": "stock"}, {"label": "guns 1M", "price_overrides": [{"type_id": 2889, "price": 1e6}]},
                                                            {"label": "x0.5", "price_overrides": [{"category_id": 7, "multiplier": 0.5}]}],
                                 "fields": PF, "deltas": True},
    "--prices eve-price-snapshot v1: source injected, snapshot_time = market_time; overrides stack over it",
    eargs=A_SNAP, price=True)
add("gap_prices_request_over_file", {"fits": [one("a", BASE)], "prices": {"isk": {"2889": 777.0, "587": 1.0}}, "fields": PF},
    "request prices.isk beats the --prices file per type; others still from the file", eargs=A_SNAP, price=True)
add("gap_use_snapshot_false", {"fits": [one("a", BASE)], "prices": {"isk": {"2889": 777.0}, "use_snapshot": False}, "fields": PF},
    "use_snapshot false disables L4 (the file): only 2889 priced, the rest missing", eargs=A_SNAP, price=True)
add("gap_use_snapshot_false_fit", {"fits": [one("a", dict(BASE, prices={"isk": {"2889": 5.0}, "use_snapshot": False})), one("b", BASE)],
                                   "fields": PF},
    "a FitRequest's own use_snapshot false only affects that fit", eargs=A_MAP, price=True)
# ---- calc's own price block (kind calc_price: ENGINE [--prices F] calc <fit with price inputs>)
add("calcprice_request_table", {"fit": dict(BASE, prices={"isk": MAP})}, "calc with prices.isk: the price block", kind="calc_price")
add("calcprice_overrides", {"fit": dict(BASE, prices={"isk": MAP}, price_overrides=[{"group_id": 55, "multiplier": 0.9},
                                                                                     {"type_id": 31015, "price": 0}])},
    "calc with prices + price_overrides", kind="calc_price")
add("calcprice_file_map", {"fit": BASE}, "calc --prices map", kind="calc_price", eargs=A_MAP)
add("calcprice_file_snapshot", {"fit": dict(BASE, price_overrides=[{"category_id": 8, "price": 0}])},
    "calc --prices snapshot + an override", kind="calc_price", eargs=A_SNAP)
add("calcprice_request_over_file", {"fit": dict(BASE, prices={"isk": {"2889": 777.0}})}, "request > file", kind="calc_price", eargs=A_SNAP)
add("calcprice_use_snapshot_false", {"fit": dict(BASE, prices={"isk": {"2889": 777.0}, "use_snapshot": False})},
    "use_snapshot false ignores the file", kind="calc_price", eargs=A_SNAP)
add("calcprice_embedded_snapshot", {"fit": dict(BASE, options={"price": True})},
    "options.price, no price inputs: lines priced from the embedded snapshot carry source/layer snapshot and snapshot_time == "
    "provenance.price_time (structural; values unknown)", kind="calc_price_embedded")

man = json.loads((ROOT / "batch" / "MANIFEST.json").read_text())
man = {k: v for k, v in man.items() if not v["kind"].startswith(("gap", "calc_price"))}
for pat in ("gap_*.json", "calcprice_*.json"):
    for p in OUT.glob(pat):
        p.unlink()
for cid, (req, note, kind, eargs) in sorted(cases.items()):
    (OUT / f"{cid}.json").write_text(json.dumps(req, sort_keys=True) + "\n")
    ops = [o for o in ("fields", "deltas", "filter", "sort_by", "top_n") if req.get(o) not in (None, False, [])]
    n = 1 if kind.startswith("calc_price") else S.count(req)
    man[cid] = dict({"kind": kind, "fits": n, "ops": ops, "note": note}, **({"engine_args": eargs} if eargs else {}))
(ROOT / "batch" / "MANIFEST.json").write_text(json.dumps(man, indent=1, sort_keys=True) + "\n")
print(len(cases), "gap/calcprice cases")
