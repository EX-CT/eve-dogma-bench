# Pending for graphs suite 0.3 (NOT released)

Status: **proposals only.** 0.2 (`CONTRACT-GRAPHS.md` revision 0.2, 178 cases / 2437 values) remains the round-2
standard. Nothing here changes `graphs/cases`, `graphs/expected` or the contract. The probes in
`graphs/pending/probes-0.3.jsonl` are not scored by `run_graphs.py`.

## Source

G2 (eve-dogma-lab `graphs-g2` @ 40ef83c, Go engine + TS evaluator) replayed 319 random oracle requests (7493 values,
`graphs-g2/tools/check_probes.py`, `testdata/oracle-probes.jsonl`) and reported six damage/application behaviours.

## Verification (2026-10-03 CST)

1. **G2's probe file re-run through `oracle/pyfa_graph_oracle.py`:** 7493/7493 values identical. The probes are
   reproducible from the oracle.
2. **Targeted probes written for each item:** `graphs/pending/probes-0.3.jsonl`, 48 requests / 1367 values, expected
   values from the oracle.
3. **Each item checked against Pyfa's source**, read only:
   - `graphs/data/fitDamageStats/calc/application.py`
   - `cache/time.py`
   - `fitApplicationProfile/getter.py`
   - `calc/projected.py`
   - `calc/charges.py`

```
python3 graphs/pending/check_pending.py --batch-cmd "<engine> graph-batch --dataset D"            # 0.3 probes
python3 graphs/pending/check_pending.py --batch-cmd "..." --file <graphs-g2>/testdata/oracle-probes.jsonl
```

| engine | G2 probes (7493) | pending 0.3 probes (1367) |
|---|---|---|
| G1 graphs-g1 df21693 | 7493 | 1367 (all 6 items) |
| G2 (lab-g2 working copy a633bcd, run read-only) | 7486 (the 7 crossover misses its DESIGN lists) | 1278: app_grid 790/874, navy_tier 155/160, others full |

## Per-item verdicts

