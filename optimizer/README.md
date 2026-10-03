# optimizer-bench (WIP, 0.1) — docs/21 `optimizer-suite`

**Status: work in progress, paused 2026-10-03 (priority change).** Cases and Pyfa-checked reference optima are done;
the scorer, baselines and full docs are not.

Done:
- `specs.py`: 27 case specs (dps 6, ehp 5, tank 4, speed 4, cap_stable 4, price 4). Small explicit pools per rack.
- `prices.json`: pinned synthetic price table (not market data), made by `tools/make_prices.py`.
- `tools/make_cases.py`: exhaustive search (every multiset per rack, 600–50,400 fits per case) scored by F `4b8f5f9`
  (Pyfa-validated engine). Writes `cases/<id>.json` (docs/21 OptimizeRequest + `search.pools`) and
  `expected/<id>.json` (optimum, every tied fit, second best, 5 runners-up, space size, rejection counts,
  `constraints_effect` = whether CPU / PG / calibration / slots-hardpoints-maxGroup / skills / meta / price / floors /
  cap_stable actually bind).
- `tools/pyfa_check.py`: Pyfa oracle (unchanged `oracle/pyfa_oracle.py`, ORACLE_EXTRA=validity) on the winners and
  runners-up: 27/27 agree (worst rel diff 1.1e-8), ranking preserved, winners legal in Pyfa.

Remaining (not started):
- `score.py`: input JSONL `{"case","fit","wall_ms"}`; legality (pool membership, rack sizes, keep modules, `lib.precheck`
  + engine `lib.postcheck`); gap = `lib.gap`; planned case score `q * min(1, time_ms / wall_ms)` with
  `q = 1 - min(1, gap / 0.25)`, illegal = 0; aggregate = mean × 100 plus per-objective means, hit rate, median gap.
- `baselines/` (greedy, random) run through the scorer; full README on formats.

Regenerate: `python3 optimizer/tools/make_prices.py && python3 optimizer/tools/make_cases.py && python3 optimizer/tools/pyfa_check.py`
(env `EVE_OPT_ENGINE`, `EVE_DOGMA_DATASET`, `REF`).
