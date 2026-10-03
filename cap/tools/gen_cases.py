#!/usr/bin/env python3
"""Generate the capacitor-simulation suite: cap/cases/<name>.json (FitRequest) + cap/index.json.

Fits are written from item names (resolved against the shared dataset, published types only) so the corpus is
readable; every name must resolve or generation fails. A few cases reuse bench 1.8.0 fits with every module
overheated (the "34 all-overheated" set where engines disagreed).
usage: python3 cap/tools/gen_cases.py [--dataset PATH]"""
import argparse, gzip, json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
BENCH = ROOT.parent
ap = argparse.ArgumentParser()
ap.add_argument("--dataset", default="/workspace/exct-eve/data/dataset-3569502.json.gz")
a = ap.parse_args()
DS = json.load(gzip.open(a.dataset))
BY = {}
for k, t in DS["types"].items():
    if t.get("published") and t.get("name"):
        BY.setdefault(t["name"], int(k))


OVERLOAD = {int(k) for k, e in DS["effects"].items() if e.get("category") == 5}


def can_overheat(type_id):
    """only modules with an overload effect are overheated: the contract keeps a requested unavailable state, while
    Pyfa (the oracle) falls back to online, so such requests would not test the capacitor simulation"""
    t = DS["types"].get(str(type_id), {})
    return any(e[0] in OVERLOAD for e in t.get("effects", []))


def tid(name):
    if name not in BY:
        raise SystemExit(f"unknown type name: {name}")
    return BY[name]


def M(name, slot, state="active", charge=None):
    return {"type_id": tid(name), "slot": slot, "state": state, "charge_type_id": tid(charge) if charge else None}


def fit(ship, modules, drones=(), projected=(), skills=5, options=None, implants=()):
    r = {"ship": {"type_id": tid(ship)}, "character": {"skills": {"default_level": skills, "levels": {}}},
         "modules": list(modules), "drones": list(drones), "projected": list(projected),
         "implants": [{"type_id": tid(i)} for i in implants]}
    if options:
        r["options"] = options
    return r


def D(name, qty, active=None):
    return {"type_id": tid(name), "quantity": qty, "active": qty if active is None else active}


def PM(name, amount=1, dist=10000, charge=None, state=None):
    m = {"type_id": tid(name)}
    if charge:
        m["charge_type_id"] = tid(charge)
    if state:
        m["state"] = state
    return {"kind": "module", "module": m, "amount": amount, "distance_m": dist}


def PD(name, qty, dist=1000):
    return {"kind": "drone", "drone": {"type_id": tid(name), "quantity": qty, "active": qty}, "amount": 1, "distance_m": dist}


def PF(req, amount=1, dist=10000):
    return {"kind": "fit", "fit": req, "amount": amount, "distance_m": dist}


def oh(mods, which=None):
    """overheat every module (or the given indexes) that has a state"""
    out = []
    for i, m in enumerate(mods):
        m = dict(m)
        if (which is None or i in which) and m["state"] == "active" and can_overheat(m["type_id"]):
            m["state"] = "overheated"
        out.append(m)
    return out


CASES = []


def case(name, cat, desc, req):
    CASES.append((name, cat, desc, req))


# ---------------------------------------------------------------- fits used in several categories
punisher = [M("5MN Microwarpdrive II", "mid"), M("Warp Scrambler II", "mid"), M("Small Armor Repairer II", "low"),
            M("Small Armor Repairer II", "low"), M("Small Focused Pulse Laser II", "high", charge="Multifrequency S"),
            M("Small Focused Pulse Laser II", "high", charge="Multifrequency S"),
            M("Small Focused Pulse Laser II", "high", charge="Multifrequency S")]
maller = [M("10MN Afterburner II", "mid"), M("Warp Disruptor II", "mid"), M("Medium Armor Repairer II", "low"),
          M("Medium Armor Repairer II", "low"), M("Multispectrum Energized Membrane II", "low"),
          M("Heavy Pulse Laser II", "high", charge="Scorch M"), M("Heavy Pulse Laser II", "high", charge="Scorch M"),
          M("Heavy Pulse Laser II", "high", charge="Scorch M"), M("Heavy Pulse Laser II", "high", charge="Scorch M")]
megathron = [M("50MN Microwarpdrive II", "mid"), M("Warp Scrambler II", "mid"), M("Stasis Webifier II", "mid"),
             M("Large Armor Repairer II", "low"), M("Reactive Armor Hardener", "low"), M("Damage Control II", "low"),
             *[M("Neutron Blaster Cannon II", "high", charge="Antimatter Charge L") for _ in range(6)]]
apocalypse = [M("100MN Afterburner II", "mid"), M("Tracking Computer II", "mid"), M("Sensor Booster II", "mid"),
              M("Large Armor Repairer II", "low"), M("Large Armor Repairer II", "low"),
              *[M("Mega Pulse Laser II", "high", charge="Multifrequency L") for _ in range(8)]]
raven = [M("X-Large Shield Booster II", "mid"), M("Multispectrum Shield Hardener II", "mid"),
         M("Multispectrum Shield Hardener II", "mid"), M("100MN Afterburner II", "mid"), M("Target Painter II", "mid"),
         *[M("Heavy Missile Launcher II", "high", charge="Scourge Heavy Missile") for _ in range(6)]]
