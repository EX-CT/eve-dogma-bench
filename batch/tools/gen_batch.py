#!/usr/bin/env python3
"""Generate batch/cases/<id>.json (BatchRequest, provisional shape) + batch/MANIFEST.json from the core (cases/) and
ext (ext/cases/) fits. Deterministic (fixed seeds, sorted inputs). Kinds:
  multi    - explicit list of independent fits ("fits")
  variants - one base fit + labelled JSON-Patch variants ("base" + "variants")
  product  - Cartesian product of patch axes ("base" + "product.axes")
  sweep    - one JSON pointer swept over values ("base" + "sweep")
Options exercised: fields (projection), deltas (vs base), filter, sort (incl. multi-key, on delta), limit.
usage: python3 batch/tools/gen_batch.py"""
import glob, json, random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "batch" / "cases"
STATES = ["offline", "online", "active", "overheated"]
F_DPS, F_EHP, F_VEL = "offense.total.dps.total", "defense.ehp.total", "navigation.max_velocity"
F_CAP, F_CPU, F_ALIGN = "capacitor.stable", "resources.cpu.used", "navigation.align_time_s"
F_VOLLEY, F_TANK = "offense.total.volley.total", "defense.tank.sustained_effective.armor"
FIELDS = [F_DPS, F_VOLLEY, F_EHP, F_VEL, F_ALIGN, F_CAP, F_CPU]


def load(pattern):
    out = {}
    for p in sorted(glob.glob(str(ROOT / pattern))):
        d = json.loads(Path(p).read_text())
        if isinstance(d, dict) and "ship" in d and "modules" in d:
            out[Path(p).stem] = d
    return out


CORE = load("cases/*.json")
EXT = load("ext/cases/*.json")
# charges seen per module type in the corpus (for charge variants)
CHARGES = {}
for f in list(CORE.values()) + list(EXT.values()):
    for m in f["modules"]:
        if m.get("charge_type_id"):
            CHARGES.setdefault(m["type_id"], set()).add(m["charge_type_id"])


def charged(f):
    return [i for i, m in enumerate(f["modules"]) if len(CHARGES.get(m["type_id"], ())) > 1 and m.get("charge_type_id")]


cases = {}


def add(cid, kind, req, note):
    assert cid not in cases, cid
    req = dict(req, batch_version="0.1-provisional")
    cases[cid] = {"kind": kind, "note": note, "request": req}


def pick(names, k, seed):
    return random.Random(seed).sample(sorted(names), k)


def fitlist(names, src=CORE):
    return [{"label": n, "fit": src[n]} for n in names]


# ------------------------------------------------------------------ multi
core_names = sorted(CORE)
add("multi_single", "multi", {"fits": fitlist(["exct_rifter"])}, "one fit, full FitStats")
add("multi_5_full", "multi", {"fits": fitlist(pick(core_names, 5, 1))}, "5 fits, full FitStats")
add("multi_10_fields", "multi", {"fits": fitlist(pick(core_names, 10, 2)), "fields": FIELDS}, "10 fits, projection")
add("multi_25_fields", "multi", {"fits": fitlist(pick(core_names, 25, 3)), "fields": FIELDS + [F_TANK]}, "25 fits, projection")
add("multi_100_full", "multi", {"fits": fitlist(pick(core_names, 100, 4))}, "100 fits, full FitStats")
add("multi_all_core", "multi", {"fits": fitlist(core_names), "fields": FIELDS}, "all core fits, projection")
add("multi_ext_mix", "multi", {"fits": fitlist(pick(sorted(EXT), 20, 5), EXT) + fitlist(pick(core_names, 10, 6)),
                               "fields": FIELDS}, "20 ext + 10 core fits")
dup = pick(core_names, 3, 7)
add("multi_duplicates", "multi", {"fits": fitlist(dup + dup[::-1] + dup)}, "same fits repeated: identical results, order kept")
bad = json.loads(json.dumps(CORE["exct_rifter"])); bad["ship"]["type_id"] = 999999999
add("multi_error_in_place", "multi", {"fits": fitlist(pick(core_names, 4, 8)) + [{"label": "bad_ship", "fit": bad}]
                                      + fitlist(pick(core_names, 3, 9)), "fields": FIELDS},
    "an unknown ship type errors in place (error code as one-by-one), neighbours unaffected")
add("multi_sort_dps_top10", "multi", {"fits": fitlist(pick(core_names, 60, 10)), "fields": FIELDS,
                                      "sort": [{"field": F_DPS, "order": "desc"}], "limit": 10}, "sort desc + limit")
add("multi_filter_fast", "multi", {"fits": fitlist(pick(core_names, 60, 11)), "fields": FIELDS,
                                   "filter": [{"field": F_VEL, "op": ">=", "value": 1000}]}, "filter on a field")
