#!/usr/bin/env python3
"""Generate stats-ext/cases/*.json (EXCT FitRequest v1) and index.json from the case table below.
usage: python3 stats-ext/make_cases.py            (then run stats-ext/oracle_ext.py to refresh expected/)"""
import json, pathlib
ROOT = pathlib.Path(__file__).resolve().parent


def mod(tid, slot, state="active", charge=None):
    return {"type_id": tid, "slot": slot, "state": state, "charge_type_id": charge}


def drone(tid, n, active=None):
    return {"type_id": tid, "quantity": n, "active": n if active is None else active}


def req(ship, modules=(), drones=(), skills=5, levels=None, **kw):
    r = {"ship": {"type_id": ship}, "character": {"skills": {"default_level": skills, "levels": levels or {}}},
         "modules": list(modules), "drones": list(drones), "implants": [], "projected": []}
    r.update(kw)
    return r


H, M, L, R = "high", "mid", "low", "rig"
CASES = {}   # name -> (category, request)


def case(cat, name, r):
    CASES[f"{cat}_{name}"] = (cat, r)


# ---------------------------------------------------------------- batch 1: mining (modules + drones, waste, crit)
VENTURE, PROSPECT, ENDURANCE, PIONEER = 32880, 33697, 37135, 89240
PROCURER, RETRIEVER, COVETOR, SKIFF, MACKINAW, HULK, PORPOISE, ORCA, RORQUAL = 17480, 17478, 17476, 22546, 22548, 22544, 42244, 28606, 28352
MINER1, MINER2, DCML1, ORE_MINER = 483, 482, 12108, 28750
STRIP1, MSM2, MDCSM2, ICE1, ICE2, ICEML1, ICEML2 = 17482, 17912, 24305, 16278, 22229, 37450, 37451
GAS1, GAS2, GAS_ORE = 60313, 60314, 60315
MLU2, IHU2 = 28576, 28578
MD1, MD2, HARV, EXC, AUG, ICE_D2, EXC_ICE = 10246, 10250, 3218, 41030, 43694, 43700, 43681
SIMPLE_A2, SIMPLE_B2, SIMPLE_C2, SIMPLE_A1, MERC_A2, VELD1 = 60281, 60283, 60284, 60276, 18608, 18066
MED_DMA1, LG_DMA2, CAP_DMA2, MED_ICE_ACC = 32043, 26328, 33287, 32819
IND_CORE_M2, IND_CORE_L2, IND_CORE_CAP2 = 62591, 58950, 42890
FOREMAN2, LASER_OPT_CHG, FIELD_ENH_CHG = 43551, 42830, 42829

case("mining", "venture_miner2", req(VENTURE, [mod(MINER2, H), mod(MINER2, H)]))
case("mining", "venture_miner2_online", req(VENTURE, [mod(MINER2, H, "online"), mod(MINER2, H, "online")]))
case("mining", "venture_miner1_skills0", req(VENTURE, [mod(MINER1, H), mod(MINER1, H)], skills=0))
case("mining", "venture_miner2_skills_mixed", req(VENTURE, [mod(MINER2, H), mod(MINER2, H), mod(MLU2, L)], skills=3,
                                                  levels={"3386": 5, "3410": 1, "32918": 4}))
case("mining", "venture_gas1", req(VENTURE, [mod(GAS1, H), mod(GAS1, H)]))
case("mining", "prospect_gas2", req(PROSPECT, [mod(GAS2, H), mod(GAS2, H)]))
case("mining", "prospect_miner2_mlu", req(PROSPECT, [mod(MINER2, H), mod(MINER2, H), mod(MLU2, L), mod(MLU2, L)]))
case("mining", "endurance_ice_laser2", req(ENDURANCE, [mod(ICEML2, H), mod(ICEML2, H)], [drone(ICE_D2, 2)]))
case("mining", "endurance_ice_laser1_off", req(ENDURANCE, [mod(ICEML1, H), mod(ICEML1, H, "offline")]))
case("mining", "pioneer_ore_miner", req(PIONEER, [mod(ORE_MINER, H), mod(ORE_MINER, H)]))
case("mining", "procurer_strip1", req(PROCURER, [mod(STRIP1, H)]))
case("mining", "procurer_ice1", req(PROCURER, [mod(ICE1, H), mod(IHU2, L)], [drone(MD1, 2)]))
case("mining", "retriever_strip1_mlu", req(RETRIEVER, [mod(STRIP1, H), mod(STRIP1, H), mod(MLU2, L), mod(MLU2, L)], [drone(MD2, 2)]))
case("mining", "covetor_msm2_nocrystal", req(COVETOR, [mod(MSM2, H), mod(MSM2, H)]))
case("mining", "covetor_msm2_simple_a2", req(COVETOR, [mod(MSM2, H, charge=SIMPLE_A2), mod(MSM2, H, charge=SIMPLE_A2)]))
case("mining", "covetor_msm2_simple_b2", req(COVETOR, [mod(MSM2, H, charge=SIMPLE_B2), mod(MSM2, H, charge=SIMPLE_B2)]))
case("mining", "covetor_msm2_simple_c2", req(COVETOR, [mod(MSM2, H, charge=SIMPLE_C2), mod(MSM2, H, charge=SIMPLE_C2)]))
case("mining", "covetor_msm2_simple_a1_reload", req(COVETOR, [mod(MSM2, H, charge=SIMPLE_A1), mod(MSM2, H, charge=SIMPLE_A1)],
                                                    options={"factor_reload": True}))