drake = [M("Large Shield Booster II", "mid"), M("Multispectrum Shield Hardener II", "mid"), M("10MN Afterburner II", "mid"),
         M("Warp Disruptor II", "mid"), *[M("Heavy Missile Launcher II", "high", charge="Scourge Heavy Missile") for _ in range(6)]]
thorax = [M("10MN Afterburner II", "mid"), M("Warp Scrambler II", "mid"), M("Stasis Webifier II", "mid"),
          M("Medium Armor Repairer II", "low"), M("Damage Control II", "low"),
          *[M("Heavy Electron Blaster II", "high", charge="Antimatter Charge M") for _ in range(5)]]
hurricane = [M("50MN Microwarpdrive II", "mid"), M("Warp Scrambler II", "mid"), M("Stasis Webifier II", "mid"),
             M("Medium Energy Neutralizer II", "high"), M("Medium Energy Neutralizer II", "high"),
             M("Medium Armor Repairer II", "low")]

# ---------------------------------------------------------------- A. baseline local modules
case("base_rifter_passive", "baseline", "no cap-using module: no drains, stable 100 %",
     fit("Rifter", [M("Damage Control II", "low")]))
case("base_punisher", "baseline", "frigate MWD + dual rep + lasers", fit("Punisher", punisher))
case("base_maller", "baseline", "cruiser AB + dual rep + lasers", fit("Maller", maller))
case("base_thorax", "baseline", "blasters (turrets, unstaggered) + AB + rep", fit("Thorax", thorax))
case("base_megathron", "baseline", "battleship MWD + blasters + rep", fit("Megathron", megathron))
case("base_apocalypse", "baseline", "8 mega pulse lasers + dual rep", fit("Apocalypse", apocalypse))
case("base_raven", "baseline", "XL shield booster + hardeners + missiles", fit("Raven", raven))
case("base_drake", "baseline", "large shield booster + hardener", fit("Drake", drake))
case("base_apocalypse_skills0", "baseline", "all skills 0", fit("Apocalypse", apocalypse, skills=0))
case("base_maller_skills3", "baseline", "all skills 3", fit("Maller", maller, skills=3))
case("base_megathron_rep_only", "baseline", "a single large armor repairer", fit("Megathron", [M("Large Armor Repairer II", "low")]))
case("base_abaddon_lasers", "baseline", "abaddon with lasers, rep, hardener", fit("Abaddon", [
    M("100MN Afterburner II", "mid"), M("Large Armor Repairer II", "low"), M("Reactive Armor Hardener", "low"),
    *[M("Mega Pulse Laser II", "high", charge="Multifrequency L") for _ in range(8)]]))

# ---------------------------------------------------------------- B. capacitor modifiers
case("mod_cap_batteries", "modifiers", "large cap batteries raise capacity",
     fit("Apocalypse", apocalypse + [M("Large Cap Battery II", "mid", "online")]))
case("mod_power_relays", "modifiers", "capacitor power relays (recharge, shield boost penalty)",
     fit("Raven", raven + [M("Capacitor Power Relay II", "low", "online"), M("Capacitor Power Relay II", "low", "online")]))
case("mod_flux_coils", "modifiers", "flux coils (recharge up, capacity down)",
     fit("Maller", maller + [M("Capacitor Flux Coil II", "low", "online"), M("Capacitor Flux Coil II", "low", "online")]))
case("mod_ccc_rigs", "modifiers", "capacitor control circuit rigs",
     fit("Megathron", megathron + [M("Large Capacitor Control Circuit I", "rig", "online") for _ in range(3)]))
case("mod_cap_rechargers", "modifiers", "cap rechargers (stacking-penalised)",
     fit("Drake", drake + [M("Cap Recharger II", "mid", "online"), M("Cap Recharger II", "mid", "online")]))
case("mod_mix_punisher", "modifiers", "small battery + CCC rigs on a frigate",
     fit("Punisher", punisher + [M("Small Cap Battery II", "mid", "online"), M("Small Capacitor Control Circuit I", "rig", "online")]))

# ---------------------------------------------------------------- C. overheating
case("oh_maller_reps", "overheat", "overheated armor repairers (cycle time to fractional ms, truncated)",
     fit("Maller", oh(maller, {2, 3})))
case("oh_maller_all", "overheat", "every module overheated", fit("Maller", oh(maller)))
case("oh_drake_booster", "overheat", "overheated shield booster", fit("Drake", oh(drake, {0})))
case("oh_raven_all", "overheat", "every module overheated", fit("Raven", oh(raven)))
case("oh_thorax_all", "overheat", "blasters, AB, web, scram, rep overheated", fit("Thorax", oh(thorax)))
case("oh_megathron_mwd", "overheat", "overheated MWD", fit("Megathron", oh(megathron, {0})))
case("oh_hurricane_neuts", "overheat", "overheated neutralizers", fit("Hurricane", oh(hurricane, {3, 4})))
case("oh_apocalypse_lasers", "overheat", "overheated lasers", fit("Apocalypse", oh(apocalypse, set(range(5, 13)))))
case("oh_punisher_all", "overheat", "frigate every module overheated", fit("Punisher", oh(punisher)))
case("oh_abaddon_reps_rah", "overheat", "overheated rep + reactive hardener", fit("Abaddon", oh([
    M("100MN Afterburner II", "mid"), M("Large Armor Repairer II", "low"), M("Reactive Armor Hardener", "low"),
    *[M("Mega Pulse Laser II", "high", charge="Multifrequency L") for _ in range(8)]], {1, 2})))

