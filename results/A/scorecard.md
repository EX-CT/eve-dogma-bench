# Scorecard: A

- command: `./target/release/eve-dogma --dataset /workspace/exct-eve/data/dataset-3569502.json.gz calc`, batch: `./target/release/eve-dogma --dataset /workspace/exct-eve/data/dataset-3569502.json.gz batch`
- cases fully correct: **226/226**
- values correct: **10732/10732** (100.00 %)
- engine errors: 0

| group | ok | total | % |
|---|---|---|---|
| capacitor | 792 | 792 | 100.0 |
| defense | 4066 | 4066 | 100.0 |
| fitting | 2034 | 2034 | 100.0 |
| navigation | 1128 | 1128 | 100.0 |
| offense | 904 | 904 | 100.0 |
| tank | 904 | 904 | 100.0 |
| targeting | 904 | 904 | 100.0 |

| perf | value |
|---|---|
| one process per case, median ms (cold start + calc) | 151.9 |
| batch throughput (corpus x5) fits/s | 704 |
| latency one fit (exct_rifter) ms/calc | 1.207 |
| startup + one calc ms | 165.2 |
| deterministic | True |
