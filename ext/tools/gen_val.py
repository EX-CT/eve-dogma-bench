#!/usr/bin/env python3
"""Cases for docs/19 ENG-OFF-003 (damage vs target profile), ENG-TGT-004 (probe size) and ENG-VAL-001..006
(violation codes), bench 1.11 draft.
  python3 ext/tools/gen_val.py
Pyfa-backed (ext/cases, expected from ext/tools/make_expected.py with ORACLE_EXTRA=ext,profile,validity):
  tp_*    feature vs_target_profile  -> /offense/vs_target_profile/{dps,volley}
  probe_* feature probe_size         -> /targeting/probe_size
  val_*   feature validity           -> `violations` (distinct codes; draft: per-module indices, missing skill ids)
Hand-derived (ext/unit, Pyfa has no equivalent check / option): unit_val_*."""
import copy, json, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import gen_ext as g  # noqa: E402
SUITE = pathlib.Path(__file__).resolve().parents[1]
tid, fit, mod = g.tid, g.fit, g.mod
cases, unit, uexp = {}, {}, {}


def C(name, feature, req):
    cases[name] = (feature, req)


def TP(em, th, ki, ex, sig=125.0, vel=0.0):
    return {"em": em, "thermal": th, "kinetic": ki, "explosive": ex, "signature_radius": sig, "max_velocity": vel, "radius": None}


# ---- ENG-OFF-003: damage vs target profile ----------------------------------------------------------------------
GUNS = fit("Rifter", [("200mm AutoCannon II", 3, "active", "EMP S"), ("Gyrostabilizer II", 2, "online")])
for n, tp in (("uniform0", TP(0, 0, 0, 0)), ("frigate_t1", TP(0.0, 0.2, 0.4, 0.5, 35)), ("armor_t2", TP(0.5, 0.45, 0.25, 0.1, 400)),
              ("shield_t2", TP(0.0, 0.2, 0.4, 0.5)), ("immune_em", TP(1.0, 0.0, 0.0, 0.0))):
    r = copy.deepcopy(GUNS); r["target_profile"] = tp
    C(f"tp_rifter_ac_{n}", "vs_target_profile", r)
r = fit("Vexor", [], [("Hammerhead II", 5, 5)]); r["target_profile"] = TP(0.3, 0.5, 0.4, 0.6)
C("tp_vexor_drones", "vs_target_profile", r)
r = fit("Vexor", [("Heavy Neutron Blaster II", 1, "active", "Void M"), ("Heavy Electron Blaster II", 3, "active", "Antimatter Charge M")],
        [("Hobgoblin II", 5, 5)]); r["target_profile"] = TP(0.55, 0.45, 0.35, 0.2, 140)
C("tp_vexor_guns_drones", "vs_target_profile", r)
r = fit("Kestrel", [("Light Missile Launcher II", 4, "active", "Scourge Light Missile")]); r["target_profile"] = TP(0.1, 0.2, 0.75, 0.3, 30, 400)
C("tp_kestrel_missiles_kinetic", "vs_target_profile", r)
r = fit("Thanatos", []); r["fighters"] = [{"type_id": tid("Templar II"), "quantity": 6, "active": True, "abilities": None}]
r["target_profile"] = TP(0.4, 0.3, 0.2, 0.1, 400)
C("tp_thanatos_fighters", "vs_target_profile", r)
r = fit("Rifter", [("200mm AutoCannon II", 3, "active", "EMP S")], skills=0); r["target_profile"] = TP(0.25, 0.25, 0.25, 0.25)
C("tp_rifter_skills0", "vs_target_profile", r)
r = fit("Rifter", []); r["target_profile"] = TP(0.5, 0.5, 0.5, 0.5)
C("tp_rifter_no_weapons", "vs_target_profile", r)
# ---- ENG-TGT-004: probe size -------------------------------------------------------------------------------------
for ship in ("Rifter", "Heron", "Vexor", "Dominix", "Ibis", "Thanatos", "Hel"):
    C(f"probe_{ship.lower()}", "probe_size", fit(ship, []))
C("probe_rifter_mwd", "probe_size", fit("Rifter", [("5MN Microwarpdrive II", 1, "active")]))
C("probe_heron_sensor_booster", "probe_size", fit("Heron", [("Sensor Booster II", 1, "active")]))
C("probe_rifter_skills0", "probe_size", fit("Rifter", [], skills=0))
# ---- ENG-VAL-001..006: violation codes ---------------------------------------------------------------------------
C("val_clean_rifter", "validity", fit("Rifter", [("200mm AutoCannon II", 3, "active", "EMP S"), ("1MN Afterburner II", 1)]))
C("val_slots_high", "validity", fit("Rifter", [("Salvager I", 4, "active")]))
C("val_slots_mid_low_rig", "validity", fit("Rifter", [("1MN Afterburner II", 1), ("Medium Shield Extender II", 3, "online"),
                                                      ("Damage Control II", 1, "online"), ("Gyrostabilizer II", 4, "online"),
                                                      ("Small Core Defense Field Extender I", 4, "online")]))
