# pending-1.10 (staged, not released)

Branch from main (32295d5, bench 1.8.0). Holds minimal repro cases for **real engine bugs** found by the
legal-fit differential fuzz (A = eve-dogma-rs vs the Pyfa oracle, E 5867d53 for reference), 2026-10-03.

## Tools (GPL, Pyfa used as a library, same as `oracle/pyfa_oracle.py`)
- `oracle/fuzz/gen_legal.py OUTDIR N SEED`: random **legal** ship fits. Ship group stratified; modules are added
  only if Pyfa's `Module.fits` accepts them (slot counts after T3C subsystems, turret/launcher hardpoints, rig size,
  canFitShipGroup/Type, fitsToShipType, maxGroupFitted, no capital modules on subcaps) plus maxTypeFitted;
  charges from `Module.getValidCharges`; states respect isValidState + maxGroupOnline/maxGroupActive;
  T3D/Anhinga get a mode; drones within bay/bandwidth/5 active; fighters within tubes/class slots/bay;
  implants/boosters in distinct slots. CPU/PG/calibration not enforced. Structures excluded.
- `oracle/fuzz/check_legal.py REQ...`: the same rules as a checker (one JSON line per request). Rigs must be online
  (EVE can't offline a rig; Pyfa can). "state above the module's max" is only a note, because the contract clamps it.
- `oracle/fuzz/compare.py FITS OUT`: oracle (bench-1.9.0 `pyfa_oracle.py` + `metrics.py`) vs A and E on every fit.
  `minimize.py FIT METRIC OUT`: greedy delta minimiser (drop modules/drones/implants/boosters/charges while the
  A-vs-Pyfa gap on METRIC stays). `drift.py`: per-type attribute/effect drift, Pyfa eve.db vs dataset 3569502.
  The paths in these three are hard-coded to the EXCT box.

## Sweep (2026-10-03 10:50–11:00 CST)
`gen_legal.py fits 200 10` → 200 fits, all `check_legal` OK; 46 ship groups (4 T3C, 5 T3D, 12 with fighters,
74 with drones, 117 with implants, 51 with boosters). 12 057 compared values. A = eve-dogma-rs e4c42db, E = variant-e 5867d53.

| | fits | values | class |
|---|---|---|---|
| A = Pyfa on every value | 190 | | |
| Paladin (28659) agility: Pyfa eve.db build 3532181 has 0.858 vs SDE 3569502 0.0858 (A = E) | 2 | 2 | (a) oracle data drift (already known) |
| A ≠ Pyfa, **E = Pyfa** | 8 | 8 | (c) A bugs below |

A first pass with the same seed had 26 more diffs, all `calibration_used` (A counted offline rigs, Pyfa and E don't).
Every one of them was an offline rig. EVE can't offline a rig, so these were (b) illegal fits. The generator now
keeps rigs online; that changed exactly those 26 fits. If the bench does want offline rigs, A should count
`upgradeCost` only for rigs that are online, like Pyfa `getItemAttrOnlineSum`.

## (c) A bugs, with minimal repro cases (`cases/e_fz_*.json`, `expected/e_fz_*.json`, 1.9.0 format)
Each case is legal by `check_legal.py`. **A fails exactly one value on each one and E passes all of them.**

| Case | Bug | A | Pyfa = E |
|---|---|---|---|
| `e_fz_drone_speed_orbweaver_dagon` (Dagon, 3× Orbweaver SW-300-I active) | **E1** Drones with both `targetAttack` and an EWAR effect (group 5239: SW-300 / TD-900 …): A uses the EWAR effect's `duration` (73, 5000 ms) as the damage cycle. Pyfa and the SDE `targetAttack.duration_attr` use `speed` (51, 4000 ms). Gap is −20 % drone dps, at any skill level | drone_dps 38.81 | 48.52 |
| `e_fz_drone_speed_torafugu_odysseus` (Odysseus, Torafugu TD-900-I ×5, 1 active) | E1, same bug on the TD drone | 58.22 | 72.77 |
| `e_fz_offline_cloak_hulk` (Hulk, Dread Guristas Cloaking Device **offline**) | **E2** Pyfa `type = 'offline'` effects apply even when the module is offline: 854 cloak scanResolution, 3046 Expanded Cargohold maxVelocity, 6737 command-burst charge, 11714 Disruptive Lance cloak block. A applies none of them to an offline module | scan_resolution 825 | 536.25 |
| `e_fz_offline_expanded_cargohold_rifter` (Rifter, Expanded Cargohold II offline) | E2 control on 3046 | max_velocity 456.25 | 374.125 |
| `e_fz_cloak_wcs_penalty_group_ninazu` (Ninazu, Estamel's cloak active + 'Halcyon' Core Equalizer I) | **E3** Pyfa puts the cloak scanResolution multiplier in its own stacking-penalty group (`penaltyGroup='cloakingScanResolutionMultiplier'`). A stacks it together with the WCS `scanResolutionMultiplier` | 35.18 | 33.93 |
| `e_fz_capsim_overheat_cycle_zarmazd` (Zarmazd, 2× Small Inefficient Hull Repair Unit, one overheated) | **E4** Cap sim: A uses the overheated cycle time 15300.0 ms. Pyfa (and E) use the float 15299.999999999998, so the sim period differs (A 111 iterations, E 2612) | cap_stable_percent 91.049 | 91.020 |
| `e_fz_capsim_overheat_cycle_revelation_ni` (Revelation Navy Issue, smartbomb + small armor rep, both overheated) | E4, same (A 3825.0 vs 3824.9999999999995 ms) | 81.966 | 81.954 |
| `e_fz_cpu_round_tie_gold_magnate` (Gold Magnate, 125mm Carbide Railgun I + Small Algid Hybrid Administrations Unit I) | **E5** Multiplication order at a `round(v, 2)` tie: A computes 11 × 0.75 × 0.9 = 7.42499999… → 7.42. Pyfa computes rig then skill, 11 × 0.9 × 0.75 = 7.4250000000000007 → 7.43 | cpu_used 7.42 | 7.43 |

Notes for adjudication:
- E1 is unambiguous: Pyfa and the SDE `duration_attr` of `targetAttack` agree.
- E2 and E3 come from Pyfa hand-written effect modelling, not SDE modifiers: effect 854 has SDE category 0 and
  plain PostMul. The bench scores Pyfa parity, so they are listed as A bugs. If eve rules SDE semantics instead,
  move them to `known_divergences` (a).
- E4 and E5 are float-order artefacts, at most 0.03 percentage points of cap and 0.01 tf of CPU. They are real A ≠ Pyfa values at the bench tolerance.
