#!/usr/bin/env python3
"""Generate optimizer-bench cases by exhaustive search.

For every spec in specs.py:
  1. resolve pools; enumerate every multiset of each rack (size 0..slots, pool items may repeat) -> full space;
  2. drop candidates that fail engine-free rules (hardpoints, maxTypeFitted) without evaluating them;
  3. evaluate the rest with the reference engine (lib.ENGINE, `batch`); engine-valid = no violations[];
  4. resolve quantile thresholds ("q60") over engine-valid fits and write them into the case as numbers;
  5. apply all constraints (meta, price, floors, cap_stable) and find the optimum and every tied fit;
  6. write cases/<id>.json (OptimizeRequest + explicit pools) and expected/<id>.json.
Pyfa cross-check of the winners: tools/pyfa_check.py (separate step; needs the Pyfa checkout).
usage: python3 optimizer/tools/make_cases.py [id ...]"""
import itertools, json, math, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lib, specs  # noqa: E402

MAX_SPACE = 120_000
OUT_C, OUT_E = lib.ROOT / "cases", lib.ROOT / "expected"


CATEGORIES = {
    "cpu": lambda c: c == "CPU_OVERLOAD",
    "powergrid": lambda c: c == "POWER_OVERLOAD",
    "calibration": lambda c: c == "CALIBRATION_OVERLOAD",
    "slots_hardpoints": lambda c: c.startswith(("SLOTS_EXCEEDED", "HARDPOINTS", "TURRET_HARDPOINTS", "LAUNCHER_HARDPOINTS",
                                                "MAX_TYPE_FITTED", "MAX_GROUP")),
    "skills": lambda c: c == "MISSING_SKILL",
    "meta": lambda c: c == "META_LEVEL",
    "price": lambda c: c in ("PRICE_CEILING", "OPT_MISSING_PRICE"),
    "min_floor": lambda c: c.startswith("MIN("),
    "cap_stable": lambda c: c.startswith("CAP_"),
}


def active_or_online(tid, rack):
    if rack == "rig":
        return "online"
    cats = {lib.dataset()["effects"][str(e)]["category"] for e, _ in lib.tinfo(tid)["effects"] if str(e) in lib.dataset()["effects"]}
    return "active" if cats & {1, 2} else "online"


def pool_item(s, rack):
    mod, _, ch = s.partition("|")
    tid = lib.by_name()[mod]
    return {"name": s, "type_id": tid, "charge_type_id": lib.by_name()[ch] if ch else None, "state": active_or_online(tid, rack)}


def skills_obj(sk):
    lv = {str(lib.by_name()[n]): v for n, v in (sk.get("levels") or {}).items()}
    return {"default_level": sk.get("default_level", 0), "levels": lv}


def quantile(vals, q):
    v = sorted(vals)
    return v[min(len(v) - 1, int(math.floor(q / 100 * (len(v) - 1))))]


def fit_signature(chosen):
    return {r: sorted([it["name"] for it in items]) for r, items in chosen.items() if items}


