# Scorecard: variant-j-dev

- command: `/workspace/exct-eve/lab-j/variant-j/build/eve-dogma-j calc --dataset /workspace/exct-eve/data/dataset-3569502.json.gz`, batch: `/workspace/exct-eve/lab-j/variant-j/build/eve-dogma-j batch --dataset /workspace/exct-eve/data/dataset-3569502.json.gz`
- cases fully correct: **215/249**
- values correct: **11677/11823** (98.77 %)
- engine errors: 0

| group | ok | total | % |
|---|---|---|---|
| capacitor | 864 | 871 | 99.2 |
| defense | 4368 | 4480 | 97.5 |
| fitting | 2241 | 2241 | 100.0 |
| navigation | 1239 | 1243 | 99.7 |
| offense | 996 | 996 | 100.0 |
| tank | 982 | 996 | 98.6 |
| targeting | 987 | 996 | 99.1 |

| perf | value |
|---|---|
| one process per case, median ms (cold start + calc) | 3.7 |
| batch throughput (corpus x1) fits/s | 8474 |
| latency one fit (exct_rifter) ms/calc | 0.066 |
| startup + one calc ms | 6.2 |
| deterministic | True |

Worst metrics:

- ehp.armor: 235/248
- ehp.shield: 238/249
- hp.armor: 238/248
- res.armor.em: 240/249
- res.armor.explosive: 240/249
- res.armor.kinetic: 240/249
- res.armor.thermal: 240/249
- cap_stable: 243/249
- res.shield.explosive: 243/249
- res.shield.kinetic: 243/249
- res.shield.thermal: 243/249
- tank.armor: 243/249
- hp.shield: 244/249
- tank.passive: 244/249
- max_velocity: 244/248