# bench fits with every module overheated (where engines disagreed); copied from cases/ with states rewritten
for b in ["exct_hyperion_armor", "exct_rifter", "exct_cerberus", "exct_tengu", "exct_nightmare", "exct_kronos"]:
    p = BENCH / "cases" / f"{b}.json"
    if p.exists():
        r = json.loads(p.read_text())
        for m in r.get("modules", []):
            if m.get("state") in ("active", None) and can_overheat(m["type_id"]):
                m["state"] = "overheated"
        # bench cases carry cap_sim.stagger=false, which the main bench oracle ignores (Pyfa always staggers);
        # use the default here so this category tests overheating only (stagger-off is pending, CONTRACT-CAP §9)
        r.setdefault("options", {}).setdefault("cap_sim", {})["stagger"] = True
        case(f"oh_bench_{b}", "overheat", f"bench case {b} with every overheatable module overheated", r)

# ---------------------------------------------------------------- D. capacitor boosters (injectors)
case("inj_small_frigate", "injectors", "small cap booster on an unstable frigate",
     fit("Punisher", punisher + [M("Small Capacitor Booster II", "mid", charge="Navy Cap Booster 150")]))
case("inj_medium_maller", "injectors", "medium booster, navy 400",
     fit("Maller", maller + [M("Medium Capacitor Booster II", "mid", charge="Navy Cap Booster 400")]))
case("inj_medium_800_overshoot", "injectors", "800 charges on a cruiser (overshoot: injections postponed)",
     fit("Maller", maller + [M("Medium Capacitor Booster II", "mid", charge="Navy Cap Booster 800")]))
case("inj_heavy_megathron", "injectors", "heavy booster on a battleship",
     fit("Megathron", megathron + [M("Heavy Capacitor Booster II", "mid", charge="Navy Cap Booster 800")]))
case("inj_two_heavy", "injectors", "two heavy boosters (injectors never staggered)",
     fit("Apocalypse", apocalypse + [M("Heavy Capacitor Booster II", "mid", charge="Navy Cap Booster 800"),
                                     M("Heavy Capacitor Booster II", "mid", charge="Navy Cap Booster 800")]))
case("inj_mixed_charges", "injectors", "two boosters with different charges",
     fit("Apocalypse", apocalypse + [M("Heavy Capacitor Booster II", "mid", charge="Navy Cap Booster 800"),
                                     M("Heavy Capacitor Booster II", "mid", charge="Navy Cap Booster 400")]))
case("inj_factor_reload", "injectors", "booster with options.factor_reload (reload in the simulation for every module)",
     fit("Maller", maller + [M("Medium Capacitor Booster II", "mid", charge="Navy Cap Booster 400")], options={"factor_reload": True}))
case("inj_offline", "injectors", "offline booster: no injection", fit("Maller", maller + [M("Medium Capacitor Booster II", "mid", "offline", charge="Navy Cap Booster 400")]))
case("inj_no_charge", "injectors", "booster without charges: no injection", fit("Maller", maller + [M("Medium Capacitor Booster II", "mid")]))
case("inj_frigate_huge_charge", "injectors", "800 charge into a frigate capacitor (always overshoots)",
     fit("Punisher", punisher + [M("Small Capacitor Booster II", "mid", charge="Navy Cap Booster 800")]))
case("inj_capital", "injectors", "capital booster on a dreadnought with a capital rep",
     fit("Revelation", [M("Capital Armor Repairer II", "low"), M("Capital Armor Repairer II", "low"),
                        M("Capital Capacitor Booster II", "mid", charge="Navy Cap Booster 3200")]))
case("inj_asb", "injectors", "ancillary shield booster with cap booster charges (no cap use while loaded)",
     fit("Drake", drake + [M("Large Ancillary Shield Booster", "mid", charge="Navy Cap Booster 400")]))
case("inj_asb_reload", "injectors", "ancillary shield booster, factor_reload",
     fit("Drake", drake + [M("Large Ancillary Shield Booster", "mid", charge="Navy Cap Booster 400")], options={"factor_reload": True}))
case("inj_stable_ship", "injectors", "booster on an already stable fit (postponed, stays full)",
     fit("Drake", drake + [M("Medium Capacitor Booster II", "mid", charge="Navy Cap Booster 400")]))

# ---------------------------------------------------------------- E. own neutralizers / nosferatu
curse = [M("Heavy Energy Neutralizer II", "high"), M("Heavy Energy Neutralizer II", "high"),
         M("Medium Energy Neutralizer II", "high"), M("10MN Afterburner II", "mid"), M("Medium Armor Repairer II", "low")]
case("own_curse_neuts", "own_neut_nos", "heavy + medium neuts", fit("Curse", curse))
case("own_curse_neuts_oh", "own_neut_nos", "neuts overheated", fit("Curse", oh(curse, {0, 1, 2})))
case("own_bhaalgorn", "own_neut_nos", "battleship heavy neuts", fit("Bhaalgorn", [
    *[M("Heavy Energy Neutralizer II", "high") for _ in range(4)], M("Large Armor Repairer II", "low"),
    M("100MN Afterburner II", "mid"), M("Stasis Webifier II", "mid")]))
