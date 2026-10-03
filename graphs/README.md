# Round 2: graphs (branch `graphs-round2`, contract 0.3)

Pyfa-verified sample points for Pyfa's graph subsystem, scored separately from the 1.x stats corpus (main / tag 1.8.0
are untouched). Contract: [CONTRACT-GRAPHS.md](CONTRACT-GRAPHS.md), revision **0.3** (released 2026-10-03, tag `graphs-v0.3`). Round 2 itself
was scored on 0.2 @ `0397d95`.

```
graphs/CONTRACT-GRAPHS.md        GraphRequest / GraphResult, 10 graph types, axes, units, semantics, error codes (rev 0.3)
graphs/cases/*.json              192 GraphRequests: 172 value cases + 20 error cases err_* (source fit embedded; most fits from cases/ of the 1.x corpus)
graphs/expected/*.json           Pyfa values at every sample point (oracle/pyfa_graph_oracle.py); err_*: contract error code
graphs/CHANGELOG.md              corpus / contract revisions
graphs/tools/make_graph_cases.py regenerates cases/ (sample points chosen per graph)
graphs/tools/make_graph_expected.py  regenerates expected/ with the Pyfa graph oracle (GPL test tool)
graphs/run_graphs.py             scorer: --batch-cmd | --cmd | --rpc-cmd (method "graph") | --self-test
```

| graph | cases | scored values | new vs 0.2 |
|---|---|---|---|
| application_profile | 14 | 161 | +4 cases / +41 (XL navy tier ×3, Maelstrom arty web+TP sampled off the edges) |
| capacitor | 14 | 173 | – |
| damage | 70 | 1134 | +10 cases / +216 (state correction: overheated Bastion → online ×1, sentries follow_target ×2, breacher distance ×2, bomb time ×2, fighters vs fast target ×3) |
| ecm_burst | 11 | 218 | – |
| ewar | 22 | 337 | – |
| lock_time | 7 | 82 | – |
| mobility | 10 | 259 | – |
| remote_reps | 11 | 151 | – |
| shield_regen | 5 | 66 | – |
| warp_time | 8 | 93 | – |
| errors | 20 | 20 | – |
| **total** | **192** | **2694** | +14 cases / +257 values (0.2: 178 / 2437) |

Contract 0.3 (see [CHANGELOG.md](CHANGELOG.md)): 0.2 had 178 cases / 2437 values, 0.1 had 111 cases / 1843 values.
To score on 0.2 exactly, use the bench at commit `0397d95` (what `tools/evaluate_graphs.py` pins). Empty-x cases score one value per
y series (`[]` expected); error cases score one value (matching `error.code`).

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
- **Covered since 0.2:** the hidden "ECM Burst + Scanres Damps" graph (`ecm_burst`, Pyfa's own getters);
  `%`-of-target x axes (`tgt_speed_pct`, `tgt_sig_pct`, Pyfa's normalisers).
- **Derived, not Pyfa graph output (0.2):** `ewar` / `remote_reps` with `target.fit`. Pyfa's EWAR and RR graphs have no
  target, so the oracle evaluates Pyfa's getter and then applies the target ship's resistance attribute: for ewar
  `resist = 1 − attr` (energyWarfare/stasisWebifier/ECM/sensorDampener/weaponDisruption/targetPainter resistance, as
  Pyfa's `getResistance` does for projected fits), 0 for `disallowOffensiveModifiers` (except neuts); for RR
  `× remoteRepairImpedance` and 0 for `disallowAssistance`. Pyfa's projected-fit RR ignores the impedance. The contract
  follows the effect's SDE `resistanceID`. See CONTRACT-GRAPHS.md "Target fits for ewar / remote_reps".
- **Error cases** (`err_*`) have no oracle: the expected code is the one CONTRACT-GRAPHS.md "Validation and error codes"
  prescribes.
- **Exotic weapons** are exercised by a few cases each: fighters (Hel, Nidhoggur, Thanatos/Templar II), doomsday
  (Avatar lance), Entropic Disintegrator spool-up (Kikimora, distance + time), Vorton (Skybreaker), breacher pods
  (Kestrel vs. target fit, time axis), bombs (Manticore). Target-fit cases include scram-vs-MWD (Rifter → Stiletto)
  and web-vs-fit (Hyperion → Sabre). Coverage is still thinner than the 1.x corpus.
