#!/usr/bin/env python3
"""DRAFT 0.3 corpus generator -> graphs/draft-0.3/cases (+ expected/err_*.json). Does not touch graphs/cases.

0.3 draft = the frozen 0.2 corpus (imported from graphs/tools/make_graph_cases.py, unchanged) + the cases below
(eve's 0.3 rulings, items 1-4 and 6 of graphs/pending.md). Application-profile sample points must not be
interpolation/transition-scan sensitive: check with tools/edge_check.py (see README)."""
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DRAFT = HERE.parent
ROOT = DRAFT.parents[1]
sys.path.insert(0, str(ROOT / "graphs/tools"))
import make_graph_cases as M  # noqa: E402  (module-level adds only; nothing is written on import)

cases = dict(M.cases)
ERRORS = dict(M.ERRORS)
NEW = []


def add(name, *a, **kw):
    assert name not in cases, name
    M.add(name, *a, **kw)  # M.add writes into M.cases
    cases[name] = M.cases[name]
    NEW.append(name)


KM, C = M.KM, M.corpus
D = KM(0, 2, 5, 10, 15, 20, 25, 30, 40, 50, 60, 70, 80)
# (1) sentry drones never follow (drone speed <= 1), even in follow_target
add("dmg_dist_ishtar_sentries_follow_target", "damage", C("drones_sentry_ishtar"), "distance_m", D, ["dps"], {"tgt_speed_pct": 100}, M.CRUISER,
    {"mobile_drone_mode": "follow_target"})
add("dmg_dist_dominix_sentries_follow_target", "damage", C("drones_sentry_dominix"), "distance_m", D, ["dps"], {"tgt_speed_pct": 100}, M.CRUISER,
    {"mobile_drone_mode": "follow_target"})
# (2) breacher pods: missile range chance x breacherPodDamageResistance on the per-tick value
add("dmg_dist_kestrel_breacher_fine", "damage", M.KESTREL_BREACHER, "distance_m", [5000 + 250 * i for i in range(25)], ["dps", "damage"],
    {"time_s": 30}, {"fit": C("exct_hyperion")})
add("dmg_dist_kestrel_breacher_profile", "damage", M.KESTREL_BREACHER, "distance_m", KM(0, 2, 4, 5, 6, 7, 8, 9, 10, 12, 15), ["dps"], {}, M.CRUISER_RES)
# (3) dps/volley are 0 between active cycle segments (bomb reactivation delay, reload); damage holds
add("dmg_time_manticore_bomb", "damage", M.MANTICORE_BOMB, "time_s", [0, 0.5, 1, 2, 5, 9, 10, 11, 12, 13, 15, 20, 25, 30, 40, 60, 120],
    ["dps", "volley", "damage"], {"distance_m": 20000, "tgt_speed_pct": 0}, M.BS)
add("dmg_time_manticore_bomb_reload", "damage", M.MANTICORE_BOMB, "time_s", [0, 30, 60, 90, 120, 150, 180, 240, 300, 400, 600], ["dps", "damage"],
    {"distance_m": 20000}, M.BS)
# (4) fighters that don't follow: range factor at d + r_attacker - r_fighter (no minimum speed)
FD = KM(0, 1, 2, 5, 10, 15, 20, 25, 30, 40, 50, 60, 80, 100)
for n, f in (("thanatos_templar", M.THANATOS_TEMPLAR), ("hel", C("exct_hel")), ("nidhoggur", C("exct_nidhoggur"))):
    add(f"dmg_dist_{n}_fast_target", "damage", f, "distance_m", FD, ["dps"], {"tgt_speed_mps": 8000}, M.BS)
# (6) quality tiers: XL navy = T1 + T2 + Sansha / Arch Angel / Shadow (Republic Fleet XL, Blood XL excluded)
XL = KM(0, 5, 10, 20, 30, 40, 50, 75, 100, 150)
add("app_naglfar_navy_xl", "application_profile", M.fit(19722, [(37307, 17668)] * 2), "distance_m", XL, ["dps"],
    {"tgt_speed_pct": 0, "ammo_quality": "navy"}, M.BS)
add("app_revelation_navy_xl", "application_profile", M.fit(19720, [(37298, 17686)] * 3), "distance_m", XL, ["dps"],
    {"tgt_speed_pct": 0, "ammo_quality": "navy"}, M.BS)
add("app_moros_navy_xl", "application_profile", M.fit(19724, [(3186, 17648)] * 3), "distance_m", XL, ["dps"],
    {"tgt_speed_pct": 0, "ammo_quality": "navy"}, M.BS)
# (5, ruling: not scored) projected webs/TPs in application_profile, sampled only away from the web/TP edges
MAEL_ARTY_WEB_TP = M.fit(24694, [(2961, 201)] * 4 + [(527, None), (19806, None)])
add("app_maelstrom_arty_web_tp_off_edge", "application_profile", MAEL_ARTY_WEB_TP, "distance_m", KM(0, 2, 5, 8, 15, 20, 30, 40, 60, 80, 100),
    ["dps"], {"tgt_speed_pct": 100}, M.CRUISER)

if __name__ == "__main__":
    out, exp = DRAFT / "cases", DRAFT / "expected"
    out.mkdir(parents=True, exist_ok=True)
    exp.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.json"):
        old.unlink()
    for old in exp.glob("err_*.json"):
        old.unlink()
    for name, r in sorted(cases.items()):
        (out / (name + ".json")).write_text(json.dumps(r, indent=1, sort_keys=True) + "\n")
    for name, (r, code) in sorted(ERRORS.items()):
        (out / (name + ".json")).write_text(json.dumps(r, indent=1, sort_keys=True) + "\n")
        (exp / (name + ".json")).write_text(json.dumps({"case": name, "graph": r.get("graph"), "oracle": "contract", "expect_error": code},
                                                       indent=1, sort_keys=True) + "\n")
    (DRAFT / "NEW_CASES.txt").write_text("\n".join(sorted(NEW)) + "\n")
    print(len(cases), "value cases (", len(NEW), "new in 0.3 draft ),", len(ERRORS), "error cases")
