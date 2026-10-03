# No-regression gate (`baselines/`, `tools/check_no_regress.py`)

A change to the engine (EX-CT/eve-dogma, the F mainline) must not make any bench case fail that passed before, and
must not lower any docs/19 `have` count. The gate compares a new run against a committed baseline. The baseline can
only go up.

## Files
- `baselines/f.json`: the baseline for EX-CT/eve-dogma.
  - `suites.<suite>`: `passed`, `total`, `passed_ids` (sorted case ids), and `ref` (the bench commit the suite ran from).
    `formats` has `failing_ids` (failing scored rows) instead of `passed_ids`, because formats rows have no listed ids.
  - `inventory.columns.<col>`: `have` (count) and `ids` for every docs/19 column (`f`, `mcp`, `web`, `formats`).
    Only the 200 parity items count, the same as the docs/19 counts table; `extra: true` items are excluded.
- `tools/run_all_suites.sh ENGINE OUT [NAME]`: runs every suite on one binary and writes OUT.
  - core, ext, ext_rpc, batch and effects run from this checkout.
  - graphs, cap, mutated and formats run from the pinned commits in the script. They are fetched and checked out as
    worktrees under `OUT/suites`.
  - Runner exit codes are ignored, because the gate decides.
- `tools/check_no_regress.py`: the gate.

## Suites (seeded from 2da8150 at 14:10 CST; raised to EX-CT/eve-dogma d990818 at 14:40 CST)
| suite | runner | source | passed / total |
|---|---|---|---|
| core | `run.py` | pending-1.11 | 339 / 339 |
| ext | `ext/tools/score.py` | pending-1.11 (incl. the 37 f-missing cases) | 207 / 239 |
| ext_rpc | `ext/tools/score_rpc.py` (serve-stdio) | pending-1.11 `ext/rpc` | 0 / 54 |
| batch | `batch/run_batch.py` (identity vs one-by-one calc; provisional shape) | pending-1.11 `batch/` | 0 / 58 (44 at 14:30 CST + 14 price_* at 15:10 CST; no batch API in 2da8150 / d990818) |
| effects | `effects/tools/score.py` | pending-1.11 | 2378 / 2378 |
| graphs | `graphs/run_graphs.py` (serve-stdio) | graphs-round2 db81b8c (`graphs-v0.3`) | 192 / 192 |
| cap | `cap/run_cap.py` | cap-suite d80cc38 | 150 / 150 |
| mutated | `mutated/run_mutated.py` | mutated-suite 4533dde | 93 / 93 |
| formats | `tools/evaluate_formats.py` (serve-stdio) | formats-suite 7c716e7 | 4779 / 4779 scored rows |

docs/19 (eve-fit-docs 3d99eea) `have` counts: f 104, mcp 97, web 84, formats 10.

## Rules (exit 1 = regression)
1. For each suite in the baseline, `passed` must be at least the baseline value.
2. Every id in the baseline's `passed_ids` must still pass. A swap, where one case breaks and another is fixed, is
   caught. A baseline id that is missing from the run, for example a deleted case, also counts as a regression;
   lowering the baseline for a deleted case is a reviewed edit of `f.json`, never `--update`.
3. formats: a scored row failing now that was not failing in the baseline is a regression. If the run has more rows
   than the baseline, it is only reported as a note (it may be a new row).
4. A suite in the baseline with no result in the run is a regression, unless you limit the check with `--only`.
5. With `--inventory`, for each column `have` must not drop and no baseline `have` id may disappear.

New cases that fail are fine: they are not in `passed_ids`. Improvements are reported as notes.

`--update` writes the run into the baseline. It is refused whenever the check fails, so the baseline only goes up.
Commit the updated `f.json` to eve-dogma-bench, for example after an engine release.
`--init` writes a new baseline file and refuses to overwrite an existing one.

Exit codes: 0 no regression; 1 regression; 2 usage or missing input. On GitHub Actions, a summary is appended to
`$GITHUB_STEP_SUMMARY`.

## CI (eve-dogma, after `cargo build --release`; needs python3 + pyyaml, and read access to eve-dogma-bench)
```sh
git clone -q --depth 1 -b pending-1.11 https://github.com/EX-CT/eve-dogma-bench bench && bench/tools/run_all_suites.sh target/release/eve-fit out && python3 bench/tools/check_no_regress.py --baseline bench/baselines/f.json --run-dir out
```
The docs/19 check needs eve-fit-docs: add `--inventory docs/19-pyfa-feature-inventory.csv` where that repo is checked
out, for example in eve-fit-docs CI or when updating the baseline by hand.

## Raise the baseline
```sh
tools/run_all_suites.sh /path/to/eve-fit /tmp/nr
python3 tools/check_no_regress.py --baseline baselines/f.json --run-dir /tmp/nr \
  --inventory ../eve-fit-docs/docs/19-pyfa-feature-inventory.csv --update --note "eve-dogma <sha>"
```