case("own_ashimmu_nos", "own_neut_nos", "nosferatu count as cap gain in the simulation", fit("Ashimmu", [
    M("Medium Energy Nosferatu II", "high"), M("Medium Energy Nosferatu II", "high"), M("Medium Energy Nosferatu II", "high"),
    M("10MN Afterburner II", "mid"), M("Medium Armor Repairer II", "low"), M("Medium Armor Repairer II", "low")]))
case("own_nos_only", "own_neut_nos", "only nosferatu: always stable", fit("Ashimmu", [M("Heavy Energy Nosferatu II", "high")]))
case("own_neut_nos_mix", "own_neut_nos", "neuts and nos together", fit("Bhaalgorn", [
    M("Heavy Energy Neutralizer II", "high"), M("Heavy Energy Neutralizer II", "high"), M("Heavy Energy Nosferatu II", "high"),
    M("Heavy Energy Nosferatu II", "high"), M("Large Armor Repairer II", "low"), M("100MN Afterburner II", "mid")]))
case("own_faction_neuts", "own_neut_nos", "faction / compact neuts (different cycle times)", fit("Armageddon", [
    M("Imperial Navy Heavy Energy Neutralizer", "high"), M("Corpus X-Type Heavy Energy Neutralizer", "high"),
    M("Heavy Gremlin Compact Energy Neutralizer", "high"), M("Large Armor Repairer II", "low"), M("100MN Afterburner II", "mid")]))
case("own_pilgrim", "own_neut_nos", "recon neut + nos", fit("Pilgrim", [
    M("Medium Energy Neutralizer II", "high"), M("Medium Energy Nosferatu II", "high"), M("10MN Afterburner II", "mid"),
    M("Medium Armor Repairer II", "low")]))
case("own_hurricane", "own_neut_nos", "medium neuts on a battlecruiser", fit("Hurricane", hurricane))
case("own_nos_oh", "own_neut_nos", "overheated nosferatu", fit("Ashimmu", oh([
    M("Medium Energy Nosferatu II", "high"), M("Medium Energy Nosferatu II", "high"), M("10MN Afterburner II", "mid"),
    M("Medium Armor Repairer II", "low")], {0, 1})))

# ---------------------------------------------------------------- F. incoming drains
case("in_neut_1heavy", "incoming", "one heavy neut on a cruiser", fit("Maller", maller, projected=[PM("Heavy Energy Neutralizer II")]))
case("in_neut_3heavy", "incoming", "three heavy neuts (amount 3)", fit("Maller", maller, projected=[PM("Heavy Energy Neutralizer II", 3)]))
case("in_neut_falloff", "incoming", "neut in falloff (range factor)", fit("Maller", maller, projected=[PM("Heavy Energy Neutralizer II", 1, 20000)]))
case("in_neut_out_of_range", "incoming", "neut far beyond falloff", fit("Maller", maller, projected=[PM("Heavy Energy Neutralizer II", 1, 90000)]))
case("in_neut_sigres_frigate", "incoming", "heavy neut on a frigate (signature resolution)", fit("Punisher", punisher, projected=[PM("Heavy Energy Neutralizer II")]))
case("in_neut_small_on_bs", "incoming", "small neuts on a battleship", fit("Megathron", megathron, projected=[PM("Small Energy Neutralizer II", 4)]))
case("in_nos_enemy", "incoming", "enemy nosferatu drain the target", fit("Maller", maller, projected=[PM("Heavy Energy Nosferatu II", 2)]))
case("in_drone_acolyte", "incoming", "5 light neut drones", fit("Maller", maller, projected=[PD("Acolyte EV-300", 5)]))
case("in_drone_infiltrator", "incoming", "medium neut drones", fit("Megathron", megathron, projected=[PD("Infiltrator EV-600", 5)]))
case("in_drone_praetor", "incoming", "heavy neut drones on a frigate (sig resolution)", fit("Punisher", punisher, projected=[PD("Praetor EV-900", 2)]))
case("in_drone_out_of_optimal", "incoming", "neut drones beyond their neutralizer optimal range (no drain)", fit("Maller", maller, projected=[PD("Acolyte EV-300", 5, 12000)]))
case("in_void_bomb", "incoming", "void bomb (bomb launcher cycle + reactivation)", fit("Maller", maller, projected=[PM("Bomb Launcher I", 1, 10000, charge="Void Bomb")]))
case("in_neut_fit", "incoming", "projected fit with two heavy neuts", fit("Maller", maller, projected=[PF(fit("Curse", curse))]))
case("in_neut_capital", "incoming", "battleship neuts on a dreadnought", fit("Revelation", [M("Capital Armor Repairer II", "low")], projected=[PM("Heavy Energy Neutralizer II", 4)]))
case("in_neut_stable_target", "incoming", "neut on a fit with no own cap use", fit("Rifter", [M("Damage Control II", "low")], projected=[PM("Small Energy Neutralizer II")]))
case("in_neut_mixed", "incoming", "neut module + drones + nos", fit("Megathron", megathron, projected=[
    PM("Heavy Energy Neutralizer II", 2), PD("Acolyte EV-300", 5), PM("Medium Energy Nosferatu II")]))

