#!/usr/bin/env python3
"""Pyfa import/export format oracle (GPL-3.0-or-later, test tool only; see LICENSE-GPL-NOTE).

Loads Pyfa's own service/port/*.py exporters/importers (unmodified) with small stand-ins for the GUI-only
imports (wx, Market singleton, service.fit, price service), builds each FitRequest JSON in Pyfa, and emits per
case one JSON line with every export format plus the result of importing each export back.

usage: python pyfa_formats.py req.json [...]          -> one JSON object per case on stdout
       python pyfa_formats.py --import FMT FILE [...]   -> import text files with Pyfa (FMT = auto|eft|dna|dna_alt|xml|esi|eftcfg)
"""
import json, os, re, sys, types, importlib.util
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pyfa_oracle as po  # noqa: E402  (sets up Pyfa paths/db)
import eos.db  # noqa: E402
from eos.const import FittingModuleState, FittingSlot  # noqa: E402
from eos.saveddata.cargo import Cargo  # noqa: E402
from service.const import PortEftOptions, PortDnaOptions, PortMultiBuyOptions  # noqa: E402
import eos.gamedata  # noqa: E402
import xml.dom.minidom  # noqa: E402,F401  (Pyfa's xml.py relies on it being imported elsewhere)


def _stub(name, **attrs):
    m = types.ModuleType(name)
    m.__dict__.update(attrs)
    sys.modules[name] = m
    return m


# ---- stand-ins -------------------------------------------------------------------------------------------
_stub("service.market", Market=None)  # placeholder so service.conversions can import cleanly
import service.conversions as conversions  # noqa: E402

_FORCE_UNPUB = {}
_src = open(os.path.join(po.PYFA, "service/market.py")).read()
_blk = _src[_src.index("self.ITEMS_FORCEPUBLISHED = {"):]
_blk = _blk[:_blk.index("}")]
for _n in re.findall(r'"([^"]+)"\s*:\s*False', _blk):
    _FORCE_UNPUB[_n] = False
for _n in conversions.packs.get("skinnedShips", {}):
    _FORCE_UNPUB[_n] = False


class _Market:
    """Mirrors service.market.Market for the calls the port modules make (getItem incl. name conversions,
    publicity incl. ITEMS_FORCEPUBLISHED, market/group lookups)."""

    @staticmethod
    def getInstance():
        return _Market

    @staticmethod
    def getItem(identity, *args, **kwargs):
        if isinstance(identity, eos.gamedata.Item):
            return identity
        if isinstance(identity, float):
            identity = int(identity)
        if isinstance(identity, str):
            identity = conversions.all.get(identity, identity)
        return eos.db.getItem(identity, *args, **kwargs)

    @staticmethod
    def getPublicityByItem(item):
        return _FORCE_UNPUB.get(item.typeName, item.published)

    @staticmethod
    def getMarketGroupByItem(item, parentcheck=True):
        if item.marketGroupID:
            return item.marketGroup
        if parentcheck and getattr(item, "varParent", None) is not None:
            return _Market.getMarketGroupByItem(item.varParent, False)
        return None

    @staticmethod
    def getGroupByItem(item):
        return item.group


class _SvcFit:
    serviceFittingOptions = {"useGlobalForceReload": False}

    @staticmethod
    def getInstance():
        return _SvcFit

    @staticmethod
    def recalc(fit):
        fit.factorReload = False
        fit.clear()
        fit.calculateModifiedAttributes()

    @staticmethod
    def fill(fit):
        return fit.fill()


_ASL = None


def activeStateLimit(itemIdentity):
    return _ASL(itemIdentity)


sys.modules["service.market"].Market = _Market
_stub("service.esiAccess", EsiAccess=object)
_stub("service.fit", Fit=_SvcFit)
_stub("service.price", Price=object)
_stub("gui.fitCommands.helpers", activeStateLimit=activeStateLimit)
_stub("service.port", __path__=[os.path.join(po.PYFA, "service/port")])


def _load(modname, rel):
    spec = importlib.util.spec_from_file_location(modname, os.path.join(po.PYFA, rel))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[modname] = mod
    spec.loader.exec_module(mod)
    return mod


# activeStateLimit straight from Pyfa's helpers.py source (function body only; module imports wx)
_hsrc = open(os.path.join(po.PYFA, "gui/fitCommands/helpers.py")).read()
_m = re.search(r"^def activeStateLimit\(itemIdentity\):\n(?:(?:    .*|)\n)+", _hsrc, re.M)
_ns = {"Market": _Market, "FittingModuleState": FittingModuleState}
exec(_m.group(0), _ns)
_ASL = _ns["activeStateLimit"]

shared = _load("service.port.shared", "service/port/shared.py")
muta = _load("service.port.muta", "service/port/muta.py")
eft = _load("service.port.eft", "service/port/eft.py")
dna = _load("service.port.dna", "service/port/dna.py")
esi = _load("service.port.esi", "service/port/esi.py")
xmlp = _load("service.port.xml", "service/port/xml.py")
multibuy = _load("service.port.multibuy", "service/port/multibuy.py")
try:
    shipstats = _load("service.port.shipstats", "service/port/shipstats.py")
    sys.modules["service.port.efs"] = _stub("service.port.efs", EfsPort=object)
    Port = _load("service.port.port", "service/port/port.py").Port
