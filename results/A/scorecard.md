# Scorecard: A

- command: `./target/release/eve-dogma --dataset /workspace/exct-eve/data/dataset-3569502.json.gz calc`, batch: `./target/release/eve-dogma --dataset /workspace/exct-eve/data/dataset-3569502.json.gz batch`
- cases fully correct: **207/207**
- values correct: **9827/9827** (100.00 %)
- engine errors: 0

| group | ok | total | % |
|---|---|---|---|
| capacitor | 723 | 723 | 100.0 |
| defense | 3724 | 3724 | 100.0 |
| fitting | 1863 | 1863 | 100.0 |
| navigation | 1033 | 1033 | 100.0 |
| offense | 828 | 828 | 100.0 |
| tank | 828 | 828 | 100.0 |
| targeting | 828 | 828 | 100.0 |

| perf | value |
|---|---|
| one process per case, median ms (cold start + calc) | 160.5 |
| batch throughput (corpus x1) fits/s | 405 |
| latency one fit (exct_rifter) ms/calc | 0.762 |
| startup + one calc ms | 196.6 |
| deterministic | True |
