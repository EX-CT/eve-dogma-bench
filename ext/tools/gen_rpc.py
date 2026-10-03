#!/usr/bin/env python3
"""ext/rpc lookup cases for docs/19 items `missing` in the f column (bench 1.11 draft "lookups"; F may fail them).
  python3 ext/tools/gen_rpc.py && python3 ext/tools/make_rpc_expected.py && python3 ext/tools/score_rpc.py --cmd "ENGINE serve-stdio"
A case is a JSON-RPC call {"method", "params"} (CONTRACT.md "Draft 1.11: lookups"); the expectation comes from the
Pyfa service layer (oracle/pyfa_lookup.py). ext/rpc/MANIFEST.json: {case: {feature (= method), item, source}}."""
import gzip, json, os, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
SUITE = ROOT / "ext" / "rpc"
D = json.load(gzip.open(os.environ.get("EVE_DOGMA_DATASET", "/workspace/exct-eve/data/dataset-3569502.json.gz")))
T = {int(k): v for k, v in D["types"].items()}
NAME = {}
for k, v in sorted(T.items()):
    NAME.setdefault(v["name"], k)
tid = NAME.__getitem__
cases = {}


def C(name, item, method, params):
    cases[name] = (item, {"method": method, "params": params})


def fitreq(ship, mods=(), drones=()):
    return {"schema_version": 1, "ship": {"type_id": tid(ship), "mode_type_id": None},
            "character": {"skills": {"default_level": 5, "levels": {}}, "security_status": None},
            "modules": [{"type_id": tid(n), "state": "active", "charge_type_id": tid(c) if c else None, "mutation": None, "spool": None}
                        for n, c in mods],
            "drones": [{"type_id": tid(n), "quantity": q, "active": q, "mutation": None} for n, q in drones],
            "fighters": [], "implants": [], "boosters": [], "cargo": [], "fleet": {"buffs": [], "booster_fits": []},
            "projected": [], "environment": {"effect_type_ids": [], "system_security": None}, "damage_pattern": None, "options": {}}


# ENG-MOD-013 variations (meta group siblings of the parent item; drones / implants by Pyfa's rules)
for n in ("Damage Control II", "200mm AutoCannon II", "Hammerhead II", "High-grade Snake Alpha", "Large Shield Extender II", "Medium Armor Repairer I"):
    C("var_" + n.lower().replace(" ", "_").replace("-", "_"), "ENG-MOD-013", "item.variations", {"type_id": tid(n)})
# MKT-004 item compare (variations x base attribute values)
for n, attrs in (("Damage Control II", ["cpu", "power", "hullEmDamageResonance", "armorEmDamageResonance", "shieldEmDamageResonance"]),
                 ("Large Shield Extender II", ["cpu", "power", "capacityBonus", "signatureRadiusAdd"]),
                 ("1MN Afterburner II", ["cpu", "power", "speedFactor", "capacitorNeed", "duration"]),
                 ("Heat Sink II", ["cpu", "damageMultiplier", "speedMultiplier"])):
    C("cmp_" + n.lower().replace(" ", "_"), "MKT-004", "item.compare", {"type_id": tid(n), "attributes": attrs})
# MKT-001 market tree browsing
C("mkt_root", "MKT-001", "market.group", {"market_group_id": None})
for n in ("Damage Control II", "Hammerhead II", "1MN Afterburner II"):
    C("mkt_group_" + n.lower().replace(" ", "_"), "MKT-001", "market.group", {"market_group_id": T[tid(n)]["market_group"]})
# MKT-002 search with jargon (service/jargon defaults.yaml) and Pyfa regex search
for n, q in (("dc_t2", "dc ii"), ("dda", "dda"), ("lse", "lse"), ("mwd", "5mn mwd"), ("plain", "damage control"), ("wildcard", "hammer*"), ("regex", "re:^Small Focused")):  # noqa: E501
    C("srch_" + n, "MKT-002", "market.search", {"query": q, "filter": "market"})
