#!/usr/bin/env python3
"""Cases for docs/19 ENG-FTR-004 (fighter EHP / shield regen), bench 1.11 draft.
  python3 ext/tools/gen_fighters.py && python3 ext/tools/make_expected.py ext/cases/fehp_*.json
Pyfa-backed (expected from ext/tools/make_expected.py, ORACLE_EXTRA=ext): fehp_* feature fighter_ehp ->
/fighters/items[fighter_index=i]/{hp,ehp}/{shield,armor,hull} and /fighters/items[fighter_index=i]/shield_peak_recharge_hp_s
(CONTRACT.md "Draft 1.10: stats-ext", same pointers as drone_ehp). Carriers and supercarriers with light, support and
heavy squadrons; Fighter Support Units, skill and damage-pattern variants."""
import copy, json, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import gen_ext as g  # noqa: E402
SUITE = pathlib.Path(__file__).resolve().parents[1]
tid, fit = g.tid, g.fit
cases = {}


def F(ship, squads, mods=(), skills=5, **kw):
    r = fit(ship, mods, skills=skills, **kw)
    r["fighters"] = [{"type_id": tid(n), "quantity": q, "active": a, "abilities": None} for n, q, a in squads]
    return r


C = lambda n, r: cases.__setitem__(n, r)  # noqa: E731
C("fehp_thanatos_firbolg", F("Thanatos", [("Firbolg II", 6, True)]))
C("fehp_archon_templar_cenobite", F("Archon", [("Templar II", 6, True), ("Cenobite II", 3, True)]))
C("fehp_chimera_dragonfly_scarab", F("Chimera", [("Dragonfly II", 6, True), ("Scarab II", 3, True)]))
C("fehp_nidhoggur_einherji_siren", F("Nidhoggur", [("Einherji II", 6, True), ("Siren II", 3, True)]))
C("fehp_nyx_malleus_firbolg", F("Nyx", [("Malleus II", 3, True), ("Firbolg II", 6, True)]))
C("fehp_aeon_ametat_templar", F("Aeon", [("Ametat II", 3, True), ("Templar II", 6, True)]))
C("fehp_wyvern_cyclops_dromi", F("Wyvern", [("Cyclops II", 3, True), ("Dromi II", 3, True)]))
C("fehp_hel_mantis_einherji", F("Hel", [("Mantis II", 3, True), ("Einherji II", 6, True)]))
C("fehp_thanatos_fsu2", F("Thanatos", [("Firbolg II", 6, True)], [("Fighter Support Unit II", 2, "online")]))
C("fehp_hel_fsu3_mantis", F("Hel", [("Mantis II", 3, True)], [("Fighter Support Unit II", 3, "online")]))
C("fehp_thanatos_skills0", F("Thanatos", [("Firbolg II", 6, True)], skills=0))
r = F("Thanatos", [("Firbolg II", 6, True), ("Dromi II", 3, True)])
r["character"]["skills"]["levels"] = {str(tid("Light Fighters")): 1, str(tid("Fighters")): 1, str(tid("Gallente Carrier")): 1}
C("fehp_thanatos_skills_fighters1", r)
C("fehp_nyx_explosive_pattern", F("Nyx", [("Malleus II", 3, True)], damage_pattern={"em": 0, "thermal": 0, "kinetic": 0, "explosive": 100}))
C("fehp_archon_em_thermal_pattern", F("Archon", [("Templar II", 6, True)], damage_pattern={"em": 60, "thermal": 40, "kinetic": 0, "explosive": 0}))
C("fehp_chimera_inactive_squadron", F("Chimera", [("Dragonfly II", 6, False), ("Scarab II", 3, True)]))

man = json.loads((SUITE / "MANIFEST.json").read_text())
for n, r in cases.items():
    (SUITE / "cases" / f"{n}.json").write_text(json.dumps(r, indent=1, sort_keys=True) + "\n")
    man[n] = {"feature": "fighter_ehp", "source": "hand-built (Pyfa oracle)"}
(SUITE / "MANIFEST.json").write_text(json.dumps(man, indent=1, sort_keys=True) + "\n")
print(len(cases), "fighter_ehp cases")
