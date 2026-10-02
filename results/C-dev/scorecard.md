# Scorecard: C-dev

- command: `/workspace/exct-eve/lab-c/variant-c/bin/eve-dogma-go --dataset /workspace/exct-eve/data/dataset-3569502.json.gz calc`, batch: `/workspace/exct-eve/lab-c/variant-c/bin/eve-dogma-go --dataset /workspace/exct-eve/data/dataset-3569502.json.gz batch`
- cases fully correct: **228/249**
- values correct: **11772/11823** (99.57 %)
- engine errors: 0

| group | ok | total | % |
|---|---|---|---|
| capacitor | 864 | 871 | 99.2 |
| defense | 4458 | 4480 | 99.5 |
| fitting | 2241 | 2241 | 100.0 |
| navigation | 1239 | 1243 | 99.7 |
| offense | 996 | 996 | 100.0 |
| tank | 987 | 996 | 99.1 |
| targeting | 987 | 996 | 99.1 |

| perf | value |
|---|---|
| one process per case, median ms (cold start + calc) | 300.6 |
| batch throughput (corpus x5) fits/s | 963 |
| latency one fit (exct_rifter) ms/calc | 0.192 |
| startup + one calc ms | 283.9 |
| deterministic | True |

Worst metrics:

- cap_stable: 243/249
- tank.armor: 243/249
- max_velocity: 244/248
- max_target_range: 245/249
- scan_resolution: 245/249
- ehp.armor: 246/248
- hp.armor: 246/248
- ehp.shield: 247/249
- res.armor.em: 247/249
- res.armor.explosive: 247/249
- res.armor.kinetic: 247/249
- res.armor.thermal: 247/249
- res.shield.em: 247/249
- res.shield.explosive: 247/249
- res.shield.kinetic: 247/249
