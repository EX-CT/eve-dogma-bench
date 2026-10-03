#!/usr/bin/env python3
"""Pyfa graphs oracle (GPL-3.0-or-later test tool, see ./LICENSE-GPL-NOTE).

Evaluates Pyfa's own graph getters (graphs/data/*/getter.py, `getPoint`) headless at the explicit sample points of
an EXCT GraphRequest (graphs/CONTRACT-GRAPHS.md) and prints one JSON result line per request file.
Fits are built with oracle/pyfa_oracle.py `build()` (the same FitRequest -> Pyfa Fit mapping as the 1.x corpus).

usage: PYFA=/path/to/Pyfa PYTHONPATH=<wx stub> python pyfa_graph_oracle.py graphs/cases/x.json [...]
Every sample point is evaluated with fresh graph caches (Pyfa keys its time/projected caches by fit ID, which is
None for unsaved fits), so points are independent of evaluation order.
"""
import json, math, os, sys, types

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pyfa_oracle as O  # noqa: E402  (sets up Pyfa + eve.db)

# graphs/data/__init__ imports every graph; fitShieldRegen/graph.py imports gui.mainFrame (wx GUI). Stub it.
import gui  # noqa: E402
_mf = types.ModuleType("gui.mainFrame")
_mf.MainFrame = None
sys.modules["gui.mainFrame"] = _mf
gui.mainFrame = _mf

from eos.saveddata.targetProfile import TargetProfile  # noqa: E402
from graphs.wrapper import SourceWrapper, TargetWrapper  # noqa: E402
from service.const import TargetResistMode, GraphDpsDroneMode  # noqa: E402
from service.settings import GraphSettings  # noqa: E402
from graphs.data.fitDamageStats import getter as DMG  # noqa: E402
from graphs.data.fitDamageStats.cache import ProjectedDataCache, TimeCache as DmgTimeCache  # noqa: E402
from graphs.data.fitEwarStats import getter as EWAR  # noqa: E402
from graphs.data.fitRemoteReps import getter as RR  # noqa: E402
from graphs.data.fitRemoteReps.cache import TimeCache as RrTimeCache  # noqa: E402
from graphs.data.fitCapacitor import getter as CAP  # noqa: E402
from graphs.data.fitShieldRegen import getter as SHD  # noqa: E402
from graphs.data.fitMobility import getter as MOB  # noqa: E402
from graphs.data.fitWarpTime import getter as WARP  # noqa: E402
from graphs.data.fitWarpTime.cache import SubwarpSpeedCache  # noqa: E402
from graphs.data.fitLockTime import getter as LOCK  # noqa: E402
from graphs.data.fitApplicationProfile import getter as APP  # noqa: E402
from graphs.data.fitEcmBurstScanresDamps import getter as ECMB  # noqa: E402

AU = WARP.AU_METERS

DEFAULT_SETTINGS = {"ignore_resists": True, "apply_projected": True, "ignore_lock_range": True,
                    "ignore_drone_control_range": False, "mobile_drone_mode": "auto"}
_SETTING_KEYS = {"ignore_resists": "ignoreResists", "apply_projected": "applyProjected",
                 "ignore_lock_range": "ignoreLockRange", "ignore_drone_control_range": "ignoreDCR",
                 "mobile_drone_mode": "mobileDroneMode"}
_DRONE_MODES = {"auto": GraphDpsDroneMode.auto, "follow_attacker": GraphDpsDroneMode.followAttacker,
                "follow_target": GraphDpsDroneMode.followTarget}
_RESIST_MODES = {"auto": TargetResistMode.auto, "shield": TargetResistMode.shield, "armor": TargetResistMode.armor,
                 "hull": TargetResistMode.hull, "weighted_average": TargetResistMode.weightedAverage}


def apply_settings(req):
    s = dict(DEFAULT_SETTINGS)
    s.update(req.get("settings") or {})
    gs = GraphSettings.getInstance()
    for k, pk in _SETTING_KEYS.items():
        v = s[k]
        if k == "mobile_drone_mode":
            v = _DRONE_MODES[v]
        gs.set(pk, v)


class FakeGraph:
    """The attributes Pyfa getters read from their FitGraph (fresh caches per point)."""

    def __init__(self):
        self._timeCache = None
        self._projectedCache = ProjectedDataCache()
        self._subspeedCache = SubwarpSpeedCache()


