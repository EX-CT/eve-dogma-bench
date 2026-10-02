# eve-dogma-bench

Shared, engine-agnostic test & benchmark harness for EVE Online fitting engines (EX-CT).
Any implementation of [CONTRACT.md](CONTRACT.md) (stateless FitRequest JSON → FitStats JSON) can be scored
on **correctness against Pyfa** (per stat, with tolerance), **speed** (cold start, per-fit latency, batch throughput)
and **determinism**.

```
cases/       FitRequest JSON files (the corpus; fully resolved type ids, no EFT needed)
expected/    expected values per case, produced by the Pyfa oracle (+ known_divergences.json)
oracle/      pyfa_oracle.py (GPL-3.0 test tool: runs Pyfa's eos engine headless as a black box)
tools/       metrics.py (metric -> JSON pointer, tolerance), make_expected.py (regenerate expected/)
run.py       the runner / scorer
results/     scorecards (results/<variant>/scorecard.{md,json}, failures.json)
```

## Dataset (same for every variant)

All variants must load the **same SDE build**: `dataset-3569502.json.gz` (CCP SDE build 3569502, 2026-10-02),
published as a release asset of [EX-CT/eve-sde-pipeline](https://github.com/EX-CT/eve-sde-pipeline/releases/tag/sde-3569502):

```bash
gh release download sde-3569502 -R EX-CT/eve-sde-pipeline -D data/
# on the shared EXCT box it already exists at /workspace/exct-eve/data/dataset-3569502.json.gz
```

Format: gzip JSON documented in eve-sde-pipeline (`types`, `attributes`, `effects` with compact modifier tuples
`[func, domain, modified_attr, modifying_attr, operation, group_or_skill]`, `dbuffs`, `mutaplasmids`, …).
A variant may convert it to any internal format, but must not use other data.

## Scoring all variants (A–K)

```bash
python3 bench.py                 # all variants in variants.yaml -> results/combined.md + per-variant scorecards
python3 bench.py --only A,C --quick --no-build
```

Each lab variant (branch `variant-x` of EX-CT/eve-dogma-lab, directory `variant-x/`) ships a **`bench.yaml`**:

```yaml
build: cargo build --release                      # run in variant-x/ (optional)
cmd: ./target/release/engine calc --dataset {dataset}        # one request on stdin -> one response on stdout
batch_cmd: ./target/release/engine batch --dataset {dataset} # JSONL in -> JSONL out (optional but scored)
```

Placeholders: `{dataset}` (shared dataset path from variants.yaml), `{bench}` (bench checkout), `{dir}` (variant dir).
bench.py clones/fetches the branch into `work/<letter>/`, builds, runs, and records status
(`unavailable`, `no-manifest`, `build-failed`, `run-failed`, `ok`) in the combined table.

## Plugging a variant in (single run)

Provide one command that reads one FitRequest on stdin and prints one FitStats JSON on stdout, and (strongly
recommended) a batch command that reads JSONL requests and prints JSONL responses in order:

```bash
python3 run.py --name variant-x \
  --cmd       "/path/to/engine calc  --dataset /workspace/exct-eve/data/dataset-3569502.json.gz" \
  --batch-cmd "/path/to/engine batch --dataset /workspace/exct-eve/data/dataset-3569502.json.gz" \
  [--cwd DIR] [--cases 'cases/esf_*.json'] [--batch-repeat 5] [--latency-n 500]
```

The response only needs the fields listed in [tools/metrics.py](tools/metrics.py) (JSON pointers into FitStats,
e.g. `/defense/ehp/armor`, `/capacitor/stable_percent`; `a+b` = sum). Missing fields count as wrong.
Tolerance: `|got-want| <= max(1e-3, 1e-4*|want|)`; booleans exact.

Scorecard (`results/<name>/scorecard.md`): cases fully correct, values correct per group (fitting, defense,
tank, offense, capacitor, navigation, targeting), one-process-per-case median wall time (≈ cold start),
batch throughput (fits/s over the whole corpus × N), per-calc latency for one fit (N repetitions in one process),
determinism (identical output for identical input), plus `failures.json` with every mismatch.

## Corpus

249 cases: 101 dogma-engine (EVE Ship Fit) community/regression fits, 24 hand-written fits (frigates, destroyers,
T3D modes, cruisers, HACs, T3C subsystems, battleships, marauders in bastion, logistics, command ships, interdictor,
mining, carriers/supercarrier with fighters, structures with rigs/service modules), 124 variations (fleet command booster fits, projected whole fits, incoming remote reps/neuts/nos/cap transfers, scripted projected modules, wormhole environments C1–C6, implant sets, combat boosters, skills 0/2/3/4,
damage patterns incl. Reactive Armor Hardener adaptation, reload, projected webs/target painters/damps/web drones,
mutated modules and drones). See `cases/`.

Expected values come from Pyfa (eos, Pyfa client data build 3532181) via `oracle/pyfa_oracle.py`; regenerate with
`python3 tools/make_expected.py`. Pyfa is the reference, not the truth: `expected/known_divergences.json` lists
metrics excluded because Pyfa's data is older than the SDE or because Pyfa disagrees with CCP's own modifiers.

## Current results

| variant | cases | values | latency/fit | batch fits/s | cold start |
|---|---|---|---|---|---|
| A: eve-dogma-rs (Rust, lazy memoised dogma graph) | 249/249 | 11 823/11 823 | 1.42 ms | 587 | 182 ms |
| Pyfa (reference, Python) | – | – | 10–31 ms | – | ~390 ms first calc + startup |

## License

Runner, metrics and corpus: MIT. `oracle/` is GPL-3.0-or-later (imports Pyfa). EVE Online data © CCP hf.
