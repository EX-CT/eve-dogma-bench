# Bench changelog

Variants: compare scores only at the same bench version (`VERSION`, shown in results/combined.md).
Expected values always come from the Pyfa oracle (`oracle/pyfa_oracle.py`). Re-run `python3 bench.py --only <X>` after
pulling.

## 1.3.0 (2026-10-03 04:20 CST, b687270)
- New metric group `application`: per weapon `w<module_index>.{optimal_m,falloff_m,tracking,range_m,explosion_radius,
  explosion_velocity}` at `/offense/weapons[module_index=N]/<field>` (array-selector pointer, see tools/metrics.py).
  Missile `range_m` = Pyfa `missileMaxRangeData` (ship radius flight-time bonus, acceleration, floor/ceil blend).
  13 812 values.

## 1.2.0 (2026-10-03 04:10 CST, 6533a02)
- +23 cases: projected whole fits (`projected[].kind = "fit"`), projected module charges/scripts, incoming remote
  reps (Pyfa diminishing-returns formula into `/defense/tank/raw/*`), neuts/nos/cap transfers (extra cap-sim drains).
  249 cases.

## 1.1.0 (2026-10-03 04:00 CST, be77fa7)
- +19 cases: `fleet.booster_fits`, wormhole environments (`environment.effect_type_ids`), implant sets, boosters.
  226 cases.

## 1.0.0 (2026-10-03 03:45 CST, a834277)
- 207 cases, 9 827 values; runner, variants.yaml, combined scorecard.

## Harness
- results/: only `combined.{md,json}` are tracked; `--only X` merges into combined (use `--fresh` to reset).
