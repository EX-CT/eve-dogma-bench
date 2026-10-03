#!/usr/bin/env python3
"""`overrides` cases (bench 1.11 draft, CONTRACT.md "Draft 1.11: overrides semantics").
  python3 ext/tools/gen_overrides.py
Pyfa-backed: ext/cases/ovr_*.json (feature "overrides", MANIFEST source "Pyfa oracle (attribute overrides)");
  expected values from ext/tools/make_expected.py (oracle `apply_overrides`: Pyfa's eos/saveddata/override.py).
Unit, hand-derived: ext/unit/cases/unit_ovr_*.json + ext/unit/expected (ext/unit/MANIFEST.json), each with a
  `derivation`: the six 1.10 hand-derived cases (renamed from ovr_*; Pyfa agrees with all six) and the parts of our
  contract that go beyond Pyfa (skill-type overrides, attributes the type does not have, overrides inside a nested
  projected / booster FitRequest)."""
import copy, json, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import gen_ext as g  # noqa: E402  (helpers only; gen_ext writes nothing on import)
ROOT = pathlib.Path(__file__).resolve().parents[2]
SUITE = ROOT / "ext"
tid, fit, mod, T, A = g.tid, g.fit, g.mod, g.T, g.A


def base(t, attr):
    return T[t]["attrs"].get(str(A[attr]))


def ov(t, attr, v, must_have=True):
    if must_have and base(t, attr) is None:
        raise SystemExit(f"{T[t]['name']} has no {attr}")
    return {"type_id": t, "attribute_id": A[attr], "value": float(v)}


pyfa, unit, uexp = {}, {}, {}


def P(name, req, ovs):
    req["overrides"] = ovs
    pyfa[name] = req


def U(name, req, ovs, values, derivation):
    req["overrides"] = ovs
    unit[name] = req
    uexp[name] = {"case": name, "oracle": "hand-derived (non-Pyfa)", "feature": "overrides-unit", "values": values,
                  "ext": {}, "derivation": derivation, "excluded": {}}


RIF, VEX = tid("Rifter"), tid("Vexor")
WEB = tid("Stasis Webifier I")
v0 = base(RIF, "maxVelocity")
# ---- the six 1.10 requests, now Pyfa-backed (same names) + their hand-derived twins as unit tests ----------------
six = [
    ("rifter_velocity_skills0", fit("Rifter", [], skills=0), [ov(RIF, "maxVelocity", 400)], {"max_velocity": 400.0},
     "Empty Rifter, all skills 0: no modifier touches maxVelocity, so max_velocity = the overridden base 400."),
    ("rifter_velocity_skills5", fit("Rifter", []), [ov(RIF, "maxVelocity", 400)], {"max_velocity": 500.0},
     "All skills V: Navigation +5%/level on ship maxVelocity -> 400 * 1.25 = 500."),
    ("rifter_shield_skills0", fit("Rifter", [], skills=0), [ov(RIF, "shieldCapacity", 1000)], {"hp.shield": 1000.0},
     "Skills 0, no modules: hp.shield = overridden shieldCapacity 1000."),
    ("rifter_shield_skills5", fit("Rifter", []), [ov(RIF, "shieldCapacity", 1000)], {"hp.shield": 1250.0},
     "Shield Management +5%/level on shieldCapacity: 1000 * 1.25 = 1250."),
]
lse = tid("Medium Shield Extender II")
sb = base(RIF, "shieldCapacity")
six.append(("module_shield_extender_x2", fit("Rifter", [("Medium Shield Extender II", 2, "online")], skills=0),
            [ov(lse, "capacityBonus", 1000)], {"hp.shield": sb + 2000.0},
            f"Skills 0: Rifter base shieldCapacity {sb} + 2 extenders x overridden capacityBonus 1000 (modAdd, not "
            f"stacking-penalised; the override applies to every module of that type) = {sb + 2000.0}."))
ac, emp = tid("200mm AutoCannon I"), tid("EMP S")
dm = base(ac, "damageMultiplier")
six.append(("charge_damage_volley", fit("Rifter", [("200mm AutoCannon I", 1, "active", "EMP S")], skills=0),
            [ov(emp, "emDamage", 100), ov(emp, "thermalDamage", 0), ov(emp, "kineticDamage", 0), ov(emp, "explosiveDamage", 0)],
            {"weapon_volley": 100.0 * dm},
            f"Skills 0 (no Gunnery / Minmatar Frigate bonuses): volley = charge damage (overridden to 100 EM, 0 else) x "
            f"200mm AutoCannon I damageMultiplier {dm} = {100.0 * dm}."))