def target_wrapper(req):
    t = req.get("target") or {"profile": {}}
    if "fit" in t:
        f = O.build(t["fit"])
        f.calculateModifiedAttributes()
        w = TargetWrapper(f, 0, 0)
        w.resistMode = _RESIST_MODES[t.get("resist_mode", "auto")]
        return w
    p = t.get("profile") or {}
    tp = TargetProfile()
    tp.update(p.get("em", 0), p.get("thermal", 0), p.get("kinetic", 0), p.get("explosive", 0),
              maxVelocity=p.get("max_velocity", 0), signatureRadius=p.get("signature_radius"),
              radius=p.get("radius", 0), hp=p.get("hp"))
    return TargetWrapper(tp, 0, 0)


def num(v):
    if v is None:
        return None
    if hasattr(v, "total"):
        v = v.total
    v = float(v)
    return v if math.isfinite(v) else None


def in_range(x, lo, hi):
    return x is not None and lo <= x <= hi


# ---------------------------------------------------------------- per graph
DMG_GETTERS = {
    ("distance_m", "dps"): DMG.Distance2DpsGetter, ("distance_m", "volley"): DMG.Distance2VolleyGetter,
    ("distance_m", "damage"): DMG.Distance2InflictedDamageGetter,
    ("time_s", "dps"): DMG.Time2DpsGetter, ("time_s", "volley"): DMG.Time2VolleyGetter,
    ("time_s", "damage"): DMG.Time2InflictedDamageGetter,
    ("tgt_speed_mps", "dps"): DMG.TgtSpeed2DpsGetter, ("tgt_speed_mps", "volley"): DMG.TgtSpeed2VolleyGetter,
    ("tgt_speed_mps", "damage"): DMG.TgtSpeed2InflictedDamageGetter,
    ("tgt_sig_m", "dps"): DMG.TgtSigRadius2DpsGetter, ("tgt_sig_m", "volley"): DMG.TgtSigRadius2VolleyGetter,
    ("tgt_sig_m", "damage"): DMG.TgtSigRadius2InflictedDamageGetter,
}


def damage_point(req, fit, axis, y, x):
    p = req.get("params") or {}
    src = SourceWrapper(fit, 0)
    tgt = target_wrapper(req)
    tgt_speed = p.get("tgt_speed_mps")
    if tgt_speed is None:
        tgt_speed = p.get("tgt_speed_pct", 100) / 100 * tgt.getMaxVelocity()
    atk_speed = p.get("atk_speed_mps")
    if atk_speed is None:
        atk_speed = p.get("atk_speed_pct", 0) / 100 * src.getMaxVelocity()
    misc = {"distance": p.get("distance_m"), "time": p.get("time_s"), "tgtSpeed": tgt_speed,
            "atkSpeed": atk_speed, "atkAngle": p.get("atk_angle_deg", 90), "tgtAngle": p.get("tgt_angle_deg", 90)}
    if misc["time"] is not None:
        misc["time"] = max(0, min(2500, misc["time"]))
    if axis == "time_s" and not in_range(x, 0, 2500):
        return None
    if y == "damage" and axis != "time_s" and misc["time"] is None:
        return None  # Pyfa: inflicted damage needs a time
    g = FakeGraph()
    g._timeCache = DmgTimeCache()
    # percentage axes: Pyfa `_normalizers` ('tgtSpeed', '%') / ('tgtSigRad', '%') -> absolute value
    if axis == "tgt_speed_pct":
        axis, x = "tgt_speed_mps", x / 100 * tgt.getMaxVelocity()
    elif axis == "tgt_sig_pct":
        sig = tgt.getSigRadius()
        if sig is None or not math.isfinite(sig):
            return None  # infinite-signature (ideal) target: % of infinity is not a sample point
        axis, x = "tgt_sig_m", x / 100 * sig
    if axis == "tgt_sig_m" and not x > 0:
        return None
    getter = DMG_GETTERS[(axis, y)](g)
    return num(getter.getPoint(x=x, miscParams=misc, src=src, tgt=tgt))


EWAR_GETTERS = {"neut_gj_s": EWAR.Distance2NeutingStrGetter, "web_pct": EWAR.Distance2WebbingStrGetter,
                "ecm_strength": EWAR.Distance2EcmStrMaxGetter, "damp_lock_range_pct": EWAR.Distance2DampStrLockRangeGetter,
                "td_optimal_pct": EWAR.Distance2TdStrOptimalGetter, "gd_range_pct": EWAR.Distance2GdStrRangeGetter,
                "tp_sig_pct": EWAR.Distance2TpStrGetter}


