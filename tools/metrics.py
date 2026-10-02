"""Metric definitions shared by make_expected.py and run.py.
Each metric = JSON pointer(s) into the FitStats response (CONTRACT.md). "a+b" means sum of pointers."""

DMG = ("em", "thermal", "kinetic", "explosive")
LAYERS = ("shield", "armor", "hull")

# metric name -> (pointer expression, group)
METRICS = {
    "cpu_used": ("/resources/cpu/used", "fitting"), "cpu_total": ("/resources/cpu/total", "fitting"),
    "power_used": ("/resources/power/used", "fitting"), "power_total": ("/resources/power/total", "fitting"),
    "calibration_used": ("/resources/calibration/used", "fitting"),
    "drone_bandwidth_used": ("/resources/drone_bandwidth/used", "fitting"),
    "hi_slots": ("/resources/slots/high/total", "fitting"), "med_slots": ("/resources/slots/mid/total", "fitting"),
    "low_slots": ("/resources/slots/low/total", "fitting"),
    **{f"hp.{l}": (f"/defense/hp/{l}", "defense") for l in LAYERS},
    **{f"ehp.{l}": (f"/defense/ehp/{l}", "defense") for l in LAYERS},
    **{f"res.{l}.{k}": (f"/defense/resonance/{l}/{k}", "defense") for l in LAYERS for k in DMG},
    "tank.armor": ("/defense/tank/raw/armor_repair", "tank"), "tank.shield": ("/defense/tank/raw/shield_repair", "tank"),
    "tank.hull": ("/defense/tank/raw/hull_repair", "tank"), "tank.passive": ("/defense/tank/raw/passive_shield", "tank"),
    "weapon_dps": ("/offense/total/weapon_dps", "offense"), "weapon_volley": ("/offense/total/weapon_volley", "offense"),
    "drone_dps": ("/offense/total/drone_dps+/offense/total/fighter_dps", "offense"),
    "drone_volley": ("/offense/total/drone_volley+/offense/total/fighter_volley", "offense"),
    "cap_capacity": ("/capacitor/capacity", "capacitor"), "cap_recharge_s": ("/capacitor/recharge_time_s", "capacitor"),
    "cap_stable": ("/capacitor/stable", "capacitor"), "cap_stable_percent": ("/capacitor/stable_percent", "capacitor"),
    "max_velocity": ("/navigation/max_velocity", "navigation"), "align_time_s": ("/navigation/align_time_s", "navigation"),
    "mass": ("/navigation/mass", "navigation"), "signature_radius": ("/navigation/signature_radius", "navigation"),
    "warp_speed": ("/navigation/warp_speed_au_s", "navigation"),
    "max_targets": ("/targeting/max_targets", "targeting"), "max_target_range": ("/targeting/max_range_m", "targeting"),
    "scan_resolution": ("/targeting/scan_resolution", "targeting"), "scan_strength": ("/targeting/sensor_strength", "targeting"),
}

REL_TOL = 1e-4
ABS_TOL = 1e-3


def pointer(doc, ptr):
    cur = doc
    for part in ptr.strip("/").split("/"):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        elif isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
            cur = cur[int(part)]
        else:
            return None
    return cur


def extract(doc, expr):
    if "+" in expr:
        vals = [pointer(doc, p) for p in expr.split("+")]
        if all(v is None for v in vals):
            return None
        return sum(float(v or 0) for v in vals)
    return pointer(doc, expr)


def close(got, want):
    if isinstance(want, bool) or isinstance(got, bool):
        return got is not None and bool(got) == bool(want)
    if got is None or want is None:
        return got == want
    try:
        g, w = float(got), float(want)
    except (TypeError, ValueError):
        return got == want
    return abs(g - w) <= max(ABS_TOL, REL_TOL * abs(w))


def from_pyfa(s):
    """Pyfa oracle stats (oracle/pyfa_oracle.py) -> {metric: value}"""
    out = {k: s[k] for k in ("cpu_used", "cpu_total", "power_used", "power_total", "calibration_used", "drone_bandwidth_used",
                             "weapon_dps", "weapon_volley", "drone_dps", "drone_volley", "cap_capacity", "cap_recharge_s",
                             "cap_stable", "max_velocity", "align_time_s", "mass", "signature_radius", "warp_speed",
                             "max_targets", "max_target_range", "scan_resolution", "scan_strength", "hi_slots", "med_slots", "low_slots")}
    for l in LAYERS:
        out[f"hp.{l}"] = s["hp"][l]
        out[f"ehp.{l}"] = s["ehp"][l]
        for k in DMG:
            out[f"res.{l}.{k}"] = s["resonance"][l][k]
    t = s["tank"]
    out.update({"tank.armor": t["armorRepair"], "tank.shield": t["shieldRepair"], "tank.hull": t["hullRepair"],
                "tank.passive": t["passiveShield"]})
    if s["cap_stable"]:
        out["cap_stable_percent"] = s["cap_state"]
    return out
