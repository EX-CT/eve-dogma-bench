# Bench changelog

Variants: compare scores only at the same bench version (`VERSION`, shown in results/combined.md).
Expected values always come from the Pyfa oracle (`oracle/pyfa_oracle.py`). Re-run `python3 bench.py --only <X>` after
pulling.

## 1.4.1 (2026-10-03 05:40 CST)
- CONTRACT.md = eve-dogma contract revision 1.4.1 (coordinator rulings): (1) a calc error exits 2 and still prints
  the `{"error":…}` JSON on stdout; (2) `options` missing entirely → `validate` defaults to true; (3) `search` is out
  of dogma scoring, interim spec only (limit 20; kinds ship/module/charge/drone/fighter/implant/booster/subsystem/skill;
  exact > prefix > substring; ties by typeID ascending); (4) `eft_export` must match Pyfa's exporter byte for byte
  (Pyfa writes no T3D mode line); (5) duplicate changelog heading removed.
- Corpus and accuracy scoring unchanged (289 cases, 18 591 values): scores from 1.4.0 remain comparable.
- New informational check (not in accuracy): EFT export vs Pyfa `exportEft` (all options on, after GUI `fill()`),
  `expected_extra/eft_export.jsonl` (289 fits; `oracle/pyfa_eft_export.py` generates it). Run
  `python3 tools/check_eft_export.py --rpc-cmd "<engine serve-stdio>"`, or add `rpc_cmd:` to bench.yaml and bench.py
  shows an "eft export" column. RPC: JSONL `{"id","method":"eft_export","params":{"fit","name"}}` →
  `{"id","result":{"text"}}`. Accepted data divergence: T3C maxSubSystems 5 (SDE) vs 4 (Pyfa eve.db).

## 1.4.0 (2026-10-03 04:50 CST)
- +40 cases (289): sustainable tank (factor_reload / neuted fits), ECM (racial/multispectral modules, falloff, EC drones,
  burst jammer), projected fighters (`projected[].kind = "fighter"`, `fighter`: FighterReq; web / point / neut / ECM),
  active drones (light/medium/heavy/sentry), local fighter abilities (MWD / evasive / MJD via `fighters[].abilities`),
  booster side effects (`boosters[].side_effects` = effect IDs).
- New metrics (18 591 values): `stank.{armor,shield,hull}` → `/defense/tank/sustained/*` (Pyfa `sustainableTank`),
  `jam_chance` → `/targeting/jam_chance_percent` (Pyfa `jamChance`, 0 when no ECM), `warp_scramble_status` →
  `/navigation/warp_scramble_status`, `drone_control_range` → `/drones/control_range_m`, per active damaging drone
  `d<drone_index>.{optimal_m,falloff_m,tracking,max_velocity,signature_radius}` → `/offense/drones[drone_index=N]/…`,
  per damaging fighter `f<fighter_index>.{max_velocity,signature_radius}` → `/offense/fighters[fighter_index=N]/…`.
- Known divergence: Networked Sensor Array `warpScrambleStatus` (SDE +100, Pyfa omits) for Hel/Nidhoggur cases.
- Note: `capacitor.use_gj_s` semantics (contract v1.4) not scored.

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