# 0.2: target fit for ewar / remote_reps. Pyfa's ewar and RR graphs have no target; values are derived from Pyfa's
# own projected-effect handlers (eos/effects.py): resistance = the target ship's resistance attribute named by the
# effect (`resistanceID`, applied by ModifiedAttributeDict.getResistance), and the handlers' early returns on
# `disallowOffensiveModifiers` (all ewar except neutralizers) / `disallowAssistance` (all remote repairs).
EWAR_RESIST_ATTR = {"neut_gj_s": "energyWarfareResistance", "web_pct": "stasisWebifierResistance",
                    "ecm_strength": "ECMResistance", "damp_lock_range_pct": "sensorDampenerResistance",
                    "td_optimal_pct": "weaponDisruptionResistance", "gd_range_pct": "weaponDisruptionResistance",
                    "tp_sig_pct": "targetPainterResistance"}


def target_ship_attr(req, name, default):
    t = req.get("target") or {}
    if "fit" not in t:
        return None
    tf = O.build(t["fit"])
    tf.calculateModifiedAttributes()
    v = tf.ship.getModifiedItemAttr(name)
    return default if v is None else v


def ewar_point(req, fit, axis, y, x):
    p = req.get("params") or {}
    resist = p.get("resist")
    if resist is not None:
        resist = max(0, min(1, resist))
    elif (req.get("target") or {}).get("fit") is not None:
        if y != "neut_gj_s" and target_ship_attr(req, "disallowOffensiveModifiers", 0):
            return 0.0
        resist = max(0, min(1, 1 - (target_ship_attr(req, EWAR_RESIST_ATTR[y], 1) or 1)))  # Pyfa: `resist or 1`
    misc = {"distance": x, "resist": resist}
    return num(EWAR_GETTERS[y](FakeGraph()).getPoint(x=x, miscParams=misc, src=SourceWrapper(fit, 0), tgt=None))


RR_GETTERS = {("distance_m", "rps"): RR.Distance2RpsGetter, ("distance_m", "total"): RR.Distance2RepAmountGetter,
              ("time_s", "rps"): RR.Time2RpsGetter, ("time_s", "total"): RR.Time2RepAmountGetter}


def rr_point(req, fit, axis, y, x):
    p = req.get("params") or {}
    t = p.get("time_s")
    if t is not None:
        t = max(0, min(2500, t))
    if axis == "time_s" and not in_range(x, 0, 2500):
        return None
    if y == "total" and axis != "time_s" and t is None:
        return None
    misc = {"distance": p.get("distance_m"), "time": t, "ancReload": p.get("anc_reload", True)}
    if axis == "distance_m":
        misc["distance"] = x
    mult = 1
    if (req.get("target") or {}).get("fit") is not None:
        if target_ship_attr(req, "disallowAssistance", 0):
            return 0.0
        # remote repair effects carry resistanceID 2116 (remoteRepairImpedance); Pyfa's RR handlers do not apply it
        # (they append to fit._armorRr without the effect kwarg), so it is applied here as getResistance would.
        mult = target_ship_attr(req, "remoteRepairImpedance", 1) or 1
    g = FakeGraph()
    g._timeCache = RrTimeCache()
    v = num(RR_GETTERS[(axis, y)](g).getPoint(x=x, miscParams=misc, src=SourceWrapper(fit, 0), tgt=None))
    return None if v is None else v * mult


def cap_point(req, fit, axis, y, x):
    p = req.get("params") or {}
    capmax = fit.ship.getModifiedItemAttr("capacitorCapacity")
    t0 = max(0, min(100, p.get("cap_start_pct", 100))) / 100 * capmax
    misc = {"capAmountT0": t0, "useCapsim": p.get("use_capsim", True)}
    if axis == "time_s":
        if not in_range(x, 0, 3600):
            return None
        g = CAP.Time2CapAmountGetter if y == "cap_gj" else CAP.Time2CapRegenGetter
        if y == "cap_regen_gj_s":
            misc["useCapsim"] = False
    else:  # cap_pct
        if not in_range(x, 0, 100):
            return None
        x = x / 100 * capmax
        g = CAP.CapAmount2CapAmountGetter if y == "cap_gj" else CAP.CapAmount2CapRegenGetter
    return num(g(FakeGraph()).getPoint(x=x, miscParams=misc, src=SourceWrapper(fit, 0), tgt=None))


