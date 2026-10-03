#!/usr/bin/env python3
"""price_* cases for the batch suite (eve-fit-docs docs/23 §5–§6): price_overrides by type / market group (incl.
children) / group / category, price 0 and multipliers, layer precedence (variant > request > injected; L4 snapshot
empty in the first implementation), per-line source, missing list, sections summing to the total, and batch variants /
product options / fit entries carrying their own overrides. Expected price blocks come from batch/prices.py (bench
reference resolver); stats must still equal one-by-one calc. Writes batch/cases/price_*.json and adds them to
batch/MANIFEST.json (kind "price"). usage: python3 batch/tools/gen_price_cases.py (after gen_batch.py)"""
import copy, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "batch"))
import prices as P, semantics as S  # noqa: E402

OUT = ROOT / "batch" / "cases"
BASE = json.loads((ROOT / "cases" / "exct_rifter.json").read_text())
BASE = copy.deepcopy(BASE)
BASE["implants"] = [20121, 20157]
BASE["boosters"] = [{"type_id": 10156}]
BASE["cargo"] = [{"type_id": 21898, "quantity": 1000}, {"type_id": 24473, "quantity": 200}]
TYPES = sorted({t for _, _, t, _ in P.items(BASE)})


def isk(t):
    return float(1000 + (t * 7919) % 100000 * 10)


INJ = {str(t): isk(t) for t in TYPES}
INJ_PARTIAL = {k: v for k, v in INJ.items() if int(k) not in (2048, 21898, 20157)}   # 3 types unpriced
PF = ["price.total_isk", "price.complete", "price.sections.modules.total_isk", "price.sections.charges.total_isk",
      "offense.total.dps.total", "defense.ehp.total"]
cases = {}


def add(cid, req, note):
    req = dict(req, batch_version=1, price=True)
    cases[cid] = (req, note)


one = lambda fid, fit, **kw: dict({"id": fid, "fit": fit}, **kw)  # noqa: E731
# ---- single-fit (form 1, one entry) checks of the resolver rules
add("price_injected_complete", {"fits": [one("rifter", BASE)], "prices": {"isk": INJ}, "fields": PF},
    "injected table prices every item: sources injected, complete, sections sum to total")
add("price_missing_list", {"fits": [one("rifter", BASE)], "prices": {"isk": INJ_PARTIAL}, "fields": PF},
    "3 types unpriced -> missing (no_price) with section/index/quantity; not in totals")
add("price_type_beats_injected", {"fits": [one("rifter", BASE)], "prices": {"isk": INJ},
                                  "price_overrides": [{"type_id": 2889, "price": 2500000}], "fields": PF},
    "request type override beats injected")
add("price_zero_self_made", {"fits": [one("rifter", BASE)], "prices": {"isk": INJ},
                             "price_overrides": [{"type_id": 2048, "price": 0}, {"type_id": 587, "price": 0}], "fields": PF},
    "price 0 (self-made): line kept with 0 ISK")
add("price_market_group_children", {"fits": [one("rifter", BASE)], "prices": {"isk": INJ},
                                    "price_overrides": [{"market_group_id": 9, "multiplier": 0.8}], "fields": PF},
    "market group 9 (Ship Equipment) matches modules in child market groups (deepest-first walk)")
add("price_market_group_deepest", {"fits": [one("rifter", BASE)], "prices": {"isk": INJ},
                                   "price_overrides": [{"market_group_id": 9, "price": 111}, {"market_group_id": 657, "price": 222},
                                                       {"market_group_id": 87, "multiplier": 2}], "fields": PF},
    "parent vs child market groups: the deepest matching group wins")
add("price_specificity_order", {"fits": [one("rifter", BASE)], "prices": {"isk": INJ},
                                "price_overrides": [{"category_id": 7, "price": 1}, {"group_id": 55, "price": 2},
                                                    {"market_group_id": 574, "price": 3}, {"type_id": 448, "price": 4},
                                                    {"group_id": 52, "price": 5}, {"category_id": 8, "multiplier": 1.5}],
                                "fields": PF},
    "type > market group > group > category within one layer (2889 -> mg 574; 448 -> type; 527 -> category)")
add("price_multiplier_without_base", {"fits": [one("rifter", BASE)], "prices": {"isk": INJ_PARTIAL},
                                      "price_overrides": [{"category_id": 7, "multiplier": 1.1}], "fields": PF},
    "multiplier over an unpriced type -> missing reason multiplier_without_base")
