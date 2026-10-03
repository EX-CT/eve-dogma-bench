# eve-fit-mcp v0.4.0 (d3786eb) through tools/mcp_batch.py (eve3, 2026-10-03 15:40 CST)

Engine: the MCP's pin eve-dogma 197223f (engines.lock; contains d990818), `EVE_DOGMA_BIN=eve-fit-197223f`,
dataset-3569502. Read-only run; graphs from graphs-round2 db81b8c, cap d80cc38, mutated 4533dde.

| suite | v0.4.0 + 197223f |
|---|---|
| core (mcp-bench) | 339/339 |
| ext (mcp-ext, mcp-ext-unit) | 208/239 (= engine; failures are the F-missing cases) |
| effects (mcp-effects) | 2378/2378 |
| cap (mcp-cap) | 150/150 |
| mutated (mcp-mut) | 93/93 |
| graphs (mcp-graphs) | 189/189 + 3 n/a (err_missing_x, err_missing_x_values, err_missing_y; eve ruling: the MCP fills defaults) |
| batch (mcp-batch, compute_batch, bench 1fd7e37 = before the docs/22-23 provenance rulings) | 52/92 (engine 197223f directly: 62/92) |
| batch (bench e3e3895, after the provenance rulings) | 8/93 (engine 197223f directly: 10/93; 197223f has no provenance) |

brdc_* 4/4 (ENG-MISC-004) and effects 2378/2378 (ENG-CORE-003) hold on the pinned engine.

MCP-only batch differences (bench 1fd7e37, 10 cases where the engine passes and the MCP does not):
- `multi_*_full`, `product_full_output`, `variants_full_output`: results carry extra keys `engine`, `notes`,
  `request_hash` (MCP additions), so a full-output result is not identical to one-by-one calc.
- `multi_error_in_place`: the MCP rejects the whole request at normalisation (UNKNOWN_TYPE at fits/4/fit) instead of
  leaving the per-fit error in place.
- `multi_ext_mix`: two ext fits that should error (tpb_/dpb_ profile names) are computed by the MCP.
- `gap_too_large_default` / `gap_too_large_lowered`: BATCH_TOO_LARGE comes back without `count` / `limit`.
- `--prices FILE` cases (gap file / calc_price file): no MCP equivalent (reported UNSUPPORTED by the adapter).

Files: `mcp-v0.4.0-197223f/` (core-*, ext, effects, graphs-* incl. `-na`, batch-bench-<rev> and batch-engine-bench-<rev>).

# F eve-dogma 8bde0ba (native), bench 05ae5a1 (re-run 2026-10-03 15:45 CST)
batch 93/93, d22 sde 18/18 (+5 pending without SDE_PACK), price_inject 32/32 (+1 pending). Files: `F-8bde0ba/`.

Correction: the earlier 8bde0ba numbers in this file (batch 77/93, price_inject 21/32 on bench 1fdcf61) came from a
local build that compiled in dataset-3569502 r1 (EVE_DOGMA_DATASET leaked from the 197223f build; `version` said
sde_revision 1). The price cases need the r5 market-group tables. Rebuilt with dataset r5 (sde_revision 5).
The engine 197223f binary used for the v0.4.0 MCP run above had the same r1 problem, so its batch price numbers are
not representative; the v0.4.1 re-run (mcp-v0.4.1.md) uses r5 builds.