def shield_point(req, fit, axis, y, x):
    p = req.get("params") or {}
    ship = fit.ship
    smax = ship.getModifiedItemAttr("shieldCapacity")
    t0 = max(0, min(100, p.get("shield_start_pct", 0))) / 100 * smax
    misc = {"shieldAmountT0": t0}
    if axis == "time_s":
        g = SHD.Time2ShieldAmountGetter if y == "shield_hp" else SHD.Time2ShieldRegenGetter
    else:  # shield_pct
        if not in_range(x, 0, 100):
            return None
        x = x / 100 * smax
        g = SHD.ShieldAmount2ShieldAmountGetter if y == "shield_hp" else SHD.ShieldAmount2ShieldRegenGetter
    v = g(FakeGraph()).getPoint(x=x, miscParams=misc, src=SourceWrapper(fit, 0), tgt=None)
    if p.get("effective", False) and v is not None:
        v = fit.damagePattern.effectivify(ship, v, "shield")
    return num(v)


MOB_GETTERS = {"speed_mps": MOB.Time2SpeedGetter, "distance_m": MOB.Time2DistanceGetter,
               "momentum_kg_mps": MOB.Time2MomentumGetter, "bump_speed_mps": MOB.Time2BumpSpeedGetter,
               "bump_distance_m": MOB.Time2BumpDistanceGetter}


def mobility_point(req, fit, axis, y, x):
    p = req.get("params") or {}
    misc = {"tgtMass": p.get("tgt_mass_kg", 1300e6), "tgtInertia": p.get("tgt_inertia", 0.015)}
    return num(MOB_GETTERS[y](FakeGraph()).getPoint(x=x, miscParams=misc, src=SourceWrapper(fit, 0), tgt=None))


def warp_point(req, fit, axis, y, x):
    if not in_range(x, 0, fit.maxWarpDistance * AU):
        return None
    return num(WARP.Distance2TimeGetter(FakeGraph()).getPoint(x=x, miscParams={}, src=SourceWrapper(fit, 0), tgt=None))


def lock_point(req, fit, axis, y, x):
    if x is None or x < 1:
        return None
    return num(LOCK.TgtSigRadius2LockTimeGetter(FakeGraph()).getPoint(x=x, miscParams={}, src=SourceWrapper(fit, 0), tgt=None))


def app_point(req, fit, axis, y, x):
    """Application profile (Pyfa 'ammoOptimalDpsGraph'): best charge per distance; returns (value, charge type id)."""
    p = req.get("params") or {}
    gs = GraphSettings.getInstance()
    s = req.get("settings") or {}
    gs.set("ammoOptimalIgnoreResists", s.get("ignore_resists", True))
    gs.set("ammoOptimalApplyProjected", s.get("apply_projected", True))
    src = SourceWrapper(fit, 0)
    tgt = target_wrapper(req)
    tgt_speed = p.get("tgt_speed_mps")
    if tgt_speed is None:
        tgt_speed = p.get("tgt_speed_pct", 100) / 100 * tgt.getMaxVelocity()
    atk_speed = p.get("atk_speed_mps")
    if atk_speed is None:
        atk_speed = p.get("atk_speed_pct", 0) / 100 * src.getMaxVelocity()
    misc = {"distance": x, "tgtSpeed": tgt_speed, "atkSpeed": atk_speed,
            "atkAngle": p.get("atk_angle_deg", 90), "tgtAngle": p.get("tgt_angle_deg", 90)}
    g = FakeGraph()
    g._ammoQuality = p.get("ammo_quality", "all")
    cls = APP.Distance2OptimalAmmoDpsGetter if y == "dps" else APP.Distance2OptimalAmmoVolleyGetter
    v, extra = cls(g).getPointExtended(x=x, miscParams=misc, src=src, tgt=tgt)
    name = (extra or {}).get("ammo")
    cid = None
    if name:
        it = O.eos.db.getItem(name)
        cid = it.ID if it is not None else None
    return num(v), cid


