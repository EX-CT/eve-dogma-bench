#!/usr/bin/env python3
"""Pyfa lookup oracle for the ext/rpc suite (bench 1.11 draft "missing-f" lookups; CONTRACT.md "Draft 1.11:
lookups"). Runs Pyfa's service layer headless on one {"method", "params"} case file per argument and prints
{"file", "result"} lines. A separate script: pyfa_oracle.py and its default output are untouched (its build() is
reused for fits.backup). GPL-3.0-or-later like pyfa_oracle.py (uses Pyfa as a library); test tool only.
usage: PYFA=... PYTHONPATH=<wx stub> python pyfa_lookup.py case.json [...]
Methods (result shapes are the draft contract):
  item.variations {type_id}             -> {type_ids}   Market.getVariationsByItems([item])        ENG-MOD-013
  item.compare {type_id, attributes}    -> {items: [{type_id, attributes{name: value}}]}  variations x base
                                           attribute values (gui/itemCompare shows Item.attributes)  MKT-004
  market.group {market_group_id|null}   -> {groups, items}  null = Market.getMarketRoot(); else
                                           getMarketGroupChildren + getItemsByMarketGroup(vars_=False)  MKT-001
  market.search {query, filter}         -> {type_ids}  SearchWorkerThread.processSearches (jargon applied)  MKT-002
  implant_sets.list {}                  -> {sets: {setName: {gradeName: [type_ids]}}}  getStructuredSets  ENG-IMP-005
  character.import_evemon {xml}         -> {name, security_status, skills{type_id: level}}
                                           CharacterImportThread.run (EVEMon XML)          CHR-004
  names.resolve {names}                 -> {resolved: {name: type_id|null}}  Market.getItem(str) (conversions)  SVC-005
  type {id, _fields}                    -> Pyfa item stats: attributes, effects, description, traits_html,
                                           required_skills (only the `_fields` asked)      MKT-003, ENG-SHIP-006, CHR-008
  fits.backup {fits: [{name, fit}]}     -> {xml}  Port.backupFits = exportXml of all fits        DB-003
"""
import json, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pyfa_oracle as O  # noqa: E402  (Pyfa setup: paths, eve.db, saveddata db)
import eos.db  # noqa: E402
import wx  # noqa: E402  (stub)
wx.CallAfter = lambda f, *a, **k: f(*a, **k)
from service.market import Market, SearchWorkerThread  # noqa: E402
import service.market as _sm  # noqa: E402
import types  # noqa: E402
# service.character imports service.esi (ESI SSO -> gui.globalEvents -> wx.lib); not used by the EVEMon import
sys.modules.setdefault("service.esi", types.SimpleNamespace(Esi=type("Esi", (), {"getInstance": staticmethod(lambda: None)})))
import service.character as _sc  # noqa: E402
_sm.wx.CallAfter = _sc.wx.CallAfter = wx.CallAfter

M = Market.getInstance()


def ids(items):
    return sorted(i.ID for i in items if i is not None)


def variations(p):
    return {"type_ids": ids(M.getVariationsByItems([eos.db.getItem(int(p["type_id"]))]))}


def compare(p):
    out = []
    for it in sorted(M.getVariationsByItems([eos.db.getItem(int(p["type_id"]))]), key=lambda i: i.ID):
        out.append({"type_id": it.ID, "attributes": {a: it.attributes[a].value for a in p["attributes"] if a in it.attributes}})
    return {"items": out}


def market_group(p):
    g = p.get("market_group_id")
    if g is None:
        return {"groups": ids(M.getMarketRoot()), "items": []}
    mg = M.getMarketGroup(int(g))
    return {"groups": ids(M.getMarketGroupChildren(mg)), "items": ids(M.getItemsByMarketGroup(mg, vars_=False))}


def search(p):
    import threading
    t = SearchWorkerThread()
    t.cv = threading.Condition()
    got = []

    def cb(r):
        got.append(r)
        t.running = False
    t.searchRequest = (p["query"], cb, p.get("filter", "market"))
    t.processSearches()
    return {"type_ids": got[0]}


