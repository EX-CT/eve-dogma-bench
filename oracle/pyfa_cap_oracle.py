#!/usr/bin/env python3
"""Capacitor-suite oracle: Pyfa (eos) as a black box on EXCT FitRequests, capacitor figures only.
Builds fits with pyfa_oracle.build() and reports Pyfa's capacitor results plus the simulator inputs and details
(drain list, iterations, EVE stability estimate) for diagnosis. Imports Pyfa, so like pyfa_oracle.py it is
GPL-3.0-or-later (see ./LICENSE-GPL-NOTE); a test tool, never linked into an engine.

usage: PYFA=/path/to/Pyfa PYTHONPATH=<wx stub dir> python pyfa_cap_oracle.py case.json [...]  > out.jsonl"""
import json, math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pyfa_oracle as po  # noqa: E402  (sets up Pyfa / eos)


def run_sim(fit, drains, stagger, reload, t_max_ms):
    """Pyfa's CapSimulator on the fit's drain list with explicit options (Fit.simulateCap always uses stagger on,
    reload = factorReload, 6 h); maps the result the way Fit.simulateCap does"""
    from eos import capSim
    sim = capSim.CapSimulator()
    sim.init(drains)
    sim.capacitorCapacity = fit.ship.getModifiedItemAttr("capacitorCapacity")
    sim.capacitorRecharge = fit.ship.getModifiedItemAttr("rechargeRate")
    sim.startingCapacity = sim.capacitorCapacity
    sim.stagger, sim.scale, sim.t_max, sim.reload = stagger, False, t_max_ms, reload
    sim.run()
    frac = (sim.cap_stable_low + sim.cap_stable_high) / (2 * sim.capacitorCapacity)
    stable = frac > 0
    return sim, stable, (min(100, frac * 100) if stable else sim.t / 1000.0)


def cap(fit, opts=None):
    g = fit.ship.getModifiedItemAttr
    capacity, rr_ms = g("capacitorCapacity"), g("rechargeRate")
    peak = fit.calculateCapRecharge()
    stable, state = fit.capStable, fit.capState   # runs Pyfa's simulateCap (stagger on, 6 h, reload = factorReload)
    used, recharge = fit.capUsed, fit.capRecharge  # capRecharge = peak + cap added (boosters, own nos, incoming fills)
    drains = fit._Fit__generateDrain()[0]
    cs = (opts or {}).get("cap_sim") or {}
    if cs and drains:
        # request options.cap_sim (CONTRACT-CAP 0.1): stagger default true, reload = cap_sim.reload or factor_reload
        sim, stable, state = run_sim(fit, drains, bool(cs.get("stagger", True)), bool(cs.get("reload")) or fit.factorReload,
                                     (cs.get("max_time_s") or 6 * 3600) * 1000)
    else:
        sim = fit._Fit__runCapSim(drains=drains)  # same run again, to read the simulator's details
    out = {
        "capacity": capacity, "recharge_time_s": rr_ms / 1000, "peak_recharge_gj_s": peak,
        "use_gj_s": used, "injected_gj_s": recharge - peak, "delta_gj_s": recharge - used,
        "stable": bool(stable),
        "stable_percent": state if stable else None, "depletes_in_s": None if stable else state,
        "drains": [list(d) for d in drains],
    }
    if sim is not None:
        out.update({"sim_iterations": sim.iterations, "sim_end_ms": sim.t,
                    "eve_stable_percent": sim.cap_stable_eve * 100 if sim.cap_stable_eve else 0.0,
                    "optimized_repeat": bool(sim.result_optimized_repeats),
                    "low_gj": sim.cap_stable_low, "high_gj": sim.cap_stable_high})
    return out


def main():
    for path in sys.argv[1:]:
        req = json.load(open(path))
        name = os.path.basename(path)
        try:
            fit = po.build(req)
            fit.calculateModifiedAttributes()
            res = cap(fit, req.get("options"))
        except Exception as e:
            try:
                po.eos.db.saveddata_session.rollback()
            except Exception:
                pass
            print(json.dumps({"file": name, "error": repr(e)}))
            continue
        print(json.dumps({"file": name, "cap": res}, default=str))


if __name__ == "__main__":
    main()
