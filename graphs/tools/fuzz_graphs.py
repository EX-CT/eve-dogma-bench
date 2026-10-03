#!/usr/bin/env python3
"""Differential fuzzer for the round-2 graph engines (G1 vs G3, plus G2/G4 when they exist), adjudicated by the
Pyfa graph oracle (oracle/pyfa_graph_oracle.py, GPL test tool).

  python3 graphs/tools/fuzz_graphs.py [--n 400] [--seed 1] [--variants G1,G2,G3,G4] [--work-dir work/graphs-eval]
                                      [--out results/graphs-fuzz] [--record]

1. Generates random GraphRequests over the contract-0.1 feature set (9 graphs, mps/m axes; the 0.2 additions are
   covered by the corpus and not implemented by every variant yet, so they would only measure missing features): fits drawn from the graph corpus and the 1.8.0 stats
   corpus (cases/*.json, 326 FitRequests), random graph / x axis / y series, random x samples (incl. limiter edges),
   random params, settings and targets (ideal, random profile, random target fit with a resist mode).
2. Runs every request through each variant's graph-batch command. Variants are the read-only worktrees that
   tools/evaluate_graphs.py prepared in --work-dir (same command resolution). A request is a *disagreement*
   when two variants differ on any sample value (corpus tolerance, tools/metrics.close) or one answers and another errors.
3. Each disagreement goes to the Pyfa graph oracle. Each variant's answer is then scored against the oracle with
   graphs/run_graphs.score_case. Confirmed cases (oracle answered and at least one variant is wrong) are clustered by
   (graph, axis, set of wrong variants, request features).
4. --record writes graphs/pending/cases/<id>.json + graphs/pending/expected/<id>.json for one representative per cluster
   and appends a section to graphs/pending.md. Nothing is added to the scored corpus (graphs/cases) automatically.
Outputs: <out>/fuzz.json (all requests, verdicts), <out>/fuzz.md (summary)."""
import argparse, collections, copy, gzip, hashlib, importlib.util, json, os, pathlib, random, subprocess, sys, tempfile, time

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "graphs"))
from metrics import close  # noqa: E402
from run_graphs import score_case  # noqa: E402

_spec = importlib.util.spec_from_file_location("evaluate_graphs", ROOT / "tools" / "evaluate_graphs.py")
EG = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(EG)
DATASET = EG.DATASET
REF = os.environ.get("EXCT_REF", "/workspace/exct-eve/ref")
PYFA = os.environ.get("PYFA", f"{REF}/pyfa")
PYFA_PY = os.environ.get("PYFA_PY", f"{REF}/pyfa-venv/bin/python")
WX_STUB = os.environ.get("WX_STUB", f"{REF}/stubs")

AXES = {
    "damage": {"distance_m": ("dps", "volley", "damage"), "time_s": ("dps", "volley", "damage"),
               "tgt_speed_mps": ("dps", "volley", "damage"), "tgt_sig_m": ("dps", "volley", "damage")},
    "application_profile": {"distance_m": ("dps", "volley")},
    "ewar": {"distance_m": ("neut_gj_s", "web_pct", "ecm_strength", "damp_lock_range_pct", "td_optimal_pct",
                            "gd_range_pct", "tp_sig_pct")},
    "remote_reps": {"distance_m": ("rps", "total"), "time_s": ("rps", "total")},
    "capacitor": {"time_s": ("cap_gj", "cap_regen_gj_s"), "cap_pct": ("cap_gj", "cap_regen_gj_s")},
    "shield_regen": {"time_s": ("shield_hp", "shield_regen_hp_s"), "shield_pct": ("shield_hp", "shield_regen_hp_s")},
    "mobility": {"time_s": ("speed_mps", "distance_m", "momentum_kg_mps", "bump_speed_mps", "bump_distance_m")},
    "warp_time": {"distance_m": ("time_s",)},
    "lock_time": {"tgt_sig_m": ("time_s",)},
}
GRAPH_W = {"damage": 34, "application_profile": 12, "ewar": 10, "remote_reps": 8, "capacitor": 10, "shield_regen": 6,
           "mobility": 6, "warp_time": 7, "lock_time": 7}
GRAPH_FITS = {}  # graph -> fits from the graph corpus that exercise it (biases sampling toward meaningful fits)


