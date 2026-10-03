"""optimizer-bench shared code: dataset lookups, fit building, engine evaluation, constraints, objective, price.
Used by tools/make_cases.py (exhaustive reference), score.py (scorer) and baselines/*. No Pyfa code."""
import gzip, json, math, os, subprocess
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATASET = os.environ.get("EVE_DOGMA_DATASET", "/workspace/exct-eve/data/dataset-3569502.json.gz")
# Reference evaluator: an engine validated against Pyfa (F variant-f-features 4b8f5f9 passes bench 1.9.0, cap, mutated,
# formats, graphs and pending-1.10; see results/F-coverage on main). Override with EVE_OPT_ENGINE="<cmd>" (must accept
# `batch` JSONL on stdin like the bench contract).
ENGINE = os.environ.get("EVE_OPT_ENGINE", "/workspace/exct-eve/fvj-work/bin/F-4b8f5f9")
REL_TIE = 1e-6          # two objective values are equal if |a-b| <= REL_TIE * max(1, |b|)
CAP_UNSTABLE_OFFSET = 1e9
TURRET_EFFECT, LAUNCHER_EFFECT = 42, 40
RACKS = ("high", "mid", "low", "rig")


@lru_cache(maxsize=1)
def dataset():
    return json.load(gzip.open(DATASET))


@lru_cache(maxsize=1)
def attr_ids():
    return {v["name"]: k for k, v in dataset()["attributes"].items()}


@lru_cache(maxsize=1)
def by_name():
    return {t["name"]: int(k) for k, t in dataset()["types"].items() if t.get("published")}


def tinfo(tid):
    return dataset()["types"][str(tid)]


def tattr(tid, name, default=None):
    return tinfo(tid)["attrs"].get(attr_ids()[name], default)


def meta_level(tid):
    return tinfo(tid).get("meta_level") or 0


def is_turret(tid):
    return any(e == TURRET_EFFECT for e, _ in tinfo(tid)["effects"])


def is_launcher(tid):
    return any(e == LAUNCHER_EFFECT for e, _ in tinfo(tid)["effects"])


@lru_cache(maxsize=1)
def prices():
    return {int(k): v["isk"] for k, v in json.loads((ROOT / "prices.json").read_text())["prices"].items()}


def item_key(m):
    return (m["type_id"], m.get("charge_type_id"))


def build_fit(case, chosen):
    """chosen: {rack: [pool items]} -> FitRequest. Keep modules from base first, then racks in RACKS order."""
    base = case["request"]["base"]
    fit = json.loads(json.dumps(base))
    mods = list(fit.get("modules", []))
    for rack in RACKS:
        for it in chosen.get(rack, []):
            mods.append({"type_id": it["type_id"], "slot": rack, "state": it["state"],
                         "charge_type_id": it.get("charge_type_id")})
    fit["modules"] = mods
    return fit


def evaluate(fits, engine=None):
    """Run the engine `batch` on a list of FitRequests; returns list of outputs (dict or {'error':...})."""
    if not fits:
        return []
    cmd = (engine or ENGINE).split() + ["batch", "--dataset", DATASET]
    out = []
    for i in range(0, len(fits), 20000):
        chunk = fits[i:i + 20000]
        r = subprocess.run(cmd, input="".join(json.dumps(f) + "\n" for f in chunk), capture_output=True, text=True)
        lines = r.stdout.splitlines()
        if len(lines) != len(chunk):
            raise RuntimeError(f"engine returned {len(lines)} lines for {len(chunk)} fits: {r.stderr[-500:]}")
        out += [json.loads(l) for l in lines]
    return out


def fit_price(fit):
    p, missing = 0.0, []
    ids = [fit["ship"]["type_id"]]
    for m in fit.get("modules", []):
        ids.append(m["type_id"])
        if m.get("charge_type_id"):
            ids.append(m["charge_type_id"])
    for d in fit.get("drones", []):
        ids += [d["type_id"]] * int(d.get("quantity", 1))
    for t in ids:
        if t in prices():
            p += prices()[t]
        else:
            missing.append(t)
    return p, missing


