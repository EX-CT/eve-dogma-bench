#!/usr/bin/env python3
"""Round-2 (graphs) evaluation for the EX-CT graph bake-off (variants G1–G4): reproducible, one command.
Structured like tools/evaluate.py (round 1, branch main); bench round 2 = branch graphs-round2.

  python3 tools/evaluate_graphs.py [--runs 3] [--only G1,G3] [--quick] [--dry-run] [--out results]
                                   [--as-of 2026-10-03T10:15:00+08:00] [--work-dir work/graphs-eval]
                                   [--no-fetch] [--no-build] [--no-tests] [--no-stats-gate] [--latency-samples 5]
                                   [--graphs-ref 0397d95] [--stats-ref 3da9671]

Shared code: helpers come from tools/evaluate.py (round 1): static metrics, license detection, portability, test
discovery, L()/med()/loadavg, timed_batch(), pin_bench() and the latency constants, so both rounds measure alike.
Pins (independent of the checked-out branch): graphs/ corpus, expected values, run_graphs.py and CONTRACT-GRAPHS.md
from commit 0397d95 (graph contract revision 0.2, 178 graph cases) and the stats gate's run.py/cases/expected from
bench 1.8.0 (3da9671, 326 cases), each extracted with `git archive` into <work-dir>/bench-<sha>; the pinned SHAs,
contract revision and case counts are recorded in the output (meta.graphs_pin / meta.stats_pin).

Per variant (sequentially, so variants never compete for the CPU with each other):
  1. fetch   EX-CT/eve-dogma-lab@graphs-g<n> into one blobless clone (--work-dir/_lab), checked out read-only as a
             detached worktree per variant (current head, or the last first-parent commit <= --as-of). Nothing is ever
             pushed. The variant directory is the one whose bench.yaml declares graph_batch_cmd/graph_cmd, else
             graphs-g<n>/. Commands not declared in bench.yaml are INFERRED (recorded as such in the report):
             build + --batch-cmd from the variant's own score*.sh (run_graphs.py invocation), or
             `<batch_cmd> -> graph-batch` and RPC method `graph`, accepted only if a probe request answers with a
             GraphResult.
  2. build   manifest (or inferred) build command; wall time recorded.
  3. correctness  graphs/run_graphs.py (the official scorer, unchanged) over every interface the variant offers
             (graph-batch, graph single, RPC `graph`); the gate uses the preferred one (batch > rpc > single) and
             requires the others to agree. Stats gate: run.py (bench 1.8.0, unchanged) on the variant's round-1
             commands (bench.yaml cmd/batch_cmd in the graph dir or its round-1 sibling dir), quick perf settings.
  4. perf    (medians over --runs; loadavg recorded per run)
             points/s   corpus (111 requests, all x samples) through one graph-batch process, start-up excluded:
                        points / (wall(corpus) − wall(1 small request)); raw points/s incl. start-up also shown
                        (if the difference is < 5 % of the corpus wall time, the raw value is used and flagged);
             latency    dense interactive request: every distance-axis damage case re-sampled at 500 points (distinct
                        fits => includes the fit calculation). SCORED value = round-1 rules, measured once per
                        variant outside the runs (dense_latency()): graph-batch pinned to ONE cpu (taskset),
                        (T_N − T_1)/(N − 1) with T_1 = one dense request (median of 3) and N dense requests sized for
                        ≈0.5 s, ≥ --latency-samples (5) independent samples, median; a sample is invalid if ≤ 0,
                        < 0.002 ms, > T_N/N or the response count is wrong; spread > 50 % => up to 3 extra samples,
                        then flagged. Spread and flags are in md + json. Informational: RPC warm-process median
                        (dense_rpc_ms) and the same Kronos request repeated (dense_repeat_ms); without graph-batch
                        the RPC median is used and flagged.
             cold       wall time of a fresh process answering one small request (graph single mode, else
                        graph-batch with one line); median of 5.
  5. maint.  static metrics on the variant directory (same heuristics as round 1) + round-2 core LOC = lines added
             in hand-written core source since the merge-base with the round-1 branch the variant started from
             (variant-e/c/g/f), the variant's own test suite, docs, deps.
SCORING RULES (round 2, plan docs/10-round-2-graphs-plan.md §8)
  Gate: all graph cases fully correct (every interface offered agrees) AND 326/326 stats cases (unless
        --no-stats-gate). Ungated variants are listed with the reason, unscored.
  Total = 0.40·Speed + 0.35·Maintainability + 0.15·Features + 0.10·Portability
  L(x, best, span) = clamp(1 − log10(x/best)/log10(span), 0, 1) for lower-is-better x (as round 1).
  Speed = 0.4·L(1/points-per-s, 100) + 0.4·L(dense latency ms, 100) + 0.2·L(cold ms, 100)
  Maintainability = 0.30·Tests + 0.30·Size + 0.20·Docs + 0.20·Deps
        Tests/Docs/Deps as round 1; Size = L(round-2 core LOC added, min, 10).
        (round 1's DataDriven sub-score is reported for information only: graph code legitimately names effects.)
  Features = 0.6·(graphs with all cases correct / graphs in the corpus) + 0.3·(interfaces offered of batch/single/rpc, each passing
        the corpus) + 0.1·(empty x.values -> empty series, contract ruling 2026-10-03)
  Portability = round-1 heuristic (1 WASM/browser build in code, 0.5 documented, 0 none).
  Licensing (informational, not scored; same detection as round 1, judged at the evaluated --as-of commit):
        license from the actual LICENSE texts of the graph dir (+ branch root); a round-2 variant also inherits the
        license of the round-1 variant it is built on (G1 on variant-e = GPL-3.0-or-later, a Pyfa-derived port):
        G1 is therefore NOT mergeable into the LGPL-3.0-or-later mainline whatever its own LICENSE file says.
Outputs: <out>/evaluation-graphs.md, <out>/evaluation-graphs.json (+ <out>/raw-graphs/<G>/ scorecards); default
  <out> = results/ (results/dryrun/ with --dry-run, every output labelled DRY RUN)."""
import argparse, gzip, json, math, os, pathlib, re, shutil, signal, statistics, subprocess, sys, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import evaluate as ev  # noqa: E402  round-1 tool: shared helpers (static metrics, license, latency rules, pinning)
from evaluate import (load3, L, med, log, CODE_EXT, SKIP_DIRS, classify, comment_prefix, static_metrics,  # noqa: E402
                      test_command, portability, commit_time, timed_batch, pin_bench, LAT_FLOOR_MS, LAT_SPREAD_MAX)
DATASET = os.environ.get("EVE_DOGMA_DATASET", "/workspace/exct-eve/data/dataset-3569502.json.gz")
LAB = "https://github.com/EX-CT/eve-dogma-lab"
VARIANTS = {"G1": ("graphs-g1", "variant-e", "Pyfa-faithful graph port (Rust, on E)"),
            "G2": ("graphs-g2", "variant-c", "engine primitives + TS evaluator (on C)"),
            "G3": ("graphs-g3", "variant-g", "vectorised NumPy grid + fit cache (on G)"),
            "G4": ("graphs-g4", "variant-f", "declarative graph specs (Rust, on F)")}
