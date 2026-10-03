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
- `oracle/fuzz/check_legal.py REQ...`: the same rules as a checker (one JSON line per request).

## Findings
(in progress)
