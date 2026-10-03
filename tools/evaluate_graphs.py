#!/usr/bin/env python3
"""Round-2 (graphs) evaluation for the EX-CT graph bake-off (variants G1–G4): reproducible, one command.
Structured like tools/evaluate.py (round 1, branch main); bench round 2 = branch graphs-round2.

  python3 tools/evaluate_graphs.py [--runs 3] [--only G1,G3] [--quick] [--dry-run] [--out results/graphs-eval]
                                   [--as-of 2026-10-03T10:15:00+08:00] [--work-dir work/graphs-eval]
                                   [--no-fetch] [--no-build] [--no-tests] [--no-stats-gate]

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
                        points / (wall(corpus) − wall(1 small request)); raw points/s incl. start-up also shown;
             latency    dense interactive request: every distance-axis damage case re-sampled at 500 points, one
                        request at a time through RPC `graph` in a warm process (distinct fits => includes the fit
                        calculation); median ms. Fallback without RPC: batch wall difference / n.
                        Also reported: the same Kronos request repeated (warm fit), informational.
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
  Features = 0.6·(graphs with all cases correct / 9) + 0.3·(interfaces offered of batch/single/rpc, each passing
        the corpus) + 0.1·(empty x.values -> empty series, contract ruling 2026-10-03)
  Portability = round-1 heuristic (1 WASM/browser build in code, 0.5 documented, 0 none).
Outputs: <out>/evaluation.md, <out>/evaluation.json (+ <out>/raw/<G>/ scorecards and logs)."""
import argparse, gzip, json, math, os, pathlib, re, shutil, signal, statistics, subprocess, sys, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
DATASET = os.environ.get("EVE_DOGMA_DATASET", "/workspace/exct-eve/data/dataset-3569502.json.gz")
LAB = "https://github.com/EX-CT/eve-dogma-lab"
VARIANTS = {"G1": ("graphs-g1", "variant-e", "Pyfa-faithful graph port (Rust, on E)"),
            "G2": ("graphs-g2", "variant-c", "engine primitives + TS evaluator (on C)"),
            "G3": ("graphs-g3", "variant-g", "vectorised NumPy grid + fit cache (on G)"),
            "G4": ("graphs-g4", "variant-f", "declarative graph specs (Rust, on F)")}
W = dict(speed=0.40, maint=0.35, feat=0.15, port=0.10)
SPEED_W = dict(throughput=0.4, latency=0.4, cold=0.2)
MAINT_W = dict(tests=0.30, size=0.30, docs=0.20, deps=0.20)
N_GRAPHS = 9

ENV = dict(os.environ)
_dn = pathlib.Path.home() / ".dotnet"
if _dn.exists():
    ENV["PATH"] = f"{_dn}:{ENV['PATH']}"; ENV.setdefault("DOTNET_ROOT", str(_dn))
ENV.update(DOTNET_CLI_TELEMETRY_OPTOUT="1", DOTNET_NOLOGO="1")


def log(*a):
    print(time.strftime("[%H:%M:%S]"), *a, flush=True)


def sh(cmd, cwd, timeout, env=None, inp=None):
    """Run in its own process group; kill the whole group on timeout. -> (rc|None, seconds, output tail)."""
    t0 = time.time()
    p = subprocess.Popen(cmd, shell=True, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         stdin=subprocess.PIPE if inp is not None else subprocess.DEVNULL, text=True,
                         start_new_session=True, env=env or ENV)
    try:
        out, _ = p.communicate(inp, timeout=timeout)
        return p.returncode, time.time() - t0, out
    except subprocess.TimeoutExpired:
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        out = p.communicate()[0] or ""
        return None, time.time() - t0, out + f"\n[timeout after {timeout}s]"


def load3():
    return [round(x, 2) for x in os.getloadavg()]


def L(x, best, span):
    if x is None or best is None or x <= 0 or best <= 0:
        return 0.0
    return max(0.0, min(1.0, 1 - math.log10(x / best) / math.log10(span)))



# ---------------------------------------------------------------- static maintainability metrics
CODE_EXT = {".rs": "Rust", ".go": "Go", ".ts": "TypeScript", ".tsx": "TypeScript", ".js": "JavaScript", ".mjs": "JavaScript",
            ".cjs": "JavaScript", ".py": "Python", ".cpp": "C++", ".cc": "C++", ".cxx": "C++", ".hpp": "C++", ".h": "C/C++ header",
            ".cs": "C#", ".kt": "Kotlin", ".java": "Java", ".sh": "Shell", ".cmake": "CMake"}