def metric(name, out, fit):
    if name == "dps":
        return out["offense"]["total"]["dps"]["total"]
    if name == "ehp":
        return out["defense"]["ehp"]["total"]
    if name == "tank":
        return max(out["defense"]["tank"]["sustained_effective"].values())
    if name == "speed":
        return out["navigation"]["max_velocity"]
    if name == "cap_stable":
        c = out["capacitor"]
        return c["stable_percent"] if c["stable"] else c["depletes_in_s"] - CAP_UNSTABLE_OFFSET
    if name == "price":
        return fit_price(fit)[0]
    raise KeyError(name)


def objective_value(case, out, fit):
    return metric(case["request"]["objective"]["metric"], out, fit)


def precheck(case, chosen):
    """Engine-free checks on a candidate (pool rules already hold): hardpoints, maxTypeFitted, meta, price.
    Returns list of violation codes."""
    v = []
    ship = case["request"]["base"]["ship"]["type_id"]
    allm = [(m["type_id"], m.get("charge_type_id")) for m in case["request"]["base"].get("modules", [])]
    allm += [(it["type_id"], it.get("charge_type_id")) for r in chosen.values() for it in r]
    if sum(is_turret(t) for t, _ in allm) > (tattr(ship, "turretSlotsLeft", 0) or 0):
        v.append("HARDPOINTS_EXCEEDED(turret)")
    if sum(is_launcher(t) for t, _ in allm) > (tattr(ship, "launcherSlotsLeft", 0) or 0):
        v.append("HARDPOINTS_EXCEEDED(launcher)")
    cnt = {}
    for t, _ in allm:
        cnt[t] = cnt.get(t, 0) + 1
    for t, n in cnt.items():
        mt = tattr(t, "maxTypeFitted")
        if mt and n > mt:
            v.append(f"MAX_TYPE_FITTED({t})")
    cons = case["request"]["constraints"]
    mx = (cons.get("meta") or {}).get("max_meta_level")
    if mx is not None:
        for t, c in allm:
            if meta_level(t) > mx or (c and meta_level(c) > mx):
                v.append("META_LEVEL")
                break
    pr = cons.get("price")
    if pr and pr.get("max_isk") is not None:
        p, miss = fit_price(build_fit(case, chosen))
        if miss:
            v.append("OPT_MISSING_PRICE")
        elif p > pr["max_isk"]:
            v.append("PRICE_CEILING")
    return v


def postcheck(case, out, fit):
    """Checks needing the engine output: engine validation (violations[]), floors, cap_stable."""
    if "error" in out:
        return ["ENGINE_ERROR:" + str(out["error"].get("code"))]
    v = sorted({x["code"] for x in out.get("violations", [])})
    cons = case["request"]["constraints"]
    for k, lo in (cons.get("min") or {}).items():
        if metric(k, out, fit) < lo:
            v.append(f"MIN({k})")
    cs = cons.get("cap_stable")
    if cs is True and not out["capacitor"]["stable"]:
        v.append("CAP_UNSTABLE")
    elif isinstance(cs, dict) and not (out["capacitor"]["stable"] and out["capacitor"]["stable_percent"] >= cs["min_percent"]):
        v.append("CAP_BELOW_MIN")
    return v


def better(a, b, direction):
    """a strictly better than b beyond tie tolerance."""
    tol = REL_TIE * max(1.0, abs(b))
    return a > b + tol if direction == "max" else a < b - tol


def equal(a, b):
    return abs(a - b) <= REL_TIE * max(1.0, abs(b))


def gap(got, opt, direction):
    d = (opt - got) if direction == "max" else (got - opt)
    return max(0.0, d) / max(abs(opt), 1e-12)