GRAPHS_PIN, GRAPHS_PIN_REVISION = "0397d95", "0.2"   # graph contract 0.2 (corpus/expected/run_graphs.py), this repo
STATS_PIN = ev.BENCH_PIN                              # bench 1.8.0 (3da9671) for the 326-case stats gate
GROOT = ROOT                                          # replaced in main() by the pinned 0397d95 snapshot
SROOT = ROOT                                          # replaced in main() by the pinned 3da9671 snapshot
# round-2 variants built on a GPL round-1 variant inherit its license (in addition to the LICENSE-file check)
DERIVED = {"G1": "built on variant-e (GPL-3.0-or-later, Pyfa-derived port)"}
W = dict(speed=0.40, maint=0.35, feat=0.15, port=0.10)
SPEED_W = dict(throughput=0.4, latency=0.4, cold=0.2)
MAINT_W = dict(tests=0.30, size=0.30, docs=0.20, deps=0.20)

ENV = dict(os.environ)
_dn = pathlib.Path.home() / ".dotnet"
if _dn.exists():
    ENV["PATH"] = f"{_dn}:{ENV['PATH']}"; ENV.setdefault("DOTNET_ROOT", str(_dn))
ENV.update(DOTNET_CLI_TELEMETRY_OPTOUT="1", DOTNET_NOLOGO="1")


# ---------------------------------------------------------------- static maintainability metrics


# ---------------------------------------------------------------- own test suites


def parse_tests(kind, out):
    p = f = None
    if kind == "cargo":
        rs = re.findall(r"test result: \w+\. (\d+) passed; (\d+) failed", out)
        if rs: p, f = sum(int(a) for a, _ in rs), sum(int(b) for _, b in rs)
    elif kind == "go":
        p, f = len(re.findall(r"^\s*--- PASS", out, re.M)), len(re.findall(r"^\s*--- FAIL", out, re.M))
    elif kind == "ctest":
        r = re.search(r"(\d+) tests failed out of (\d+)", out)
        if r: f = int(r.group(1)); p = int(r.group(2)) - f
    elif kind in ("unittest",):
        r = re.search(r"Ran (\d+) tests?", out)
        if r:
            n = int(r.group(1)); fm = re.search(r"FAILED \((?:failures=(\d+))?(?:, )?(?:errors=(\d+))?", out)
            f = sum(int(x or 0) for x in fm.groups()) if fm else 0
            sk = re.search(r"skipped=(\d+)", out); p = n - f - (int(sk.group(1)) if sk else 0)
    elif kind == "pytest":
        r1, r2 = re.search(r"(\d+) passed", out), re.search(r"(\d+) failed", out)
        p, f = int(r1.group(1)) if r1 else 0, int(r2.group(1)) if r2 else 0
    else:  # npm (node:test / jest / mocha / vitest) or manifest
        for pat_p, pat_f in ((r"^# pass (\d+)", r"^# fail (\d+)"), (r"Tests:.*?(\d+) passed", r"Tests:.*?(\d+) failed"),
                             (r"(\d+) passing", r"(\d+) failing"), (r"ℹ pass (\d+)", r"ℹ fail (\d+)"), (r"(\d+) passed", r"(\d+) failed")):
            r1 = re.search(pat_p, out, re.M)
            if r1:
                r2 = re.search(pat_f, out, re.M); p, f = int(r1.group(1)), int(r2.group(1)) if r2 else 0; break
        if kind == "dotnet":
            r = re.search(r"Passed:\s*(\d+)", out); r2 = re.search(r"Failed:\s*(\d+)", out)
            if r: p, f = int(r.group(1)), int(r2.group(1)) if r2 else 0
    return p, f


def run_tests(m, vd, timeout):
    cmd, kind = test_command(m, vd)
    if not cmd:
        return {"found": False}
    cmd = cmd.format(dataset=DATASET, bench=GROOT, dir=vd)
    env = dict(ENV, EVE_DOGMA_DATASET=DATASET, EVE_DOGMA_GRAPH_CASES=str(GROOT / "graphs" / "cases"))
    rc, dt, out = sh(cmd, str(vd), timeout, env=env)
    p, f = parse_tests(kind, out or "")
    st = "timeout" if rc is None else ("passed" if rc == 0 and not f else "failed")
    return {"found": True, "cmd": cmd, "runner": kind, "status": st, "rc": rc, "passed": p, "failed": f,
            "seconds": round(dt, 1), "tail": (out or "")[-600:] if st != "passed" else ""}


# ---------------------------------------------------------------- portability heuristic


def sh(cmd, cwd, timeout, env=None, inp=None):
    """Run in its own process group; kill the whole group on timeout. -> (rc|None, seconds, output)."""
    t0 = time.time()
    p = subprocess.Popen(cmd, shell=True, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         stdin=subprocess.PIPE if inp is not None else subprocess.DEVNULL, text=True,
                         start_new_session=True, env=env or ENV)
    try:
        out, err = p.communicate(inp, timeout=timeout)
        return p.returncode, time.time() - t0, out + (err or "")[-2000:] if p.returncode else out
    except subprocess.TimeoutExpired:
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        out = p.communicate()[0] or ""
        return None, time.time() - t0, out + f"\n[timeout after {timeout}s]"


def q(s):
    import shlex
    return shlex.quote(str(s))


# ---------------------------------------------------------------- fetch (read-only)
def git(cwd, *args, check=True):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, env=ENV)
    if check and r.returncode:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip()[-300:]}")
    return r.stdout.strip()


def fetch(g, work, no_fetch, as_of):
    br, base_br, _ = VARIANTS[g]
    lab = work / "_lab"
    if not lab.exists():
        git(work, "clone", "-q", "--filter=blob:none", "--no-checkout", LAB, str(lab))
    elif not no_fetch:
        git(lab, "fetch", "-q", "--prune", "origin")
    if not git(lab, "ls-remote", "--heads", "origin", br, check=False) and not no_fetch:
        return None, {"branch": br, "error": "branch does not exist"}
    head = git(lab, "rev-parse", f"origin/{br}", check=False)
    if not head:
        return None, {"branch": br, "error": "branch not found"}
    target = head
    if as_of:
        target = git(lab, "rev-list", "-1", "--first-parent", f"--before={int(as_of)}", f"origin/{br}")
        if not target:
            return None, {"branch": br, "head": head, "error": "no commit at or before --as-of"}
    wt = work / g
    if wt.exists():
        git(lab, "worktree", "remove", "--force", str(wt), check=False)
        shutil.rmtree(wt, ignore_errors=True)
    git(lab, "worktree", "prune")
    git(lab, "worktree", "add", "-q", "--detach", str(wt), target)
    mb = git(lab, "merge-base", target, f"origin/{base_br}", check=False)
    info = {"url": LAB, "branch": br, "sha": target, "commit_time": git(wt, "log", "-1", "--format=%cI"),
            "branch_head_at_fetch": head, "is_branch_head": head == target, "base_branch": base_br, "merge_base": mb}
    return wt, info


