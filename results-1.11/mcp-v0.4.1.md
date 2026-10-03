# eve-fit-mcp v0.4.1 (447420f): batch suite on bench pending-1.11 26e3833

- eve-fit-mcp v0.4.1 = 447420f. It pins engine eve-dogma-f 8bde0ba, and docs/test-ids.json has 90 ids.
- Run setup:
  - `EVE_DOGMA_BIN=eve-fit-8bde0ba-r5`, `EVE_DOGMA_DATASET=dataset-3569502-r5`.
  - Command: `python3 batch/run_batch.py --transport cli --cmd "python3 tools/mcp_batch.py --mcp-dir <eve-fit-mcp> --tool compute_batch"`.
  - Raw results: [mcp-v0.4.1/batch.json](mcp-v0.4.1/batch.json).
- **Result: 71/93.** Reference: F 8bde0ba (r5) scores 93/93 on the same bench.
  - calc_price 2/6, calc_price_embedded 1/1, gap 10/16, gap_error 9/12, multi 6/12, price 14/14, product 8/9, sweep 10/11, variants 11/12.
- Bench fix in 26e3833: identity checks now compare JSON numbers canonically. Before it, 14 price_* cases failed only because a JS transport prints `1` for `1.0`. All price_* cases now pass, and F and the self-test stay 93/93.

## MCP-only failures (all 22 pass on F 8bde0ba)

| group | cases | cause |
|---|---|---|
| no `--prices FILE` input | calcprice_file_map, calcprice_file_snapshot, calcprice_request_over_file, calcprice_use_snapshot_false, gap_prices_file_map, gap_prices_file_snapshot, gap_prices_request_over_file, gap_use_snapshot_false, gap_use_snapshot_false_fit, gap_variant_own_price_table (10) | The MCP has no equivalent of the engine's global `--prices FILE` option, so the adapter returns UNSUPPORTED. Whether these are n/a for the MCP column is eve's call; they are not marked n/a here. |
| BATCH_TOO_LARGE details | gap_too_large_ceiling, gap_too_large_default, gap_too_large_lowered (3) | The error code is right, but `count` and `limit` are missing from the error. |
| extra keys in full results | multi_100_full, multi_5_full, multi_duplicates, multi_single, product_full_output, variants_full_output, sweep_skill_override_full (7) | Full-output `stats` carry `engine`, `notes` and `request_hash`, which the one-by-one compute_fit stats don't. Batch results are therefore not identical to one-by-one results. |
| per-fit error in place | multi_error_in_place (1) | The whole request is rejected up front with `UNKNOWN_TYPE ... (at fits/4/fit)`. The contract requires the error to stay at index 4 while the other fits are computed. |
| builtin profiles: compute_fit vs compute_batch | multi_ext_mix (1) | compute_fit rejects fits with `target_profile: {"builtin": ...}` or `damage_pattern: {"builtin": ...}` with `-32602 Invalid input at fit.ship` (the error names the wrong field). compute_batch computes the same fits, so batch and one-by-one disagree at [4] tpb_rifter_uniform50 and [14] dpb_thorax_uniform. |

## MCP CI on v0.4.1 (features + unit)
- Run locally on 2026-10-03 at 15:52 CST, read-only, with engine 8bde0ba-r5: [mcp-v0.4.1/mcp-ci-features-unit.tap](mcp-v0.4.1/mcp-ci-features-unit.tap).
- Result: 38 pass, 0 fail, 1 todo (security-status-value, effect 6871), 1 skip (variant C binary missing).
- These tests pass: provenance, price-passthrough, price-fit-engine, compute-batch, price-inputs, batch-prepare and batch-table.
- docs/19 decisions:
  - ENG-PRICE-001 mcp: partial → have. mcp-batch price_* is 14/14, and the full refs pass. The `--prices FILE` cases are an engine global option outside the request contract, so their status is left to eve.
  - ENG-BATCH-001 mcp: stays partial, because of the 12 non-price failures above.
