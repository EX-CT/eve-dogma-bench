#!/usr/bin/env python3
"""Cross-check the reference optima with the Pyfa oracle (oracle/pyfa_oracle.py, unchanged, ORACLE_EXTRA=validity).
For every expected/<id>.json: the optimal fits (up to 10 ties) and the 5 best runner-up values are run through Pyfa.
Checks (written to expected/<id>.json under "pyfa_check"):
  agree   - Pyfa objective value within 0.5% (relative) of the reference engine value for every checked fit
  rank    - min Pyfa value over the winners >= max Pyfa value over the runners-up (direction-aware, 1e-6 slack)
  legal   - Pyfa validity reports no violation for any winner (Pyfa has no maxTypeFitted check)
Pyfa-side metric definitions: dps = weapon_dps + drone_dps; ehp = sum of ehp layers (uniform damage);
tank = max over layers of sustainable_tank[layer] * ehp[layer] / hp[layer]; speed = max_velocity;
cap_stable = cap_state (percent) if stable else cap_state (seconds) - 1e9; price = pinned table (no Pyfa involved).
usage: python3 optimizer/tools/pyfa_check.py [id ...]   (env REF=/workspace/exct-eve/ref)"""
import json, os, subprocess, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lib  # noqa: E402

REF = os.environ.get("REF", "/workspace/exct-eve/ref")
ORACLE = str(lib.ROOT.parent / "oracle" / "pyfa_oracle.py")
AGREE_REL = 5e-3
LAYERS = {"shield": "shieldRepair", "armor": "armorRepair", "hull": "hullRepair"}


def pyfa_metric(name, s, fit):
    if name == "dps":
        return s["weapon_dps"] + s["drone_dps"]
    if name == "ehp":
        return sum(s["ehp"].values())
    if name == "tank":
        st = s.get("sustainable_tank") or {}
        return max((st.get(k) or 0) * (s["ehp"][l] / s["hp"][l] if s["hp"][l] else 0) for l, k in LAYERS.items())
    if name == "speed":
        return s["max_velocity"]
    if name == "cap_stable":
        return s["cap_state"] if s["cap_stable"] else s["cap_state"] - lib.CAP_UNSTABLE_OFFSET
    if name == "price":
        return lib.fit_price(fit)[0]
    raise KeyError(name)


def run_pyfa(fits):
    with tempfile.TemporaryDirectory() as d:
        paths = []
        for i, f in enumerate(fits):
            p = Path(d) / f"{i:04d}.json"
            p.write_text(json.dumps(f))
            paths.append(str(p))
        env = dict(os.environ, PYTHONPATH=REF + "/stubs", PYFA=REF + "/pyfa", ORACLE_REPEAT="0", ORACLE_EXTRA="validity")
        r = subprocess.run([REF + "/pyfa-venv/bin/python", ORACLE, *paths], cwd=REF + "/pyfa", env=env,
                           capture_output=True, text=True)
        res = {}
        for line in r.stdout.splitlines():
            if line.startswith("{"):
                j = json.loads(line)
                res[int(j["file"][:4])] = j
        return [res.get(i, {"error": "no output"}) for i in range(len(fits))]


def check(cid):
    ep = lib.ROOT / "expected" / f"{cid}.json"
    case = json.loads((lib.ROOT / "cases" / f"{cid}.json").read_text())
    exp = json.loads(ep.read_text())
    m, direction = exp["objective"]["metric"], exp["objective"]["direction"]
    base = case["request"]["base"]
    win = [dict(base, modules=f["modules"]) for f in exp["optimal_fits"][:10]]
    run = [dict(base, modules=f["modules"]) for f in exp["runners_up"]]
    ref_vals = [exp["optimum"]] * len(win) + [r["value"] for r in exp["runners_up"]]
    outs = run_pyfa(win + run)
    rows, agree, legal = [], True, True
    for i, (f, o, rv) in enumerate(zip(win + run, outs, ref_vals)):
        if "error" in o:
            rows.append({"role": "winner" if i < len(win) else "runner_up", "error": o["error"]})
            agree = False
            continue
        pv = pyfa_metric(m, o["stats"], f)
        rel = abs(pv - rv) / max(abs(rv), 1e-9) if m != "cap_stable" or rv >= 0 else abs(pv - rv) / max(abs(rv + lib.CAP_UNSTABLE_OFFSET), 1e-9)
        viol = [v["code"] for v in o["stats"].get("validity", {}).get("violations", [])] if isinstance(o["stats"].get("validity"), dict) \
            else [v["code"] for v in (o["stats"].get("validity") or [])]
        row = {"role": "winner" if i < len(win) else "runner_up", "engine": rv, "pyfa": pv, "rel_diff": rel}
        if i < len(win):
            row["pyfa_violations"] = viol
            legal &= not viol
        agree &= rel <= AGREE_REL
        rows.append(row)
    wp = [r["pyfa"] for r in rows if r["role"] == "winner" and "pyfa" in r]
    rp = [r["pyfa"] for r in rows if r["role"] == "runner_up" and "pyfa" in r]
    if not wp:
        rank = False
    elif not rp:
        rank = True
    elif direction == "max":
        rank = min(wp) >= max(rp) - 1e-6 * max(1, abs(max(rp)))
    else:
        rank = max(wp) <= min(rp) + 1e-6 * max(1, abs(min(rp)))
    exp["pyfa_check"] = {"agree": agree, "rank": rank, "legal": legal, "agree_rel_tolerance": AGREE_REL, "fits": rows}
    ep.write_text(json.dumps(exp, indent=1, sort_keys=True) + "\n")
    worst = max((r.get("rel_diff", 1) for r in rows), default=None)
    print(f"{cid}: agree={agree} rank={rank} legal={legal} worst_rel={worst:.2e}", flush=True)
    return agree and rank and legal


if __name__ == "__main__":
    ids = sys.argv[1:] or sorted(p.stem for p in (lib.ROOT / "expected").glob("*.json"))
    bad = [c for c in ids if not check(c)]
    print("pyfa_check:", len(ids) - len(bad), "/", len(ids), "ok", ("FAILED: " + " ".join(bad)) if bad else "")