add("multi_filter_sort_2key", "multi", {"fits": fitlist(pick(core_names, 80, 12)), "fields": FIELDS,
                                        "filter": [{"field": F_EHP, "op": ">", "value": 5000}, {"field": F_DPS, "op": ">", "value": 0}],
                                        "sort": [{"field": F_CAP, "order": "desc"}, {"field": F_EHP, "order": "asc"}]},
    "two filters (AND) + two sort keys (bool desc, then ehp asc)")

# ------------------------------------------------------------------ variants
rng = random.Random(100)
var_bases = [n for n in core_names if n.startswith(("exct_", "esf_")) and len(CORE[n]["modules"]) >= 4 and CORE[n]["ship"]["type_id"]]
var_bases = sorted(var_bases)


def state_variants(f, idxs):
    out = []
    for i in idxs:
        for s in STATES:
            if s != f["modules"][i].get("state"):
                out.append({"label": f"m{i}:{s}", "patch": [{"op": "replace", "path": f"/modules/{i}/state", "value": s}]})
    return out


def charge_variants(f, i):
    m = f["modules"][i]
    return [{"label": f"m{i}:charge{c}", "patch": [{"op": "replace", "path": f"/modules/{i}/charge_type_id", "value": c}]}
            for c in sorted(CHARGES[m["type_id"]]) if c != m["charge_type_id"]]


def skill_variants(levels):
    return [{"label": f"skills{l}", "patch": [{"op": "replace", "path": "/character/skills/default_level", "value": l}]}
            for l in levels]


def struct_variants(f, idxs):
    out = []
    for i in idxs:
        out.append({"label": f"remove m{i}", "patch": [{"op": "remove", "path": f"/modules/{i}"}]})
        out.append({"label": f"dup m{i}", "patch": [{"op": "add", "path": "/modules/-", "value": f["modules"][i]}]})
    return out


DP = [None, {"em": 25, "thermal": 25, "kinetic": 25, "explosive": 25}, {"em": 0, "thermal": 0, "kinetic": 80, "explosive": 20},
      {"em": 10, "thermal": 45, "kinetic": 45, "explosive": 0}, {"em": 100, "thermal": 0, "kinetic": 0, "explosive": 0}]
withcharge = [n for n in var_bases if charged(CORE[n])]
for k, n in enumerate(pick(var_bases, 4, 101)):
    f = CORE[n]
    idx = sorted(random.Random(k).sample(range(len(f["modules"])), 2))
    add(f"variants_states_{k}", "variants", {"base": f, "variants": state_variants(f, idx), "fields": FIELDS, "deltas": True},
        f"{n}: every other state of 2 modules, deltas vs base")
for k, n in enumerate(pick(withcharge, 3, 102)):
    f = CORE[n]
    add(f"variants_charges_{k}", "variants", {"base": f, "variants": charge_variants(f, charged(f)[0]), "fields": FIELDS,
                                              "deltas": True, "sort": [{"field": F_DPS, "on": "delta", "order": "desc"}]},
        f"{n}: every corpus charge of module {charged(f)[0]}, sorted by dps delta")
for k, n in enumerate(pick(var_bases, 3, 103)):
    f = CORE[n]
    idx = sorted(random.Random(10 + k).sample(range(len(f["modules"])), 2))
    add(f"variants_struct_{k}", "variants", {"base": f, "variants": struct_variants(f, idx) + skill_variants([0, 3]),
                                             "fields": FIELDS + [F_TANK], "deltas": True,
                                             "filter": [{"field": F_EHP, "on": "delta", "op": "!=", "value": 0}]},
        f"{n}: remove / duplicate modules, skill levels; keep only variants whose ehp changed")
n = "exct_rifter"
add("variants_damage_pattern", "variants", {"base": CORE[n], "fields": [F_EHP, "defense.ehp.shield", "defense.ehp.armor", "defense.ehp.hull"],
                                            "deltas": True, "variants": [{"label": json.dumps(d), "patch": [{"op": "add", "path": "/damage_pattern", "value": d}]} for d in DP]},
    "damage patterns change ehp only")
add("variants_full_output", "variants", {"base": CORE["exct_rifter"], "variants": state_variants(CORE["exct_rifter"], [0, 3])},
    "no projection: full FitStats per variant")

# ------------------------------------------------------------------ product
for k, n in enumerate(pick(withcharge, 4, 200)):
    f = CORE[n]
    ci = charged(f)[0]
    other = [i for i in range(len(f["modules"])) if i != ci][:1]
    axes = [skill_variants([0, 3, 5]),
            [{"label": "as-is", "patch": []}] + charge_variants(f, ci)[:3],
            [{"label": f"m{other[0]}:{s}", "patch": [{"op": "replace", "path": f"/modules/{other[0]}/state", "value": s}]} for s in ("online", "active")]]
    req = {"base": f, "product": {"axes": axes}, "fields": FIELDS, "deltas": True}
    if k % 2:
        req.update(sort=[{"field": F_DPS, "order": "desc"}, {"field": F_CPU, "order": "asc"}], limit=5)
    add(f"product_skill_charge_state_{k}", "product", req, f"{n}: skills × charge × state")