ECMB_GETTERS = {("tgt_scan_res_mm", "src_damage"): ECMB.TgtScanRes2SrcDmgGetter,
                ("tgt_scan_res_mm", "tgt_lock_time_s"): ECMB.TgtScanRes2TgtLockTimeGetter,
                ("tgt_scan_res_mm", "tgt_lock_uptime_s"): ECMB.TgtScanRes2TgtLockUptimeGetter,
                ("tgt_dps", "src_damage"): ECMB.TgtDps2SrcDmgGetter}


def ecm_point(req, fit, axis, y, x):
    """Pyfa's hidden experimental 'ECM Burst + Scanres Damps' graph (fitEcmBurstScanresDamps)."""
    p = req.get("params") or {}
    if (axis, y) not in ECMB_GETTERS:
        raise ValueError("BAD_AXIS %s/%s" % (axis, y))
    misc = {"tgtScanRes": p.get("tgt_scan_res_mm", 700), "tgtDps": p.get("tgt_dps", 200),
            "uptimeAdj": p.get("uptime_adj_s", 1), "uptimeAmtLimit": p.get("uptime_amount_limit", 3),
            "applyDamps": p.get("apply_damps", True), "applyDrones": p.get("apply_drones", True)}
    if axis == "tgt_scan_res_mm" and not x >= 1:
        return None  # Pyfa limiter (1, inf)
    tgt_dps = x if axis == "tgt_dps" else misc["tgtDps"]
    if y == "src_damage" and not tgt_dps > 0:
        return None  # Pyfa divides remaining EHP by enemy dps
    if axis == "tgt_dps" and not misc["tgtScanRes"] >= 1:
        return None
    return num(ECMB_GETTERS[(axis, y)](FakeGraph()).getPoint(x=x, miscParams=misc, src=SourceWrapper(fit, 0), tgt=None))


GRAPHS = {
    "application_profile": (app_point, {"distance_m"}, {"dps", "volley"}),
    "damage": (damage_point, {"distance_m", "time_s", "tgt_speed_mps", "tgt_speed_pct", "tgt_sig_m", "tgt_sig_pct"}, {"dps", "volley", "damage"}),
    "ewar": (ewar_point, {"distance_m"}, set(EWAR_GETTERS)),
    "remote_reps": (rr_point, {"distance_m", "time_s"}, {"rps", "total"}),
    "capacitor": (cap_point, {"time_s", "cap_pct"}, {"cap_gj", "cap_regen_gj_s"}),
    "shield_regen": (shield_point, {"time_s", "shield_pct"}, {"shield_hp", "shield_regen_hp_s"}),
    "mobility": (mobility_point, {"time_s"}, set(MOB_GETTERS)),
    "warp_time": (warp_point, {"distance_m"}, {"time_s"}),
    "lock_time": (lock_point, {"tgt_sig_m"}, {"time_s"}),
    "ecm_burst": (ecm_point, {"tgt_scan_res_mm", "tgt_dps"}, {"src_damage", "tgt_lock_time_s", "tgt_lock_uptime_s"}),
}


def run(req):
    kind = req["graph"]
    fn, axes, ys = GRAPHS[kind]
    axis = req["x"]["axis"]
    if axis not in axes:
        raise ValueError("axis %s not valid for %s" % (axis, kind))
    apply_settings(req)
    series = {}
    extra = {}
    for y in req["y"]:
        if y not in ys:
            raise ValueError("y %s not valid for %s" % (y, kind))
        vals = []
        for x in req["x"]["values"]:
            fit = O.build(req["fit"])  # fresh fit per point: Pyfa graph code mutates/caches fit state
            fit.calculateModifiedAttributes()
            v = fn(req, fit, axis, y, x)
            if isinstance(v, tuple):
                v, cid = v
                extra.setdefault(y + "_charge_type_id", []).append(cid)
            vals.append(v)
        series[y] = vals
    series.update(extra)
    return {"graph": kind, "x_axis": axis, "x": req["x"]["values"], "series": series}


def main():
    for path in sys.argv[1:]:
        req = json.load(open(path))
        try:
            out = run(req)
        except Exception as e:
            import traceback
            traceback.print_exc(file=sys.stderr)
            try:
                O.eos.db.saveddata_session.rollback()
            except Exception:
                pass
            print(json.dumps({"file": os.path.basename(path), "error": repr(e)}))
            continue
        out["file"] = os.path.basename(path)
        print(json.dumps(out))
        sys.stdout.flush()


if __name__ == "__main__":
    main()