def implant_sets(p):
    from service.precalcImplantSet import PrecalcedImplantSets
    s = PrecalcedImplantSets.getStructuredSets()
    conv = PrecalcedImplantSets.stringToImplants
    return {"sets": {n: {g or "": sorted(i.item.ID for i in conv(imps)) for g, imps in sorted(grades.items(), key=lambda x: x[0] or "")}
                     for n, grades in sorted(s.items())}}


def import_evemon(p):
    sC = _sc.Character.getInstance()
    rec = []
    orig_new, orig_upd = sC.new, sC.apiUpdateCharSheet
    sC.new = lambda name: rec.append({"name": name}) or orig_new(name)
    sC.apiUpdateCharSheet = lambda cid, skills, sec: rec[-1].update(skills=skills, sec=sec)
    path = tempfile.mktemp(suffix=".xml")
    open(path, "w").write(p["xml"])
    try:
        _sc.CharacterImportThread([path], lambda: None).run()
    finally:
        sC.new, sC.apiUpdateCharSheet = orig_new, orig_upd
    if not rec or "skills" not in rec[-1]:
        return {"error": "INVALID_CHARACTER_XML"}
    r = rec[-1]
    return {"name": r["name"], "security_status": float(r["sec"]), "skills": {str(s["typeID"]): s["level"] for s in r["skills"]}}


def resolve(p):
    out = {}
    for n in p["names"]:
        try:
            it = M.getItem(n)
        except Exception:
            it = None
        out[n] = it.ID if it is not None else None
    return {"resolved": out}


def _export_xml():
    """service/port/xml.py exportXml, loaded from Pyfa's source unmodified (the module imports gui.fitCommands /
    service.fit -> wx GUI, so only the function body is executed, with the names it uses; the cases have no
    mutated items, so renderMutantAttrs is never reached)."""
    import re, xml.dom.minidom
    from logbook import Logger
    from eos.const import FittingSlot
    src = open(os.path.join(O.PYFA, "service/port/xml.py")).read()
    body = src[src.index("def exportXml("):]
    ns = {"re": re, "xml": xml, "FittingSlot": FittingSlot, "pyfalog": Logger("xml"),
          "renderMutantAttrs": lambda m: (_ for _ in ()).throw(NotImplementedError("mutated"))}
    exec(compile(body, "xml.py:exportXml", "exec"), ns)
    return ns["exportXml"]


def backup(p):
    fits = []
    for f in p["fits"]:
        fit = O.build(f["fit"])
        fit.name = f["name"]
        fit.calculateModifiedAttributes()
        fits.append(fit)
    return {"xml": _export_xml()(fits, None, None)}


def type_info(p):
    """`type` (F's existing method, params {id}); Pyfa item stats window data. Each case asks for some fields:
    attributes (base, Item.attributes), effects [{id, name}] (Item.effects), description, traits_html
    (Item.traits.display, the Traits tab), required_skills {skill type id: level} (Item.requiredSkills)."""
    it = eos.db.getItem(int(p["id"]))
    full = {"type_id": it.ID, "name": it.name,
            "attributes": {k: v.value for k, v in it.attributes.items()},
            "effects": sorted(({"id": e.ID, "name": e.name} for e in it.effects.values()), key=lambda x: x["id"]),
            "description": it.description,
            "traits_html": it.traits.display if it.traits is not None else None,
            "required_skills": {str(s.ID): l for s, l in it.requiredSkills.items()}}
    return {k: full[k] for k in ["type_id"] + p.get("_fields", list(full))}


METHODS = {"type": type_info, "item.variations": variations, "item.compare": compare, "market.group": market_group,
           "market.search": search, "implant_sets.list": implant_sets, "character.import_evemon": import_evemon,
           "names.resolve": resolve, "fits.backup": backup}

if __name__ == "__main__":
    for path in sys.argv[1:]:
        c = json.load(open(path))
        try:
            r = METHODS[c["method"]](c.get("params") or {})
        except Exception as e:
            print(json.dumps({"file": os.path.basename(path), "error": repr(e)}))
            continue
        print(json.dumps({"file": os.path.basename(path), "result": r}))