case("mining", "hulk_msm2_b2_mlu_drones", req(HULK, [mod(MSM2, H, charge=SIMPLE_B2), mod(MSM2, H, charge=SIMPLE_B2), mod(MSM2, H, charge=SIMPLE_B2),
                                                     mod(MLU2, L), mod(MLU2, L)], [drone(MD2, 2)]))
case("mining", "hulk_msm2_mixed_states", req(HULK, [mod(MSM2, H, charge=SIMPLE_A2), mod(MSM2, H, "online", SIMPLE_A2), mod(MSM2, H, "offline")]))
case("mining", "skiff_mdcsm2_merc_a2", req(SKIFF, [mod(MDCSM2, H, charge=MERC_A2)], [drone(MD2, 5)]))
case("mining", "mackinaw_ice2_ihu", req(MACKINAW, [mod(ICE2, H), mod(IHU2, L), mod(IHU2, L), mod(MED_ICE_ACC, R)], [drone(ICE_D2, 5)]))
case("mining", "mackinaw_ice1", req(MACKINAW, [mod(ICE1, H)]))
case("mining", "porpoise_excavator_core", req(PORPOISE, [mod(IND_CORE_M2, M), mod(MED_DMA1, R)], [drone(EXC, 2)]))
case("mining", "porpoise_md2_dma", req(PORPOISE, [mod(MED_DMA1, R), mod(MED_DMA1, R)], [drone(MD2, 5)]))
case("mining", "orca_aug_drones_core", req(ORCA, [mod(IND_CORE_L2, M), mod(LG_DMA2, R)], [drone(AUG, 5)]))
case("mining", "orca_ice_excavators", req(ORCA, [mod(IND_CORE_L2, M)], [drone(EXC_ICE, 5)]))
case("mining", "rorqual_excavators_core", req(RORQUAL, [mod(IND_CORE_CAP2, M), mod(CAP_DMA2, R), mod(CAP_DMA2, R)], [drone(EXC, 5)]))
case("mining", "rorqual_excavators_nocore", req(RORQUAL, [], [drone(EXC, 5)]))
case("mining", "retriever_drones_inactive", req(RETRIEVER, [mod(STRIP1, H, "online")], [drone(MD2, 5, 0)]))
case("mining", "mixed_drones_skills0", req(VENTURE, [mod(MINER2, H)], [drone(MD1, 1), drone(HARV, 1)], skills=0))
case("mining", "hulk_foreman_boost", req(HULK, [mod(MSM2, H, charge=SIMPLE_A2), mod(MSM2, H, charge=SIMPLE_A2), mod(MSM2, H, charge=SIMPLE_A2)],
                                         [drone(MD2, 2)],
                                         fleet={"buffs": [], "booster_fits": [req(ORCA, [mod(FOREMAN2, H, charge=LASER_OPT_CHG),
                                                                                         mod(FOREMAN2, H, charge=FIELD_ENH_CHG)])]}))


def main():
    cd = ROOT / "cases"
    cd.mkdir(exist_ok=True)
    idx = []
    for name, (cat, r) in sorted(CASES.items()):
        (cd / f"{name}.json").write_text(json.dumps(r, indent=1, sort_keys=True) + "\n")
        idx.append({"case": name, "category": cat})
    (ROOT / "index.json").write_text(json.dumps(idx, indent=1) + "\n")
    print(f"{len(idx)} cases")


if __name__ == "__main__":
    main()