SKIP_DIRS = {"target", "build", "node_modules", "bin", "obj", "dist", "dist-cli", ".git", ".cache", "__pycache__", "results",
             "bench-results", "scorecards", "out", ".venv"}
VENDOR_DIRS = {"vendor", "third_party", "third-party", "external", "deps"}
TOOL_DIRS = {"tools", "oracle", "bench", "scripts", "examples", "benches", "fixtures", "web"}
TEST_RE = re.compile(r"(^|/)(tests?|testdata|__tests__|spec)(/|$)|_test\.go$|(^|/)test_[^/]*\.py$|_test\.py$|\.test\.[jt]s$|\.spec\.[jt]s$|Tests?\.cs$|Tests?/|_test\.(cpp|cc)$")
TEST_PAT = {"Rust": r"#\[test\]", "Go": r"^func Test\w*\(", "TypeScript": r"^\s*(?:it|test)\(", "JavaScript": r"^\s*(?:it|test)\(",
            "Python": r"^\s*def test_\w*\(", "C++": r"\b(?:TEST|TEST_F|TEST_CASE|SCENARIO)\(", "C#": r"\[(?:Fact|Theory|Test|TestMethod)\b"}


def comment_prefix(lang):
    return ("#",) if lang in ("Python", "Shell", "CMake") else ("//", "/*", "*", "*/")


def walk(vd):
    for p in sorted(vd.rglob("*")):
        rel = p.relative_to(vd).as_posix()
        parts = rel.split("/")
        if any(x in SKIP_DIRS or (x.startswith(".") and x not in (".",)) for x in parts[:-1]):
            continue
        if p.is_file():
            yield p, rel, parts


def classify(rel, parts, head):
    if any(x in VENDOR_DIRS for x in parts[:-1]):
        return "vendored"
    if "generated" in rel or re.search(r"@generated|DO NOT EDIT|auto-?generated|generated by", head, re.I):
        return "generated"
    if TEST_RE.search(rel):
        return "test"
    if parts[0] in TOOL_DIRS or (len(parts) == 1 and parts[0].endswith(".py") and not parts[0].startswith("eve")):
        return "tooling"
    return "core"


def static_metrics(letter, vd, effect_names, n_mod_effects):
    loc, tests_static, core_text = {}, 0, []
    gen_loc = vend_loc = 0
    for p, rel, parts in walk(vd):
        lang = "CMake" if p.name == "CMakeLists.txt" else CODE_EXT.get(p.suffix)
        if not lang:
            continue
        try:
            txt = p.read_text(errors="replace")
        except OSError:
            continue
        if len(txt) > 3_000_000:  # data blobs masquerading as code
            continue
        kind = classify(rel, parts, txt[:600])
        cp = comment_prefix(lang)
        n = sum(1 for l in txt.splitlines() if l.strip() and not l.strip().startswith(cp))
        e = loc.setdefault(kind, {}); e[lang] = e.get(lang, 0) + n
        if lang in TEST_PAT:
            tests_static += len(re.findall(TEST_PAT[lang], txt, re.M))
        if kind == "core":
            core_text.append(txt)
    core = sum(loc.get("core", {}).values())
    blob = "\n".join(core_text)
    words = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]{7,}", blob))
    hard = sorted(n for n in effect_names if n in words)
    # docs / license
    docs_dir = vd / "docs"
    design = (vd / "DESIGN.md").exists() or any(docs_dir.glob("design*")) or any(docs_dir.glob("architecture*")) if docs_dir.exists() else (vd / "DESIGN.md").exists()
    lic_files = sorted(x.name for x in vd.glob("LICENSE*")) + sorted(x.name for x in vd.glob("COPYING*"))
    lic = license_id(vd, lic_files)
    return {"loc": loc, "core_loc": core, "test_count_static": tests_static,
            "hardcoded_effects": len(hard), "hardcoded_effect_names_sample": hard[:40],
            "data_driven_ratio": round(1 - len(hard) / n_mod_effects, 4),
            "docs": {"readme": (vd / "README.md").exists(), "design": bool(design), "license_file": bool(lic_files)},
            "license": lic, "deps": deps(vd), "loc_tool": "builtin"}