C("val_turret_hardpoints", "validity", fit("Heron Navy Issue", [("125mm Gatling AutoCannon I", 1, "active")]))
C("val_launcher_hardpoints", "validity", fit("Rifter", [("Rocket Launcher I", 3, "active")]))
C("val_cpu_power_overload", "validity", fit("Rifter", [("Medium Shield Extender II", 3, "online"), ("200mm AutoCannon II", 3, "active", "EMP S")]))
C("val_drone_bandwidth", "validity", fit("Vexor", [], [("Ogre II", 4, 4)]))
C("val_ship_restriction_burst", "validity", fit("Rifter", [("Shield Command Burst I", 1, "online")]))
C("val_capital_module_subcap", "validity", fit("Vexor", [("Capital Armor Repairer I", 1, "online")]))
C("val_rig_size", "validity", fit("Rifter", [("Medium Core Defense Field Extender I", 1, "online")]))
C("val_max_group_fitted", "validity", fit("Rifter", [("Damage Control II", 2, "online")]))
C("val_max_group_active", "validity", fit("Rifter", [("1MN Afterburner II", 2, "active")]))
C("val_max_group_online_bursts", "validity", fit("Claymore", [("Shield Command Burst II", 2, "online"), ("Skirmish Command Burst II", 2, "online")]))
C("val_charge_group", "validity", fit("Rifter", [("200mm AutoCannon II", 1, "active", "Antimatter Charge S")]))
C("val_charge_size", "validity", fit("Rifter", [("200mm AutoCannon II", 1, "active", "EMP M")]))
C("val_charge_capacity", "validity", fit("Rifter", [("Small Capacitor Booster II", 1, "active", "Cap Booster 400")]))
C("val_charge_capacity_probe", "validity", fit("Heron", [("Core Probe Launcher I", 1, "active", "Combat Scanner Probe I")]))
C("val_missing_skills_all0", "validity", fit("Rifter", [("200mm AutoCannon II", 2, "active", "EMP S"), ("Damage Control II", 1, "online")],
                                                [], skills=0))
r = fit("Rifter", [("200mm AutoCannon II", 3, "active", "EMP S")]); r["character"]["skills"]["levels"] = {str(tid("Small Projectile Turret")): 4}
C("val_missing_skills_partial", "validity", r)
C("val_missing_skills_rig_only", "validity", fit("Rifter", [("Small Core Defense Field Extender I", 1, "online")], skills=0))
r = fit("Vexor", [], [("Hammerhead II", 2, 2)], skills=0); r["implants"] = [tid("Eifyr and Co. 'Rogue' Navigation NN-605")]
C("val_missing_skills_drone_implant", "validity", r)
C("val_disable_restrictions_stats", "validity", fit("Rifter", [("200mm AutoCannon II", 4, "active", "EMP S"), ("Damage Control II", 2, "online"),
                                                               ("Medium Core Defense Field Extender I", 1, "online")]))
# ---- hand-derived (contract only): validate:false and maxTypeFitted (Pyfa has neither) --------------------------
r = fit("Rifter", [("Salvager I", 4, "active"), ("Damage Control II", 2, "online")]); r["options"] = {"validate": False}
unit["unit_val_validate_false"] = r
uexp["unit_val_validate_false"] = {"violations": {"codes": []}, "derivation":
    "options.validate=false: no violations are reported (CONTRACT.md options), the fit is still computed; Pyfa has "
    "no such option (its 'Disable Fitting Restrictions' only lets the fit be built, ENG-VAL-005)."}
r = fit("Astrahus", [("Standup Manufacturing Plant I", 2, "online")])
unit["unit_val_max_type_fitted"] = r
uexp["unit_val_max_type_fitted"] = {"violations": {"codes_include": ["MAX_TYPE_FITTED"]}, "derivation":
    "Standup Manufacturing Plant I has maxTypeFitted 1; two fitted -> MAX_TYPE_FITTED (Pyfa has no maxTypeFitted "
    "check). Only the presence of the code is checked (structure fitting is otherwise out of the bench's scope)."}

man = json.loads((SUITE / "MANIFEST.json").read_text())
for n, (feat, r) in cases.items():
    (SUITE / "cases" / f"{n}.json").write_text(json.dumps(r, indent=1, sort_keys=True) + "\n")
    man[n] = {"feature": feat, "source": "hand-built (Pyfa oracle)"}
(SUITE / "MANIFEST.json").write_text(json.dumps(man, indent=1, sort_keys=True) + "\n")
um = json.loads((SUITE / "unit/MANIFEST.json").read_text())
for n, r in unit.items():
    (SUITE / "unit/cases" / f"{n}.json").write_text(json.dumps(r, indent=1, sort_keys=True) + "\n")
    e = {"case": n, "oracle": "hand-derived (non-Pyfa)", "feature": "validity-unit", "values": {}, "ext": {}, "excluded": {}, **uexp[n]}
    (SUITE / "unit/expected" / f"{n}.json").write_text(json.dumps(e, indent=1, sort_keys=True) + "\n")
    um[n] = {"feature": "validity-unit", "source": "hand-derived (non-Pyfa)"}
(SUITE / "unit/MANIFEST.json").write_text(json.dumps(um, indent=1, sort_keys=True) + "\n")
import collections  # noqa: E402
print(len(cases), "cases", dict(collections.Counter(f for f, _ in cases.values())), len(unit), "unit")
