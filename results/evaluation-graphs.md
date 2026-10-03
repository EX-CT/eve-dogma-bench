# Graphs round 2 evaluation — F baseline (G4 only)

> **F baseline:** official settings, G4 (graphs-g4, on variant-f) only, run 11:05:42–11:09:00 CST 2026-10-03. Scores are relative to the best ranked variant, so with one variant speed = 1.00 by construction; totals are comparable only after the side-by-side run `--only G4,GJ`. First attempt 11:04:24–11:05:04 CST aborted (build killed by an external SIGTERM after 38 s; not a variant failure).

Generated 2026-10-03 11:09:00 CST (Asia/Shanghai) by `tools/evaluate_graphs.py` (`ed54676`); graph contract 0.2 pinned @ `0397d95` (178 graph cases), stats gate bench 1.8.0 @ `3da9671` (326 cases); commits: 2026-10-03T11:00:00+08:00; runs = 3; host 8 CPUs; total wall time 3.3 min. Perf was measured on a shared, loaded machine: compare with the loadavg column.

Gate: all 178 contract-0.2 cases (incl. ecm_burst and error cases) via every interface AND stats 326/326 (bench 1.8.0). Build time is not scored (no fresh clones).

## Ranking

| rank | variant | commit (CST) | graph cases | values | stats 1.8.0 | points/s | dense ms | cold ms | speed | maint | features | port | **total** | load (1m) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | G4 declarative graph specs (Rust, on F) | `f73ff1c` 10-03 10:55 | 178/178 | 2437/2437 | 326/326 | 1790 | 35.79 | 2 | 1.00 | 0.79 | 1.00 | 1.00 | **0.927** | 2.8–4.7 |

## Correctness per graph (primary interface; corpus 178 cases, contract: # eve-dogma graphs contract (DRAFT, round 2, revision 0.2))

| variant | interface | damage | application_profile | ewar | remote_reps | capacitor | shield_regen | mobility | warp_time | lock_time | ecm_burst | errors |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| G4 | batch | 918/918 | 120/120 | 337/337 | 151/151 | 173/173 | 66/66 | 259/259 | 93/93 | 82/82 | 218/218 | 20/20 |

## Interfaces, perf details, maintainability

| variant | dir | commands | interfaces (cases ok) | pts/s incl. start-up | dense via | dense repeat ms | cold via | empty x | round-2 core lines added | core LOC (dir) | tests (own suite) | deps | README/DESIGN/LICENSE | portability |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| G4 | graphs-g4 | graph_cmd inferred (calc -> graph, probe ok) | batch 178/178, rpc 178/178, single 178/178 | 1782 | graph-batch, 1 cpu, differencing | 8.45 | graph single | 154/154 | 2773 (Rust 2773) | 7942 | passed (0✓/0✗, cargo, 69.8 s) | 4 | ✓✓✓ | code |

## Commit selection (cutoff by commit date, verified by push time)

| variant | branch | commit-date pick | commit date (CST) | pushed (CST) | head pushed before cutoff | evaluated | verdict |
|---|---|---|---|---|---|---|---|
| G4 | graphs-g4 | `f73ff1c` | 2026-10-03T10:55:17+08:00 | 2026-10-03T10:55:18+08:00 | `f73ff1c` 2026-10-03T10:55:18+08:00 | `f73ff1c` | ok: commit-date pick was pushed before the cutoff |

## Licensing (mainline eve-dogma-rs is LGPL-3.0-or-later)

| variant | license (files) | round-1 base | base license | mergeable into LGPL-3.0-or-later mainline | reason |
|---|---|---|---|---|---|
| G4 | LGPL-3.0-or-later (LICENSE (LGPL-3); LICENSE.GPL-3.0 (GPL-3)) | – | – | **yes** | LGPL v3 LICENSE text + GPL companion text |

## Dense latency measurement (single CPU, same rules as round 1)