for n, r, o, vals, der in six:
    P(f"ovr_{n}", copy.deepcopy(r), copy.deepcopy(o))
    U(f"unit_ovr_{n}", copy.deepcopy(r), copy.deepcopy(o), vals, der)

# ---- new Pyfa-backed cases -----------------------------------------------------------------------------------------
P("ovr_duplicate_last_wins", fit("Rifter", []), [ov(RIF, "maxVelocity", 400), ov(RIF, "maxVelocity", 600)])
P("ovr_ship_armor_plate_skills5", fit("Rifter", [("200mm Steel Plates II", 1, "online")]), [ov(RIF, "armorHP", 1000)])
mem = tid("Multispectrum Energized Membrane II")
P("ovr_module_resist_stacking", fit("Rifter", [("Multispectrum Energized Membrane II", 3, "online")]),
  [ov(mem, "emDamageResistanceBonus", -40)])
P("ovr_module_cpu_power", fit("Rifter", [("200mm AutoCannon I", 3, "active", "EMP S")]),
  [ov(ac, "cpu", 50), ov(ac, "power", 1)])
hob = tid("Hobgoblin II")
P("ovr_drone_damage", fit("Vexor", [], [("Hobgoblin II", 5, 5)]), [ov(hob, "damageMultiplier", 3.0)])
P("ovr_drone_hp", fit("Vexor", [], [("Hobgoblin II", 5, 5)]), [ov(hob, "shieldCapacity", 5000), ov(hob, "maxVelocity", 9000)])
imp = tid("Eifyr and Co. 'Rogue' Navigation NN-605")
P("ovr_implant", fit("Rifter", [], implants=[imp]), [ov(imp, "implantBonusVelocity", 20)])
xi = tid("Standard X-Instinct Booster")
P("ovr_booster", fit("Rifter", [], boosters=[{"type_id": xi, "side_effects": []}]), [ov(xi, "signatureRadiusBonus", -50)])
conf, dmode = tid("Confessor"), tid("Confessor Defense Mode")
r = fit("Confessor", [])
r["ship"]["mode_type_id"] = dmode
P("ovr_t3d_mode", r, [ov(dmode, "modeSignatureRadiusPostDiv", 3.0), ov(dmode, "modeEmResistancePostDiv", 3.0)])
wr = tid("Class 3 Wolf Rayet Effects")
r = fit("Rifter", [])
r["environment"]["effect_type_ids"] = [wr]
P("ovr_environment", r, [ov(wr, "armorHPMultiplier", 3.0), ov(wr, "signatureRadiusMultiplier", 0.5)])
# mutated module: the rolled value of a mutated attribute wins over an override; other attributes are overridable
MUT = {"base_type_id": tid("Damage Control II"), "mutaplasmid_type_id": 52224,
       "attributes": {"50": 37.5, "974": 0.63, "975": 0.63, "976": 0.63, "977": 0.63}}
adc = tid("Abyssal Damage Control")


def mutdc():
    r = fit("Rifter", [])
    m = mod("Abyssal Damage Control", "active")
    m["mutation"] = copy.deepcopy(MUT)
    r["modules"] = [m]
    return r


P("ovr_mutated_rolled_attr", mutdc(), [ov(adc, "hullEmDamageResonance", 0.1, must_have=False), ov(adc, "cpu", 1, must_have=False)])
P("ovr_mutated_other_attr", mutdc(), [ov(adc, "power", 7, must_have=False),
                                       ov(adc, "armorEmDamageResonance", 0.5, must_have=False)])
# projection: Pyfa overrides are global per type, so they reach projected modules / fits and booster fits too
r = fit("Rifter", [], skills=0)
r["projected"] = [{"kind": "module", "module": {"type_id": WEB, "state": "active"}, "amount": 1, "distance_m": 5000}]
P("ovr_projected_module", r, [ov(WEB, "speedFactor", -90)])
r = fit("Rifter", [], skills=0)
r["projected"] = [{"kind": "fit", "fit": fit("Rifter", [("Stasis Webifier I", 1, "active")], skills=0), "amount": 1, "distance_m": 5000}]
P("ovr_projected_fit_global", r, [ov(WEB, "speedFactor", -90)])
SHIELD = [("Medium Shield Booster II", 1), ("5MN Microwarpdrive II", 1), ("Warp Scrambler II", 1), ("Stasis Webifier II", 1)]
CLAY = fit("Claymore", [("Shield Command Burst II", 1, "active", "Shield Harmonizing Charge"),
                        ("Shield Command Burst II", 1, "active", "Shield Extension Charge")])