def variant_dir(wt, g):
    import yaml
    cands = []
    for d in sorted(p for p in wt.iterdir() if p.is_dir() and not p.name.startswith(".")):
        m = d / "bench.yaml"
        y = yaml.safe_load(m.read_text()) if m.exists() else {}
        cands.append((d, y or {}))
    for d, y in cands:
        if any(k in y for k in ("graph_batch_cmd", "graph_cmd")):
            return d, y, "bench.yaml"
    for d, y in cands:
        if d.name == VARIANTS[g][0]:
            return d, y, "bench.yaml (no graph commands)" if y else "none"
    return None, {}, "none"


def fmt(m):
    return {k: (v.format(dataset=DATASET, bench=GROOT) if isinstance(v, str) else v) for k, v in m.items()}


def infer_from_score_sh(vd):
    """build + graph batch command from the variant's own scorer script (run_graphs.py --batch-cmd "...")."""
    for f in sorted(vd.glob("score*.sh")):
        t = f.read_text()
        mb = re.search(r'--batch-cmd\s+"([^"]+)"', t)
        if not mb:
            continue
        cmd = re.sub(r"\$\{?D\}?", "{dataset}", mb.group(1))
        build = None
        mbuild = re.search(r'cd\s+"\$\(dirname "\$0"\)"\s*&&\s*(.*?)\s*&&\s*python3\s', t, re.S)
        if mbuild:
            build = mbuild.group(1).strip()
            if (vd / "package-lock.json").exists():
                build = "([ -d node_modules ] || npm ci --silent --no-audit --no-fund) && " + build
        return {"graph_batch_cmd": cmd, "build": build, "source": f"inferred from {f.name}"}
    return None


def probe_ok(o):
    return isinstance(o, dict) and isinstance(o.get("series"), dict) and "graph" in o


def probe_batch(cmd, vd, req):
    rc, dt, out = sh(cmd, str(vd), 120, inp=json.dumps(req) + "\n")
    try:
        return probe_ok(json.loads(out.splitlines()[0]))
    except (ValueError, IndexError):
        return False


def probe_rpc(cmd, vd, req):
    rc, dt, out = sh(cmd, str(vd), 120, inp=json.dumps({"id": 1, "method": "graph", "params": req}) + "\n")
    for line in out.splitlines():
        try:
            o = json.loads(line)
        except ValueError:
            continue
        if isinstance(o, dict) and o.get("id") == 1:
            return probe_ok(o.get("result"))
    return False


def resolve(vd, y, src, probe_req, built):
    """-> commands dict + provenance notes; probes only run after the build."""
    m = fmt(dict(y))
    notes = []
    if "graph_batch_cmd" not in m and "graph_cmd" not in m:
        inf = infer_from_score_sh(vd)
        if inf:
            m["graph_batch_cmd"] = inf["graph_batch_cmd"].format(dataset=DATASET)
            if inf["build"] and not m.get("build"):
                m["build"] = inf["build"]
            notes.append(f"graph_batch_cmd/build {inf['source']}")
    if not built:
        return m, notes
    if "graph_batch_cmd" not in m and m.get("batch_cmd"):
        c = re.sub(r"\bbatch\b", "graph-batch", m["batch_cmd"], count=1)
        if probe_batch(c, vd, probe_req):
            m["graph_batch_cmd"] = c
            notes.append("graph_batch_cmd inferred (batch -> graph-batch, probe ok)")
    if "graph_cmd" not in m and m.get("cmd") and not y.get("graph_cmd"):
        c = re.sub(r"\bcalc\b", "graph", m["cmd"], count=1)
        if c != m["cmd"]:
            rc, dt, out = sh(c, str(vd), 60, inp=json.dumps(probe_req))
            try:
                if probe_ok(json.loads(out)):
                    m["graph_cmd"] = c
                    notes.append("graph_cmd inferred (calc -> graph, probe ok)")
            except ValueError:
                pass
    if m.get("rpc_cmd") and probe_rpc(m["rpc_cmd"], vd, probe_req):
        m["graph_rpc_cmd"] = m["rpc_cmd"]
    return m, notes


def stats_cmds(vd, m, wt):
    """round-1 stats commands: the graph dir's bench.yaml, else the round-1 sibling directory's."""
    if m.get("cmd"):
        return m, vd
    import yaml
    base = VARIANTS[vd.parent.name][1] if vd.parent.name in VARIANTS else None
    for d in ([wt / base] if base else []) + sorted(p for p in wt.iterdir() if p.is_dir()):
        f = d / "bench.yaml"
        if f.exists():
            y = fmt(yaml.safe_load(f.read_text()) or {})
            if y.get("cmd"):
                return y, d
    return None, None


# ---------------------------------------------------------------- corpus helpers
def corpus():
    """value cases with at least one x sample (error cases and empty-x cases are scored, but not used for perf)"""
    out = []
    for p in sorted((GROOT / "graphs/cases").glob("*.json")):
        e = GROOT / "graphs/expected" / p.name
        exp = json.loads(e.read_text()) if e.exists() else {}
        r = json.loads(p.read_text())
        if "expect_error" in exp or not isinstance(r.get("x"), dict) or not r["x"].get("values"):
            continue
        out.append(r)
    return out


def corpus_graphs():
    """graph types of the contract ("### `name` —" headers under "## Graph types"), cross-checked with the
    value cases; 0.1 → 9, 0.2 → 10. The coverage denominator is len() of this."""
    txt = (GROOT / "graphs/CONTRACT-GRAPHS.md").read_text()
    sec = txt.split("## Graph types", 1)[1].split("\n## ", 1)[0]
    gs = re.findall(r"^### `([a-z_]+)`", sec, flags=re.M)
    seen = {r["graph"] for r in corpus()}
    gs += sorted(seen - set(gs))  # a corpus graph the contract headers miss still counts
    return gs


def dense_requests(cases, n=500):
    out = []
    for r in cases:
        if r["graph"] == "damage" and r["x"]["axis"] == "distance_m":
            hi = max(r["x"]["values"]) or 50000
            out.append(dict(r, x=dict(r["x"], values=[hi * k / (n - 1) for k in range(n)])))
    return out


SMALL = "lock_time"  # cold start uses the first lock_time case (one fit, few points)


# ---------------------------------------------------------------- correctness (official scorer, child process)
def score_interface(kind, cmd, vd, name, out, timeout):
    flag = {"batch": "--batch-cmd", "single": "--cmd", "rpc": "--rpc-cmd"}[kind]
    rc, dt, log_ = sh(f"{q(sys.executable)} graphs/run_graphs.py --name {q(name)} {flag} {q(cmd)} --cwd {q(vd)} "
                      f"--timeout {timeout}", str(GROOT), timeout + 60)
    card = GROOT / "results" / f"graphs-{name}" / "scorecard.json"
    if rc != 0 or not card.exists():
        return {"interface": kind, "error": f"exit {rc}: {log_[-400:]}"}
    c = json.loads(card.read_text())
    dst = out / "raw-graphs" / name.split("-")[1] / kind
    shutil.copytree(card.parent, dst, dirs_exist_ok=True)
    return {"interface": kind, "cases": c["cases"], "cases_ok": c["cases_fully_correct"], "values_ok": c["values_correct"],
            "values_total": c["values_total"], "groups": c["groups"], "info_charge_ids": c.get("info_charge_ids"),
            "wall_s": round(c["wall_s"], 3)}