def first_slot(f, slot):
    return next((i for i, m in enumerate(f["modules"]) if m.get("slot") == slot), None)


hm_bases = [n for n in var_bases if first_slot(CORE[n], "high") is not None and first_slot(CORE[n], "mid") is not None]
for k, n in enumerate(pick(hm_bases, 4, 201)):
    f = CORE[n]
    i, j = first_slot(f, "high"), first_slot(f, "mid")
    axes = [[{"label": f"m{i}:{s}", "patch": [{"op": "replace", "path": f"/modules/{i}/state", "value": s}]} for s in STATES],
            [{"label": f"m{j}:{s}", "patch": [{"op": "replace", "path": f"/modules/{j}/state", "value": s}]} for s in STATES],
            [{"label": "dp-none", "patch": [{"op": "add", "path": "/damage_pattern", "value": None}]},
             {"label": "dp-kin", "patch": [{"op": "add", "path": "/damage_pattern", "value": DP[2]}]}]]
    req = {"base": f, "product": {"axes": axes}, "fields": FIELDS + [F_TANK], "deltas": True}
    if k >= 2:
        req["filter"] = ([{"field": F_DPS, "on": "delta", "op": ">", "value": 0}] if k == 2
                         else [{"field": F_VEL, "on": "delta", "op": "<", "value": 0}, {"field": F_EHP, "op": ">", "value": 0}])
    add(f"product_states_dp_{k}", "product", req, f"{n}: 4 states × 4 states × 2 damage patterns")
f = CORE["exct_rifter"]
add("product_full_output", "product", {"base": f, "product": {"axes": [skill_variants([1, 4]), state_variants(f, [1])[:2]]}},
    "small product, full FitStats")

# ------------------------------------------------------------------ sweep
for k, n in enumerate(pick(core_names, 4, 300)):
    add(f"sweep_skills_{k}", "sweep", {"base": CORE[n], "sweep": {"path": "/character/skills/default_level", "values": [0, 1, 2, 3, 4, 5]},
                                      "fields": FIELDS, "deltas": True}, f"{n}: default skill level 0..5")
for k, n in enumerate(pick(var_bases, 3, 301)):
    i = random.Random(30 + k).randrange(len(CORE[n]["modules"]))
    add(f"sweep_state_{k}", "sweep", {"base": CORE[n], "sweep": {"path": f"/modules/{i}/state", "values": STATES},
                                     "fields": FIELDS, "deltas": True, "sort": [{"field": F_CAP, "order": "asc"}, {"field": F_CPU, "order": "desc"}]},
        f"{n}: module {i} state sweep, sorted by cap stable (false first) then cpu desc")
for k, n in enumerate(pick(withcharge, 2, 302)):
    i = charged(CORE[n])[0]
    add(f"sweep_charge_{k}", "sweep", {"base": CORE[n], "sweep": {"path": f"/modules/{i}/charge_type_id", "values": sorted(CHARGES[CORE[n]['modules'][i]['type_id']])},
                                      "fields": FIELDS, "deltas": True, "sort": [{"field": F_VOLLEY, "order": "desc"}], "limit": 3},
        f"{n}: module {i} charge sweep, top 3 volley")
add("sweep_damage_pattern", "sweep", {"base": CORE["exct_rifter"], "sweep": {"path": "/damage_pattern", "values": DP},
                                     "fields": [F_EHP], "deltas": True, "sort": [{"field": F_EHP, "order": "asc"}]}, "damage pattern sweep")
add("sweep_skill_override_full", "sweep", {"base": CORE["exct_rifter"], "sweep": {"path": "/character/skills/levels", "values": [{}, {"3300": 0}, {"3300": 3}]}},
    "per-skill override sweep (Gunnery 3300), full FitStats")

OUT.mkdir(parents=True, exist_ok=True)
for old in OUT.glob("*.json"):
    old.unlink()
import sys
sys.path.insert(0, str(ROOT / "batch"))
import semantics  # noqa: E402
man = {}
for cid, c in sorted(cases.items()):
    (OUT / f"{cid}.json").write_text(json.dumps(c["request"], sort_keys=True) + "\n")
    r = c["request"]
    ops = [o for o in ("fields", "deltas", "filter", "sort", "limit") if r.get(o) not in (None, False, [])]
    man[cid] = {"kind": c["kind"], "fits": len(semantics.expand(r)), "ops": ops, "note": c["note"]}
(ROOT / "batch" / "MANIFEST.json").write_text(json.dumps(man, indent=1, sort_keys=True) + "\n")
from collections import Counter
print(len(man), "cases", dict(Counter(m["kind"] for m in man.values())), "fits", sum(m["fits"] for m in man.values()))
print("ops", dict(Counter(o for m in man.values() for o in m["ops"])))