except Exception as e:  # pragma: no cover
    shipstats = None
    sys.stderr.write("shipstats unavailable: %r\n" % (e,))

EFT_OPTS = {o: True for o in PortEftOptions}
DNA_PLAIN = {PortDnaOptions.FORMATTING: False}
DNA_FMT = {PortDnaOptions.FORMATTING: True}
MB_OPTS = {PortMultiBuyOptions.LOADED_CHARGES: True, PortMultiBuyOptions.CARGO: True,
           PortMultiBuyOptions.IMPLANTS: True, PortMultiBuyOptions.BOOSTERS: True,
           PortMultiBuyOptions.OPTIMIZE_PRICES: False}
MB_MIN = {PortMultiBuyOptions.LOADED_CHARGES: False, PortMultiBuyOptions.CARGO: False,
          PortMultiBuyOptions.IMPLANTS: False, PortMultiBuyOptions.BOOSTERS: False,
          PortMultiBuyOptions.OPTIMIZE_PRICES: False}

STATE_NAMES = {FittingModuleState.OFFLINE: "offline", FittingModuleState.ONLINE: "online",
               FittingModuleState.ACTIVE: "active", FittingModuleState.OVERHEATED: "overheated"}
SLOT_NAMES = {FittingSlot.HIGH: "high", FittingSlot.MED: "mid", FittingSlot.LOW: "low", FittingSlot.RIG: "rig",
              FittingSlot.SUBSYSTEM: "subsystem", FittingSlot.SERVICE: "service"}


def norm(fit):
    """Pyfa fit -> FitRequest-shaped JSON (what an importer must produce). Empty slots are dropped."""
    if fit is None:
        return None
    mods = []
    for m in fit.modules:
        if m.isEmpty:
            continue
        d = {"type_id": m.item.ID if not m.isMutated else m.item.ID, "slot": SLOT_NAMES.get(m.slot),
             "state": STATE_NAMES.get(m.state), "charge_type_id": m.chargeID if m.charge else None, "mutation": None}
        if m.isMutated:
            d["type_id"] = m.item.ID
            d["mutation"] = {"base_type_id": m.baseItem.ID, "mutaplasmid_type_id": m.mutaplasmid.ID,
                             "attributes": {str(k): v.value for k, v in sorted(m.mutators.items())}}
        mods.append(d)
    out = {
        "name": fit.name,
        "ship": {"type_id": fit.ship.item.ID,
                 "mode_type_id": fit.mode.item.ID if getattr(fit, "mode", None) is not None else None},
        "modules": mods,
        "drones": [{"type_id": d.item.ID, "quantity": d.amount, "active": d.amountActive} for d in fit.drones],
        "fighters": [{"type_id": f.item.ID, "quantity": f.amount, "active": bool(f.active)} for f in fit.fighters],
        "implants": [{"type_id": i.item.ID} for i in fit.implants],
        "boosters": [{"type_id": b.item.ID} for b in fit.boosters],
        "cargo": [{"type_id": c.item.ID, "quantity": c.amount} for c in fit.cargo],
        "notes": fit.notes,
    }
    return out


def _try(f, *a):
    try:
        return {"ok": f(*a)}
    except Exception as e:
        try:
            eos.db.saveddata_session.rollback()
        except Exception:
            pass
        return {"error": "%s: %s" % (type(e).__name__, e)}


def importers():
    return {
        "eft": lambda t: [eft.importEft(t.splitlines())],
        "dna": lambda t: [dna.importDna(t)],
        "dna_alt": lambda t: [dna.importDnaAlt(t)],
        "esi": lambda t: [esi.importESI(t)],
        "xml": lambda t: list(xmlp.importXml(t, None)),
    }


def _auto(text, path=None):
    """Pyfa's own Port.importAuto (service/port/port.py, unmodified). activeFit is a sentinel so the
    single-item / additions-panel branches are reachable; those return non-fit payloads."""
    if not any(line.strip() for line in text.splitlines()):
        # Pyfa's importAuto indexes the first non-blank line and raises IndexError on blank input
        raise Unrecognized("blank input (Pyfa: IndexError in importAuto)")
    res = Port.importAuto(text, path=path, activeFit=_ACTIVE)
    if res is None:
        raise Unrecognized("importAuto matched no format")
    kind, makesNew, data = res
    if makesNew:
        return kind, [norm(f) for f in data]
    return kind, [_describe(x) for x in data]


_ACTIVE = object()


class Unrecognized(Exception):
    """importAuto found no format (contract code UNRECOGNIZED_INPUT)."""