def stats_gate(sm, sd, name, a):
    if not sm:
        return {"status": "no round-1 commands found"}
    args = f"--name {q(name)} --cmd {q(sm['cmd'])} --cwd {q(sd)} --batch-repeat 1 --latency-n 20 --timeout 60"
    if sm.get("batch_cmd"):
        args += f" --batch-cmd {q(sm['batch_cmd'])}"
    rc, dt, out = sh(f"{q(sys.executable)} run.py {args}", str(SROOT), 1800)
    card = SROOT / "results" / name / "scorecard.json"
    if rc != 0 or not card.exists():
        return {"status": "error", "detail": out[-400:]}
    c = json.loads(card.read_text())
    ok = c["cases_fully_correct"] == c["cases"] and not c.get("errors")
    return {"status": "pass" if ok else "fail", "cases": c["cases"], "cases_ok": c["cases_fully_correct"],
            "values_ok": c["values_correct"], "values_total": c["values_total"], "dir": sd.name, "seconds": round(dt, 1)}


# ---------------------------------------------------------------- perf
def batch_wall(cmd, vd, reqs, timeout=600):
    rc, dt, out = sh(cmd, str(vd), timeout, inp="".join(json.dumps(r) + "\n" for r in reqs))
    n_ok = sum(1 for l in out.splitlines() if l.strip().startswith("{"))
    return (dt if rc == 0 and n_ok == len(reqs) else None), rc


def rpc_latencies(cmd, vd, reqs, warm, timeout=300):
    """one request at a time on a persistent serve-stdio process -> per-request seconds"""
    p = subprocess.Popen(cmd, shell=True, cwd=str(vd), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.DEVNULL, text=True, bufsize=1, start_new_session=True, env=ENV)
    out = []
    deadline = time.time() + timeout
    try:
        for i, r in enumerate([warm] + reqs):
            t0 = time.perf_counter()
            p.stdin.write(json.dumps({"id": i, "method": "graph", "params": r}) + "\n")
            p.stdin.flush()
            while True:
                line = p.stdout.readline()
                if not line or time.time() > deadline:
                    return None
                try:
                    o = json.loads(line)
                except ValueError:
                    continue
                if isinstance(o, dict) and o.get("id") == i:
                    break
            if i:
                if not probe_ok(o.get("result")):
                    return None
                out.append(time.perf_counter() - t0)
    finally:
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    return out


def perf_run(m, vd, cases, a):
    res = {"loadavg_before": load3()}
    gb = m.get("graph_batch_cmd")
    small = next(r for r in cases if r["graph"] == SMALL)
    pts = sum(len(r["x"]["values"]) for r in cases)
    if gb:
        w_all, _ = batch_wall(gb, vd, cases)
        w_one, _ = batch_wall(gb, vd, [small])
        if w_all:
            res["corpus_wall_s"] = round(w_all, 4)
            res["points_per_s_raw"] = round(pts / w_all, 1)
            if w_one:
                res["one_wall_s"] = round(w_one, 4)
                if w_all - w_one > 0.05 * w_all:
                    res["points_per_s"] = round(pts / (w_all - w_one), 1)
                else:  # start-up difference implausible (jitter >= corpus time): use the raw value, flagged
                    res["points_per_s"] = res["points_per_s_raw"]; res["flag"] = "corpus wall ~ 1-request wall: raw points/s used"
    dense = dense_requests(cases)
    if a.quick:
        dense = dense[:8]
    kron = next((r for r in dense if "kronos" in json.dumps(r["fit"]).lower()), dense[0])
    if m.get("graph_rpc_cmd"):  # informational (scored latency: dense_latency(), single CPU, outside the runs)
        lat = rpc_latencies(m["graph_rpc_cmd"], vd, dense, small)
        rep = rpc_latencies(m["graph_rpc_cmd"], vd, [kron] * 20, kron)
        if lat:
            res["dense_rpc_ms"] = round(1000 * statistics.median(lat), 3)
        if rep:
            res["dense_repeat_ms"] = round(1000 * statistics.median(rep), 3)
    colds = []
    for _ in range(3 if a.quick else 5):
        if m.get("graph_cmd"):
            rc, dt, out = sh(m["graph_cmd"], str(vd), 60, inp=json.dumps(small))
            colds.append(dt if rc == 0 else None)
        elif gb:
            colds.append(batch_wall(gb, vd, [small], 60)[0])
    if colds and all(c is not None for c in colds):
        res["cold_ms"] = round(1000 * statistics.median(colds), 1)
        res["cold_via"] = "graph single" if m.get("graph_cmd") else "graph-batch, 1 line"
    res["loadavg_after"] = load3()
    return res


def dense_latency(gb, vd, dense, a, work):
    """Scored dense latency, same rules as round 1 (evaluate.measure_latency): graph-batch pinned to ONE cpu
    (taskset), T_1 = one dense request (median of 3), T_N = N dense requests (the distinct-fit dense set cycled; N sized
    for ≈0.5 s, 20..2000), sample = (T_N − T_1)/(N − 1); ≥ --latency-samples samples, median; invalid if ≤ 0, below
    LAT_FLOOR_MS, above T_N/N or wrong response count; spread > LAT_SPREAD_MAX => up to 3 extra samples, then flagged."""
    tmpd = work / ".lat-graphs"; tmpd.mkdir(exist_ok=True)
    lines = [json.dumps(r) + "\n" for r in dense]
    def inp(n):
        f = tmpd / f"dense{n}.jsonl"
        if not f.exists():
            f.write_text("".join(lines[i % len(lines)] for i in range(n)))
        return f
    ncpu = os.cpu_count() or 1
    def one(n, cpu):
        t, k, rc = timed_batch(gb, str(vd), inp(n), max(120, a.timeout / 4), cpu)
        return (t if (t is not None and k == n and rc == 0) else None), k, rc
    t1s = [x for x in (one(1, 0)[0] for _ in range(3)) if x is not None]
    n0 = max(len(lines), 8)
    tp, kp, rcp = one(n0, 0)
    if not t1s or tp is None:
        return {"latency_ms": None, "flags": [f"graph-batch failed (responses {kp}/{n0}, rc {rcp})"], "samples": []}
    t1 = statistics.median(t1s)
    est = (tp - t1) / (n0 - 1) if tp > t1 else tp / n0
    N = int(max(20, min(2000, 0.5 / max(est, 1e-7))))
    samples, flags, k = [], [], 0
    while k < a.latency_samples + 3:
        cpu = (k + 1) % ncpu
        t1k = [x for x in (one(1, cpu)[0] for _ in range(3)) if x is not None]
        tN, got, rc = one(N, cpu)
        smp = {"cpu": cpu, "n": N, "load1": load3()[0]}
        if not t1k or tN is None:
            smp.update(valid=False, why=f"run failed (responses {got}/{N}, rc {rc})")
        else:
            t1m = statistics.median(t1k)
            lat = (tN - t1m) / (N - 1) * 1000; ub = tN / N * 1000
            smp.update(t1_ms=round(t1m * 1000, 2), tN_s=round(tN, 4), ms=lat, upper_ms=ub)
            why = ("non-positive differencing" if lat <= 0 else f"below physical floor {LAT_FLOOR_MS} ms" if lat < LAT_FLOOR_MS
                   else "above upper bound T_N/N" if lat > ub * 1.001 else None)
            smp.update(valid=why is None, **({"why": why} if why else {}))
        samples.append(smp); k += 1
        v = [x["ms"] for x in samples if x.get("valid")]
        if k >= a.latency_samples and len(v) >= 3 and (max(v) - min(v)) / statistics.median(v) <= LAT_SPREAD_MAX:
            break
    v = [x["ms"] for x in samples if x.get("valid")]
    bad = [x for x in samples if not x.get("valid")]
    if bad:
        flags.append(f"{len(bad)} invalid sample(s): " + "; ".join(sorted({x['why'] for x in bad})))
    spread = None
    if v:
        lat = statistics.median(v); spread = (max(v) - min(v)) / lat
        if len(v) < 3: flags.append(f"only {len(v)} valid sample(s)")
        if spread > LAT_SPREAD_MAX: flags.append(f"high spread {spread:.0%} after re-measuring")
        if len(samples) > a.latency_samples: flags.append(f"re-measured ({len(samples)} samples)")
    else:
        ubs = [x["upper_ms"] for x in samples if "upper_ms" in x]
        lat = statistics.median(ubs) if ubs else None
        flags.append("no valid differencing sample: using upper bound T_N/N")
    return {"latency_ms": lat, "min_ms": min(v) if v else None, "max_ms": max(v) if v else None, "spread": spread,
            "valid": len(v), "n_samples": len(samples), "n_per_sample": N, "startup_ms": round(t1 * 1000, 2),
            "dense_requests": len(lines), "pinned_single_cpu": bool(shutil.which("taskset")), "flags": flags, "samples": samples}