| # | G2 finding | oracle / Pyfa source | 0.2 coverage | verdict for 0.3 |
|---|---|---|---|---|
| 1 | sentry drones don't follow the target | **confirmed**: `getDroneMult` sets cth = 1 only if drone `maxVelocity > 1` *and* (auto & faster than target, or `follow_target`). Sentries (speed 0) always shoot from the attacker's centre, even in `follow_target` (Ishtar sentries follow_target: 0 dps at 0–5 km, 421 at 40 km) | none (sentry cases use auto vs moving targets only; the 0.2 contract wording says "or in `follow_target` mode hit with cth 1" — **inaccurate**) | **include**: wording fix + 2 cases |
| 2 | breacher per-tick damage × range hit chance | **confirmed**: `getBreacherMult` = `missileMaxRangeData` factor (1 ≤ lower range, `higherChance` up to higher range, else 0) × target fit `breacherPodDamageResistance`; applied to the per-tick `min(abs, rel·hp)` value (Kestrel vs Hyperion: 247.5 dps ≤ 5.75 km, 3.8 dps 6–9 km, 0 beyond) | time axis at 5 km only (inside lower range) | **include**: wording + 2 distance cases |
| 3 | bombs deal no damage during the reactivation delay | **confirmed** and more general: the time cache stores dps/volley per *active* cycle segment; any gap (reactivationDelay, reload) inserts a 0 point (`_prepareDpsVolleyData`, "Gap between items"). Manticore: dps 725 for t < 10 s, 0 during the delay, 725 again at 90 s / 180 s; cumulative damage steps per launch | reload gaps covered (`dmg_time_hyperion_reload`), reactivation delay not | **include**: wording + 2 bomb time cases |
| 4 | fighters staying at the ship measure distance from the ship's own surface | **confirmed (rephrased)**: if fighters don't follow (auto and slower than the target), range factor uses `distance + attacker radius − fighter radius` (fighter at the attacker's centre, like drones). Unlike drones there is **no** speed > 1 condition; `fighterAbilityLaunchBomb` ignores range | none (all 0.2 fighter cases have targets slower than the fighters → rf 1) | **include**: wording + 3 cases (target 8000 m/s) |
| 5 | application_profile samples every 1/250 of range and interpolates; range rounded up to 25 km | **interpolation confirmed, grid rule NOT**: Pyfa `getSampleStep(R)` = `max(100, ceil(R/300/100)·100)` m (target ~300 points, 100 m multiple); R = max over the dominant group of `int(optimal × longest-range charge multiplier + falloff × 3.1)` (turrets) or the longest missile max effective range (launchers); the projected cache (target speed/sig after the source's webs/TPs/scram) is sampled at 0, step, 2·step … and linearly interpolated. G2's rule (ceil(R/25 km)·100 m) coincides for short-reach fits but fails for Maelstrom 1400 mm arty + web (19–23 of 61 points around the web edge 9.6–10.6 km wrong) | none (0.2 app cases sample 0/2/5/10/20… km, outside the fade zones) | **include, flagged**: deterministic and changes `getPoint` values, so it is scoring-relevant; but it is a Pyfa plot-performance artefact that conflicts with design principle 1 ("sampling is a rendering detail"). Recommend specifying it for application_profile only (it is part of Pyfa's getter) with 2–3 cases; alternative = keep sample points ≥ 1 step away from web/TP/scram range edges |
| 6 | navy tier excludes top-tier pirate ammo | **not Pyfa's rule** (equivalent for most sub-cap guns, wrong for XL): `filterChargesByQuality`: `t1` = metaGroup 1 or NULL; `navy` = t1 + metaGroup 2 + metaGroup 4 whose name starts with an empire navy prefix (Imperial Navy / Republic Fleet / Caldari Navy / Federation Navy) — for charges named `… XL`, instead the prefixes Sansha / Arch Angel / Shadow; `all` = every valid charge (and if no charge has a meta group, the tier filter is skipped). So lower-tier pirate sub-cap ammo is *not* navy, Republic Fleet XL and Blood XL are *not* navy. G2 differs on Naglfar quad 3500 mm navy (4/10 wrong, 75–150 km) and Revelation Dual Giga Pulse navy (1/10) | contract says `t1` / `navy` / `all` without definition; corpus `app_hyperion_navy`, `app_rifter_volley_t1` only | **include**: wording + 2 XL cases |

All six are deterministic for the values. The only nondeterminism is the informational `*_charge_type_id` ties, which
are not scored. All six are reproducible headless with the existing oracle (no oracle change needed) and consistent
with the 0.2 contract structure (they refine existing definitions rather than adding inputs).

## Proposed 0.3 cases (generator-ready; requests are in probes-0.3.jsonl)

| proposed case | probe(s) | values |
|---|---|---|
| `dmg_dist_ishtar_sentries_follow_target` | `sentry_follow_drones_sentry_ishtar` | 13 |
| `dmg_dist_dominix_sentries_follow_target` | `sentry_follow_drones_sentry_dominix` | 13 |
| `dmg_dist_kestrel_breacher_fine` (5–11 km, dps + damage@30 s vs Hyperion fit) | `breacher_fine` | 50 |
| `dmg_dist_kestrel_breacher_profile` | `breacher_dist_profile` | 13 |
| `dmg_time_manticore_bomb` (dps/volley/damage, 0–120 s) | `bomb_time` | 51 |
| `dmg_time_manticore_bomb_reload` | `bomb_time_reload` | 22 |
| `dmg_dist_{templar,hel,nidhoggur}_fast_target` (target 8000 m/s, auto) | `fighters_fast_tgt_*` | 42 |
| `app_maelstrom_arty_web_edge` (9–12 km every 50 m, all + navy) | `mael_arty_{all,navy}` | 122 |
| `app_maelstrom_arty_web_tp_edge` | `mael_arty_tp_all` | 61 |
| `app_naglfar_navy_xl`, `app_revelation_navy_xl` | `app_naglfar_navy`, `app_revelation_navy` | 20 |

≈ 17 cases / ≈ 407 values. The remaining probes (sentry/fighter follow controls, hyperion/abaddon web edges, other
navy-tier fits, t1/all XL controls) are regression controls and need not enter the corpus.

## Proposed contract wording (0.3 drafts)

- **damage → Turrets / drones** (replace the drone sentence):
  "Drones with `maxVelocity` > 1 that are at least as fast as the target (mode `auto`), or any such drone in
  `follow_target` mode, hit with cth 1. Otherwise, including every sentry drone (speed ≤ 1) in any mode, the drone
  shoots from the attacker's centre: distance = d + r_attacker − r_drone, speed = min(attacker speed, drone speed)."
- **damage → fighters**: "Fighter abilities other than bombs: range factor 1 when the fighter follows (mode `auto` and
  fighter speed ≥ target speed, or `follow_target`, with no minimum speed); otherwise `calculateRangeFactor` at
  d + r_attacker − r_fighter. Missile factor from the ability's explosion radius/velocity and aggregated drf; × the
  target fit's `<prefix>ResistanceID` attribute. `fighterAbilityLaunchBomb`: no range check, bomb factor only."
- **damage → breacher pods**: "application = (1 if d ≤ lowerRange; higherChance if d ≤ higherRange; else 0) from
  `missileMaxRangeData` × target fit `breacherPodDamageResistance` (1 for profiles); it multiplies the per-tick value
  min(absolute, relative·HP)."
- **damage → time cache**: "dps/volley at t come from the active cycle segment containing t; between segments
  (reactivation delay, reload) they are 0. `damage` is cumulative and keeps its value during gaps."
- **application_profile → projected effects**: "With `apply_projected`, the target's speed and signature after the
  source's webs, TPs and scram are evaluated at d = 0, s, 2s, … ≤ R and interpolated linearly in between, where
  s = max(100, ceil(R / 30000) · 100) m and R = the maximum over the dominant weapon group of
  int(optimal × longest-range charge multiplier + 3.1 × falloff) for turrets, or the longest missile effective range
  for launchers. Values therefore differ from `damage` near web/TP/scram range edges. This is Pyfa behaviour, kept
  deliberately."
- **application_profile → quality tiers**: "`t1`: metaGroup 1 or no metaGroup. `navy`: `t1` + metaGroup 2 +
  metaGroup 4 whose name starts with Imperial Navy / Republic Fleet / Caldari Navy / Federation Navy. For charges
  whose name ends in ' XL', the prefixes are Sansha / Arch Angel / Shadow instead. `all`: every valid charge. If no
  candidate has a metaGroup, the tier filter is not applied." Dataset note: dataset-3569502 has no metaGroupID per
  type; engines derive it (G1: meta level 5 → 2, variation parent → 4, else 1; identical to eve.db for every
  turret/missile charge).

## Not proposed

- G2's "known deviation" (Pyfa keeps the previous charge for a few metres inside an interpolated stretch,
  Hyperion navy 10 006–10 011 m) is the coarse transition scan (`getSampleStep` + 10 m bisection). It is
  deterministic and G1 reproduces it, but points that close to a crossover are fragile (tie order, float). Keep
  sample points away from crossovers; don't score it.
