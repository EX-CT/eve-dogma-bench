#!/usr/bin/env python3
"""Write graphs/cases/<name>.json (GraphRequest, graphs/CONTRACT-GRAPHS.md).

Source fits are taken verbatim from the 1.x corpus (cases/<fit>.json) or built inline below (all-V characters).
Sample points are explicit and chosen to hit the interesting parts of each curve (inside optimal, falloff, beyond
lock / drone control range, capsim events, warp acceleration/cruise boundary, ...)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "graphs/cases"


def corpus(name):
    return json.loads((ROOT / "cases" / (name + ".json")).read_text())


def fit(ship, mods, drones=(), skills=5, fighters=()):
    r = {"schema_version": 1, "ship": {"type_id": ship}, "character": {"skills": {"default_level": skills}},
         "modules": [dict({"type_id": t, "state": "active"}, **({"charge_type_id": c} if c else {})) for t, c in mods],
         "drones": [{"type_id": t, "quantity": q, "active": a} for t, q, a in drones]}
    if fighters:
        r["fighters"] = [{"type_id": t, "quantity": q, "active": True} for t, q in fighters]
    return r


# inline EWAR / logistics fits (type ids from dataset-3569502)
VIGIL_TP = fit(3766, [(19806, None), (19806, None), (19806, None)])
MAULUS_DAMP = fit(609, [(1969, 29015), (1969, 29015), (1969, None)])
GRIFFIN_ECM = fit(584, [(2567, None), (2567, None), (2567, None)])
ARBI_TD = fit(628, [(2109, 29005), (2109, 40334), (2109, None)], drones=[(23659, 4, 4)])
HUGINN_WEB = fit(11961, [(527, None), (527, None), (19806, None), (19806, None)])
BHAAL_NEUT = fit(17920, [(12271, None), (12271, None), (12271, None), (13003, None)], drones=[(23659, 5, 5)])
ONEIROS_RR = fit(11989, [(26913, None), (26913, None), (26913, None), (41477, 28668)])
SCIMI_RR = fit(11978, [(3608, None), (3608, None), (3608, None), (41481, 11283)])
KIKIMORA = fit(49710, [(47914, 47924), (47911, None), (47911, None)])
SKYBREAKER = fit(54731, [(54742, 54772), (54742, 54772)])
KESTREL_BREACHER = fit(602, [(85084, 85088), (85084, 85088), (85084, 85088), (85084, 85088)])
MANTICORE_BOMB = fit(12032, [(27914, 27912)])
THANATOS_TEMPLAR = fit(23911, [(41415, None), (41415, None)], fighters=[(40556, 9), (40556, 9), (40556, 9)])
VEXOR_EWAR_DRONES = fit(626, [(527, None)], drones=[(23707, 5, 5)])

SMALL = {"profile": {"signature_radius": 35, "max_velocity": 400, "radius": 40}}
CRUISER = {"profile": {"signature_radius": 125, "max_velocity": 250, "radius": 150}}
BS = {"profile": {"signature_radius": 400, "max_velocity": 100, "radius": 400}}
CRUISER_RES = {"profile": {"em": 0.5, "thermal": 0.4, "kinetic": 0.3, "explosive": 0.2, "signature_radius": 125,
                           "max_velocity": 250, "radius": 150, "hp": 5000}}
IDEAL = {"profile": {"em": 0, "thermal": 0, "kinetic": 0, "explosive": 0, "max_velocity": 0, "signature_radius": None, "radius": 0}}

KM = lambda *v: [x * 1000 for x in v]  # noqa: E731
AU = 149597870700

cases = {}


def add(name, graph, f, axis, xs, ys, params=None, target=None, settings=None):
    r = {"schema_version": 1, "graph": graph, "fit": f, "x": {"axis": axis, "values": xs}, "y": ys}
    if params:
        r["params"] = params
    if target:
        r["target"] = target
    if settings:
        r["settings"] = settings
    cases[name] = r


DIST_S = KM(0, 0.5, 1, 2, 3, 5, 7.5, 10, 15, 20, 30, 50)
DIST_L = KM(0, 2, 5, 10, 20, 30, 40, 50, 60, 75, 100, 150)

# ---- damage: distance
add("dmg_dist_rifter_small", "damage", corpus("exct_rifter"), "distance_m", DIST_S, ["dps", "volley"], {"tgt_speed_pct": 100}, SMALL)
add("dmg_dist_rifter_noproj", "damage", corpus("exct_rifter"), "distance_m", DIST_S, ["dps"], {"tgt_speed_pct": 100}, SMALL, {"apply_projected": False})
add("dmg_dist_rifter_lockrange", "damage", corpus("exct_rifter"), "distance_m", KM(0, 5, 10, 20, 25, 30, 40, 60), ["dps"], {"tgt_speed_pct": 50}, CRUISER, {"ignore_lock_range": False})
add("dmg_dist_hyperion_cruiser", "damage", corpus("exct_hyperion"), "distance_m", DIST_S, ["dps", "volley"], {"tgt_speed_pct": 100}, CRUISER)
add("dmg_dist_maelstrom_bs", "damage", corpus("exct_maelstrom"), "distance_m", DIST_L, ["dps", "volley"], {"tgt_speed_pct": 100}, BS)
add("dmg_dist_tengu_cruiser", "damage", corpus("exct_tengu"), "distance_m", DIST_L, ["dps", "volley"], {"tgt_speed_pct": 100}, CRUISER)
add("dmg_dist_raven_small", "damage", corpus("exct_raven"), "distance_m", DIST_L, ["dps"], {"tgt_speed_pct": 100}, SMALL)
add("dmg_dist_cerberus_resists", "damage", corpus("exct_cerberus"), "distance_m", DIST_L, ["dps"], {"tgt_speed_pct": 100}, CRUISER_RES, {"ignore_resists": False})
add("dmg_dist_ishtar_drones", "damage", corpus("drones_heavy_ishtar"), "distance_m", DIST_L, ["dps", "volley"], {"tgt_speed_pct": 100}, CRUISER)
add("dmg_dist_ishtar_sentries", "damage", corpus("drones_sentry_ishtar"), "distance_m", DIST_L, ["dps"], {"tgt_speed_pct": 100}, CRUISER)
add("dmg_dist_ishtar_sentries_dcr", "damage", corpus("drones_sentry_ishtar"), "distance_m", DIST_L, ["dps"], {"tgt_speed_pct": 100}, CRUISER, {"ignore_drone_control_range": True})
add("dmg_dist_dominix_sentries", "damage", corpus("drones_sentry_dominix"), "distance_m", DIST_L, ["dps"], {"tgt_speed_pct": 30}, BS)
add("dmg_dist_vexor_drones_follow", "damage", corpus("drones_mixed_vexor"), "distance_m", DIST_S, ["dps"], {"tgt_speed_pct": 100}, SMALL, {"mobile_drone_mode": "follow_target"})
add("dmg_dist_hel_fighters", "damage", corpus("exct_hel"), "distance_m", DIST_L, ["dps"], {"tgt_speed_pct": 100}, BS)
add("dmg_dist_nidhoggur_fighters", "damage", corpus("exct_nidhoggur"), "distance_m", DIST_L, ["dps", "volley"], {"tgt_speed_pct": 100}, CRUISER)
add("dmg_dist_smartbomb", "damage", corpus("exct_hyperion_smartbomb"), "distance_m", KM(0, 2, 4, 5, 6, 7.5, 10), ["dps", "volley"], {"tgt_speed_pct": 0}, CRUISER)
add("dmg_dist_kronos_ideal", "damage", corpus("exct_kronos"), "distance_m", DIST_S, ["dps"], {}, IDEAL)
add("dmg_dist_vargur_moving_atk", "damage", corpus("exct_vargur"), "distance_m", DIST_L, ["dps"],
    {"tgt_speed_pct": 100, "atk_speed_pct": 100, "atk_angle_deg": 45, "tgt_angle_deg": 135}, CRUISER)
add("dmg_dist_naga_bs", "damage", corpus("exct_naga"), "distance_m", DIST_L, ["dps"], {"tgt_speed_pct": 100}, BS)
add("dmg_dist_rifter_vs_fit", "damage", corpus("exct_rifter"), "distance_m", DIST_S, ["dps", "volley"], {"tgt_speed_pct": 100},
    {"fit": corpus("exct_svipul"), "resist_mode": "auto"}, {"ignore_resists": False})
add("dmg_dist_hyperion_vs_fit_armor", "damage", corpus("exct_hyperion"), "distance_m", DIST_S, ["dps"], {"tgt_speed_pct": 50},
    {"fit": corpus("exct_guardian"), "resist_mode": "armor"}, {"ignore_resists": False})
add("dmg_dist_rifter_dmg_at_t", "damage", corpus("exct_rifter"), "distance_m", DIST_S, ["damage"], {"tgt_speed_pct": 100, "time_s": 30}, SMALL)
# special weapons
add("dmg_dist_kikimora_disintegrator", "damage", KIKIMORA, "distance_m", DIST_S, ["dps", "volley"], {"tgt_speed_pct": 100}, SMALL)
add("dmg_dist_skybreaker_vorton", "damage", SKYBREAKER, "distance_m", DIST_S, ["dps", "volley"], {"tgt_speed_pct": 100}, SMALL)
add("dmg_dist_manticore_bomb", "damage", MANTICORE_BOMB, "distance_m", KM(0, 5, 10, 15, 20, 25, 30, 35, 40), ["dps", "volley"], {"tgt_speed_pct": 0}, BS)
add("dmg_dist_thanatos_templar", "damage", THANATOS_TEMPLAR, "distance_m", DIST_L, ["dps", "volley"], {"tgt_speed_pct": 100}, CRUISER)
add("dmg_dist_thanatos_templar_slow_tgt", "damage", THANATOS_TEMPLAR, "distance_m", DIST_L, ["dps"], {"tgt_speed_pct": 20}, BS)
add("dmg_dist_vexor_drones_atk_follow", "damage", corpus("drones_mixed_vexor"), "distance_m", DIST_S, ["dps"],
    {"tgt_speed_pct": 100, "atk_speed_pct": 50, "atk_angle_deg": 0}, SMALL, {"mobile_drone_mode": "follow_attacker"})
add("dmg_dist_rifter_scram_vs_mwd_fit", "damage", corpus("exct_rifter"), "distance_m", KM(0, 2, 5, 7.5, 9, 10, 12, 15, 20), ["dps"],
    {"tgt_speed_pct": 100}, {"fit": corpus("exct_stiletto"), "resist_mode": "auto"}, {"ignore_resists": False})
add("dmg_dist_hyperion_web_vs_fit", "damage", corpus("exct_hyperion"), "distance_m", KM(0, 2, 5, 7.5, 10, 12.5, 15, 20, 30), ["dps"],
    {"tgt_speed_pct": 100}, {"fit": corpus("exct_sabre"), "resist_mode": "weighted_average"}, {"ignore_resists": False})
# ---- damage: time
TIMES = [0, 0.5, 1, 2, 2.5, 3, 5, 7.5, 10, 15, 20, 30, 45, 60, 120]
add("dmg_time_rifter", "damage", corpus("exct_rifter"), "time_s", TIMES, ["dps", "volley", "damage"], {"distance_m": 3000, "tgt_speed_pct": 100}, SMALL)
add("dmg_time_hyperion_reload", "damage", corpus("reload_hyperion"), "time_s", [0, 5, 10, 30, 60, 90, 120, 180, 240, 300], ["dps", "damage"], {"distance_m": 2000, "tgt_speed_pct": 0}, CRUISER)
add("dmg_time_tengu", "damage", corpus("exct_tengu"), "time_s", TIMES, ["dps", "volley", "damage"], {"distance_m": 30000, "tgt_speed_pct": 100}, CRUISER)
add("dmg_time_ishtar_drones", "damage", corpus("drones_heavy_ishtar"), "time_s", TIMES, ["damage"], {"distance_m": 10000, "tgt_speed_pct": 50}, CRUISER)
add("dmg_time_avatar_lance", "damage", corpus("exct_avatar_lance"), "time_s", [0, 5, 9, 10, 11, 15, 20, 30, 60, 300, 600], ["dps", "volley", "damage"], {"distance_m": 50000}, BS)
add("dmg_time_nidhoggur", "damage", corpus("exct_nidhoggur"), "time_s", TIMES, ["damage"], {"distance_m": 20000, "tgt_speed_pct": 50}, BS)
add("dmg_time_kikimora_spool", "damage", KIKIMORA, "time_s", [0, 1, 3, 5, 10, 15, 20, 30, 45, 60, 90, 120], ["dps", "volley", "damage"], {"distance_m": 2000, "tgt_speed_pct": 0}, CRUISER)
add("dmg_time_kestrel_breacher", "damage", KESTREL_BREACHER, "time_s", [0, 1, 2, 3, 5, 10, 20, 30, 60], ["dps", "damage"], {"distance_m": 5000},
    {"fit": corpus("exct_hyperion"), "resist_mode": "auto"})
add("dmg_time_thanatos_templar", "damage", THANATOS_TEMPLAR, "time_s", [0, 1, 5, 10, 20, 30, 60, 120], ["damage"], {"distance_m": 10000, "tgt_speed_pct": 50}, BS)
add("dmg_time_out_of_range", "damage", corpus("exct_rifter"), "time_s", [-5, 0, 10, 2500, 3000], ["dps"], {"distance_m": 3000}, SMALL)
# ---- damage: target speed / signature
SPEEDS = [0, 50, 100, 200, 300, 500, 750, 1000, 1500, 2500]
SIGS = [10, 25, 35, 50, 80, 125, 200, 400, 1000, 5000]
add("dmg_speed_rifter", "damage", corpus("exct_rifter"), "tgt_speed_mps", SPEEDS, ["dps", "volley"], {"distance_m": 5000}, SMALL)
add("dmg_speed_tengu", "damage", corpus("exct_tengu"), "tgt_speed_mps", SPEEDS, ["dps"], {"distance_m": 20000}, CRUISER)
add("dmg_speed_vexor_drones", "damage", corpus("drones_active_vexor"), "tgt_speed_mps", SPEEDS, ["dps"], {"distance_m": 5000}, SMALL)
add("dmg_speed_maelstrom_angle", "damage", corpus("exct_maelstrom"), "tgt_speed_mps", SPEEDS, ["dps"], {"distance_m": 20000, "tgt_angle_deg": 30}, CRUISER)
add("dmg_sig_raven", "damage", corpus("exct_raven"), "tgt_sig_m", SIGS, ["dps", "volley"], {"distance_m": 30000, "tgt_speed_pct": 100}, CRUISER)
add("dmg_sig_hyperion", "damage", corpus("exct_hyperion"), "tgt_sig_m", SIGS, ["dps"], {"distance_m": 5000, "tgt_speed_pct": 100}, CRUISER)
add("dmg_sig_cerberus_time", "damage", corpus("exct_cerberus"), "tgt_sig_m", SIGS, ["dps", "damage"], {"distance_m": 40000, "tgt_speed_pct": 100, "time_s": 20}, CRUISER)
add("dmg_sig_dominix_drones", "damage", corpus("exct_dominix"), "tgt_sig_m", SIGS, ["dps"], {"distance_m": 20000, "tgt_speed_pct": 100}, CRUISER)
# ---- application profile (best charge per distance)
for n, tgt in (("exct_rifter", SMALL), ("exct_hyperion", CRUISER), ("exct_tengu", CRUISER), ("exct_maelstrom", BS),
               ("exct_harbinger", CRUISER), ("exct_raven", BS), ("exct_kronos", CRUISER), ("exct_nightmare", BS)):
    add("app_" + n.split("_", 1)[1], "application_profile", corpus(n), "distance_m", DIST_L, ["dps"], {"tgt_speed_pct": 100}, tgt)
add("app_rifter_volley_t1", "application_profile", corpus("exct_rifter"), "distance_m", DIST_S, ["volley"], {"tgt_speed_pct": 50, "ammo_quality": "t1"}, SMALL)
add("app_hyperion_navy", "application_profile", corpus("exct_hyperion"), "distance_m", DIST_S, ["dps"], {"tgt_speed_pct": 100, "ammo_quality": "navy"}, CRUISER)
# ---- ewar
EW = KM(0, 5, 10, 15, 20, 25, 30, 40, 50, 60, 80, 100)
add("ewar_vigil_tp", "ewar", VIGIL_TP, "distance_m", EW, ["tp_sig_pct"])
add("ewar_vigil_tp_resist", "ewar", VIGIL_TP, "distance_m", EW, ["tp_sig_pct"], {"resist": 0.3})
add("ewar_maulus_damp", "ewar", MAULUS_DAMP, "distance_m", EW, ["damp_lock_range_pct"])
add("ewar_griffin_ecm", "ewar", GRIFFIN_ECM, "distance_m", EW, ["ecm_strength"])
add("ewar_arbitrator_td_gd", "ewar", ARBI_TD, "distance_m", EW, ["td_optimal_pct", "neut_gj_s"])
add("ewar_huginn_web_tp", "ewar", HUGINN_WEB, "distance_m", EW, ["web_pct", "tp_sig_pct"])
add("ewar_bhaalgorn_neut", "ewar", BHAAL_NEUT, "distance_m", EW, ["neut_gj_s"])
add("ewar_bhaalgorn_neut_resist", "ewar", BHAAL_NEUT, "distance_m", EW, ["neut_gj_s"], {"resist": 0.5})
add("ewar_curse", "ewar", corpus("exct_curse"), "distance_m", EW, ["neut_gj_s", "td_optimal_pct"])
add("ewar_vexor_ecm_drones", "ewar", VEXOR_EWAR_DRONES, "distance_m", EW, ["ecm_strength", "web_pct"])
# ---- remote reps
RRD = KM(0, 5, 10, 15, 20, 25, 30, 40, 50, 60, 80)
add("rr_guardian_dist", "remote_reps", corpus("exct_guardian"), "distance_m", RRD, ["rps"])
add("rr_oneiros_dist", "remote_reps", ONEIROS_RR, "distance_m", RRD, ["rps", "total"], {"time_s": 60})
add("rr_scimitar_dist", "remote_reps", SCIMI_RR, "distance_m", RRD, ["rps"])
add("rr_oneiros_time", "remote_reps", ONEIROS_RR, "time_s", [0, 1, 5, 10, 30, 60, 61, 90, 120, 180, 300], ["rps", "total"], {"distance_m": 10000})
add("rr_oneiros_time_noreload", "remote_reps", ONEIROS_RR, "time_s", [0, 10, 30, 60, 90, 120, 300], ["total"], {"distance_m": 10000, "anc_reload": False})
add("rr_scimitar_time", "remote_reps", SCIMI_RR, "time_s", [0, 2, 5, 10, 30, 60, 120], ["rps", "total"], {"distance_m": 40000})
# ---- capacitor
CT = [0, 1, 5, 10, 20, 30, 60, 90, 120, 180, 300, 600, 1200, 3600]
for n in ("exct_rifter", "exct_hyperion", "exct_guardian", "exct_kronos", "exct_tengu", "exct_damnation"):
    add("cap_time_" + n.split("_", 1)[1], "capacitor", corpus(n), "time_s", CT, ["cap_gj"])
add("cap_time_bhaalgorn_start50", "capacitor", BHAAL_NEUT, "time_s", CT, ["cap_gj"], {"cap_start_pct": 50})
add("cap_time_hyperion_nosim", "capacitor", corpus("exct_hyperion"), "time_s", CT, ["cap_gj", "cap_regen_gj_s"], {"use_capsim": False, "cap_start_pct": 0})
add("cap_time_reload_hyperion", "capacitor", corpus("reload_hyperion"), "time_s", CT, ["cap_gj"], {"cap_start_pct": 100})
add("cap_pct_rifter", "capacitor", corpus("exct_rifter"), "cap_pct", [0, 5, 10, 25, 50, 75, 90, 100, 120], ["cap_gj", "cap_regen_gj_s"])
add("cap_pct_kronos", "capacitor", corpus("exct_kronos"), "cap_pct", [0, 10, 25, 50, 75, 100], ["cap_regen_gj_s"])
# ---- shield regen
ST = [0, 1, 10, 30, 60, 120, 300, 600, 1200]
add("shield_time_tengu", "shield_regen", corpus("exct_tengu"), "time_s", ST, ["shield_hp", "shield_regen_hp_s"])
add("shield_time_rattlesnake_eff", "shield_regen", corpus("exct_rattlesnake"), "time_s", ST, ["shield_hp", "shield_regen_hp_s"], {"effective": True, "shield_start_pct": 25})
add("shield_pct_drake", "shield_regen", corpus("exct_naga"), "shield_pct", [0, 10, 25, 50, 75, 100], ["shield_regen_hp_s"])
add("shield_pct_vargur_eff", "shield_regen", corpus("dmgpattern_kin_maelstrom"), "shield_pct", [0, 10, 25, 50, 75, 100], ["shield_hp", "shield_regen_hp_s"], {"effective": True})
# ---- mobility
MT = [0, 0.5, 1, 2, 3, 5, 7.5, 10, 15, 20, 30]
for n in ("exct_rifter", "exct_hyperion", "exct_stiletto", "exct_venture", "exct_broadsword_bubble", "exct_vargur"):
    add("mob_" + n.split("_", 1)[1], "mobility", corpus(n), "time_s", MT, ["speed_mps", "distance_m", "momentum_kg_mps"])
add("mob_avatar_doomsday_active", "mobility", corpus("exct_avatar_lance"), "time_s", MT, ["speed_mps"])
add("mob_bump_machariel", "mobility", corpus("esf_machariel"), "time_s", MT, ["bump_speed_mps", "bump_distance_m"], {"tgt_mass_kg": 1.1e9, "tgt_inertia": 0.02})
add("mob_bump_rifter_default", "mobility", corpus("exct_rifter"), "time_s", MT, ["bump_speed_mps", "bump_distance_m"])
# ---- warp time
WD = [0, 150e3, 1e6, 1e7, 1e8, 0.5 * AU, AU, 2 * AU, 5 * AU, 10 * AU, 20 * AU, 50 * AU, 200 * AU]
for n in ("exct_rifter", "exct_hyperion", "exct_avatar_lance", "exct_stiletto", "exct_venture", "esf_orca", "exct_vargur"):
    add("warp_" + n.split("_", 1)[1], "warp_time", corpus(n), "distance_m", WD, ["time_s"])
# ---- lock time
LS = [0, 0.5, 1, 10, 25, 40, 65, 125, 250, 400, 1000, 5000, 100000]
for n in ("exct_rifter", "exct_hyperion", "exct_avatar_lance", "exct_sabre", "exct_crucifier", "exct_rattlesnake"):
    add("lock_" + n.split("_", 1)[1], "lock_time", corpus(n), "tgt_sig_m", LS, ["time_s"])

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.json"):
        old.unlink()
    for name, r in sorted(cases.items()):
        (OUT / (name + ".json")).write_text(json.dumps(r, indent=1, sort_keys=True) + "\n")
    print(len(cases), "graph cases,", sum(len(r["x"]["values"]) * len(r["y"]) for r in cases.values()), "sample values")
