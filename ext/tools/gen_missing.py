#!/usr/bin/env python3
"""Pyfa-backed cases for docs/19 items that are `missing` in the f column (bench 1.11 drafts; F may fail them).
  python3 ext/tools/gen_missing.py && python3 ext/tools/make_expected.py ext/cases/{brdc,cimp,alpha,dpb,tpb,src,dep}_*.json
Writes ext/cases/<case>.json and their ext/MANIFEST.json entries (feature, source, item). Draft request / response
fields are in CONTRACT.md "Draft 1.11: missing-f"; the oracle honours the request fields only under
ORACLE_EXTRA=drafts (attribute sources under ORACLE_EXTRA=sources), so the default oracle output is unchanged.
  breacher_dc      ENG-MISC-004  options.include_attributes "all" -> /attributes/ship/breacherPodDamageResistance
  char_implants    ENG-IMP-002, CHR-006  character.implants + options.implant_source ("character" | "fit")
  alpha_clone      ENG-CORE-009  character.alpha_clone: true (Pyfa alphaCloneID 1, skill caps from eve.db)
  damage_pattern_builtin  PRF-DMG-001  damage_pattern: {"builtin": <Pyfa builtin rawName>}
  vs_target_profile_builtin  PRF-TGT-001  target_profile: {"builtin": <Pyfa builtin rawName>}
  attr_sources     ENG-CORE-007  options.sources: true -> /sources/<target>/<attr> (Pyfa 'Affected by')
  attr_dependants  ENG-CORE-008  options.sources: true -> /dependants/<source key> (inverse)"""
import gzip, json, os, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
SUITE = ROOT / "ext"
D = json.load(gzip.open(os.environ.get("EVE_DOGMA_DATASET", "/workspace/exct-eve/data/dataset-3569502.json.gz")))
NAME = {}
for k, v in sorted((int(k), v) for k, v in D["types"].items()):
    NAME.setdefault(v["name"], k)


def tid(n):
    return NAME[n]


def F(ship, mods=(), drones=(), skills=5, implants=(), **kw):
    r = {"schema_version": 1, "ship": {"type_id": tid(ship), "mode_type_id": None},
         "character": {"skills": {"default_level": skills, "levels": {}}, "security_status": None},
         "modules": [], "drones": [], "fighters": [], "implants": [tid(i) for i in implants], "boosters": [], "cargo": [],
         "fleet": {"buffs": [], "booster_fits": []}, "projected": [],
         "environment": {"effect_type_ids": [], "system_security": None}, "damage_pattern": None, "options": {}}
    for m in mods:
        n, k, st, ch = (m + (1, "active", None)[len(m) - 1:]) if isinstance(m, tuple) else (m, 1, "active", None)
        r["modules"] += [{"type_id": tid(n), "state": st, "charge_type_id": tid(ch) if ch else None, "mutation": None,
                          "spool": None} for _ in range(k)]
    for n, q, a in drones:
        r["drones"].append({"type_id": tid(n), "quantity": q, "active": a, "mutation": None})
    r.update(kw)
    return r


cases = {}


def C(name, feature, item, req):
    cases[name] = (feature, item, req)


# ---- ENG-MISC-004 breacher pod damage control (Pyfa effect moduleBonusBreacherPodDamageControl) -------------------
ALL = {"include_attributes": "all"}
C("brdc_rifter_active", "breacher_dc", "ENG-MISC-004", F("Rifter", [("Breach Control", 1, "active")], options=ALL))
C("brdc_rifter_online", "breacher_dc", "ENG-MISC-004", F("Rifter", [("Breach Control", 1, "online")], options=ALL))
C("brdc_rifter_skills0", "breacher_dc", "ENG-MISC-004", F("Rifter", [("Breach Control", 1, "active")], skills=0, options=ALL))
C("brdc_thorax_active", "breacher_dc", "ENG-MISC-004", F("Thorax", [("Breach Control", 1, "active"), ("Medium Armor Repairer II", 1, "active")], options=ALL))

# ---- ENG-IMP-002 / CHR-006 character vs fit implants -----------------------------------------------------------
SNAKE = ["High-grade Snake Alpha", "High-grade Snake Beta", "High-grade Snake Gamma"]
def CI(req, ch_imps, src):
    req["character"]["implants"] = [tid(i) for i in ch_imps]
    if src:
        req["options"]["implant_source"] = src
    return req
C("cimp_rifter_char_source", "char_implants", "ENG-IMP-002", CI(F("Rifter", ["1MN Afterburner II"]), SNAKE, "character"))
C("cimp_rifter_fit_source", "char_implants", "ENG-IMP-002", CI(F("Rifter", ["1MN Afterburner II"], implants=["Eifyr and Co. 'Rogue' Navigation NN-605"]), SNAKE, "fit"))
C("cimp_rifter_default_fit", "char_implants", "ENG-IMP-002", CI(F("Rifter", ["1MN Afterburner II"]), SNAKE, None))
C("cimp_rifter_char_ignores_fit", "char_implants", "CHR-006", CI(F("Rifter", ["1MN Afterburner II"], implants=["Eifyr and Co. 'Rogue' Navigation NN-605"]), SNAKE + ["Zor's Custom Navigation Hyper-Link"], "character"))
C("cimp_kestrel_char_missiles", "char_implants", "CHR-006", CI(F("Kestrel", [("Light Missile Launcher II", 4, "active", "Scourge Light Missile")]), ["Zainou 'Deadeye' Guided Missile Precision GP-805"], "character"))
C("cimp_punisher_char_cap", "char_implants", "CHR-006", CI(F("Punisher", [("Small Focused Pulse Laser II", 3, "active", "Multifrequency S"), "Small Armor Repairer II"]), ["Inherent Implants 'Squire' Capacitor Management EM-805", "Inherent Implants 'Squire' Energy Pulse Weapons EP-705"], "character"))