def license_round2(g, vd, wt, static):
    """License by actual files at the evaluated commit (evaluate.license_id) + inheritance from the round-1 base."""
    lic = dict(static.get("license") or {})
    base = wt / VARIANTS[g][1] if wt else None
    if base is not None and base.is_dir():
        bl = ev.license_id(base)
        lic["base_dir"], lic["base_license"] = base.name, bl.get("effective")
        if bl.get("mergeable") == "no":
            lic["mergeable"], lic["reason"] = "no", f"derived from {base.name} ({bl.get('effective')}): {bl.get('reason')}"
    if g in DERIVED and lic.get("mergeable") != "no":
        lic["mergeable"], lic["reason"] = "no", DERIVED[g]
    elif g in DERIVED:
        lic["reason"] = f"{DERIVED[g]}; {lic.get('reason', '')}"
    return lic


def empty_x_check(m, vd, cases):
    reqs = []
    for r in cases:
        r2 = json.loads(json.dumps(r))
        r2["x"]["values"] = []
        reqs.append(r2)
    cmd = m.get("graph_batch_cmd")
    if not cmd:
        return None
    rc, dt, out = sh(cmd, str(vd), 300, inp="".join(json.dumps(r) + "\n" for r in reqs))
    ok = 0
    lines = out.splitlines()
    for r, line in zip(reqs, lines):
        try:
            o = json.loads(line)
        except ValueError:
            continue
        if probe_ok(o) and o.get("x") == [] and all(o["series"].get(y) == [] for y in r["y"]):
            ok += 1
    return {"ok": ok, "total": len(reqs)}


def r2_added_loc(wt, vd, base):
    """non-blank, non-comment lines added since the merge-base with the round-1 branch, in hand-written core source
    anywhere on the branch (graph dir and round-1 engine dir; renames are detected, so moved code does not count)"""
    if not base:
        return None
    diff = subprocess.run(["git", "diff", "-U0", "-M", "--no-color", "--no-ext-diff", base, "HEAD"], cwd=wt,
                          capture_output=True, text=True, env=ENV).stdout
    n, by, cur = 0, {}, None
    for line in diff.splitlines():
        if line.startswith("+++ "):
            path = line[4:]
            path = path[2:] if path.startswith("b/") else None
            cur = None
            if path and "/" in path:  # whole branch: round-2 work may also touch the round-1 engine directory
                rel = path.split("/", 1)[1]
                relp = rel.split("/")
                lang = CODE_EXT.get(pathlib.PurePosixPath(rel).suffix)
                fp = wt / path
                if lang and fp.exists() and not any(x in SKIP_DIRS for x in relp[:-1]) and \
                        classify(rel, relp, fp.read_text(errors="replace")[:600]) == "core":
                    cur = (lang, comment_prefix(lang))
            continue
        if cur and line.startswith("+"):
            t = line[1:].strip()
            if t and not t.startswith(cur[1]):
                n += 1
                by[cur[0]] = by.get(cur[0], 0) + 1
    return {"added_core_loc": n, "by_language": by}


# ---------------------------------------------------------------- scoring + output
def score_all(rows):
    ranked = [r for r in rows if r.get("gate") == "pass"]
    best = lambda k: min((r[k] for r in ranked if r.get(k)), default=None)  # noqa: E731
    b_lat, b_cold = best("dense_latency_ms"), best("cold_ms")
    b_inv = min((1 / r["points_per_s"] for r in ranked if r.get("points_per_s")), default=None)
    b_loc = min((r["r2"]["added_core_loc"] for r in ranked if (r.get("r2") or {}).get("added_core_loc")), default=None)
    for r in ranked:
        sp = {"throughput": L(1 / r["points_per_s"] if r.get("points_per_s") else None, b_inv, 100),
              "latency": L(r.get("dense_latency_ms"), b_lat, 100), "cold": L(r.get("cold_ms"), b_cold, 100)}
        t = r["tests"]
        n = t.get("passed") or r["static"]["test_count_static"]
        ts = (0.0 if not t.get("found") else 0.6 + 0.4 * min(1, math.log10(1 + n) / math.log10(101)) if t.get("status") == "passed"
              else 0.2 if t.get("status") == "failed" else 0.3)
        d = r["static"]["docs"]
        mt = {"tests": ts, "size": L((r.get("r2") or {}).get("added_core_loc"), b_loc, 10),
              "docs": 0.4 * d["readme"] + 0.4 * d["design"] + 0.2 * d["license_file"],
              "deps": 1 / (1 + r["static"]["deps"]["n_runtime"] / 5)}
        f = r["features"]
        s = {"speed": sum(SPEED_W[k] * v for k, v in sp.items()), "maint": sum(MAINT_W[k] * mt[k] for k in MAINT_W),
             "feat": f["score"], "port": r["portability"]["score"]}
        r["scores"] = {"speed_parts": sp, "maint_parts": mt, **{k: round(v, 4) for k, v in s.items()},
                       "total": round(sum(W[k] * s[k] for k in W), 4)}
    for i, r in enumerate(sorted(ranked, key=lambda r: -r["scores"]["total"])):
        r["rank"] = i + 1


def features(row):
    ifs = row.get("interfaces", {})
    good = [k for k, v in ifs.items() if v.get("cases_ok") == v.get("cases") and v.get("cases")]
    pref = row.get("primary") or {}
    groups = pref.get("groups") or {}
    graphs_ok = sum(1 for k, g in groups.items() if k in GRAPH_NAMES and g["ok"] == g["total"] and g["total"])
    ex = row.get("empty_x") or {}
    empty = 1.0 if ex and ex["ok"] == ex["total"] else 0.0
    sc = 0.6 * graphs_ok / len(GRAPH_NAMES) + 0.3 * len(good) / 3 + 0.1 * empty
    return {"graphs_fully_correct": graphs_ok, "interfaces_passing": sorted(good), "empty_x": ex, "score": round(sc, 4)}