def _describe(x):
    """JSON form of the non-fit payloads importAuto returns (mutated item, additions lists)."""
    if isinstance(x, (list, tuple)):
        return [_describe(y) for y in x]
    if isinstance(x, eos.gamedata.Item):
        return {"type_id": x.ID}
    if isinstance(x, dict):
        return {str(_describe(k)): _describe(v) for k, v in x.items()}
    if hasattr(x, "ID") and hasattr(x, "resultingItem"):  # DynamicItem (mutaplasmid)
        return {"mutaplasmid_type_id": x.ID}
    if hasattr(x, "item") and isinstance(getattr(x, "item"), eos.gamedata.Item):
        return {"type_id": x.item.ID}
    if isinstance(x, (int, float, str)) or x is None:
        return x
    return repr(x)


def export_all(fit):
    r = {}
    r["eft"] = _try(lambda: eft.exportEft(fit, EFT_OPTS, None))
    r["eft_min"] = _try(lambda: eft.exportEft(fit, {o: False for o in PortEftOptions}, None))
    r["dna"] = _try(lambda: dna.exportDna(fit, DNA_PLAIN, None))
    r["dna_formatted"] = _try(lambda: dna.exportDna(fit, DNA_FMT, None))
    r["esi"] = _try(lambda: esi.exportESI(fit, True, True, True, None))
    r["esi_min"] = _try(lambda: esi.exportESI(fit, False, False, False, None))
    r["xml"] = _try(lambda: xmlp.exportXml([fit], None, None))
    r["multibuy"] = _try(lambda: multibuy.exportMultiBuy(fit, MB_OPTS, None))
    r["multibuy_min"] = _try(lambda: multibuy.exportMultiBuy(fit, MB_MIN, None))
    if shipstats is not None:
        r["shipstats"] = _try(lambda: shipstats.exportFitStats(fit, None))
    return r


IMPORT_OF = {"eft": "eft", "dna": "dna", "esi": "esi", "xml": "xml"}


def build_fit(path, req):
    name = os.path.splitext(os.path.basename(path))[0]
    fit = po.build(req)
    fit.name = name
    for c in req.get("cargo", []):
        cg = Cargo(po.item(c["type_id"]))
        cg.amount = c.get("quantity", 1)
        fit.cargo.append(cg)
    for m in fit.modules:
        if getattr(m, "owner", None) is None:
            m.owner = fit
    fit.calculateModifiedAttributes()
    fit.fill()
    for m in fit.modules:
        if getattr(m, "owner", None) is None:
            m.owner = fit
    return fit


def main():
    args = sys.argv[1:]
    if args and args[0] == "--import":
        fmt = args[1]
        for p in args[2:]:
            t = open(p, encoding="utf-8").read()
            if fmt == "auto":
                # path is passed like Pyfa's file import does (EFT-config detection uses the file stem as ship name)
                res = _try(lambda: _auto(t, p if p.endswith(".cfg") else None))
                if "ok" in res:
                    res = {"kind": res["ok"][0], "ok": res["ok"][1]}
            elif fmt == "eftcfg":
                stem = os.path.basename(p).rsplit(".", 1)[0]
                res = _try(lambda: [norm(f) for f in eft.importEftCfg(stem, t.splitlines(), None)])
            else:
                imp = importers()[fmt]
                res = _try(lambda: [norm(f) for f in imp(t)])
            print(json.dumps({"file": os.path.basename(p), "format": fmt, **res}))
        return
    imps = importers()
    for path in args:
        req = json.load(open(path))
        name = os.path.splitext(os.path.basename(path))[0]
        if "fit" in req and "name" in req:  # export edge file: {"name": <fit name>, "fit": FitRequest}
            name, req = req["name"], req["fit"]
        try:
            fit = build_fit(path, req)
            fit.name = name
        except Exception as e:
            print(json.dumps({"file": os.path.basename(path), "error": repr(e)}))
            continue
        ex = export_all(fit)
        rt = {}
        for fmt, impname in IMPORT_OF.items():
            if "ok" not in ex[fmt]:
                continue
            res = _try(lambda: [norm(f) for f in imps[impname](ex[fmt]["ok"])])
            if "ok" in res:
                # round trip: re-export the imported fit in the same format
                try:
                    f2 = imps[impname](ex[fmt]["ok"])[0]
                    if f2 is not None:
                        f2.calculateModifiedAttributes()
                        re_ex = {"eft": lambda: eft.exportEft(f2, EFT_OPTS, None),
                                 "dna": lambda: dna.exportDna(f2, DNA_PLAIN, None),
                                 "esi": lambda: esi.exportESI(f2, True, True, True, None),
                                 "xml": lambda: xmlp.exportXml([f2], None, None)}[fmt]()
                        res["reexport_identical"] = re_ex == ex[fmt]["ok"]
                        if not res["reexport_identical"]:
                            res["reexport"] = re_ex
                except Exception as e:
                    res["reexport_error"] = repr(e)
                    try:
                        eos.db.saveddata_session.rollback()
                    except Exception:
                        pass
            rt[fmt] = res
        print(json.dumps({"file": os.path.basename(path), "name": name, "source": norm(fit),
                          "export": ex, "import": rt}))


if __name__ == "__main__":
    main()