def fit_pool():
    graph_fits, stats_fits = [], []
    for r in EG.corpus():  # value cases only (error cases carry deliberately broken requests)
        if r["graph"] not in AXES:
            continue
        graph_fits.append(r["fit"])
        GRAPH_FITS.setdefault(r["graph"], []).append(r["fit"])
        t = (r.get("target") or {}).get("fit")
        if t:
            graph_fits.append(t)
    for p in sorted((ROOT / "cases").glob("*.json")):
        stats_fits.append(json.loads(p.read_text()))
    return graph_fits, stats_fits


def xs_for(rng, graph, axis):
    n = rng.randint(4, 14)
    if axis == "distance_m":
        hi = rng.choice([5000, 20000, 60000, 150000, 300000]) if graph != "warp_time" else rng.choice([1e8, 1.5e12, 1e13, 5e13])
    elif axis == "time_s":
        hi = rng.choice([10, 60, 300, 1200, 2600] if graph in ("damage", "remote_reps") else [10, 60, 600, 3700])
    elif axis == "tgt_speed_mps":
        hi = rng.choice([300, 1500, 5000])
    elif axis == "tgt_sig_m":
        hi = rng.choice([100, 1000, 20000])
    else:  # pct axes
        hi = 100
    lo = 1 if axis == "tgt_sig_m" else 0  # sig <= 0 is outside the limiter (null) and the oracle divides by it
    vals = sorted({round(rng.uniform(lo, hi), rng.choice([0, 1, 3])) for _ in range(n)})
    if rng.random() < 0.3 and lo == 0:
        vals = [0] + vals
    if rng.random() < 0.15 and axis in ("cap_pct", "shield_pct"):
        vals.append(100.0)
    return vals


def rand_profile(rng):
    p = {k: round(rng.choice([0, rng.uniform(0, 0.9)]), 3) for k in ("em", "thermal", "kinetic", "explosive")}
    p.update(max_velocity=rng.choice([0, 100, 250, 1200, 3500]), signature_radius=rng.choice([None, 30, 125, 400, 2500, 40000]),
             radius=rng.choice([0, 30, 150, 400, 2000]), hp=rng.choice([None, None, 5000, 200000]))
    return p


def rand_params(rng, graph, axis):
    p = {}
    if graph in ("damage", "application_profile"):
        if rng.random() < 0.5:
            p["tgt_speed_pct"] = rng.choice([0, 25, 50, 100])
        if rng.random() < 0.3:
            p["atk_speed_pct"] = rng.choice([0, 50, 100])
        if rng.random() < 0.3:
            p["atk_angle_deg"] = rng.choice([0, 45, 90, 180])
            p["tgt_angle_deg"] = rng.choice([0, 30, 90, 135])
        if graph == "application_profile" and rng.random() < 0.5:
            p["ammo_quality"] = rng.choice(["t1", "navy", "all"])
    if graph in ("damage", "remote_reps"):
        if axis != "distance_m" and rng.random() < 0.6:
            p["distance_m"] = rng.choice([0, 2000, 10000, 30000, 70000])
        if axis != "time_s" and rng.random() < 0.4:
            p["time_s"] = rng.choice([0, 5, 20, 60, 400])
    if graph == "remote_reps" and rng.random() < 0.3:
        p["anc_reload"] = rng.random() < 0.5
    if graph == "ewar" and rng.random() < 0.4:
        p["resist"] = rng.choice([0.1, 0.3, 0.6])
    if graph == "capacitor":
        if rng.random() < 0.5:
            p["cap_start_pct"] = rng.choice([0, 30, 50, 100])
        if rng.random() < 0.3:
            p["use_capsim"] = rng.random() < 0.5
    if graph == "shield_regen":
        if rng.random() < 0.5:
            p["shield_start_pct"] = rng.choice([0, 25, 80])
        if rng.random() < 0.4:
            p["effective"] = rng.random() < 0.5
    if graph == "mobility" and rng.random() < 0.5:
        p["tgt_mass_kg"] = rng.choice([1e6, 1.3e9, 2.5e10])
        p["tgt_inertia"] = rng.choice([0.01, 0.015, 0.05])
    return p