# ---------------------------------------------------------------- G. remote capacitor
guardian = [M("Large Remote Capacitor Transmitter II", "high"), M("Large Remote Capacitor Transmitter II", "high"),
            M("Large Remote Armor Repairer II", "high"), M("Large Remote Armor Repairer II", "high"),
            M("10MN Afterburner II", "mid"), M("Medium Armor Repairer II", "low")]
case("rc_in_one", "remote_cap", "one incoming large transmitter (fill)", fit("Maller", maller, projected=[PM("Large Remote Capacitor Transmitter II", 1, 5000)]))
case("rc_in_two", "remote_cap", "two incoming transmitters", fit("Apocalypse", apocalypse, projected=[PM("Large Remote Capacitor Transmitter II", 2, 5000)]))
case("rc_in_near_max", "remote_cap", "transmitter at 9 km (inside its 9.75 km unskilled range)", fit("Maller", maller, projected=[PM("Large Remote Capacitor Transmitter II", 1, 9000)]))
case("rc_in_out_of_range", "remote_cap", "transmitter beyond max range: no fill", fit("Maller", maller, projected=[PM("Large Remote Capacitor Transmitter II", 1, 60000)]))
case("rc_in_fit", "remote_cap", "projected logistics fit", fit("Maller", maller, projected=[PF(fit("Guardian", guardian))]))
case("rc_own_guardian", "remote_cap", "own transmitters drain the logistics ship", fit("Guardian", guardian))
case("rc_own_basilisk", "remote_cap", "shield logistics transmitting cap", fit("Basilisk", [
    M("Large Remote Capacitor Transmitter II", "high"), M("Large Remote Capacitor Transmitter II", "high"),
    M("Large Remote Shield Booster II", "high"), M("Large Remote Shield Booster II", "high"), M("10MN Afterburner II", "mid")]))
case("rc_fill_and_neut", "remote_cap", "incoming transmitter and neut together", fit("Maller", maller, projected=[
    PM("Large Remote Capacitor Transmitter II", 1, 5000), PM("Heavy Energy Neutralizer II")]))
case("rc_own_and_in", "remote_cap", "logistics receiving cap while transmitting", fit("Guardian", guardian, projected=[PM("Large Remote Capacitor Transmitter II", 2, 5000)]))

# ---------------------------------------------------------------- H. spool weapons
leshak = [*[M("Supratidal Entropic Disintegrator II", "high", charge="Baryon Exotic Plasma L") for _ in range(1)],
          M("Large Armor Repairer II", "low"), M("100MN Afterburner II", "mid"), M("Heavy Energy Neutralizer II", "high")]
case("spool_leshak", "spool", "supratidal disintegrator (cap per cycle, spool does not change cap)", fit("Leshak", leshak))
case("spool_leshak_spool0", "spool", "default_spool 0", fit("Leshak", leshak, options={"default_spool": {"type": "spool_scale", "amount": 0}}))
case("spool_leshak_reload", "spool", "factor_reload with disintegrator charges", fit("Leshak", leshak, options={"factor_reload": True}))
case("spool_vedmak", "spool", "heavy entropic disintegrator", fit("Vedmak", [M("Heavy Entropic Disintegrator II", "high", charge="Baryon Exotic Plasma L"),
                                                                            M("10MN Afterburner II", "mid"), M("Medium Armor Repairer II", "low")]))
case("spool_damavik", "spool", "light entropic disintegrator", fit("Damavik", [M("Light Entropic Disintegrator II", "high", charge="Baryon Exotic Plasma S"),
                                                                              M("1MN Afterburner II", "mid"), M("Small Armor Repairer II", "low")]))
case("spool_damavik_oh", "spool", "light disintegrator, all overheated", fit("Damavik", oh([M("Light Entropic Disintegrator II", "high", charge="Baryon Exotic Plasma S"),
                                                                                             M("1MN Afterburner II", "mid"), M("Small Armor Repairer II", "low")])))

# ---------------------------------------------------------------- I. reloads (options.factor_reload)
case("rl_maller_lasers", "reload", "crystals (no clip) + reps, factor_reload", fit("Maller", maller, options={"factor_reload": True}))
case("rl_thorax_blasters", "reload", "hybrid charges: clip + reload in the simulation", fit("Thorax", thorax, options={"factor_reload": True}))
case("rl_megathron", "reload", "large blasters with reload", fit("Megathron", megathron, options={"factor_reload": True}))
case("rl_aar", "reload", "ancillary armor repairer with paste, factor_reload", fit("Maller", maller + [M("Medium Ancillary Armor Repairer", "low", charge="Nanite Repair Paste")], options={"factor_reload": True}))
case("rl_aar_noreload", "reload", "ancillary armor repairer, no reload", fit("Maller", maller + [M("Medium Ancillary Armor Repairer", "low", charge="Nanite Repair Paste")]))
case("rl_thorax_oh", "reload", "reload + overheat", fit("Thorax", oh(thorax), options={"factor_reload": True}))
case("rl_apocalypse", "reload", "8 lasers, factor_reload", fit("Apocalypse", apocalypse, options={"factor_reload": True}))
case("rl_punisher_injector", "reload", "frigate booster + factor_reload", fit("Punisher", punisher + [M("Small Capacitor Booster II", "mid", charge="Navy Cap Booster 150")], options={"factor_reload": True}))

