# Capacitor-simulation suite (draft, branch `cap-suite`)

Informational suite for the "capacitor simulation" problem: does an engine reproduce Pyfa's capacitor figures and
its capacitor simulator (stable % / time to empty) across local modules, overheating, capacitor boosters, own and
incoming neutralizers / nosferatu, remote capacitor, spool weapons, reloads, staggering and the `options.cap_sim`
simulation options. Rules: [CONTRACT-CAP.md](CONTRACT-CAP.md) (0.1 draft). Not part of the main bench score.

```
cap/cases/<case>.json      FitRequest (main contract, same dataset)
cap/expected/<case>.json   Pyfa values (scored), report-only values, simulator diagnostics (drain list, end time)
cap/index.json             case -> category, description
cap/metrics.py             scored metrics, JSON pointers, tolerances
cap/run_cap.py             scorer
cap/tools/gen_cases.py     regenerate cases from item names (dataset-3569502)
cap/tools/make_expected.py regenerate expected/ with oracle/pyfa_cap_oracle.py (GPL test tool, Pyfa as a black box)
```

```bash
python3 cap/run_cap.py --name H --batch-cmd "<engine> --dataset <dataset> batch"
python3 cap/run_cap.py --only A,H --work-root /path/to/bench/checkout   # variants.yaml + already built work/<X>
```

Results land in `cap/results/<name>.json` (untracked). Scores: [RESULTS.md](RESULTS.md).