| variant | ms/request (median) | min | max | spread | valid/samples | N per sample | startup ms | RPC warm ms (info) | flags |
|---|---|---|---|---|---|---|---|---|---|
| G4 | 35.785 | – | – | – | 0/8 | 20 | 15.89 | 9.631 | 8 invalid sample(s): above upper bound T_N/N; no valid differencing sample: using upper bound T_N/N |

## Per-run measurements

| variant | run | corpus wall s | 1-request wall s | points/s | dense RPC ms (info) | dense repeat ms | cold ms | loadavg before | loadavg after |
|---|---|---|---|---|---|---|---|---|---|
| G4 | 1 | 0.9066 | 0.0034 | 1807 | 13.54 | 8.45 | 2 | [2.8, 4.37, 3.36] | [3.3, 4.45, 3.39] |
| G4 | 2 | 0.9156 | 0.0041 | 1790 | 9.16 | 11.52 | 2 | [3.3, 4.45, 3.39] | [4.23, 4.62, 3.45] |
| G4 | 3 | 0.9797 | 0.0032 | 1671 | 9.63 | 8.12 | 2 | [4.23, 4.62, 3.45] | [4.7, 4.72, 3.49] |

## Scoring rules (round 2)

- **Version rule:** each variant at its branch HEAD (or the last commit at or before `--as-of`); evaluated read-only from detached worktrees, nothing pushed.
- **Gate (confirmed):** (a) all **178/178** cases of graph contract 0.2 @ `0397d95` — every case incl. `ecm_burst` and the error cases, not only the nine Pyfa graphs — through **every** interface offered; **and** (b) the branch's stats engine passes bench 1.8.0 (`3da9671`) **326/326**. Weights 40/35/15/10. Official cutoff `--as-of 2026-10-03T11:00:00+08:00`.
- **Builds:** no fresh clones; build time is informational and not scored.
- **Total = 0.40·Speed + 0.35·Maintainability + 0.15·Features + 0.10·Portability**, `L(x, best, span) = clamp(1 − log10(x/best)/log10(span), 0, 1)`.
- **Pins:** graph corpus / expected / run_graphs.py from `0397d95` (contract 0.2, 178 cases); stats gate from bench 1.8.0 `3da9671` (326 cases); recorded in the output.
- **Speed** = 0.4·L(1/points·s⁻¹ batch, start-up excluded) + 0.4·L(dense 500-point damage latency, distinct fits) + 0.2·L(cold start + one request); points/s and cold = medians over runs.
- **Dense latency** (round-1 rules): graph-batch pinned to one CPU, (T_N − T_1)/(N − 1), ≥5 independent samples, median; samples ≤0, <0.002 ms, >T_N/N or with missing responses are invalid; spread >50 % ⇒ re-measure (≤3 extra), then flagged. RPC warm latency is informational.
- **Licensing** (not scored): actual LICENSE files at the evaluated commit + the round-1 base variant's license; G1 (built on GPL variant E) is not mergeable into the LGPL-3.0-or-later mainline.
- **Maintainability** = 0.3·Tests + 0.3·Size (L(round-2 core lines added on the branch since the round-1 merge-base, min, 10)) + 0.2·Docs + 0.2·Deps (round-1 definitions; test runs get `EVE_DOGMA_DATASET` and `EVE_DOGMA_GRAPH_CASES`, skipped tests are not counted as passed).
- **Features** = 0.6·graphs fully correct/(graphs in the corpus) + 0.3·interfaces passing (graph-batch, graph, RPC)/3 + 0.1·empty `x.values` → empty series.
- **Portability** = round-1 heuristic (WASM/browser build in code 1, documented 0.5).
- Commands not declared in `bench.yaml` are inferred (variant's own `score*.sh`, or `batch`→`graph-batch` / RPC `graph` with a probe) and flagged in the table.

## Reproduce

```
python3 tools/evaluate_graphs.py --as-of 2026-10-03T11:00:00+08:00 --runs 3 --only G4
```

