# batch-suite (bench 1.11 draft, PROVISIONAL shape)

There are 44 batch requests built from the core (`cases/`) and ext (`ext/cases/`) fits, 1024 expanded fits in
total. The core assertion is that a batch answer is identical to computing each fit on its own (`ENGINE calc`, one
process per fit). Deltas, sorting, filtering, `fields` projection and limits are checked against a reference built
from those single results. See `CONTRACT-BATCH.md`.

| kind | cases | what it covers |
|---|---|---|
| multi | 12 | 1, 5, 10, 25, 100 and all 339 core fits; ext + core mix; duplicates; an error in place; sort + limit; filter; 2 filters + 2 sort keys |
| variants | 12 | module states, charges (sorted by dps delta), remove/duplicate module + skill levels (filtered on ehp delta), damage patterns, full FitStats |
| product | 9 | skills × charge × state (some with 2-key sort + limit), state × state × damage pattern (some filtered), full FitStats |
| sweep | 11 | default skill level 0..5, module state, charge (top 3), damage pattern, per-skill override (full FitStats) |

Option use across cases: `fields` 37, `deltas` 29, `sort` 13, `filter` 7, `limit` 5.

Files:
- `MANIFEST.json`: kind, number of fits and options per case.
- `cases/<id>.json`: the BatchRequest.
- `semantics.py`: expansion, reference answer and comparison.
- `adapter.py`: shape and transport. This is the only file that changes when F's contract lands.
- `tools/gen_batch.py`: regenerates the cases.
- `run_batch.py`: the scorer.

```sh
python3 batch/run_batch.py --cmd target/release/eve-fit [--transport rpc|cli] --name F --out batch.json
python3 batch/run_batch.py --cmd target/release/eve-fit --self-test   # reference batch from `ENGINE batch` JSONL: must be 44/44
```

An engine without batch support scores 0/44 without crashing (rpc answers UNKNOWN_METHOD). EX-CT/eve-dogma 2da8150:
0/44. Self-test with the same binary: 44/44. The no-regression gate (`baselines/f.json`) records the suite as
`batch` at 0/44, so it can only go up.