shc = tid("Shield Harmonizing Charge")
r = fit("Vexor", SHIELD)
r["fleet"]["booster_fits"] = [CLAY]
P("ovr_booster_fit_charge", r, [ov(shc, "warfareBuff1Multiplier", -20)])
tmp = tid("Templar II")
r = fit("Thanatos", [])
r["fighters"] = [{"type_id": tmp, "quantity": 6, "active": True, "abilities": None}]
P("ovr_fighter", r, [ov(tmp, "fighterAbilityAttackMissileDamageEM", 400), ov(tmp, "shieldCapacity", 9000)])

# ---- beyond Pyfa: hand-derived unit tests --------------------------------------------------------------------------
nav = tid("Navigation")
r = fit("Rifter", [], skills=0)
r["character"]["skills"]["levels"] = {str(nav): 5}
U("unit_ovr_skill_attribute", r, [ov(nav, "velocityBonus", 10)], {"max_velocity": v0 * 1.5},
  f"Skill-type override (Pyfa's Skill.getModifiedItemAttr reads the raw type attributes, so Pyfa ignores it): "
  f"only Navigation trained (V), velocityBonus overridden 5 -> 10 %/level: {v0} * (1 + 5 * 0.10) = {v0 * 1.5}.")
U("unit_ovr_attr_not_on_type", fit("Rifter", [], skills=0), [ov(RIF, "warpScrambleStatus", 2, must_have=False)],
  {"warp_scramble_status": 2.0},
  "Attribute the type does not have (Rifter has no warpScrambleStatus; Pyfa's Item.overrides only loads overrides "
  "for the type's own attributes, so Pyfa ignores it): the override adds the base value, warp_scramble_status = 2.")
r = fit("Rifter", [], skills=0)
pf = fit("Rifter", [("Stasis Webifier I", 1, "active")], skills=0)
pf["overrides"] = [ov(WEB, "speedFactor", -90)]
r["projected"] = [{"kind": "fit", "fit": pf, "amount": 1, "distance_m": 5000}]
U("unit_ovr_nested_projected_fit", r, [], {"max_velocity": v0 * 0.1},
  f"`overrides` inside a nested projected FitRequest apply to that fit (Pyfa has one global override table and "
  f"no per-fit overrides). Skills 0 on both: the projector's Stasis Webifier I speedFactor overridden -50 -> -90, "
  f"5 km (inside its 10 km optimal), single web, no stacking penalty: {v0} * (1 - 0.90) = {v0 * 0.1:.4f}.")
r = fit("Rifter", [], skills=0)
pf = fit("Rifter", [("Stasis Webifier I", 1, "active")], skills=0)
r["projected"] = [{"kind": "fit", "fit": pf, "amount": 1, "distance_m": 5000}]
U("unit_ovr_nested_projected_fit_control", r, [], {"max_velocity": v0 * 0.5},
  f"Control for unit_ovr_nested_projected_fit: same request without overrides, web -50 %: {v0} * 0.5 = {v0 * 0.5}.")

man = json.loads((SUITE / "MANIFEST.json").read_text())
for n in [n for n, m in man.items() if m["feature"] == "overrides"]:
    del man[n]
    for d in ("cases", "expected"):
        p = SUITE / d / f"{n}.json"
        if p.exists():
            p.unlink()
for n, r in pyfa.items():
    (SUITE / "cases" / f"{n}.json").write_text(json.dumps(r, indent=1, sort_keys=True) + "\n")
    man[n] = {"feature": "overrides", "source": "Pyfa oracle (attribute overrides)"}
(SUITE / "MANIFEST.json").write_text(json.dumps(man, indent=1, sort_keys=True) + "\n")
um = {}
for n, r in unit.items():
    (SUITE / "unit/cases" / f"{n}.json").write_text(json.dumps(r, indent=1, sort_keys=True) + "\n")
    (SUITE / "unit/expected" / f"{n}.json").write_text(json.dumps(uexp[n], indent=1, sort_keys=True) + "\n")
    um[n] = {"feature": "overrides-unit", "source": "hand-derived (non-Pyfa)"}
(SUITE / "unit/MANIFEST.json").write_text(json.dumps(um, indent=1, sort_keys=True) + "\n")
print(f"{len(pyfa)} Pyfa-backed overrides cases, {len(unit)} hand-derived unit cases")