def license_id(vd, files):
    ids = []
    for f in files:
        t = (vd / f).read_text(errors="replace")[:3000]
        if "GNU LESSER GENERAL PUBLIC" in t: ids.append("LGPL-3.0")
        elif "GNU GENERAL PUBLIC LICENSE" in t: ids.append("GPL-3.0")
        elif "Permission is hereby granted" in t: ids.append("MIT")
        elif "Apache License" in t: ids.append("Apache-2.0")
        else: ids.append(f"{f}?")
    decl = []
    for mf, pat in (("Cargo.toml", r'^license\s*=\s*"([^"]+)"'), ("package.json", r'"license"\s*:\s*"([^"]+)"')):
        if (vd / mf).exists():
            decl += re.findall(pat, (vd / mf).read_text(), re.M)
    for x in vd.rglob("*.csproj"):
        decl += re.findall(r"<PackageLicenseExpression>([^<]+)<", x.read_text())
    return {"files": files, "detected": sorted(set(ids)), "declared": sorted(set(decl))}


def deps(vd):
    out = {"runtime": [], "dev": [], "build": []}
    ct = vd / "Cargo.toml"
    if ct.exists():
        import tomllib
        t = tomllib.loads(ct.read_text())
        out["runtime"] += list(t.get("dependencies", {}))
        for tv in t.get("target", {}).values():
            out["runtime"] += list(tv.get("dependencies", {}))
        out["dev"] += list(t.get("dev-dependencies", {})); out["build"] += list(t.get("build-dependencies", {}))
    gm = vd / "go.mod"
    if gm.exists():
        txt = gm.read_text()
        blk = re.findall(r"require\s*\((.*?)\)", txt, re.S)
        lines = [l for b in blk for l in b.splitlines()] + re.findall(r"^require\s+(\S+\s+\S+.*)$", txt, re.M)
        out["runtime"] += [l.split()[0] for l in lines if l.strip() and "// indirect" not in l]
    pj = vd / "package.json"
    if pj.exists():
        j = json.loads(pj.read_text())
        out["runtime"] += list(j.get("dependencies", {})); out["dev"] += list(j.get("devDependencies", {}))
    for x in vd.rglob("*.csproj"):
        if any(s in x.parts for s in SKIP_DIRS):
            continue
        out["runtime"] += re.findall(r'<PackageReference\s+Include="([^"]+)"', x.read_text())
    cm = vd / "CMakeLists.txt"
    if cm.exists():
        txt = cm.read_text()
        fp = [n for n in re.findall(r"find_package\(\s*(\w+)", txt) if n not in ("Threads",)]
        fc = re.findall(r"FetchContent_Declare\(\s*(\w+)", txt) + re.findall(r"ExternalProject_Add\(\s*(\w+)", txt)
        out["runtime"] += sorted(set(fp + fc))
        for vdir in VENDOR_DIRS:
            if (vd / vdir).is_dir():
                out["runtime"] += [f"{vdir}/{x.name}" for x in (vd / vdir).iterdir() if x.is_dir() and x.name.lower() not in {n.lower() for n in fp + fc}]
    if not any(out.values()) and any(vd.rglob("*.py")):
        std = set(sys.stdlib_module_names)
        own = {p.name for p in vd.iterdir() if p.is_dir()} | {p.stem for p in vd.glob("*.py")}
        imps = set()
        for p, rel, parts in walk(vd):
            if p.suffix == ".py" and classify(rel, parts, "") == "core":
                imps |= set(re.findall(r"^\s*(?:import|from)\s+([A-Za-z_]\w*)", p.read_text(errors="replace"), re.M))
        out["runtime"] += sorted(i for i in imps if i not in std and i not in own and i != "__future__")
    if (vd / "vendor").is_dir() and ct.exists():
        out["vendored"] = sorted(x.name for x in (vd / "vendor").iterdir())
    out = {k: sorted(set(v)) for k, v in out.items()}
    out["n_runtime"] = len(out["runtime"])
    return out