# ---------------------------------------------------------------- J. staggering / grouping
case("stg_four_reps", "stagger", "four identical repairers (staggered: duration / 4)", fit("Armageddon", [
    *[M("Large Armor Repairer II", "low") for _ in range(4)], M("100MN Afterburner II", "mid")]))
case("stg_three_neuts", "stagger", "three identical heavy neuts", fit("Armageddon", [
    *[M("Heavy Energy Neutralizer II", "high") for _ in range(3)], M("Large Armor Repairer II", "low")]))
case("stg_turrets", "stagger", "eight identical turrets (never staggered, cap need x8)", fit("Apocalypse", [
    *[M("Mega Pulse Laser II", "high", charge="Multifrequency L") for _ in range(8)]]))
case("stg_reps_reload", "stagger", "identical ancillary repairers with clip + reload (staggered by clip)", fit("Maller", [
    M("Medium Ancillary Armor Repairer", "low", charge="Nanite Repair Paste"), M("Medium Ancillary Armor Repairer", "low", charge="Nanite Repair Paste"),
    M("10MN Afterburner II", "mid")], options={"factor_reload": True}))
case("stg_neuts_oh_mix", "stagger", "two neuts overheated, one not (different groups)", fit("Armageddon", oh([
    *[M("Heavy Energy Neutralizer II", "high") for _ in range(3)], M("Large Armor Repairer II", "low")], {0, 1})))
case("stg_boosters", "stagger", "two shield boosters", fit("Rokh", [M("Large Shield Booster II", "mid"), M("Large Shield Booster II", "mid"),
                                                                   M("Multispectrum Shield Hardener II", "mid"), M("100MN Afterburner II", "mid")]))

# ---------------------------------------------------------------- K. lighter fits (mostly stable: the stable_percent path)
light_rifter = [M("1MN Afterburner II", "mid"), M("Warp Scrambler II", "mid"), M("Stasis Webifier II", "mid"), M("Small Armor Repairer II", "low")]
case("st_rifter_light", "light", "frigate AB, scram, web, rep", fit("Rifter", light_rifter))
case("st_thorax_ab_rep", "light", "AB + rep only", fit("Thorax", [M("10MN Afterburner II", "mid"), M("Medium Armor Repairer II", "low")]))
case("st_raven_hardeners", "light", "two active hardeners", fit("Raven", [M("Multispectrum Shield Hardener II", "mid"), M("Multispectrum Shield Hardener II", "mid")]))
case("st_megathron_rep_ccc", "light", "rep + CCC rigs", fit("Megathron", [M("Large Armor Repairer II", "low")] + [M("Large Capacitor Control Circuit I", "rig", "online") for _ in range(3)]))
case("st_abaddon_four_lasers", "light", "four lasers + batteries", fit("Abaddon", [*[M("Mega Pulse Laser II", "high", charge="Multifrequency L") for _ in range(4)],
                                                                               M("Large Cap Battery II", "mid", "online"), M("Large Cap Battery II", "mid", "online")]))
case("st_harbinger_lasers", "light", "battlecruiser lasers only", fit("Harbinger", [*[M("Heavy Pulse Laser II", "high", charge="Multifrequency M") for _ in range(7)]]))
case("st_omen_rechargers", "light", "lasers with cap rechargers", fit("Omen", [*[M("Heavy Pulse Laser II", "high", charge="Multifrequency M") for _ in range(4)],
                                                                             M("Cap Recharger II", "mid", "online"), M("Cap Recharger II", "mid", "online")]))
case("st_myrmidon_rep_rech", "light", "dual rep with cap rechargers", fit("Myrmidon", [M("Medium Armor Repairer II", "low"), M("Medium Armor Repairer II", "low"),
                                                                                      M("Cap Recharger II", "mid", "online"), M("Cap Recharger II", "mid", "online"), M("Cap Recharger II", "mid", "online")]))
case("st_rokh_booster_rech", "light", "shield booster + rechargers + relays", fit("Rokh", [M("Large Shield Booster II", "mid"), M("Cap Recharger II", "mid", "online"),
                                                                                           M("Cap Recharger II", "mid", "online"), M("Capacitor Power Relay II", "low", "online")]))
case("st_rifter_small_neut_in", "light", "light fit under one small neut", fit("Rifter", light_rifter, projected=[PM("Small Energy Neutralizer II")]))
case("st_maller_rct_in", "light", "cruiser kept stable by two incoming transmitters", fit("Maller", maller, projected=[PM("Large Remote Capacitor Transmitter II", 2, 5000)]))
case("st_thorax_nos_in", "light", "AB + rep under an enemy nosferatu", fit("Thorax", [M("10MN Afterburner II", "mid"), M("Medium Armor Repairer II", "low")], projected=[PM("Medium Energy Nosferatu II")]))
case("st_thorax_ab_rep_oh", "light", "AB + rep overheated", fit("Thorax", oh([M("10MN Afterburner II", "mid"), M("Medium Armor Repairer II", "low")])))
case("st_raven_hardeners_oh", "light", "hardeners overheated", fit("Raven", oh([M("Multispectrum Shield Hardener II", "mid"), M("Multispectrum Shield Hardener II", "mid")])))