def gen(rng, graph_fits, stats_fits, k):
    graph = rng.choices(list(GRAPH_W), weights=list(GRAPH_W.values()))[0]
    axis = rng.choice(list(AXES[graph]))
    pool = rng.random()
    if pool < 0.45 and GRAPH_FITS.get(graph):
        fit = rng.choice(GRAPH_FITS[graph])
    elif pool < 0.7:
        fit = rng.choice(graph_fits)
    else:
        fit = rng.choice(stats_fits)
    fit = copy.deepcopy(fit)
    if rng.random() < 0.25:  # mutate module states / drop a module
        mods = fit.get("modules") or []
        for m in mods:
            if rng.random() < 0.2 and m.get("state") in ("active", "online", "overheated"):
                m["state"] = rng.choice(["online", "active", "overheated"])
        if mods and rng.random() < 0.3:
            mods.pop(rng.randrange(len(mods)))
    ys = list(AXES[graph][axis])
    if rng.random() < 0.4:
        ys = rng.sample(ys, rng.randint(1, len(ys)))
    r = {"schema_version": 1, "graph": graph, "fit": fit, "x": {"axis": axis, "values": xs_for(rng, graph, axis)}, "y": ys}
    params = rand_params(rng, graph, axis)
    if params:
        r["params"] = params
    if graph in ("damage", "application_profile"):
        t = rng.random()
        if t < 0.35:
            r["target"] = {"profile": rand_profile(rng)}
        elif t < 0.6:
            r["target"] = {"fit": copy.deepcopy(rng.choice(graph_fits + stats_fits[:60])),
                           "resist_mode": rng.choice(["auto", "shield", "armor", "hull", "weighted_average"])}
        s = {}
        for key, choices in (("ignore_resists", [True, False]), ("apply_projected", [True, False]),
                             ("ignore_lock_range", [True, False]), ("ignore_drone_control_range", [False, True]),
                             ("mobile_drone_mode", ["auto", "follow_attacker", "follow_target"])):
            if rng.random() < 0.35:
                s[key] = rng.choice(choices)
        if s:
            r["settings"] = s
    r["_id"] = f"fz{k:04d}-" + hashlib.sha1(json.dumps(r, sort_keys=True).encode()).hexdigest()[:8]
    return r


def strip(r):
    return {k: v for k, v in r.items() if not k.startswith("_")}


def run_variant(cmd, vd, reqs, timeout=1800):
    rc, dt, out = EG.sh(cmd, str(vd), timeout, inp="".join(json.dumps(strip(r)) + "\n" for r in reqs))
    res = []
    for line in out.splitlines():
        try:
            res.append(json.loads(line))
        except ValueError:
            res.append(None)
    if len(res) != len(reqs):  # crashed batch: fall back to one process per request so one bad line can't hide all
        res = []
        for r in reqs:
            rc, dt, o = EG.sh(cmd, str(vd), 120, inp=json.dumps(strip(r)) + "\n")
            try:
                res.append(json.loads(o.splitlines()[0]))
            except (ValueError, IndexError):
                res.append({"error": {"code": "NO_RESPONSE", "message": (o or "")[-200:]}})
    return res, dt


def ok_result(o):
    return isinstance(o, dict) and isinstance(o.get("series"), dict)


def agree(a, b, ys):
    if ok_result(a) != ok_result(b):
        return False
    if not ok_result(a):
        return True  # both errors: not a value disagreement
    for y in ys:
        sa, sb = a["series"].get(y), b["series"].get(y)
        if not isinstance(sa, list) or not isinstance(sb, list) or len(sa) != len(sb):
            return False
        if not all(close(u, v) and close(v, u) for u, v in zip(sa, sb)):
            return False
    return True


def oracle(reqs):
    out = {}
    with tempfile.TemporaryDirectory() as td:
        files = []
        for r in reqs:
            f = pathlib.Path(td) / f"{r['_id']}.json"
            f.write_text(json.dumps(strip(r)))
            files.append(str(f))
        env = dict(os.environ, PYTHONPATH=WX_STUB, PYFA=PYFA)
        for i in range(0, len(files), 40):
            p = subprocess.run([PYFA_PY, str(ROOT / "oracle/pyfa_graph_oracle.py"), *files[i:i + 40]], capture_output=True,
                               text=True, cwd=PYFA, env=env, timeout=1800)
            for line in p.stdout.splitlines():
                try:
                    o = json.loads(line)
                except ValueError:
                    continue
                out[o.pop("file")[:-5]] = o
    return out


def features(r):
    f = [r["graph"], r["x"]["axis"]]
    t = r.get("target") or {}
    f.append("tgt-fit" if t.get("fit") else "tgt-profile" if t.get("profile") else "tgt-ideal")
    for k, v in sorted((r.get("settings") or {}).items()):
        f.append(f"{k}={v}")
    for k in sorted(r.get("params") or {}):
        f.append(k)
    return f


