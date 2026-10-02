# Combined scorecard

Generated 2026-10-03 03:57 CST — corpus: 207 cases, expected values from Pyfa (see README).

| variant | status | cases ok | values ok | accuracy % | capacitor | defense | fitting | navigation | offense | tank | targeting | ms/fit | fits/s (batch) | cold ms | deterministic |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A eve-dogma-rs main (Rust, lazy memoised modifier graph) | ok | 207/207 | 9827/9827 | 100.00 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 0.762 | 405 | 161 | True |
| B data-oriented Rust | unavailable | | | | | | | | | | | | | | | |
| C Go | no-manifest | | | | | | | | | | | | | | | |

Notes:

- B: unavailable: clone failed: warning: Could not find remote branch variant-b to clone.
fatal: Remote branch variant-b not found in upstream origin
- C: no-manifest: missing work/C/variant-c/bench.yaml