RULES_MD = """## Scoring rules (round 2)

- **Version rule:** each variant at its branch HEAD (or the last commit at or before `--as-of`); evaluated read-only from detached worktrees, nothing pushed.
- **Gate:** every graph case fully correct through every interface the variant offers, and 326/326 bench-1.8.0 stats cases (round-1 commands of the same branch).
- **Total = 0.40·Speed + 0.35·Maintainability + 0.15·Features + 0.10·Portability**, `L(x, best, span) = clamp(1 − log10(x/best)/log10(span), 0, 1)`.
- **Pins:** graph corpus / expected / run_graphs.py from `0397d95` (contract 0.2, 178 cases); stats gate from bench 1.8.0 `3da9671` (326 cases); recorded in the output.
- **Speed** = 0.4·L(1/points·s⁻¹ batch, start-up excluded) + 0.4·L(dense 500-point damage latency, distinct fits) + 0.2·L(cold start + one request); points/s and cold = medians over runs.
- **Dense latency** (round-1 rules): graph-batch pinned to one CPU, (T_N − T_1)/(N − 1), ≥5 independent samples, median; samples ≤0, <0.002 ms, >T_N/N or with missing responses are invalid; spread >50 % ⇒ re-measure (≤3 extra), then flagged. RPC warm latency is informational.
- **Licensing** (not scored): actual LICENSE files at the evaluated commit + the round-1 base variant's license; G1 (built on GPL variant E) is not mergeable into the LGPL-3.0-or-later mainline.
- **Maintainability** = 0.3·Tests + 0.3·Size (L(round-2 core lines added on the branch since the round-1 merge-base, min, 10)) + 0.2·Docs + 0.2·Deps (round-1 definitions; test runs get `EVE_DOGMA_DATASET` and `EVE_DOGMA_GRAPH_CASES`, skipped tests are not counted as passed).
- **Features** = 0.6·graphs fully correct/(graphs in the corpus) + 0.3·interfaces passing (graph-batch, graph, RPC)/3 + 0.1·empty `x.values` → empty series.
- **Portability** = round-1 heuristic (WASM/browser build in code 1, documented 0.5).
- Commands not declared in `bench.yaml` are inferred (variant's own `score*.sh`, or `batch`→`graph-batch` / RPC `graph` with a probe) and flagged in the table.
"""


