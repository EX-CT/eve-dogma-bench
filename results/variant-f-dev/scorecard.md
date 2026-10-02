# Scorecard: variant-f-dev

- command: `/workspace/exct-eve/lab-f/variant-f/target/release/eve-dogma-f calc`, batch: `/workspace/exct-eve/lab-f/variant-f/target/release/eve-dogma-f batch`
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
| one process per case, median ms (cold start + calc) | 2.8 |
| batch throughput (corpus x5) fits/s | 2332 |
| latency one fit (exct_rifter) ms/calc | 0.348 |
| startup + one calc ms | 3.1 |
| deterministic | True |