# ---------------------------------------------------------------- L. options.cap_sim (simulation options; oracle runs Pyfa's CapSimulator with them)
four_reps = [*[M("Large Armor Repairer II", "low") for _ in range(4)], M("100MN Afterburner II", "mid")]
three_neuts = [*[M("Heavy Energy Neutralizer II", "high") for _ in range(3)], M("Large Armor Repairer II", "low")]
aar2 = [M("Medium Ancillary Armor Repairer", "low", charge="Nanite Repair Paste"), M("Medium Ancillary Armor Repairer", "low", charge="Nanite Repair Paste"),
        M("10MN Afterburner II", "mid")]
case("so_stagger_off_reps", "sim_options", "cap_sim.stagger false: identical repairers fire together", fit("Armageddon", four_reps, options={"cap_sim": {"stagger": False}}))
case("so_stagger_on_reps", "sim_options", "cap_sim.stagger true (explicit; same as default)", fit("Armageddon", four_reps, options={"cap_sim": {"stagger": True}}))
case("so_stagger_off_neuts", "sim_options", "stagger false, three neuts", fit("Armageddon", three_neuts, options={"cap_sim": {"stagger": False}}))
case("so_stagger_off_maller", "sim_options", "stagger false, dual rep cruiser", fit("Maller", maller, options={"cap_sim": {"stagger": False}}))
case("so_stagger_off_light", "sim_options", "stagger false on a stable fit (stable % changes)", fit("Myrmidon", [M("Medium Armor Repairer II", "low"), M("Medium Armor Repairer II", "low"),
     M("Cap Recharger II", "mid", "online"), M("Cap Recharger II", "mid", "online"), M("Cap Recharger II", "mid", "online"), M("Cap Recharger II", "mid", "online")],
     options={"cap_sim": {"stagger": False}}))
case("so_stagger_off_injectors", "sim_options", "stagger false with two cap boosters", fit("Apocalypse", apocalypse + [
    M("Heavy Capacitor Booster II", "mid", charge="Navy Cap Booster 800"), M("Heavy Capacitor Booster II", "mid", charge="Navy Cap Booster 800")], options={"cap_sim": {"stagger": False}}))
case("so_reload_thorax", "sim_options", "cap_sim.reload true without factor_reload (reload only in the simulation)", fit("Thorax", thorax, options={"cap_sim": {"reload": True}}))
case("so_reload_aar", "sim_options", "cap_sim.reload, ancillary repairers (staggered by clip)", fit("Maller", aar2, options={"cap_sim": {"reload": True}}))
case("so_reload_stagger_off_aar", "sim_options", "reload on, stagger off", fit("Maller", aar2, options={"cap_sim": {"reload": True, "stagger": False}}))
case("so_maxtime_60_unstable", "sim_options", "cap_sim.max_time_s 60 on a fit that empties later (stable within the window)", fit("Megathron", megathron, options={"cap_sim": {"max_time_s": 60}}))
case("so_maxtime_30_drake", "sim_options", "max_time_s 30, drake", fit("Drake", drake, options={"cap_sim": {"max_time_s": 30}}))
case("so_maxtime_long", "sim_options", "max_time_s 3600 on a fit that empties at 88 s (no effect)", fit("Drake", drake, options={"cap_sim": {"max_time_s": 3600}}))
case("so_maxtime_600_slow", "sim_options", "max_time_s 600 vs a 4300 s depletion", fit("Megathron", [M("Large Armor Repairer II", "low")] + [M("Large Capacitor Control Circuit I", "rig", "online") for _ in range(3)],
     options={"cap_sim": {"max_time_s": 600}}))
case("so_maxtime_stable_fit", "sim_options", "max_time_s 120 on a stable fit", fit("Raven", [M("Multispectrum Shield Hardener II", "mid"), M("Multispectrum Shield Hardener II", "mid")],
     options={"cap_sim": {"max_time_s": 120}}))
case("so_all_options_incoming", "sim_options", "stagger off + reload + max time, with incoming neut drones", fit("Thorax", thorax, projected=[PD("Acolyte EV-300", 3)],
     options={"cap_sim": {"stagger": False, "reload": True, "max_time_s": 1800}}))
case("so_factor_reload_stagger_off", "sim_options", "factor_reload with stagger off", fit("Maller", aar2, options={"factor_reload": True, "cap_sim": {"stagger": False}}))

# ---------------------------------------------------------------- M. edge cases
case("edge_mjd", "edge", "micro jump drive (long cycle, big cap need)", fit("Megathron", megathron + [M("Large Micro Jump Drive", "mid")]))
case("edge_mjd_alone", "edge", "only a micro jump drive", fit("Megathron", [M("Large Micro Jump Drive", "mid")]))
case("edge_dominix_drones", "edge", "drones never use cap", fit("Dominix", [M("Large Armor Repairer II", "low")], drones=[D("Praetor EV-900", 5)]))
case("edge_tiny_drain", "edge", "a very small drain on a big capacitor (long stable run)", fit("Revelation", [M("Sensor Booster II", "mid")]))

# ---------------------------------------------------------------- N. hard simulator paths
def skl(req, **levels):
    """set individual skill levels by skill name"""
    req["character"]["skills"]["levels"] = {str(tid(k.replace("_", " "))): v for k, v in levels.items()}
    return req


