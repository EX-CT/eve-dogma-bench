# eve-dogma graphs contract (DRAFT, round 2, revision 0.1)

Extension of the eve-dogma request/response contract (`CONTRACT.md`, revision 1.4.3) with **Pyfa's graph
subsystem** (`graphs/data/*` in Pyfa). Same style and rules as the base contract: stateless, **one JSON
`GraphRequest` in → one JSON `GraphResult` out**, no clocks, no network, byte-identical output for identical input on
the same dataset, unknown request fields ignored. Expected values come from Pyfa itself
(`oracle/pyfa_graph_oracle.py` runs Pyfa's own getters headless).

Status: draft for review. Nothing here is part of 1.x scoring. Field names may still change before revision 1.0.

## Process interface (CLI / RPC)

| Mode | Command | I/O |
|---|---|---|
| single | `eve-dogma graph [FILE]` | GraphRequest JSON on stdin (or FILE) → GraphResult JSON on stdout. Exit 0, or exit 2 with `{"error":…}` on stdout |
| batch | `eve-dogma graph-batch` | one GraphRequest per line (JSONL) → one GraphResult per line, same order; a failing line yields its `{"error":…}` line |
| rpc | `eve-dogma serve-stdio` | new method `graph`: `{"id","method":"graph","params":<GraphRequest>}` → `{"id","result":<GraphResult>}` |

Variants announce support in `bench.yaml` with any of `graph_cmd`, `graph_batch_cmd`, or (via `rpc_cmd`) the `graph`
method. Errors use the base contract's `{"error":{"code","message","path"}}`; new codes: `UNKNOWN_GRAPH`,
`BAD_AXIS` (x axis or y series not valid for the graph).

## Design principles

1. **Explicit sample points.** The request lists the x values; the engine evaluates the curve exactly there
   (Pyfa `FitGraph.getPoint` semantics, the "x mark" value). Pyfa's adaptive plot sampling (`getRange`:
   `_baseResolution` + `_extraDepth` bisection, capsim event insertion) is a rendering detail and is **not** part
   of the contract. A UI samples as densely as it likes.
2. **SI units everywhere.** Pyfa's display units (km, AU, Mkg, Gkg⋅m/s, %-of-target) are normalised away:
   distances m, times s, speeds m/s, mass kg, capacitor GJ, HP, momentum kg⋅m/s. The only percentages are
   inputs/axes that Pyfa itself defines relative to the fit (`*_pct`) and the EWAR strength outputs, which Pyfa
   defines as percent.
3. **Each point is independent.** Engines must not let one sample influence another (Pyfa's caches are keyed by
   fit id; the oracle uses fresh caches per point).