# ENG-IMP-005 precalculated implant sets
C("isets_all", "ENG-IMP-005", "implant_sets.list", {})
# CHR-004 EVEMon character XML import
def evemon(root, name, sec, skills):
    sk = "".join(f'<skill typeID="{t}" name="x" level="{l}" />' for t, l in skills)
    return f'<?xml version="1.0"?><{root}><name>{name}</name><securityStatus>{sec}</securityStatus><skills>{sk}</skills></{root}>'
C("evemon_ccp", "CHR-004", "character.import_evemon", {"xml": evemon("SerializableCCPCharacter", "Pilot A", "2.5", [(tid("Navigation"), 5), (tid("Gunnery"), 4), (tid("Drones"), 3)])})
C("evemon_uri", "CHR-004", "character.import_evemon", {"xml": evemon("SerializableUriCharacter", "Pilot B", "-1.25", [(tid("Spaceship Command"), 2)])})
C("evemon_filtered", "CHR-004", "character.import_evemon", {"xml": evemon("SerializableCCPCharacter", "Pilot C", "0", [(tid("Navigation"), 7), (tid("Rifter"), 3), (tid("Mechanics"), 0), (tid("Hull Upgrades"), 5)])})
C("evemon_bad_root", "CHR-004", "character.import_evemon", {"xml": evemon("Character", "Pilot D", "0", [(tid("Navigation"), 5)])})
# SVC-005 old -> current item names (service/conversions) when resolving names
C("names_renamed", "SVC-005", "names.resolve", {"names": ["Inertia Stabilizers I", "Small Anti-Explosive Screen Reinforcer I", "Limited Energized Thermal Membrane I",
                                                                  "200mm Reinforced Crystalline Carbonide Plates I"]})
C("names_officer", "SVC-005", "names.resolve", {"names": ["Cormack's Modified Armor Thermal Hardener", "Tuvan's Modified Armor Kinetic Hardener", "Damage Control II"]})
C("names_trig", "SVC-005", "names.resolve", {"names": ["XL Entropic Disintegrator", "PLACEHOLDER TRIG DREAD", "No Such Item Name"]})
# DB-003 backup of all fits (Pyfa Port.backupFits = exportXml of every fit)
C("backup_one", "DB-003", "fits.backup", {"fits": [{"name": "Rifter AC", "fit": fitreq("Rifter", [("200mm AutoCannon II", "EMP S"), ("1MN Afterburner II", None)])}]})
C("backup_three", "DB-003", "fits.backup", {"fits": [
    {"name": "Kestrel LML", "fit": fitreq("Kestrel", [("Light Missile Launcher II", "Scourge Light Missile")] * 2)},
    {"name": "Vexor drones", "fit": fitreq("Vexor", [("Drone Damage Amplifier II", None)], [("Hammerhead II", 5)])},
    {"name": "Thorax plate", "fit": fitreq("Thorax", [("800mm Steel Plates II", None), ("Damage Control II", None)])}]})

# MKT-003 item stats / ENG-SHIP-006 traits / CHR-008 required skills: F's `type` method ({id}); `_fields` names the
# fields a case scores (an engine ignores it)
for n in ("Rifter", "Ishtar", "Svipul", "Damage Control II", "Hammerhead II", "Large Shield Extender II"):
    s = n.lower().replace(" ", "_")
    C("type_attr_" + s, "MKT-003", "type", {"id": tid(n), "_fields": ["name", "attributes", "effects"]})
    C("type_desc_" + s, "MKT-003", "type", {"id": tid(n), "_fields": ["description"]})
    C("type_reqskills_" + s, "CHR-008", "type", {"id": tid(n), "_fields": ["required_skills"]})
for n in ("Rifter", "Ishtar", "Svipul", "Nyx", "Tengu"):
    C("type_traits_" + n.lower(), "ENG-SHIP-006", "type", {"id": tid(n), "_fields": ["traits_html"]})

man = {}
for n, (it, c) in cases.items():
    (SUITE / "cases" / f"{n}.json").write_text(json.dumps(c, indent=1, sort_keys=True) + "\n")
    man[n] = {"feature": c["method"], "item": it, "source": "hand-built (Pyfa lookup oracle)"}
(SUITE / "MANIFEST.json").write_text(json.dumps(man, indent=1, sort_keys=True) + "\n")
print(len(cases), "rpc cases")