# ---------------------------------------------------------------- own test suites
def test_command(m, vd):
    if m.get("test"):
        return m["test"], "manifest"
    if (vd / "Cargo.toml").exists():
        return "cargo test --release 2>&1", "cargo"
    if (vd / "go.mod").exists():
        return "go test -v ./... 2>&1", "go"
    if (vd / "package.json").exists() and "test" in json.loads((vd / "package.json").read_text()).get("scripts", {}):
        return "npm test --silent 2>&1", "npm"
    if (vd / "CMakeLists.txt").exists() and "add_test" in (vd / "CMakeLists.txt").read_text():
        return "ctest --test-dir build --output-on-failure 2>&1", "ctest"
    tp = [x for x in vd.rglob("*.csproj") if re.search(r"test", x.name, re.I) and not any(s in x.parts for s in SKIP_DIRS)]
    if tp:
        return f"dotnet test {tp[0].relative_to(vd)} --nologo 2>&1", "dotnet"
    for scr in ("tests/run_tests.py", "tests/run.py", "test/run_tests.py"):
        if (vd / scr).exists():
            return f"{sys.executable} {scr} 2>&1", "script"
    if (vd / "tests").is_dir() and any((vd / "tests").glob("test*.py")):
        try:
            import pytest  # noqa: F401
            return f"{sys.executable} -m pytest -q tests 2>&1", "pytest"
        except ImportError:
            return f"{sys.executable} -m unittest discover -s tests -v 2>&1", "unittest"
    return None, None


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
            f = sum(int(x or 0) for x in fm.groups()) if fm else 0; p = n - f
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
    cmd = cmd.format(dataset=DATASET, bench=ROOT, dir=vd)
    env = dict(ENV, EVE_DOGMA_DATASET=DATASET)
    rc, dt, out = sh(cmd, str(vd), timeout, env=env)
    p, f = parse_tests(kind, out or "")
    st = "timeout" if rc is None else ("passed" if rc == 0 and not f else "failed")
    return {"found": True, "cmd": cmd, "runner": kind, "status": st, "rc": rc, "passed": p, "failed": f,
            "seconds": round(dt, 1), "tail": (out or "")[-600:] if st != "passed" else ""}


# ---------------------------------------------------------------- portability heuristic
WASM_CODE = re.compile(r"wasm-bindgen|wasm_bindgen|wasm32|emscripten|EMSCRIPTEN|emcmake|pyodide|DecompressionStream|tsconfig\.browser|wasm-pack|<script type=\"module\"")
WASM_DOC = re.compile(r"\bWASM\b|WebAssembly|\bbrowser\b|浏览器", re.I)


def portability(vd):
    ev = []
    for p, rel, parts in walk(vd):
        if p.suffix in (".md",) or p.stat().st_size > 2_000_000:
            continue
        if p.suffix in CODE_EXT or p.name in ("Cargo.toml", "package.json", "CMakeLists.txt", "go.mod") or p.suffix in (".json", ".toml", ".html", ".csproj", ".yaml", ".yml"):
            try:
                t = p.read_text(errors="replace")
            except OSError:
                continue
            for mt in set(WASM_CODE.findall(t)):
                ev.append(f"{rel}: {mt}")
    if ev:
        return {"score": 1.0, "level": "code", "evidence": sorted(set(ev))[:12]}
    docs = " ".join((vd / f).read_text(errors="replace") for f in ("README.md", "DESIGN.md") if (vd / f).exists())
    if WASM_DOC.search(docs):
        return {"score": 0.5, "level": "docs-only", "evidence": sorted(set(WASM_DOC.findall(docs)))[:5]}
    return {"score": 0.0, "level": "none", "evidence": []}




def log(*a):
    print(time.strftime("[%H:%M:%S]"), *a, flush=True)


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


def load3():
    return [round(x, 2) for x in os.getloadavg()]


def L(x, best, span):
    if x is None or best is None or x <= 0 or best <= 0:
        return 0.0
    return max(0.0, min(1.0, 1 - math.log10(x / best) / math.log10(span)))