4. **Distances are surface-to-surface** (as in the overview, and as Pyfa's inputs). Engines add ship radii where the
   math needs centre-to-centre distance.
5. **`null`** is returned where Pyfa returns `None` or a non-finite number, and for x values outside the graph's
   valid range ("limiters", listed per graph). Never `NaN`/`Infinity` in JSON.

## GraphRequest

```jsonc
{
  "schema_version": 1,
  "graph": "damage",                       // see "Graph types"
  "fit": { /* FitRequest (CONTRACT.md) of the source / attacker */ },
  "target": {                              // only graphs `damage` and `application_profile`; default = ideal target
    "profile": {"em": 0.0, "thermal": 0.0, "kinetic": 0.0, "explosive": 0.0,   // resist fractions 0..1
                "max_velocity": 250, "signature_radius": 125, "radius": 150,   // m/s, m (null sig = infinite), m
                "hp": null}                                                    // total HP (null = infinite); informational
    // or: "fit": { /* FitRequest */ }, "resist_mode": "auto"   // auto | shield | armor | hull | weighted_average
  },
  "x": {"axis": "distance_m", "values": [0, 1000, 5000]},   // axis valid for the graph; values in the axis unit
  "y": ["dps", "volley"],                  // one or more series valid for the graph
  "params": { /* graph-specific inputs, see below; omitted = Pyfa GUI defaults */ },
  "settings": {                            // Pyfa graph settings (GraphSettings) — defaults shown
    "ignore_resists": true,                // damage/app: ignore target resists (Pyfa default true)
    "apply_projected": true,               // damage/app: apply the source's own webs/TPs (+ scram vs MWD) to the target
    "ignore_lock_range": true,             // weapons/ewar/RR still apply beyond the source's lock range
    "ignore_drone_control_range": false,   // drones apply beyond drone control range
    "mobile_drone_mode": "auto"            // auto | follow_attacker | follow_target
  }
}
```

The x value `null` is not allowed in `x.values`. Parameters that Pyfa allows to be "not set" (e.g. damage `distance_m`,
`time_s`) take `null` = not set.

## GraphResult

```jsonc
{
  "graph": "damage",
  "x_axis": "distance_m",
  "x": [0, 1000, 5000],                    // echo of the request values
  "series": {"dps": [58.27, 261.25, 239.54], "volley": [201.2, 465.7, 437.5]},   // one array per requested y, same length as x
  "meta": { /* optional, informational: e.g. resolved target_speed_mps, target resist layer */ }
}
```

Application profile additionally returns `"<y>_charge_type_id": [...]` arrays (the charge Pyfa picks at each
point; informational, see that graph).

## Graph types

Notation: `src` = source fit after a normal `calc` (same FitRequest semantics, including `projected`,
`fleet`, `environment` applied to it). "Pyfa:" names the Pyfa getter class that defines the value.

### `damage` — Pyfa "Damage Stats" (`fitDamageStats`)

| x axis | unit | valid range | notes |
|---|---|---|---|
| `distance_m` | m | ≥ 0 | surface-to-surface distance |
| `time_s` | s | 0 … 2500 (else `null`) | |
| `tgt_speed_mps` | m/s | ≥ 0 | target's current speed (absolute) |
| `tgt_sig_m` | m | > 0 | target signature radius before the source's TPs |

| y | unit | definition |
|---|---|---|
| `dps` | HP/s | Σ over damage dealers of dps × application (× (1 − resist) unless `ignore_resists`) |
| `volley` | HP | same with volley (best volley of the current cycle for time axis) |
| `damage` | HP | cumulative damage inflicted from t = 0 to `time_s` (needs `params.time_s` unless x = `time_s`; else `null`) |

| param | default | meaning |
|---|---|---|
| `distance_m` | `null` | when x ≠ distance. `null` = "not set": every weapon hits, no range/tracking penalty from distance (Pyfa: distance None → range factor 1, angular speed 0) |
| `time_s` | `null` | when x ≠ time. `null` = stats-panel dps/volley (spool at `globalDefaultSpoolupPercentage` = 100 %); a number = exact state at that time (spool by cycles, **reloads always included**, Pyfa `getCycleParametersForDps(reloadOverride=True)`) |
| `tgt_speed_mps` / `tgt_speed_pct` | 100 % of target max velocity | target speed (absolute wins over pct) |
| `atk_speed_mps` / `atk_speed_pct` | 0 % | attacker speed |
| `atk_angle_deg`, `tgt_angle_deg` | 90, 90 | movement directions; transversal = \|v_a·sin(a_a) − v_t·sin(a_t)\| |

Definitions (Pyfa `graphs/data/fitDamageStats/calc/application.py`):
- Damage dealers: active modules with `isDealingDamage`, active drones, active fighter abilities that deal damage.
  At `time_s` set, dps/volley/damage per dealer come from the time cache (`cache/time.py`): cycle by cycle from
  t = 0 (module `getCycleParametersForDps(reloadOverride=True)`, volley parameters with
  `SpoolOptions(CYCLES, nonstopCycles)`, breacher pods offset 1 s), value at t = last change point ≤ t (with
  `floatUnerr` comparison).
- Turrets / drones: chance to hit = range factor (`calculateRangeFactor`, not restricted to 3× falloff) ×
  `0.5^((ω·optimalSigRadius/(tracking·sig))²)`, ω = transversal / (r_atk + distance + r_tgt); damage multiplier
  from chance to hit with 1 % wrecking hits (×3) and the (0.01 + cth)/2 + 0.49 average (`_calcTurretMult`).
  Drones faster than the target (mode auto) or in `follow_target` mode hit with cth 1; otherwise they are
  placed at the attacker's centre, moving at min(attacker speed, drone speed).
- Missiles: distance factor from `missileMaxRangeData` (lower range → 1, between lower and higher → higher chance,
  beyond → 0) × `min(1, sig/eR, (eV·sig/(eR·v))^drf)`; FoF ignores lock range. Vorton: range factor (no falloff)
  × missile formula with the module's aoe attributes. Smartbombs: 1 inside range, else 0. Bombs / guided bombs /
  doomsdays / breachers / fighter abilities as in Pyfa (doomsday: `min(1, sig/signatureRadius)`; titan single-target
  DDs 0 vs sub-capital target fits).
- Application multipliers are rounded with `floatUnerr` before use.
- `apply_projected`: the source's own active webs and TPs (modules with range factor; drones/fighters as mobile
  sources) slow / paint the target, stacking-penalised together with the target fit's own modifiers (Pyfa
  `getTackledSpeed`, `getSigRadiusMult`, `getModifiedItemAttrExtended`); a source scram in range also cancels the
  target fit's MWD/MJD. Target speed keeps its ratio to the target's max speed. Targets with
  `disallowOffensiveModifiers` are not affected.