def make(spec):
    t0 = time.time()
    ship = lib.by_name()[spec["ship"]]
    base_mods = []
    for k in spec.get("keep", []):
        name, slot = k[0], k[1]
        ch = k[2] if len(k) > 2 else None
        tid = lib.by_name()[name]
        base_mods.append({"type_id": tid, "slot": slot, "state": active_or_online(tid, slot),
                          "charge_type_id": lib.by_name()[ch] if ch else None})
    racks = {}
    for rack, (n, pool) in spec["racks"].items():
        cap = int(lib.tattr(ship, {"high": "hiSlots", "mid": "medSlots", "low": "lowSlots", "rig": "rigSlots"}[rack]) or 0)
        used = sum(1 for m in base_mods if m["slot"] == rack)
        assert n + used <= cap, (spec["id"], rack, n, used, cap)
        racks[rack] = {"slots": n, "pool": [pool_item(s, rack) for s in pool]}
    prices = {str(t): v["isk"] for t, v in json.loads((lib.ROOT / "prices.json").read_text())["prices"].items()}
    case = {
        "id": spec["id"], "description": spec.get("note", ""), "bench": "optimizer-bench 0.1",
        "request": {
            "base": {"ship": {"type_id": ship}, "character": {"skills": skills_obj(spec["skills"])},
                     "modules": base_mods, "damage_pattern": None},
            "objective": {"metric": spec["objective"], "direction": "min" if spec["objective"] == "price" else "max"},
            "constraints": {"skills": "character"},
            "search": {"slots": list(racks), "charges": False, "drones": False,
                       "keep": list(range(len(base_mods))), "candidates": "explicit", "pools": racks},
            "limits": {"max_evaluations": 2000, "time_ms": 5000, "results": 1, "seed": 0},
        },
    }
    cons = case["request"]["constraints"]
    if spec.get("meta") is not None:
        cons["meta"] = {"max_meta_level": spec["meta"]}
    if spec.get("cap_stable"):
        cons["cap_stable"] = True
    # enumerate
    per_rack = []
    for rack, r in racks.items():
        opts = r["pool"] + [None]
        combos = [tuple(opts[i] for i in c if opts[i] is not None) for c in itertools.combinations_with_replacement(range(len(opts)), r["slots"])]
        per_rack.append((rack, combos))
    size = math.prod(len(c) for _, c in per_rack)
    assert size <= MAX_SPACE, (spec["id"], size)
    cands, struct = [], []
    nocons = json.loads(json.dumps(case)); nocons["request"]["constraints"] = {}   # structural rules only
    for prod in itertools.product(*[c for _, c in per_rack]):
        chosen = {rack: list(items) for (rack, _), items in zip(per_rack, prod)}
        cands.append(chosen)
        struct.append(lib.precheck(nocons, chosen))
    pruned = sum(1 for x in struct if x)
    fits = [lib.build_fit(case, c) for c in cands]
    outs = lib.evaluate(fits)          # everything is evaluated so constraint bindingness can be measured
    allc = [(c, f, o, sv + (sorted({v["code"] for v in o.get("violations", [])}) if "error" not in o else ["ENGINE_ERROR"]))
            for c, f, o, sv in zip(cands, fits, outs, struct)]
    valid = [(c, f, o) for c, f, o, codes in allc if not codes]
    reasons = {}
    for *_, codes in allc:
        for code in set(codes):
            reasons[code] = reasons.get(code, 0) + 1
    # quantile thresholds
    if isinstance(spec.get("price"), str):
        q = float(spec["price"][1:])
        cons["price"] = {"max_isk": quantile([lib.fit_price(f)[0] for _, f, _ in valid], q)}
    if spec.get("price") is not None and not isinstance(spec.get("price"), str):
        cons["price"] = {"max_isk": spec["price"]}
    if "price" in cons or spec["objective"] == "price":
        used = {str(m["type_id"]) for _, f, _ in valid for m in f["modules"]} | {str(ship)}
        used |= {str(m["charge_type_id"]) for _, f, _ in valid for m in f["modules"] if m.get("charge_type_id")}
        cons.setdefault("price", {})["prices"] = {k: prices[k] for k in sorted(used, key=int)}
    if spec.get("min"):
        cons["min"] = {}
        for k, v in spec["min"].items():
            cons["min"][k] = quantile([lib.metric(k, o, f) for _, f, o in valid], float(v[1:])) if isinstance(v, str) else v
    # full constraints and optimum
    direction = case["request"]["objective"]["direction"]
    feas, scored = [], []
    for c, f, o, codes in allc:
        if "ENGINE_ERROR" in codes:
            continue
        codes = codes + [x for x in lib.precheck(case, c) if x not in codes] \
            + [x for x in lib.postcheck(case, o, f) if x not in codes]
        val = lib.objective_value(case, o, f)
        scored.append((val, codes))
        if not codes:
            feas.append((val, c, f, o))
    assert feas, spec["id"]
    best = feas[0][0]
    for v, *_ in feas:
        if lib.better(v, best, direction):
            best = v
    ties = [x for x in feas if lib.equal(x[0], best)]
    others = sorted({round(x[0], 6) for x in feas if not lib.equal(x[0], best)}, reverse=(direction == "max"))
    runners, seen = [], set()
    for v, c, f, o in sorted((x for x in feas if not lib.equal(x[0], best)), key=lambda x: x[0], reverse=(direction == "max")):
        if round(v, 6) in seen:
            continue
        seen.add(round(v, 6))
        runners.append({"value": v, "racks": fit_signature(c), "modules": f["modules"]})
        if len(runners) == 5:
            break
    binding = {}
    for cat, pred in CATEGORIES.items():
        rejected = [v for v, codes in scored if codes and any(pred(x) for x in codes)]
        relaxed = [v for v, codes in scored if codes and all(pred(x) for x in codes)]
        if not rejected:
            continue
        rb = None
        for v in relaxed:
            if rb is None or lib.better(v, rb, direction):
                rb = v
        binding[cat] = {"rejected": len(rejected), "best_if_relaxed": rb,
                        "binding": rb is not None and lib.better(rb, best, direction)}
    vals = [v for v, _ in scored]
    unconstrained = max(vals) if direction == "max" else min(vals)
    exp = {
        "id": spec["id"], "objective": case["request"]["objective"], "optimum": best,
        "optimal_fits": [{"racks": fit_signature(c), "modules": f["modules"], "metrics": {
            m: lib.metric(m, o, f) for m in ("dps", "ehp", "tank", "speed", "cap_stable", "price")}} for _, c, f, o in ties[:50]],
        "ties": len(ties), "second_best": others[0] if others else None, "runners_up": runners,
        "best_ignoring_all_rules": unconstrained, "constraints_effect": binding,
        "space": {"size": size, "pruned_structural": pruned, "engine_evaluated": len(fits), "engine_valid": len(valid),
                  "feasible": len(feas), "engine_violations": reasons},
        "reference": {"engine": lib.ENGINE.split("/")[-1], "engine_note": "F variant-f-features 4b8f5f9 (EX-CT/eve-dogma-lab)",
                      "dataset": Path(lib.DATASET).name, "tie_tolerance_rel": lib.REL_TIE,
                      "generated_s": round(time.time() - t0, 1)},
    }
    case["request"]["limits"]["max_evaluations"] = max(500, min(20000, size // 10))
    OUT_C.mkdir(exist_ok=True); OUT_E.mkdir(exist_ok=True)
    (OUT_C / f"{spec['id']}.json").write_text(json.dumps(case, indent=1, sort_keys=True) + "\n")
    (OUT_E / f"{spec['id']}.json").write_text(json.dumps(exp, indent=1, sort_keys=True) + "\n")
    print(f"{spec['id']}: size {size} evaluated {len(fits)} valid {len(valid)} feasible {len(feas)} "
          f"opt {best:.6g} ties {len(ties)} 2nd {exp['second_best']} unconstrained {unconstrained} ({time.time()-t0:.1f}s)", flush=True)


if __name__ == "__main__":
    want = set(sys.argv[1:])
    for s in specs.SPECS:
        if not want or s["id"] in want:
            make(s)