add("price_fit_level_overrides", {"fits": [one("rifter", dict(BASE, price_overrides=[{"group_id": 55, "price": 1000000}]))],
                                  "prices": {"isk": INJ}, "fields": PF},
    "the FitRequest's own price_overrides are layer L2 (request)")
# ---- layers / chains
add("price_chain_variant_over_request", {"base": BASE, "prices": {"isk": INJ},
                                         "price_overrides": [{"category_id": 7, "multiplier": 0.5}],
                                         "variants": [{"label": "x0.9 guns", "price_overrides": [{"type_id": 2889, "multiplier": 0.9}]},
                                                      {"label": "fixed guns", "price_overrides": [{"type_id": 2889, "price": 100}]},
                                                      {"label": "no variant layer"}],
                                         "fields": PF, "deltas": True},
    "L1 x0.9 over L2 x0.5 over injected (stacked 0.45); fixed L1 stops the chain; deltas on price")
add("price_variant_fixed_beats_request_fixed", {"base": BASE, "prices": {"isk": INJ},
                                                "price_overrides": [{"type_id": 587, "price": 5}],
                                                "variants": [{"label": "ship 7", "price_overrides": [{"type_id": 587, "price": 7}]},
                                                             {"label": "ship by category", "price_overrides": [{"category_id": 6, "price": 9}]}],
                                                "fields": PF},
    "variant layer beats request layer even when less specific")
# ---- batch forms with per-item overrides, sort / filter / deltas by price
add("price_variants_sort_filter", {"base": BASE, "prices": {"isk": INJ},
                                   "variants": [{"label": f"guns {p}", "price_overrides": [{"type_id": 2889, "price": p}]} for p in (0, 50000, 900000, 2500000)]
                                   + [{"label": "stock modules", "price_overrides": [{"category_id": 7, "price": 0}]},
                                      {"label": "T2 swap + market", "patch": [{"op": "replace", "path": "/modules/3/type_id", "value": 439}]}],
                                   "fields": PF, "deltas": True,
                                   "filter": [{"field": "price.total_isk", "op": "<=", "value": 1.535e8}],
                                   "sort_by": [{"field": "price.total_isk", "order": "asc"}]},
    "variants with their own overrides; filter + sort by price.total_isk; a patched variant with a type missing from the injected table")
add("price_product_options", {"base": BASE, "prices": {"isk": INJ},
                              "product": {"axes": [
                                  {"name": "ammo", "options": [{"id": "market", "label": "market ammo"},
                                                               {"id": "free", "label": "own ammo", "price_overrides": [{"category_id": 8, "price": 0}]}]},
                                  {"name": "mods", "options": [{"id": "x1", "label": "x1"},
                                                               {"id": "x09", "label": "x0.9", "price_overrides": [{"market_group_id": 9, "multiplier": 0.9}]},
                                                               {"id": "skills3", "label": "skills 3", "patch": [{"op": "replace", "path": "/character/skills/default_level", "value": 3}]}]}]},
                              "fields": PF, "deltas": True, "sort_by": [{"field": "price.total_isk", "order": "desc"}]},
    "axis options carry overrides (concatenated in axis order = one L1 layer)")
add("price_fits_entries", {"fits": [one("a", BASE, price_overrides=[{"type_id": 2889, "price": 0}]),
                                    one("b", BASE),
                                    one("c", dict(BASE, modules=BASE["modules"][:6]), price_overrides=[{"group_id": 60, "multiplier": 3}])],
                           "prices": {"isk": INJ}, "price_overrides": [{"group_id": 60, "multiplier": 0.5}],
                           "fields": PF, "sort_by": [{"field": "price.total_isk", "order": "asc"}]},
    "form 1 entries with their own L1 overrides over a batch-wide L2")

man = json.loads((ROOT / "batch" / "MANIFEST.json").read_text())
man = {k: v for k, v in man.items() if v["kind"] != "price"}
for p in OUT.glob("price_*.json"):
    p.unlink()
for cid, (req, note) in sorted(cases.items()):
    (OUT / f"{cid}.json").write_text(json.dumps(req, sort_keys=True) + "\n")
    ops = [o for o in ("fields", "deltas", "filter", "sort_by", "top_n") if req.get(o) not in (None, False, [])]
    man[cid] = {"kind": "price", "fits": len(S.expand3(req)), "ops": ops, "note": note}
(ROOT / "batch" / "MANIFEST.json").write_text(json.dumps(man, indent=1, sort_keys=True) + "\n")
print(len(cases), "price cases")
