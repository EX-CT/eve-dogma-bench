# Scorecard: variant-a

- command: `/workspace/exct-eve/eve-dogma-rs/target/release/eve-dogma --dataset /workspace/exct-eve/data/dataset-3569502.json.gz calc`, batch: `/workspace/exct-eve/eve-dogma-rs/target/release/eve-dogma --dataset /workspace/exct-eve/data/dataset-3569502.json.gz batch`
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
| one process per case, median ms (cold start + calc) | 148.7 |
| batch throughput (corpus x5) fits/s | 773 |
| latency one fit (exct_rifter) ms/calc | 1.115 |
| startup + one calc ms | 140.8 |
| deterministic | True |