def med(xs):
    xs = [x for x in xs if x is not None]
    return statistics.median(xs) if xs else None


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
    return {k: (v.format(dataset=DATASET, bench=ROOT) if isinstance(v, str) else v) for k, v in m.items()}


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
    return [json.loads(p.read_text()) for p in sorted((ROOT / "graphs/cases").glob("*.json"))]


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
                      f"--timeout {timeout}", str(ROOT), timeout + 60)
    card = ROOT / "results" / f"graphs-{name}" / "scorecard.json"
    if rc != 0 or not card.exists():
        return {"interface": kind, "error": f"exit {rc}: {log_[-400:]}"}
    c = json.loads(card.read_text())
    dst = out / "raw" / name.split("-")[1] / kind
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
    rc, dt, out = sh(f"{q(sys.executable)} run.py {args}", str(ROOT), 1800)
    card = ROOT / "results" / name / "scorecard.json"
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
                res["points_per_s"] = round(pts / max(w_all - w_one, 1e-3), 1)
    dense = dense_requests(cases)
    if a.quick:
        dense = dense[:8]
    kron = next((r for r in dense if "kronos" in json.dumps(r["fit"]).lower()), dense[0])
    if m.get("graph_rpc_cmd"):
        lat = rpc_latencies(m["graph_rpc_cmd"], vd, dense, small)
        rep = rpc_latencies(m["graph_rpc_cmd"], vd, [kron] * 20, kron)
        if lat:
            res["dense_latency_ms"] = round(1000 * statistics.median(lat), 3)
            res["dense_latency_via"] = "rpc"
        if rep:
            res["dense_repeat_ms"] = round(1000 * statistics.median(rep), 3)
    elif gb:
        w0, _ = batch_wall(gb, vd, [small])
        w1, _ = batch_wall(gb, vd, [small] + dense)
        if w0 and w1:
            res["dense_latency_ms"] = round(1000 * max(w1 - w0, 1e-6) / len(dense), 3)
            res["dense_latency_via"] = "batch difference"
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
    graphs_ok = sum(1 for g in (pref.get("groups") or {}).values() if g["ok"] == g["total"] and g["total"])
    ex = row.get("empty_x") or {}
    empty = 1.0 if ex and ex["ok"] == ex["total"] else 0.0
    sc = 0.6 * graphs_ok / N_GRAPHS + 0.3 * len(good) / 3 + 0.1 * empty
    return {"graphs_fully_correct": graphs_ok, "interfaces_passing": sorted(good), "empty_x": ex, "score": round(sc, 4)}


def commit_time(r):
    g = r.get("git") or {}
    if not g.get("commit_time"):
        return ""
    import datetime
    t = datetime.datetime.fromisoformat(g["commit_time"]).astimezone(datetime.timezone(datetime.timedelta(hours=8)))
    return t.strftime("%m-%d %H:%M") + ("" if g.get("is_branch_head", True) else " (not head)")


RULES_MD = """## Scoring rules (round 2)

- **Version rule:** each variant at its branch HEAD (or the last commit at or before `--as-of`); evaluated read-only from detached worktrees, nothing pushed.
- **Gate:** every graph case fully correct through every interface the variant offers, and 326/326 bench-1.8.0 stats cases (round-1 commands of the same branch).
- **Total = 0.40·Speed + 0.35·Maintainability + 0.15·Features + 0.10·Portability**, `L(x, best, span) = clamp(1 − log10(x/best)/log10(span), 0, 1)`.
- **Speed** = 0.4·L(1/points·s⁻¹ batch, start-up excluded) + 0.4·L(dense 500-point damage latency, distinct fits) + 0.2·L(cold start + one request); medians over runs.
- **Maintainability** = 0.3·Tests + 0.3·Size (L(round-2 core lines added on the branch since the round-1 merge-base, min, 10)) + 0.2·Docs + 0.2·Deps (round-1 definitions).
- **Features** = 0.6·graphs fully correct/9 + 0.3·interfaces passing (graph-batch, graph, RPC)/3 + 0.1·empty `x.values` → empty series.
- **Portability** = round-1 heuristic (WASM/browser build in code 1, documented 0.5).
- Commands not declared in `bench.yaml` are inferred (variant's own `score*.sh`, or `batch`→`graph-batch` / RPC `graph` with a probe) and flagged in the table.
"""