- Resists (`ignore_resists: false`): profile resists, or for a target fit the layer chosen by `resist_mode`
  (`auto` = Pyfa `_getAutoResists` scoring of EHP, resist factor, active tank and regen; `weighted_average` = HP-weighted).

### `application_profile` — Pyfa "Application Profile" (`fitApplicationProfile`, newer Pyfa)

x: `distance_m` (≥ 0). y: `dps`, `volley` — the best value over every charge the fit's dominant weapon group can
load (Pyfa `getValidChargesForModule`, quality tier `params.ammo_quality`: `t1` | `navy` | `all`, default `all`),
with the same application math and target parameters as `damage` (settings `ignore_resists` /
`apply_projected` map to Pyfa's `ammoOptimal*` settings). Returns `<y>_charge_type_id` per point:
**informational only** — Pyfa breaks exact DPS ties between equal-stat faction charges (e.g. Dark Blood vs True
Sansha) by set iteration order, so the id is not well defined. Params: `tgt_speed_*`, `atk_speed_*`, angles as for
`damage`.

### `ewar` — Pyfa "Electronic Warfare Stats" (`fitEwarStats`)

x: `distance_m` (≥ 0). Param `resist` (0..1, default 0; target's resistance to the EWAR type).
Sources: active modules (incl. burst projectors `doomsdayAOE*`, range = maxRange + doomsdayAOERange, no lock
needed), active drones (need lock + drone control range), active fighter abilities (need lock).

| y | unit | definition |
|---|---|---|
| `neut_gj_s` | GJ/s | Σ energyNeutralizerAmount / avg cycle s × (1 − resist) × rf (nosferatu only with `nosOverride`) |
| `web_pct` | % | speed reduction `(1 − m)·100`, m = stacking-penalised product (`calculateMultiplier`) of `1 + speedFactor·(1 − resist)·rf/100` |
| `ecm_strength` | points | Σ max(racial jam strengths) × (1 − resist) × rf |
| `damp_lock_range_pct` | % | lock range reduction `(1 − m)·100` from `maxTargetRangeBonus` |
| `td_optimal_pct` | % | turret optimal reduction `(1 − m)·100` from `maxRangeBonus` |
| `gd_range_pct` | % | missile flight range reduction `(1 − m_vel·m_time)·100` from `missileVelocityBonus` and `explosionDelayBonus` (guidance disruptors) |
| `tp_sig_pct` | % | signature increase `(m − 1)·100` from `signatureRadiusBonus` |

rf = range factor. Range factor = `calculateRangeFactor` (restricted: 0 beyond optimal + 3 × falloff). Drones/fighters: infinite range.

### `remote_reps` — Pyfa "Remote Repairs" (`fitRemoteReps`)

| x | unit | valid |
|---|---|---|
| `distance_m` | m | ≥ 0 |
| `time_s` | s | 0 … 2500 |

y: `rps` (HP/s, shield+armor+hull; energy transfers excluded), `total` (HP repaired from t = 0; needs
`params.time_s` unless x = time). Params: `distance_m`, `time_s` (as for `damage`), `anc_reload` (default true:
ancillary remote reps include their reload; Pyfa checkbox "Reload ancillary RRs"). Range factor
`calculateRangeFactor(optimal, falloff, d)`; drones 1 inside drone control range.

### `capacitor` — Pyfa "Capacitor" (`fitCapacitor`)

| x | unit | valid |
|---|---|---|
| `time_s` | s | 0 … 3600 |
| `cap_pct` | % of capacitorCapacity | 0 … 100 |

y: `cap_gj` (GJ), `cap_regen_gj_s` (GJ/s, passive recharge at that cap level). Params: `cap_start_pct`
(default 100), `use_capsim` (default true).
- `time_s` + `cap_gj` with `use_capsim`: Pyfa's capacitor simulator (`Fit.getCapSimData(startingCap)`: stagger on,
  reload = `options.factor_reload`, t_max 3600 s, no repeat optimisation); the value at t is the last simulated
  point ≤ t advanced by the regen formula; `null` once the simulation has ended (cap ran out) and t is past its last
  point. Without drains or `use_capsim: false`: regen only,
  `C·(1 + e^(−5t/τ)·(√(C0/C) − 1))²`, τ = rechargeRate/1000.
- `cap_regen_gj_s` = `10·C/τ·(√(c/C) − c/C)` at the cap level c of the point (regen-only curve on the time axis).

### `shield_regen` — Pyfa "Shield Regeneration" (`fitShieldRegen`)

x: `time_s` (≥ 0) or `shield_pct` (0 … 100 of shieldCapacity). y: `shield_hp`, `shield_regen_hp_s`. Params:
`shield_start_pct` (default 0), `effective` (default false: when true both y are EHP using the fit's
`damage_pattern`, Pyfa `effectivify(ship, v, "shield")`). Same formulas as capacitor with shieldCapacity /
shieldRechargeRate.

### `mobility` — Pyfa "Mobility" (`fitMobility`)

x: `time_s` (≥ 0, from standstill, full throttle). y:
`speed_mps` = v·(1 − e^(−t·10⁶/(agility·mass))); `distance_m` (integral of speed); `momentum_kg_mps` = speed·mass;
`bump_speed_mps` = 2·v_s·m_s/(m_s + m_t) (masses in Mkg); `bump_distance_m` = bump speed · m_t(Mkg) · tgt_inertia.
Params `tgt_mass_kg` (default 1.3e9), `tgt_inertia` (default 0.015). v = ship maxVelocity with all active
modules.

### `warp_time` — Pyfa "Warp Time" (`fitWarpTime`)

x: `distance_m` (0 … maxWarpDistance(AU)·149597870700, else `null`). y: `time_s` — Pyfa `calculate_time_in_warp`
(EVE University model): k_accel = warp speed (AU/s), k_decel = min(warp/3, 2), dropout speed = min(subwarp/2,
100), cruise only if distance > 1 AU + decel distance. **Subwarp speed** is the ship's max velocity recomputed with
propulsion / cloak / siege / doomsday / cyno / jump-portal modules set to online and every projected effect on the
fit switched off (Pyfa `SubwarpSpeedCache`). 0 m → 0 s.

### `lock_time` — Pyfa "Lock Time" (`fitLockTime`)

x: `tgt_sig_m` (≥ 1, else `null`). y: `time_s` = `min(40000 / scanResolution / asinh(sig)², 1800)` (if
scanResolution ≤ 0: scanSpeed/1000).

Not covered: Pyfa's hidden experimental "ECM Burst + Scanres Damps" graph (`fitEcmBurstScanresDamps`).

## Scoring (bench, branch `graphs-round2`)

`graphs/run_graphs.py` compares every sample value with the corpus tolerance
(|got − want| ≤ max(1e-3, 1e-4·|want|), or both `null`), grouped by graph type; `*_charge_type_id` series are
reported separately and not scored. Corpus: `graphs/cases/*.json` (GraphRequests, fits embedded) and
`graphs/expected/*.json` (Pyfa values).

## Changelog

- 0.1 (2026-10-03): first draft; 9 graph types (Pyfa's 9 public graphs), explicit sampling, SI units.
