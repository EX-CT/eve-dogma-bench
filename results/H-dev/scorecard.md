# Scorecard: H-dev

- command: `/workspace/exct-eve/lab-h/variant-h/target/release/eve-dogma-h calc --dataset /workspace/exct-eve/data/dataset-3569502.json.gz`, batch: `/workspace/exct-eve/lab-h/variant-h/target/release/eve-dogma-h batch --dataset /workspace/exct-eve/data/dataset-3569502.json.gz`
- cases fully correct: **223/226**
- values correct: **10706/10732** (99.76 %)
- engine errors: 0

| group | ok | total | % |
|---|---|---|---|
| capacitor | 792 | 792 | 100.0 |
| defense | 4044 | 4066 | 99.5 |
| fitting | 2034 | 2034 | 100.0 |
| navigation | 1126 | 1128 | 99.8 |
| offense | 904 | 904 | 100.0 |
| tank | 902 | 904 | 99.8 |
| targeting | 904 | 904 | 100.0 |

| perf | value |
|---|---|
| one process per case, median ms (cold start + calc) | 120.6 |
| batch throughput (corpus x1) fits/s | 659 |
| latency one fit (exct_rifter) ms/calc | 0.927 |
| startup + one calc ms | 118.3 |
| deterministic | True |

Worst metrics:

- ehp.armor: 223/225
- hp.armor: 223/225
- max_velocity: 223/225
- ehp.shield: 224/226
- res.armor.em: 224/226
- res.armor.explosive: 224/226
- res.armor.kinetic: 224/226
- res.armor.thermal: 224/226
- res.shield.em: 224/226
- res.shield.explosive: 224/226
- res.shield.kinetic: 224/226
- res.shield.thermal: 224/226
- tank.armor: 224/226