def write(rows, a, meta):
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "evaluation.json").write_text(json.dumps({"meta": meta, "weights": {"total": W, "speed": SPEED_W, "maint": MAINT_W},
                                                         "variants": rows}, indent=1, default=str, ensure_ascii=False))
    f2 = lambda x, f="{:.2f}": "–" if x is None else f.format(x)  # noqa: E731
    dry = "**DRY RUN — not final results.** " if a.dry_run else ""
    md = [f"# Graphs round 2 evaluation{' (DRY RUN)' if a.dry_run else ''}", "",
          f"{dry}Generated {meta['finished']} (Asia/Shanghai) by `tools/evaluate_graphs.py` at bench graphs-round2 "
          f"`{meta['bench_sha'][:7]}`; commits: {meta['as_of']}; runs = {a.runs}{' (quick)' if a.quick else ''}; host {meta['nproc']} CPUs; "
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
    md += ["", "## Correctness per graph (primary interface)", "",
           "| variant | interface | " + " | ".join(GRAPH_NAMES) + " |", "|---|---|" + "---|" * len(GRAPH_NAMES)]
    for r in order:
        p = r.get("primary") or {}
        gr = p.get("groups") or {}
        md.append(f"| {r['variant']} | {p.get('interface', '–')} | " + " | ".join(
            (f"{gr[g]['ok']}/{gr[g]['total']}" if g in gr else "–") for g in GRAPH_NAMES) + " |")
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
    notes = [f"- **{r['variant']}**: {r.get('gate_reason', '')}" for r in order if r.get("gate") != "pass"]
    notes += [f"- {r['variant']} tests {r['tests']['status']}: `{r['tests'].get('tail', '')[-200:].strip()}`".replace("\n", " ")
              for r in order if (r.get("tests") or {}).get("status") in ("failed", "timeout")]
    if notes:
        md += ["", "## Not ranked / problems", ""] + notes
    md += ["", "## Per-run measurements", "", "| variant | run | corpus wall s | 1-request wall s | points/s | dense ms | dense repeat ms | cold ms | loadavg before | loadavg after |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    for r in order:
        for x in r.get("runs", []):
            md.append(f"| {r['variant']} | {x['run']} | {x.get('corpus_wall_s', '–')} | {x.get('one_wall_s', '–')} | {f2(x.get('points_per_s'), '{:.0f}')} | "
                      f"{f2(x.get('dense_latency_ms'), '{:.2f}')} | {f2(x.get('dense_repeat_ms'), '{:.2f}')} | {f2(x.get('cold_ms'), '{:.0f}')} | "
                      f"{x['loadavg_before']} | {x['loadavg_after']} |")
    md += ["", RULES_MD, "## Reproduce", "", f"```\n{meta['command']}\n```", ""]
    (a.out / "evaluation.md").write_text("\n".join(md) + "\n")
    return "\n".join(md)


GRAPH_NAMES = ["damage", "application_profile", "ewar", "remote_reps", "capacitor", "shield_regen", "mobility", "warp_time", "lock_time"]


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
    a = ap.parse_args()
    a.out = (pathlib.Path(a.out) if a.out else ROOT / "results" / ("graphs-eval-dryrun" if a.dry_run else "graphs-eval")).resolve()
    work = pathlib.Path(a.work_dir).resolve()
    work.mkdir(parents=True, exist_ok=True)
    import datetime
    if a.as_of and datetime.datetime.fromisoformat(a.as_of).tzinfo is None:
        ap.error("--as-of needs an explicit UTC offset, e.g. 2026-10-03T10:15:00+08:00")
    as_of = datetime.datetime.fromisoformat(a.as_of).timestamp() if a.as_of else None
    tag = time.strftime("%H%M%S")
    t_start = time.time()
    bench_sha = git(ROOT, "rev-parse", "HEAD", check=False)
    meta = {"started": time.strftime("%Y-%m-%d %H:%M:%S %Z"), "bench_sha": bench_sha, "nproc": os.cpu_count(),
            "command": " ".join(["python3", "tools/evaluate_graphs.py"] + sys.argv[1:]), "dry_run": a.dry_run,
            "as_of": a.as_of or "current heads", "host_loadavg_start": load3()}
    ds = json.load(gzip.open(DATASET))
    names = {e["name"] for e in ds["effects"].values() if re.search(r"[A-Z]", e["name"]) and len(e["name"]) >= 8}
    n_mod = sum(1 for e in ds["effects"].values() if e.get("mods"))
    del ds
    cases = corpus()
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
        m, notes = resolve(vd, y, src, cases[0], built=False)
        if m.get("build") and not a.no_build:
            rc, dt, out = sh(m["build"], str(vd), a.build_timeout)
            row["build_s"] = round(dt, 1)
            log(f"{g} build rc={rc} {dt:.1f}s")
            if rc != 0:
                row["gate_reason"] = f"build failed ({'timeout' if rc is None else rc}): {out[-300:]}"
                row["static"] = static_metrics(g, vd, names, n_mod)
                continue
        m, notes = resolve(vd, y, src, cases[0], built=True)
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
        for k in ("points_per_s", "points_per_s_raw", "dense_latency_ms", "dense_repeat_ms", "cold_ms"):
            row[k] = med([x.get(k) for x in runs])
        for k in ("dense_latency_via", "cold_via"):
            row[k] = next((x[k] for x in runs if x.get(k)), None)
        row["empty_x"] = empty_x_check(m, vd, cases) if ifs else None
        row["features"] = features(row)
        row["static"] = static_metrics(g, vd, names, n_mod)
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
