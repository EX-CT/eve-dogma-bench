# batch-suite (bench 1.11 draft; contract eve-fit-docs docs/23)

There are 58 batch requests. 44 are built from the core (`cases/`) and ext (`ext/cases/`) fits (1024 expanded fits);
14 `price_*` cases (docs/23 §5–§6) are built on one Rifter fit with implants, a booster and cargo. The core assertion is that a batch answer is identical to computing each fit on its own (`ENGINE calc`, one
process per fit). Deltas, sorting, filtering, `fields` projection and limits are checked against a reference built
from those single results. See `CONTRACT-BATCH.md`.

| kind | cases | what it covers |
|---|---|---|
| multi | 12 | 1, 5, 10, 25, 100 and all 339 core fits; ext + core mix; duplicates; an error in place; sort_by + top_n; filter; 2 filters + 2 sort keys |
| variants | 12 | module states, charges (sorted by dps delta), remove/duplicate module + skill levels (filtered on ehp delta), damage patterns, full FitStats |
| product | 9 | skills × charge × state (some with 2-key sort_by + top_n), state × state × damage pattern (some filtered), full FitStats |
| price | 14 | injected-only, missing list (`no_price`), type override beats injected, price 0, market group with children and deepest-wins, type > market group > group > category, `multiplier_without_base`, the FitRequest's own overrides (L2), variant > request chains (×0.9 over ×0.5 = 0.45; a fixed L1 price stops the chain), variant fixed price beats request fixed price, variants / product options / fit entries with their own overrides, filter + sort + deltas on `price.total_isk` |
| sweep | 11 | default skill level 0..5, module state, charge (top 3), damage pattern, per-skill override (full FitStats) |

Option use across cases: `fields` 37, `deltas` 29, `sort_by` 13, `filter` 7, `top_n` 5.

Files:
- `MANIFEST.json`: kind, number of fits and options per case.
- `cases/<id>.json`: the BatchRequest.
- `semantics.py`: expansion, reference answer and comparison.
- `adapter.py`: shape and transport. This is the only file that changes when F's contract lands.
- `tools/gen_batch.py`, then `tools/gen_price_cases.py`: regenerate the cases (gen_batch rewrites MANIFEST and
  deletes every case file, so run the price generator second).
- `prices.py`: the bench's reference price resolver and price-block comparer (Pyfa has no overrides; the expected
  values are a pure function of docs/23 §5 and SDE metadata from dataset r5).
- `run_batch.py`: the scorer.

```sh
python3 batch/run_batch.py --cmd target/release/eve-fit [--transport rpc|cli] --name F --out batch.json
python3 batch/run_batch.py --cmd target/release/eve-fit --self-test   # reference batch from `ENGINE batch` JSONL: must be 58/58
```

An engine without batch support scores 0/58 without crashing (rpc answers UNKNOWN_METHOD). EX-CT/eve-dogma 2da8150 and d990818:
0/58. Self-test with the same binary: 58/58. The no-regression gate (`baselines/f.json`) records the suite as
`batch` at 0/44, so it can only go up.

## Gap cases (gen_gap_cases.py)
`python3 batch/tools/gen_gap_cases.py` (run after gen_batch.py and gen_price_cases.py) writes 34 more cases and
`batch/data/` (a plain `--prices` map and a synthetic eve-price-snapshot v1 file with a valid `content_hash`):
- `gap` (15): filter `in` / `not_null` (incl. `on: delta`), form-1 `delta_ref`, int / float numeric sweeps
  (`from + k*step`, `to` inclusive), a product of two sweep axes, `swap_type`, `--prices` map / snapshot files,
  request table over file, `use_snapshot: false` (request-wide and per FitRequest).
- `gap_error` (12): BATCH_TOO_LARGE `{count, limit}` (default 2000, ceiling 100000, lowered `max_combinations`) and
  BAD_PRICE_OVERRIDE variants; the whole request must fail.
- `calc_price` (6): `ENGINE [--prices F] calc` with price inputs; the price block must equal the bench resolver and
  every other key (except `provenance`) must equal calc without price inputs.
- `calc_price_embedded` (1): no price inputs; structural check of lines priced from the embedded snapshot.
MANIFEST `engine_args` are global options placed before the subcommand (`batch/...` paths made absolute).
