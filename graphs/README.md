# Round 2: graphs (draft, branch `graphs-round2`)

Pyfa-verified sample points for Pyfa's graph subsystem, scored separately from the 1.x stats corpus (main / tag 1.8.0
are untouched). Contract draft: [CONTRACT-GRAPHS.md](CONTRACT-GRAPHS.md).

```
graphs/CONTRACT-GRAPHS.md        GraphRequest / GraphResult, 9 graph types, axes, units, semantics
graphs/cases/*.json              100 GraphRequests (source fit embedded; most fits taken from cases/ of the 1.x corpus)
graphs/expected/*.json           Pyfa values at every sample point (oracle/pyfa_graph_oracle.py)
graphs/tools/make_graph_cases.py regenerates cases/ (sample points chosen per graph)
graphs/tools/make_graph_expected.py  regenerates expected/ with the Pyfa graph oracle (GPL test tool)
graphs/run_graphs.py             scorer: --batch-cmd | --cmd | --rpc-cmd (method "graph") | --self-test
```

| graph | cases | scored sample values |
|---|---|---|
| `application_profile` | 10 | 120 (+120 informational charge ids) |
| `capacitor` | 11 | 164 |
| `damage` | 37 | 634 |
| `ewar` | 10 | 168 |
| `lock_time` | 6 | 78 |
| `mobility` | 9 | 253 |
| `remote_reps` | 6 | 87 |
| `shield_regen` | 4 | 54 |
| `warp_time` | 7 | 91 |
| **total** | **100** | **1649** |

## Running

```bash
python3 graphs/run_graphs.py --self-test                       # sanity: expected vs itself = 100 %
python3 graphs/run_graphs.py --name E --batch-cmd "./target/release/engine graph-batch --dataset $D" --cwd <variant dir>
python3 graphs/run_graphs.py --name E --rpc-cmd "./target/release/engine serve-stdio --dataset $D" --cwd <variant dir>
# -> results/graphs-<name>/scorecard.{md,json}, failures.json (results/ is untracked)
```

Variant manifest (proposal): `graph_batch_cmd:` / `graph_cmd:` in `bench.yaml`, or the `graph` method on `rpc_cmd`.
Tolerance per value: max(1e-3, 1e-4·|want|) as in the 1.x corpus; `null` must match `null`.

## Regenerating expected values

```bash
python3 graphs/tools/make_graph_cases.py
python3 graphs/tools/make_graph_expected.py         # ~30 s; needs ref/pyfa + eve.db, ref/pyfa-venv, ref/stubs (wx stub)
```

The oracle builds each fit with `oracle/pyfa_oracle.py build()` (same mapping as the 1.x corpus) and calls Pyfa's
own getter classes (`graphs/data/<graph>/getter.py`, `getPoint`) with a fresh fit and fresh graph caches per sample
point. Verified: running every case in its own process gives identical numbers to the batch run.

## Oracle limitations / caveats

- **Charge choice ties (application_profile):** Pyfa returns only the charge *name* and breaks exact DPS ties between
  equal-stat faction charges by set iteration order (it differs between processes: Dark Blood vs True Sansha,
  Federation Navy vs Caldari Navy, Guardian vs Dread Guristas). The DPS value is stable; the charge id is reported as
  informational only. The candidate charge list comes from Pyfa's market data (`getValidChargesForModule`).
- **Same data as the 1.x corpus:** values come from Pyfa's eve.db (built from the same SDE as dataset-3569502); any
  SDE/eve.db divergence documented for the 1.x corpus applies here too.
- **`getPoint`, not the plotted curve:** the GUI plot (`getRange`) uses adaptive sampling and inserts capsim events;
  the contract and the expected values are the exact value at each requested x. Limiters (Pyfa clamps x into a valid
  range when plotting) are expressed as `null` outside the range.
- **Headless shims:** `gui.mainFrame` is stubbed (only the shield graph's EHP toggle reads it; the oracle applies
  `effectivify` itself for `effective: true`), `GraphSettings` is a process-wide singleton and is reset from each
  request's `settings`.
- **Unsaved fits:** Pyfa keys graph caches by fit ID (None for oracle fits) — hence fresh caches per point.
- **Not covered:** the hidden experimental "ECM Burst + Scanres Damps" graph; `%`-of-target x axes (`tgt_speed`/
  `tgt_sig` in %) — engines get absolute axes, the GUI converts; target fits only as `damage`/`application_profile`
  targets (not as EWAR/RR targets: Pyfa's EWAR and RR graphs have no target).
- **Fighter abilities, doomsdays, breachers, bombs** are exercised by a few cases only (Hel, Nidhoggur, Avatar lance);
  coverage of exotic weapons is thinner than the 1.x corpus.