# ---- ENG-CORE-009 alpha clone -------------------------------------------------------------------------------------
def A(req):
    req["character"]["alpha_clone"] = True
    return req
C("alpha_rifter", "alpha_clone", "ENG-CORE-009", A(F("Rifter", [("200mm AutoCannon II", 3, "active", "EMP S"), "1MN Afterburner II"])))
C("alpha_kestrel", "alpha_clone", "ENG-CORE-009", A(F("Kestrel", [("Light Missile Launcher II", 4, "active", "Scourge Light Missile")])))
C("alpha_vexor_drones", "alpha_clone", "ENG-CORE-009", A(F("Vexor", [], [("Hammerhead II", 5, 5)])))
C("alpha_drake", "alpha_clone", "ENG-CORE-009", A(F("Drake", [("Heavy Missile Launcher II", 6, "active", "Scourge Heavy Missile"), ("Large Shield Extender II", 2, "online")])))
C("alpha_omen_skills4", "alpha_clone", "ENG-CORE-009", A(F("Omen", [("Focused Medium Pulse Laser II", 4, "active", "Multifrequency M")], skills=4)))

# ---- PRF-DMG-001 builtin damage patterns (EHP) ------------------------------------------------------------------
for n, ship, pat in (("dpb_rifter_generic_em", "Rifter", "[Generic]EM"), ("dpb_rifter_generic_explosive", "Rifter", "[Generic]Explosive"),
                     ("dpb_drake_guristas", "Drake", "[NPC][Asteroid]Guristas"), ("dpb_drake_abyssal_drifter", "Drake", "[NPC][Abyssal]Drifter"),
                     ("dpb_thorax_scourge", "Thorax", "[Missiles]Scourge"), ("dpb_thorax_uniform", "Thorax", "Uniform")):
    C(n, "damage_pattern_builtin", "PRF-DMG-001", F(ship, [("Damage Control II", 1, "active")], damage_pattern={"builtin": pat}))

# ---- PRF-TGT-001 builtin target profiles ------------------------------------------------------------------------
for n, req, prof in (("tpb_kestrel_t1_shield", F("Kestrel", [("Light Missile Launcher II", 4, "active", "Scourge Light Missile")]), "[T1 Resist]Shield"),
                     ("tpb_kestrel_serpentis", F("Kestrel", [("Light Missile Launcher II", 4, "active", "Mjolnir Light Missile")]), "[NPC][Asteroid]Serpentis"),
                     ("tpb_rifter_uniform50", F("Rifter", [("200mm AutoCannon II", 3, "active", "EMP S")]), "Uniform (50%)"),
                     ("tpb_rifter_t2_amarr_armor", F("Rifter", [("200mm AutoCannon II", 3, "active", "Phased Plasma S")]), "[T2 Resist]Amarr (Armor)"),
                     ("tpb_vexor_rogue_drones", F("Vexor", [], [("Hammerhead II", 5, 5)]), "[NPC][Asteroid]Rogue Drones"),
                     ("tpb_punisher_sleeper", F("Punisher", [("Small Focused Pulse Laser II", 3, "active", "Multifrequency S")]), "[NPC][Other]Sleeper")):
    req["target_profile"] = {"builtin": prof}
    C(n, "vs_target_profile_builtin", "PRF-TGT-001", req)

# ---- ENG-CORE-007 / ENG-CORE-008 attribute sources and dependants -------------------------------------------------
SRC = {"sources": True}
SF = (("rifter_ab_gyro", F("Rifter", [("200mm AutoCannon II", 2, "active", "EMP S"), "1MN Afterburner II", ("Gyrostabilizer II", 1, "online")], options=SRC)),
      ("kestrel_bcs_skills0", F("Kestrel", [("Light Missile Launcher II", 2, "active", "Scourge Light Missile"), ("Ballistic Control System II", 1, "online")], skills=0, options=SRC)),
      ("thorax_plate_dc", F("Thorax", [("800mm Steel Plates II", 1, "online"), ("Damage Control II", 1, "active"), ("Multispectrum Energized Membrane II", 1, "online")], options=SRC)),
      ("vexor_drones_dda", F("Vexor", [("Drone Damage Amplifier II", 2, "online")], [("Hammerhead II", 5, 5)], options=SRC)),
      ("drake_implants", F("Drake", [("Heavy Missile Launcher II", 2, "active", "Scourge Heavy Missile"), ("Large Shield Extender II", 1, "online")], implants=["High-grade Crystal Alpha", "Zainou 'Deadeye' Guided Missile Precision GP-805"], options=SRC)),
      ("punisher_stacking", F("Punisher", [("Small Focused Pulse Laser II", 1, "active", "Multifrequency S"), ("Heat Sink II", 3, "online")], options=SRC)))
for n, r in SF:
    C("src_" + n, "attr_sources", "ENG-CORE-007", json.loads(json.dumps(r)))
for n, r in SF[:4]:
    C("dep_" + n, "attr_dependants", "ENG-CORE-008", json.loads(json.dumps(r)))

man = json.loads((SUITE / "MANIFEST.json").read_text())
for n, (feat, it, r) in cases.items():
    (SUITE / "cases" / f"{n}.json").write_text(json.dumps(r, indent=1, sort_keys=True) + "\n")
    man[n] = {"feature": feat, "item": it, "source": "hand-built (Pyfa oracle)"}
(SUITE / "MANIFEST.json").write_text(json.dumps(man, indent=1, sort_keys=True) + "\n")
print(len(cases), "missing-f cases")
