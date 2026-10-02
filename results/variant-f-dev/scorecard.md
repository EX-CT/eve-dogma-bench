# Scorecard: variant-f-dev

- command: `/workspace/exct-eve/lab-f/variant-f/target/release/eve-dogma-f calc`, batch: `/workspace/exct-eve/lab-f/variant-f/target/release/eve-dogma-f batch`
- cases fully correct: **216/249**
- values correct: **13682/13812** (99.06 %)
- engine errors: 0

| group | ok | total | % |
|---|---|---|---|
| application | 1860 | 1989 | 93.5 |
| capacitor | 871 | 871 | 100.0 |
| defense | 4480 | 4480 | 100.0 |
| fitting | 2241 | 2241 | 100.0 |
| navigation | 1243 | 1243 | 100.0 |
| offense | 996 | 996 | 100.0 |
| tank | 996 | 996 | 100.0 |
| targeting | 995 | 996 | 99.9 |

| perf | value |
|---|---|
| one process per case, median ms (cold start + calc) | 2.6 |
| batch throughput (corpus x5) fits/s | 2249 |
| latency one fit (exct_rifter) ms/calc | 0.350 |
| startup + one calc ms | 10.9 |
| deterministic | True |

Worst metrics:

- w2.range_m: 0/1
- w10.range_m: 5/30
- w15.range_m: 1/6
- w11.range_m: 8/33
- w9.range_m: 8/30
- w12.range_m: 10/31
- w13.range_m: 10/31
- w0.range_m: 1/3
- w14.range_m: 5/10
- w8.range_m: 2/4
- scan_strength: 248/249