def write(rows, a, meta):
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "evaluation-graphs.json").write_text(json.dumps({"meta": meta, "weights": {"total": W, "speed": SPEED_W, "maint": MAINT_W},
                                                         "variants": rows}, indent=1, default=str, ensure_ascii=False))
    f2 = lambda x, f="{:.2f}": "–" if x is None else f.format(x)  # noqa: E731
    dry = "**DRY RUN — not final results.** " if a.dry_run else ""
    md = [f"# Graphs round 2 evaluation{' (DRY RUN)' if a.dry_run else ''}", "",
          f"{dry}Generated {meta['finished']} (Asia/Shanghai) by `tools/evaluate_graphs.py` (`{meta['evaluate_graphs_py_commit'][:7]}`); "
          f"graph contract {meta['graphs_pin']['contract_revision']} pinned @ `{meta['graphs_pin']['sha'][:7]}` ({meta['graphs_pin']['graph_cases']} graph cases), "
          f"stats gate bench {meta['stats_pin']['version']} @ `{meta['stats_pin']['sha'][:7]}` ({meta['stats_pin']['cases']} cases); commits: {meta['as_of']}; runs = {a.runs}{' (quick)' if a.quick else ''}; host {meta['nproc']} CPUs; "
          f"total wall time {meta['wall_s']/60:.1f} min. Perf was measured on a shared, loaded machine: compare with the loadavg column.", "",
          "## Ranking", "",
          "| rank | variant | commit (CST) | graph cases | values | stats 1.8.0 | points/s | dense ms | cold ms | speed | maint | features | port | **total** | load (1m) |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    order = sorted(rows, key=lambda r: (r.get("rank") or 99, r["variant"]))
    for r in order:
        s = r.get("scores", {})
        p = r.get("primary") or {}
        st = r.get("stats") or {}
        lo = "–" if not r.get("loads") else f"{min(r['loads']):.1f}–{max(r['loads']):.1f}"
        sg = f"{st.get('cases_ok')}/{st.get('cases')}" if st.get("cases") else st.get("status", "–")
        md.append(f"| {r.get('rank', '–')} | {r['variant']} {r['label']} | `{(r.get('git') or {}).get('sha', '')[:7]}` {commit_time(r)} | "
                  f"{p.get('cases_ok', '–')}/{p.get('cases', '–')} | {p.get('values_ok', '–')}/{p.get('values_total', '–')} | {sg} | "
                  f"{f2(r.get('points_per_s'), '{:.0f}')} | {f2(r.get('dense_latency_ms'), '{:.2f}')} | {f2(r.get('cold_ms'), '{:.0f}')} | "
                  f"{f2(s.get('speed'))} | {f2(s.get('maint'))} | {f2(s.get('feat'))} | {f2(s.get('port'))} | **{f2(s.get('total'), '{:.3f}')}** | {lo} |")
    cols = GRAPH_NAMES + ["errors"]
    md += ["", f"## Correctness per graph (primary interface; corpus {meta['corpus']['graph_cases']} cases, contract: {meta.get('contract', '')})", "",
           "| variant | interface | " + " | ".join(cols) + " |", "|---|---|" + "---|" * len(cols)]
    for r in order:
        p = r.get("primary") or {}
        gr = p.get("groups") or {}
        md.append(f"| {r['variant']} | {p.get('interface', '–')} | " + " | ".join(
            (f"{gr[g]['ok']}/{gr[g]['total']}" if g in gr else "–") for g in cols) + " |")
    md += ["", "## Interfaces, perf details, maintainability", "",
           "| variant | dir | commands | interfaces (cases ok) | pts/s incl. start-up | dense via | dense repeat ms | cold via | empty x | round-2 core lines added | core LOC (dir) | tests (own suite) | deps | README/DESIGN/LICENSE | portability |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    yn = lambda b: "✓" if b else "✗"  # noqa: E731
    for r in order:
        st = r.get("static") or {}
        ifs = ", ".join(f"{k} {v.get('cases_ok', 'err')}/{v.get('cases', '–')}" for k, v in (r.get("interfaces") or {}).items()) or "–"
        t = r.get("tests") or {}
        ts = ("none found" if not t.get("found") else "found, not run" if t.get("status") == "not run"
              else f"{t['status']} ({t.get('passed', '?')}✓/{t.get('failed', '?')}✗, {t.get('runner')}, {t.get('seconds')} s)") if t else "–"
        d = st.get("docs") or {}
        r2 = r.get("r2") or {}
        ex = r.get("empty_x") or {}
        md.append(f"| {r['variant']} | {r.get('dir', '–')} | {'; '.join(r.get('cmd_notes') or ['bench.yaml'])} | {ifs} | "
                  f"{f2(r.get('points_per_s_raw'), '{:.0f}')} | {r.get('dense_latency_via', '–')} | {f2(r.get('dense_repeat_ms'), '{:.2f}')} | "
                  f"{r.get('cold_via', '–')} | {ex.get('ok', '–')}/{ex.get('total', '–')} | {r2.get('added_core_loc', '–')} "
                  f"({', '.join(f'{k} {v}' for k, v in sorted((r2.get('by_language') or {}).items(), key=lambda kv: -kv[1]))}) | "
                  f"{st.get('core_loc', '–')} | {ts} | {(st.get('deps') or {}).get('n_runtime', '–')} | "
                  f"{yn(d.get('readme'))}{yn(d.get('design'))}{yn(d.get('license_file'))} | {(r.get('portability') or {}).get('level', '–')} |")
    md += ["", "## Licensing (mainline eve-dogma-rs is LGPL-3.0-or-later)", "",
           "| variant | license (files) | round-1 base | base license | mergeable into LGPL-3.0-or-later mainline | reason |", "|---|---|---|---|---|---|"]
    for r in order:
        li = (r.get("static") or {}).get("license")
        if li:
            md.append(f"| {r['variant']} | {li.get('effective') or 'none'} ({'; '.join(li.get('files') or []) or '–'}) | {li.get('base_dir', '–')} | "
                      f"{li.get('base_license') or '–'} | **{li.get('mergeable')}** | {li.get('reason')} |")
    md += ["", "## Dense latency measurement (single CPU, same rules as round 1)", "",
           "| variant | ms/request (median) | min | max | spread | valid/samples | N per sample | startup ms | RPC warm ms (info) | flags |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    for r in order:
        la = r.get("latency")
        if la:
            md.append(f"| {r['variant']} | {f2(la.get('latency_ms'), '{:.3f}')} | {f2(la.get('min_ms'), '{:.3f}')} | {f2(la.get('max_ms'), '{:.3f}')} | "
                      f"{f2(la['spread'] * 100 if la.get('spread') is not None else None, '{:.0f}%')} | {la.get('valid', '–')}/{la.get('n_samples', '–')} | "
                      f"{la.get('n_per_sample', '–')} | {la.get('startup_ms', '–')} | {f2(r.get('dense_rpc_ms'), '{:.3f}')} | "
                      f"{'; '.join((la.get('flags') or []) + (r.get('perf_flags') or [])) or 'ok'} |")
    notes = [f"- **{r['variant']}**: {r.get('gate_reason', '')}" for r in order if r.get("gate") != "pass"]
    notes += [f"- {r['variant']} tests {r['tests']['status']}: `{r['tests'].get('tail', '')[-200:].strip()}`".replace("\n", " ")
              for r in order if (r.get("tests") or {}).get("status") in ("failed", "timeout")]
    if notes:
        md += ["", "## Not ranked / problems", ""] + notes
    md += ["", "## Per-run measurements", "", "| variant | run | corpus wall s | 1-request wall s | points/s | dense RPC ms (info) | dense repeat ms | cold ms | loadavg before | loadavg after |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    for r in order:
        for x in r.get("runs", []):
            md.append(f"| {r['variant']} | {x['run']} | {x.get('corpus_wall_s', '–')} | {x.get('one_wall_s', '–')} | {f2(x.get('points_per_s'), '{:.0f}')} | "
                      f"{f2(x.get('dense_rpc_ms'), '{:.2f}')} | {f2(x.get('dense_repeat_ms'), '{:.2f}')} | {f2(x.get('cold_ms'), '{:.0f}')} | "
                      f"{x['loadavg_before']} | {x['loadavg_after']} |")
    md += ["", RULES_MD, "## Reproduce", "", f"```\n{meta['command']}\n```", ""]
    (a.out / "evaluation-graphs.md").write_text("\n".join(md) + "\n")
    return "\n".join(md)


GRAPH_NAMES = []  # filled from graphs/expected at start-up (contract 0.1: 9 graphs, 0.2: + ecm_burst)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--only", help="comma-separated, e.g. G1,G3")
    ap.add_argument("--quick", action="store_true", help="fewer dense requests / cold repetitions; single-mode scoring skipped")
    ap.add_argument("--dry-run", action="store_true", help="label output DRY RUN; default --out results/graphs-eval-dryrun")
    ap.add_argument("--out")
    ap.add_argument("--work-dir", default=str(ROOT / "work" / "graphs-eval"))
    ap.add_argument("--as-of", help="ISO-8601 cutoff with UTC offset (default: current branch heads)")
    ap.add_argument("--no-fetch", action="store_true")
    ap.add_argument("--no-build", action="store_true")
    ap.add_argument("--no-tests", action="store_true")
    ap.add_argument("--no-stats-gate", action="store_true")
    ap.add_argument("--build-timeout", type=float, default=900)
    ap.add_argument("--test-timeout", type=float, default=600)
    ap.add_argument("--timeout", type=float, default=900, help="per scorer run")
    ap.add_argument("--graphs-ref", default=GRAPHS_PIN, help="commit for graphs/ corpus + run_graphs.py (default: contract 0.2 pin)")
    ap.add_argument("--stats-ref", default=STATS_PIN, help="bench commit for the stats gate (default: 1.8.0 pin)")
    ap.add_argument("--latency-samples", type=int, default=5)
    a = ap.parse_args()
    a.out = (pathlib.Path(a.out) if a.out else ROOT / "results" / ("dryrun" if a.dry_run else "")).resolve()
    work = pathlib.Path(a.work_dir).resolve()
    work.mkdir(parents=True, exist_ok=True)
    import datetime
    if a.as_of and datetime.datetime.fromisoformat(a.as_of).tzinfo is None:
        ap.error("--as-of needs an explicit UTC offset, e.g. 2026-10-03T10:15:00+08:00")
    as_of = datetime.datetime.fromisoformat(a.as_of).timestamp() if a.as_of else None
    tag = time.strftime("%H%M%S")
    t_start = time.time()
    global GROOT, SROOT
    GROOT, gpin = pin_bench(work, a.graphs_ref)
    SROOT, spin = pin_bench(work, a.stats_ref)
    hdr = (GROOT / "graphs/CONTRACT-GRAPHS.md").read_text().split("\n", 1)[0]
    gpin["contract_revision"] = (re.search(r"revision ([0-9.]+)", hdr) or [None, "?"])[1]
    gpin["graph_cases"] = len(list((GROOT / "graphs/cases").glob("*.json")))
    if a.graphs_ref == GRAPHS_PIN and gpin["contract_revision"] != GRAPHS_PIN_REVISION:
        sys.exit(f"graphs pin mismatch: contract revision {gpin['contract_revision']} at {a.graphs_ref}")
    log(f"graphs pinned: {gpin}; stats pinned: {spin}")
    bench_sha = gpin["sha"]
    meta = {"started": time.strftime("%Y-%m-%d %H:%M:%S %Z"), "bench_sha": bench_sha, "graphs_pin": gpin, "stats_pin": spin,
            "evaluate_graphs_py_commit": git(ROOT, "rev-parse", "HEAD", check=False), "nproc": os.cpu_count(),
            "command": " ".join(["python3", "tools/evaluate_graphs.py"] + sys.argv[1:]), "dry_run": a.dry_run,
            "as_of": a.as_of or "current heads", "host_loadavg_start": load3()}
    ds = json.load(gzip.open(DATASET))
    names = {e["name"] for e in ds["effects"].values() if re.search(r"[A-Z]", e["name"]) and len(e["name"]) >= 8}
    n_mod = sum(1 for e in ds["effects"].values() if e.get("mods"))
    del ds
    cases = corpus()
    GRAPH_NAMES[:] = corpus_graphs()
    meta["contract"] = next((l.strip() for l in (GROOT / "graphs/CONTRACT-GRAPHS.md").read_text().splitlines()
                             if "revision" in l.lower() or l.lower().startswith("status")), "")
    meta["corpus"] = {"graph_cases": len(list((GROOT / "graphs/cases").glob("*.json"))), "perf_cases": len(cases),
                      "graphs": list(GRAPH_NAMES)}
    rows = []
    for g in (a.only.upper().split(",") if a.only else list(VARIANTS)):
        log(f"== {g}")
        row = {"variant": g, "label": VARIANTS[g][2], "gate": "fail"}
        rows.append(row)
        try:
            wt, info = fetch(g, work, a.no_fetch, as_of)
        except Exception as e:  # noqa: BLE001
            wt, info = None, {"error": repr(e)[:300]}
        row["git"] = info
        if wt is None:
            row["gate_reason"] = f"unavailable: {info.get('error', '')}"
            continue
        vd, y, src = variant_dir(wt, g)
        if vd is None:
            row["gate_reason"] = "no variant directory"
            continue
        row["dir"] = vd.name
        probe = next(r for r in cases if r["graph"] == "damage")
        m, notes = resolve(vd, y, src, probe, built=False)
        if m.get("build") and not a.no_build:
            rc, dt, out = sh(m["build"], str(vd), a.build_timeout)
            row["build_s"] = round(dt, 1)
            log(f"{g} build rc={rc} {dt:.1f}s")
            if rc != 0:
                row["gate_reason"] = f"build failed ({'timeout' if rc is None else rc}): {out[-300:]}"
                row["static"] = static_metrics(g, vd, names, n_mod)
                continue
        m, notes = resolve(vd, y, src, probe, built=True)
        row["cmd_notes"] = notes or ["bench.yaml"]
        row["manifest"] = {k: v for k, v in m.items() if k.startswith(("graph", "build", "cmd", "batch", "rpc"))}
        # correctness over every interface
        ifs = {}
        for kind, key in (("batch", "graph_batch_cmd"), ("rpc", "graph_rpc_cmd"), ("single", "graph_cmd")):
            if m.get(key) and not (kind == "single" and a.quick and ifs):
                ifs[kind] = score_interface(kind, m[key], vd, f"eval-{g}-{kind}-{tag}", a.out, a.timeout)
                log(f"{g} {kind}: {ifs[kind].get('cases_ok')}/{ifs[kind].get('cases')} {ifs[kind].get('error', '')[:200]}")
        row["interfaces"] = ifs
        if not ifs:
            row["gate_reason"] = "no graph interface (graph_batch_cmd / graph_cmd / RPC graph) found"
        else:
            row["primary"] = next(ifs[k] for k in ("batch", "rpc", "single") if k in ifs)
        # stats gate (round-1 commands)
        if a.no_stats_gate:
            row["stats"] = {"status": "skipped"}
        else:
            sm, sd = stats_cmds(vd, m, wt)
            if sm and sd != vd and sm.get("build") and not a.no_build:
                sh(sm["build"], str(sd), a.build_timeout)
            row["stats"] = stats_gate(sm, sd, f"_graphs-eval/{g}-stats-{tag}", a)
            log(f"{g} stats: {row['stats']}")
        # perf
        runs = []
        if ifs:
            for i in range(1, a.runs + 1):
                x = perf_run(m, vd, cases, a)
                x["run"] = i
                runs.append(x)
                log(f"{g} run{i}: pts/s={x.get('points_per_s')} dense={x.get('dense_latency_ms')} cold={x.get('cold_ms')} load={x['loadavg_before'][0]}")
        row["runs"] = runs
        row["loads"] = [x["loadavg_before"][0] for x in runs] + [x["loadavg_after"][0] for x in runs]
        for k in ("points_per_s", "points_per_s_raw", "dense_rpc_ms", "dense_repeat_ms", "cold_ms"):
            row[k] = med([x.get(k) for x in runs])
        row["cold_via"] = next((x["cold_via"] for x in runs if x.get("cold_via")), None)
        row["perf_flags"] = sorted({x["flag"] for x in runs if x.get("flag")})
        if ifs and m.get("graph_batch_cmd"):
            row["latency"] = dense_latency(m["graph_batch_cmd"], vd, dense_requests(cases), a, work)
            row["dense_latency_ms"] = row["latency"]["latency_ms"]; row["dense_latency_via"] = "graph-batch, 1 cpu, differencing"
        elif row.get("dense_rpc_ms"):
            row["dense_latency_ms"] = row["dense_rpc_ms"]; row["dense_latency_via"] = "rpc (no graph-batch; not pinned)"
            row["latency"] = {"latency_ms": row["dense_rpc_ms"], "flags": ["no graph_batch_cmd: RPC warm-process median, not pinned"]}
        log(f"{g} dense latency {row.get('dense_latency_ms')} ms flags={(row.get('latency') or {}).get('flags')}")
        row["empty_x"] = empty_x_check(m, vd, cases) if ifs else None
        row["features"] = features(row)
        row["static"] = static_metrics(g, vd, names, n_mod)
        row["static"]["license"] = license_round2(g, vd, wt, row["static"])
        row["r2"] = r2_added_loc(wt, vd, info.get("merge_base"))
        row["portability"] = portability(vd)
        row["tests"] = {"found": test_command(m, vd)[0] is not None, "status": "not run"} if a.no_tests else run_tests(m, vd, a.test_timeout)
        # gate
        p = row.get("primary") or {}
        bad_if = [k for k, v in ifs.items() if v.get("cases_ok") != v.get("cases")]
        st = row["stats"]
        if not ifs:
            pass
        elif bad_if:
            row["gate_reason"] = f"graph corpus not fully correct via {', '.join(bad_if)}: " + "; ".join(
                f"{k} {ifs[k].get('cases_ok', 'error')}/{ifs[k].get('cases', '–')} {ifs[k].get('error', '')[:120]}" for k in bad_if)
        elif st.get("status") not in ("pass", "skipped"):
            row["gate_reason"] = f"stats gate: {st.get('status')} {st.get('cases_ok', '')}/{st.get('cases', '')} {st.get('detail', '')[:200]}"
        else:
            row["gate"] = "pass"
        log(f"{g} gate={row['gate']} {row.get('gate_reason', '')[:200]}")
    score_all(rows)
    meta.update(finished=time.strftime("%Y-%m-%d %H:%M:%S %Z"), wall_s=round(time.time() - t_start, 1), host_loadavg_end=load3())
    print(write(rows, a, meta))


if __name__ == "__main__":
    main()