FR = {"factor_reload": True}
aar3 = [M("Medium Ancillary Armor Repairer", "low", charge="Nanite Repair Paste") for _ in range(3)]
case("hard_aar3_clip_offsets", "hard", "three identical ancillary repairers + reload: fractional staggered start times",
     fit("Maller", aar3 + [M("10MN Afterburner II", "mid")], options=FR))
case("hard_lcm_period", "hard", "cycle times 5 s / 7.5 s / 12 s / 15 s / 24 s: long period before the repeat check",
     fit("Armageddon", [M("Heavy Energy Neutralizer II", "high"), M("Large Armor Repairer II", "low"), M("100MN Afterburner II", "mid"),
                        M("Sensor Booster II", "mid"), M("Large Micro Jump Drive", "mid")]))
case("hard_injector_topup_mjd", "hard", "booster waits (overshoot) and fires before the MJD's big need",
     fit("Megathron", [M("Large Micro Jump Drive", "mid"), M("Heavy Capacitor Booster II", "mid", charge="Navy Cap Booster 800"),
                       M("Large Armor Repairer II", "low")]))
case("hard_injector_two_sizes_topup", "hard", "two waiting boosters of different sizes: smallest sufficient fires first",
     fit("Apocalypse", apocalypse + [M("Large Micro Jump Drive", "mid"), M("Heavy Capacitor Booster II", "mid", charge="Navy Cap Booster 800"),
                                     M("Medium Capacitor Booster II", "mid", charge="Navy Cap Booster 400")]))
case("hard_void_bomb_bs", "hard", "void bomb on a battleship (survives the first hit)",
     fit("Apocalypse", apocalypse, projected=[PM("Bomb Launcher I", 1, 10000, charge="Void Bomb")]))
case("hard_three_void_bombs", "hard", "three identical incoming void bombs (grouped and staggered like local modules)",
     fit("Apocalypse", apocalypse, projected=[PM("Bomb Launcher I", 3, 10000, charge="Void Bomb")]))
case("hard_incoming_mixed_cycles", "hard", "incoming heavy neut + medium neut + neut drones (different durations)",
     fit("Megathron", megathron, projected=[PM("Heavy Energy Neutralizer II", 1, 10000), PM("Medium Energy Neutralizer II", 2, 5000),
                                            PD("Infiltrator EV-600", 2)]))
case("hard_command_burst", "hard", "command bursts with charges (cap need per cycle, clip + reload)",
     fit("Claymore", [M("Shield Command Burst II", "high", charge="Shield Harmonizing Charge"),
                      M("Skirmish Command Burst II", "high", charge="Rapid Deployment Charge"),
                      M("Large Shield Booster II", "mid"), M("50MN Microwarpdrive II", "mid")], options=FR))
case("hard_smartbombs", "hard", "four identical smartbombs (not turrets: staggered)",
     fit("Armageddon", [M("Large EMP Smartbomb II", "high") for _ in range(4)] + [M("100MN Afterburner II", "mid")]))
case("hard_smartbombs_oh", "hard", "four overheated smartbombs", fit("Armageddon", oh([M("Large EMP Smartbomb II", "high") for _ in range(4)])))
case("hard_skill_levels", "hard", "capacitor skills at mixed levels (capacity, recharge, module cap need)",
     skl(fit("Maller", maller), Capacitor_Management=2, Capacitor_Systems_Operation=1, Energy_Grid_Upgrades=0, Repair_Systems=3))
case("hard_nos_neut_incoming_vs_own_nos", "hard", "own nos gain while neutralized by heavy neuts",
     fit("Ashimmu", [M("Medium Energy Nosferatu II", "high"), M("Medium Energy Nosferatu II", "high"), M("Medium Armor Repairer II", "low"),
                     M("10MN Afterburner II", "mid")], projected=[PM("Heavy Energy Neutralizer II", 2, 10000)]))
case("hard_rct_fill_injector_waits", "hard", "incoming cap transfer keeps the capacitor full: booster stays postponed",
     fit("Maller", maller + [M("Medium Capacitor Booster II", "mid", charge="Navy Cap Booster 400")],
         projected=[PM("Large Remote Capacitor Transmitter II", 2, 5000)]))
case("hard_turrets_plus_neuts_oh", "hard", "overheated turrets (x n need) and overheated neuts (staggered) together",
     fit("Armageddon", oh([*[M("Mega Pulse Laser II", "high", charge="Multifrequency L") for _ in range(4)],
                           *[M("Heavy Energy Neutralizer II", "high") for _ in range(3)], M("Large Armor Repairer II", "low")])))

out = ROOT / "cases"
out.mkdir(exist_ok=True)
for p in out.glob("*.json"):
    p.unlink()
index = []
seen = set()
for name, cat, desc, req in CASES:
    assert name not in seen, name
    seen.add(name)
    (out / f"{name}.json").write_text(json.dumps(req, indent=1, sort_keys=True) + "\n")
    index.append({"case": name, "category": cat, "description": desc})
(ROOT / "index.json").write_text(json.dumps(index, indent=1) + "\n")
print(len(CASES), "cases;", {c: sum(1 for x in CASES if x[1] == c) for c in dict.fromkeys(x[1] for x in CASES)})
