# EX-CT/eve-fit-mcp v0.3.1 (e7b794a; release commit 5356b81) through tools/mcp_batch.py

Run 2026-10-03 15:05-15:20 CST, read-only clone checked out at e7b794a (`npm ci && npm run build`), engine via
`EVE_DOGMA_BIN`, `dataset-3569502.json.gz`. Same adapter and suites as `mcp-8c6b93d-F2da8150.md`.

| suite | engine d990818 | engine 2da8150 | F d990818 directly | (8c6b93d + 2da8150) |
|---|---|---|---|---|
| core (`run.py --cmd`) | 339/339 | 339/339 | 339/339 | 322/339 |
| ext | 208/239 | 205/239 | 208/239 | 198/239 |
| effects | 2378/2378 | 2352/2378 | 2378/2378 | 2348/2378 |
| cap | 150/150 | 150/150 | 150/150 | 150/150 |
| mutated | 93/93 | 93/93 | 93/93 | 93/93 |
| graphs (compute_graph) | 189/192 | 189/192 | 192/192 | 176/192 |

The MCP now matches the engine on every Pyfa-backed case: both 8c6b93d bugs are fixed (nested empty `booster_fits`;
projected fighter default quantity), and so are the contract error codes and empty-`x.values` passthrough. The ext
failures are the docs/19 f-missing draft cases, which the engine fails too.
The ext numbers match the engine's own scores on this bench (pending-1.11 tip, incl. 583f912): 2da8150 = the 202
earlier cases + brdc_rifter_online + the 2 fit-source cimp cases. eve4's 207/239 on 2da8150 was measured on another bench
ref and is not comparable.

Graphs, the 3 remaining failures (contract error cases, not Pyfa): `err_missing_x`, `err_missing_x_values`,
`err_missing_y`. The MCP fills in a default x range / default series where the contract expects BAD_REQUEST. eve4
proposes treating them as n/a for MCP; that is eve's decision, so they are left as failures here.

Files: `mcp-v0.3.1-d990818/`, `mcp-v0.3.1-2da8150/` (core-*, ext, effects, graphs-*).

## n/a ruling (eve, 2026-10-03 15:09 CST)
err_missing_x, err_missing_x_values and err_missing_y are n/a in the MCP column (the MCP fills in defaults before the
engine sees the request). inventory/suites.yaml `mcp-graphs.na` lists them; `tools/apply_na.py` writes
`graphs-scorecard-na.json` / `graphs-failures-na.json`: mcp-graphs 189/189 on both engines (192 run, 3 n/a).