def ship_name(type_id, names):
    return names.get(type_id, str(type_id))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--n", type=int, default=400)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--variants", default="G1,G2,G3,G4")
    ap.add_argument("--work-dir", default=str(ROOT / "work" / "graphs-eval"))
    ap.add_argument("--out", default=str(ROOT / "results" / "graphs-fuzz"))
    ap.add_argument("--oracle-sample", type=int, default=0,
                    help="also adjudicate this many randomly chosen requests on which all variants agree")
    ap.add_argument("--record", action="store_true", help="write confirmed clusters to graphs/pending/ and graphs/pending.md")
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    work = pathlib.Path(a.work_dir).resolve()
    rng = random.Random(a.seed)
    graph_fits, stats_fits = fit_pool()
    reqs = [gen(rng, graph_fits, stats_fits, k) for k in range(a.n)]
    variants = {}
    for g in a.variants.upper().split(","):
        wt = work / g
        if not wt.exists():
            print(f"{g}: no worktree in {work} (run tools/evaluate_graphs.py first); skipped")
            continue
        vd, y, src = EG.variant_dir(wt, g)
        m, notes = EG.resolve(vd, y, src, next(r for r in EG.corpus() if r["graph"] == "damage"), built=True)
        if not m.get("graph_batch_cmd"):
            print(f"{g}: no graph-batch command; skipped")
            continue
        variants[g] = (m["graph_batch_cmd"], vd, EG.git(wt, "rev-parse", "HEAD"))
    print(f"{len(reqs)} requests, variants: {', '.join(f'{g}@{v[2][:7]}' for g, v in variants.items())}", flush=True)
    answers = {}
    for g, (cmd, vd, sha) in variants.items():
        answers[g], dt = run_variant(cmd, vd, reqs)
        errs = sum(1 for o in answers[g] if not ok_result(o))
        print(f"{g}: {dt:.1f} s, {errs} error responses", flush=True)
    names = list(variants)
    dis = []
    for i, r in enumerate(reqs):
        if not all(agree(answers[names[0]][i], answers[g][i], r["y"]) for g in names[1:]):
            dis.append(i)
    print(f"disagreements: {len(dis)}/{len(reqs)}", flush=True)
    agreeing = [i for i in range(len(reqs)) if i not in set(dis)]
    sample = sorted(random.Random(a.seed + 1).sample(agreeing, min(a.oracle_sample, len(agreeing))))
    t0 = time.time()
    ora = oracle([reqs[i] for i in dis + sample]) if dis or sample else {}
    print(f"oracle: {len(ora)} answers in {time.time() - t0:.0f} s", flush=True)
    verdicts = []
    for i in dis + sample:
        r = reqs[i]
        o = ora.get(r["_id"])
        v = {"id": r["_id"], "kind": "disagreement" if i in dis else "agreeing sample", "features": features(r), "ship": r["fit"].get("ship", {}).get("type_id") if isinstance(r["fit"].get("ship"), dict) else r["fit"].get("ship")}
        if not o or "error" in o:
            v["status"] = "oracle error"
            v["oracle_error"] = (o or {}).get("error", "no oracle output")
        else:
            exp = {"x": o["x"], "series": {y: o["series"][y] for y in r["y"] if y in o["series"]}}
            wrong, right = [], []
            detail = {}
            for g in names:
                okv, tot, _, _, bad = score_case(answers[g][i], exp)
                (right if not bad and tot else wrong).append(g)
                if bad or not tot:
                    resp = answers[g][i]
                    detail[g] = (resp or {}).get("error") if isinstance(resp, dict) and "error" in resp else bad[:3]
            v.update(status="confirmed" if wrong else "all match oracle", wrong=wrong, right=right, detail=detail,
                     expected=exp)
        verdicts.append(v)
    clusters = collections.OrderedDict()
    for v in verdicts:
        if v["status"] != "confirmed":
            continue
        key = (v["features"][0], v["features"][1], tuple(v["wrong"]))
        clusters.setdefault(key, []).append(v)
    summary = {"requests": len(reqs), "seed": a.seed, "variants": {g: v[2] for g, v in variants.items()},
               "disagreements": len(dis), "oracle_sampled_agreeing": len(sample),
               "agreeing_sample_wrong": sum(1 for v in verdicts if v["kind"] == "agreeing sample" and v["status"] == "confirmed"),
               "confirmed": sum(1 for v in verdicts if v["status"] == "confirmed"),
               "oracle_errors": sum(1 for v in verdicts if v["status"] == "oracle error"),
               "all_match_oracle": sum(1 for v in verdicts if v["status"] == "all match oracle"),
               "wrong_by_variant": dict(collections.Counter(g for v in verdicts if v["status"] == "confirmed" for g in v["wrong"])),
               "clusters": [{"graph": k[0], "axis": k[1], "wrong": list(k[2]), "n": len(vs), "ids": [x["id"] for x in vs]}
                            for k, vs in clusters.items()]}
    (out / "fuzz.json").write_text(json.dumps({"summary": summary, "verdicts": verdicts,
                                               "requests": {r["_id"]: strip(r) for r in (reqs[i] for i in dis)}}, indent=1))
    md = [f"# Graph differential fuzz (seed {a.seed}, {len(reqs)} requests)", "",
          "Variants: " + ", ".join(f"{g} `{s[:7]}`" for g, s in summary["variants"].items()), "",
          f"- disagreements between variants: **{len(dis)}**",
          f"- agreeing requests also checked against the oracle: {len(sample)} (all variants wrong together: {summary['agreeing_sample_wrong']})",
          f"- confirmed by the Pyfa oracle (≥ 1 variant wrong): **{summary['confirmed']}**",
          f"- adjudicated requests where every variant matches the oracle: {summary['all_match_oracle']}",
          f"- oracle could not evaluate: {summary['oracle_errors']}",
          f"- wrong answers by variant: {summary['wrong_by_variant']}", "",
          "| cluster | graph | axis | wrong | right | n | example | example mismatch |", "|---|---|---|---|---|---|---|---|"]
    for k, (key, vs) in enumerate(clusters.items()):
        ex = vs[0]
        d = json.dumps(ex["detail"], default=str)[:220].replace("|", "\\|")
        md.append(f"| C{k+1} | {key[0]} | {key[1]} | {', '.join(key[2])} | {', '.join(ex['right']) or '–'} | {len(vs)} | {ex['id']} | {d} |")
    (out / "fuzz.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))
    if a.record:
        record(clusters, reqs, summary, a)


def record(clusters, reqs, summary, a):
    byid = {r["_id"]: r for r in reqs}
    pc, pe = ROOT / "graphs/pending/cases", ROOT / "graphs/pending/expected"
    pc.mkdir(parents=True, exist_ok=True)
    pe.mkdir(parents=True, exist_ok=True)
    lines = []
    for k, (key, vs) in enumerate(clusters.items()):
        ex = vs[0]
        r = byid[ex["id"]]
        name = f"fuzz_{key[0]}_{key[1]}_{ex['id']}"
        (pc / f"{name}.json").write_text(json.dumps(strip(r), indent=1, sort_keys=True) + "\n")
        e = {"case": name, "oracle": "pyfa-graphs", "graph": r["graph"], "x_axis": r["x"]["axis"], **ex["expected"]}
        (pe / f"{name}.json").write_text(json.dumps(e, indent=1, sort_keys=True) + "\n")
        det = json.dumps(ex["detail"], default=str)[:400]
        lines.append(f"- **{name}**: {key[0]} / {key[1]}; features `{' '.join(ex['features'][2:]) or '-'}`; "
                     f"wrong: **{', '.join(key[2])}**; matches oracle: {', '.join(ex['right']) or 'none'}; "
                     f"{len(vs)} fuzz request(s) in this cluster. Example: `{det}`")
    pm = ROOT / "graphs/pending.md"
    head = "" if pm.exists() else ("# Pending graph cases\n\nCandidate cases (not scored yet). Each one has a request in "
                                   "`graphs/pending/cases/` and Pyfa oracle values in `graphs/pending/expected/`.\n")
    sec = [f"\n## Differential fuzz {time.strftime('%Y-%m-%d %H:%M')} CST (seed {a.seed}, {summary['requests']} requests)", "",
           "Variants: " + ", ".join(f"{g} `{s[:7]}`" for g, s in summary["variants"].items()) +
           f". Disagreements {summary['disagreements']}, confirmed by the oracle {summary['confirmed']}, "
           f"oracle errors {summary['oracle_errors']}. Wrong answers by variant: {summary['wrong_by_variant']}.", ""] + lines
    with open(pm, "a") as f:
        f.write(head + "\n".join(sec) + "\n")


if __name__ == "__main__":
    main()
