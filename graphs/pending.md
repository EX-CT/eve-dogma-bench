# Pending for graphs suite 0.3 (NOT released)

> **Rulings (eve, 2026-10-03 08:46 CST):**
> - Items 1–4 and 6 are **included** as scored cases, with the contract wording fixes.
> - Item 5 is **not scored**. Pyfa's grid step is documented in the contract as informational only, and sample
>   points are kept away from web/TP edges.
> - Ammo-switch hysteresis is **not scored**.
> - Round 2 is scored on **0.2 as frozen at 0397d95**.
>
> Implemented as an unreleased draft in `graphs/draft-0.3/` (contract, corpus, scorer, edge check). The 0.2 paths
> are untouched. Status of each item: see the "Ruling" column below and graphs/draft-0.3/README.md.

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

| # | G2 finding | oracle / Pyfa source | 0.2 coverage | verdict for 0.3 (Ruling) |
|---|---|---|---|---|
| 1 | sentry drones don't follow the target | **confirmed**: `getDroneMult` sets cth = 1 only if drone `maxVelocity > 1` *and* (auto & faster than target, or `follow_target`). Sentries (speed 0) always shoot from the attacker's centre, even in `follow_target` (Ishtar sentries follow_target: 0 dps at 0–5 km, 421 at 40 km) | none (sentry cases use auto vs moving targets only; the 0.2 contract wording says "or in `follow_target` mode hit with cth 1" — **inaccurate**) | **include** → ruled IN: draft cases `dmg_dist_{ishtar,dominix}_sentries_follow_target` |
| 2 | breacher per-tick damage × range hit chance | **confirmed**: `getBreacherMult` = `missileMaxRangeData` factor (1 ≤ lower range, `higherChance` up to higher range, else 0) × target fit `breacherPodDamageResistance`; applied to the per-tick `min(abs, rel·hp)` value (Kestrel vs Hyperion: 247.5 dps ≤ 5.75 km, 3.8 dps 6–9 km, 0 beyond) | time axis at 5 km only (inside lower range) | **include** → ruled IN: `dmg_dist_kestrel_breacher_{fine,profile}` |
| 3 | bombs deal no damage during the reactivation delay | **confirmed** and more general: the time cache stores dps/volley per *active* cycle segment; any gap (reactivationDelay, reload) inserts a 0 point (`_prepareDpsVolleyData`, "Gap between items"). Manticore: dps 725 for t < 10 s, 0 during the delay, 725 again at 90 s / 180 s; cumulative damage steps per launch | reload gaps covered (`dmg_time_hyperion_reload`), reactivation delay not | **include** → ruled IN: `dmg_time_manticore_bomb{,_reload}` |
| 4 | fighters staying at the ship measure distance from the ship's own surface | **confirmed (rephrased)**: if fighters don't follow (auto and slower than the target), range factor uses `distance + attacker radius − fighter radius` (fighter at the attacker's centre, like drones). Unlike drones there is **no** speed > 1 condition; `fighterAbilityLaunchBomb` ignores range | none (all 0.2 fighter cases have targets slower than the fighters → rf 1) | **include** → ruled IN: `dmg_dist_{thanatos_templar,hel,nidhoggur}_fast_target` |
| 5 | application_profile samples every 1/250 of range and interpolates; range rounded up to 25 km | **interpolation confirmed, grid rule NOT**: Pyfa `getSampleStep(R)` = `max(100, ceil(R/300/100)·100)` m (target ~300 points, 100 m multiple); R = max over the dominant group of `int(optimal × longest-range charge multiplier + falloff × 3.1)` (turrets) or the longest missile max effective range (launchers); the projected cache (target speed/sig after the source's webs/TPs/scram) is sampled at 0, step, 2·step … and linearly interpolated. G2's rule (ceil(R/25 km)·100 m) coincides for short-reach fits but fails for Maelstrom 1400 mm arty + web (19–23 of 61 points around the web edge 9.6–10.6 km wrong) | none (0.2 app cases sample 0/2/5/10/20… km, outside the fade zones) | **include, flagged**: deterministic and changes `getPoint` values, so it is scoring-relevant; but it is a Pyfa plot-performance artefact that conflicts with design principle 1 ("sampling is a rendering detail"). → **ruled NOT scored**: step formula documented as informational in the 0.3 draft contract; corpus points verified off edges with `graphs/draft-0.3/tools/edge_check.py` (0 sensitive); `app_maelstrom_arty_web_tp_off_edge` samples projected webs/TPs away from the edge |
| 6 | navy tier excludes top-tier pirate ammo | **not Pyfa's rule** (equivalent for most sub-cap guns, wrong for XL): `filterChargesByQuality`: `t1` = metaGroup 1 or NULL; `navy` = t1 + metaGroup 2 + metaGroup 4 whose name starts with an empire navy prefix (Imperial Navy / Republic Fleet / Caldari Navy / Federation Navy) — for charges named `… XL`, instead the prefixes Sansha / Arch Angel / Shadow; `all` = every valid charge (and if no charge has a meta group, the tier filter is skipped). So lower-tier pirate sub-cap ammo is *not* navy, Republic Fleet XL and Blood XL are *not* navy. G2 differs on Naglfar quad 3500 mm navy (4/10 wrong, 75–150 km) and Revelation Dual Giga Pulse navy (1/10) | contract says `t1` / `navy` / `all` without definition; corpus `app_hyperion_navy`, `app_rifter_volley_t1` only | **include** → ruled IN: `app_{naglfar,revelation,moros}_navy_xl` |

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

## Not proposed (ruled: not scored)

- G2's "known deviation" (Pyfa keeps the previous charge for a few metres inside an interpolated stretch,
  Hyperion navy 10 006–10 011 m) is the coarse transition scan (`getSampleStep` + 10 m bisection). It is
  deterministic and G1 reproduces it, but points that close to a crossover are fragile (tie order, float). Keep
  sample points away from crossovers; don't score it.

## Differential fuzz 2026-10-03 08:53 CST (seed 1, 400 requests)

Variants: G1 `df21693`, G2 `6c5211e`, G3 `63e728b`, G4 `463d945`. Disagreements 28, confirmed by the oracle 28, oracle errors 0. Wrong answers by variant: {'G2': 27, 'G3': 1}.

- **fuzz_application_profile_distance_m_fz0026-3426c1a0**: application_profile / distance_m; features `tgt-profile ignore_lock_range=True`; wrong: **G2**; matches oracle: G1, G3, G4; 9 fuzz request(s) in this cluster. Example: `{"G2": [{"y": "dps", "x": 31748.9, "got": 363.5669234047936, "want": 356.8755072170638}, {"y": "dps", "x": 34847.1, "got": 259.3290309680891, "want": 254.55610434470006}, {"y": "dps", "x": 60360.019, "got": 18.710652126287087, "want": 18.3662839644073}]}`
- **fuzz_capacitor_time_s_fz0035-0cbad615**: capacitor / time_s; features `tgt-ideal cap_start_pct use_capsim`; wrong: **G2**; matches oracle: G1, G3, G4; 14 fuzz request(s) in this cluster. Example: `{"G2": [{"y": "cap_regen_gj_s", "x": 0, "got": 1.9111809436304437, "want": 0.0}, {"y": "cap_regen_gj_s", "x": 166.424, "got": 12.822747222106026, "want": 0.0}, {"y": "cap_regen_gj_s", "x": 332.0, "got": 13.862162950790522, "want": 0.0}]}`
- **fuzz_damage_tgt_speed_mps_fz0117-30c2b6f9**: damage / tgt_speed_mps; features `tgt-profile ignore_lock_range=False ignore_resists=True distance_m tgt_speed_pct time_s`; wrong: **G2**; matches oracle: G1, G3, G4; 2 fuzz request(s) in this cluster. Example: `{"G2": [{"y": "dps", "x": 116.0, "got": 0, "want": 41.53094439333468}, {"y": "dps", "x": 154.7, "got": 0, "want": 41.53094439333468}, {"y": "dps", "x": 251.6, "got": 0, "want": 41.53094439333468}]}`
- **fuzz_damage_tgt_sig_m_fz0122-b406fadf**: damage / tgt_sig_m; features `tgt-profile ignore_resists=True mobile_drone_mode=follow_attacker time_s`; wrong: **G2**; matches oracle: G1, G3, G4; 1 fuzz request(s) in this cluster. Example: `{"G2": [{"y": "damage", "x": 20.0, "got": 442815.4294718653, "want": 333078.8683751719}, {"y": "damage", "x": 42.643, "got": 944148.9166168177, "want": 710174.0884125938}, {"y": "damage", "x": 57.0, "got": 1262023.973347825, "want": 949274.9087440781}]}`
- **fuzz_damage_time_s_fz0143-ba34abb6**: damage / time_s; features `tgt-fit apply_projected=False ignore_lock_range=True atk_angle_deg distance_m tgt_angle_deg tgt_speed_pct`; wrong: **G2**; matches oracle: G1, G3, G4; 1 fuzz request(s) in this cluster. Example: `{"G2": [{"y": "dps", "x": 156.934, "got": 276.80838745436785, "want": 0.0}, {"y": "dps", "x": 583.7, "got": 276.80838745436785, "want": 0.0}, {"y": "dps", "x": 605.3, "got": 276.80838745436785, "want": 0.0}]}`
- **fuzz_application_profile_distance_m_fz0185-c3a9d7ab**: application_profile / distance_m; features `tgt-fit apply_projected=True ignore_drone_control_range=False ammo_quality atk_angle_deg atk_speed_pct tgt_angle_deg`; wrong: **G3**; matches oracle: G1, G2, G4; 1 fuzz request(s) in this cluster. Example: `{"G3": [{"y": "volley", "x": 367.2, "got": 2987.614683539827, "want": 2929.909757587224}, {"y": "volley", "x": 704.0, "got": 2987.614683539827, "want": 2929.909757587224}, {"y": "volley", "x": 842.8, "got": 2987.614683539827, "want": 2929.909757587224}]}`

## Differential fuzz 2026-10-03 09:26 CST (seed 2, 500 requests)

Variants: G1 `1c8424c`, G2 `96e612a`, G3 `a6e8dc5`, G4 `7c35c04`. Disagreements 25, confirmed by the oracle 25, oracle errors 0. Wrong answers by variant: {'G2': 23, 'G3': 3}.

- **fuzz_application_profile_distance_m_fz0027-88e4cfe3**: application_profile / distance_m; features `tgt-profile apply_projected=False ignore_resists=False mobile_drone_mode=auto tgt_speed_pct`; wrong: **G2**; matches oracle: G1, G3, G4; 2 fuzz request(s) in this cluster. Example: `{"G2": [{"y": "volley", "x": 11193.37, "got": null, "want": 7837.264060068688}, {"y": "volley", "x": 13974.375, "got": null, "want": 7837.264060068688}, {"y": "volley", "x": 25337.165, "got": null, "want": 7837.264060068688}]}`
- **fuzz_damage_distance_m_fz0038-7ba04408**: damage / distance_m; features `tgt-fit mobile_drone_mode=follow_attacker`; wrong: **G2, G3**; matches oracle: G1, G4; 1 fuzz request(s) in this cluster. Example: `{"G2": [{"y": "dps", "x": 2761.4, "got": 2215.7220776087347, "want": 1107.8610470485446}, {"y": "dps", "x": 4857.0, "got": 2537.1998018923923, "want": 1265.5503021764514}, {"y": "dps", "x": 9181.0, "got": 2629.873315552308, "want": 1288.1829604466998}], "G3": [{"y": "dps", "x": 2761.4, "got": 2215.7220778207497, "want": 1107.8610470485446}, {"y": "dps", "x": 4857.0, "got": 2537.1998021351683, "wan`
- **fuzz_capacitor_time_s_fz0074-63158ce4**: capacitor / time_s; features `tgt-ideal cap_start_pct`; wrong: **G2**; matches oracle: G1, G3, G4; 17 fuzz request(s) in this cluster. Example: `{"G2": [{"y": "cap_regen_gj_s", "x": 0.5, "got": null, "want": 0.6801829635056609}, {"y": "cap_regen_gj_s", "x": 3.0, "got": null, "want": 3.875296381181346}, {"y": "cap_regen_gj_s", "x": 13.0, "got": null, "want": 13.666911385781436}]}`
- **fuzz_damage_tgt_sig_m_fz0137-dd056346**: damage / tgt_sig_m; features `tgt-ideal atk_speed_pct distance_m tgt_speed_pct time_s`; wrong: **G2**; matches oracle: G1, G3, G4; 2 fuzz request(s) in this cluster. Example: `{"G2": [{"y": "damage", "x": 271.0, "got": 8791.340918509448, "want": 9955.487544114776}, {"y": "damage", "x": 518.208, "got": 10124.687342618283, "want": 11288.833644978295}, {"y": "damage", "x": 1694.477, "got": 10729.4204628435, "want": 11893.566958188765}]}`
- **fuzz_application_profile_distance_m_fz0278-6a1506cd**: application_profile / distance_m; features `tgt-fit ignore_drone_control_range=False ignore_lock_range=False ignore_resists=False atk_angle_deg tgt_angle_deg`; wrong: **G3**; matches oracle: G1, G2, G4; 2 fuzz request(s) in this cluster. Example: `{"G3": [{"y": "dps", "x": 1282.095, "got": 80.60343982590258, "want": 105.9910781927622}, {"y": "dps", "x": 30521.9, "got": 80.60343982590258, "want": 105.9910781927622}, {"y": "dps", "x": 56140.0, "got": 58.36927738355493, "want": 76.75382507680165}]}`
- **fuzz_damage_time_s_fz0374-9483420c**: damage / time_s; features `tgt-fit ignore_drone_control_range=True atk_angle_deg tgt_angle_deg tgt_speed_pct`; wrong: **G2**; matches oracle: G1, G3, G4; 1 fuzz request(s) in this cluster. Example: `{"G2": [{"y": "damage", "x": 44.0, "got": 23062.01181306945, "want": 24226.158301673775}]}`

### Adjudication notes (G3 maintainer, 2026-10-03 09:30 CST)

- seed 1 `fuzz_application_profile_distance_m_fz0185-c3a9d7ab` (G3 wrong): fixed in graphs-g3 a6e8dc5. Projected TPs and webs now
  stack with the target fit's own penalised multipliers (Pyfa `getModifiedItemAttrExtended`). Cause: CDFE rig sig drawbacks on
  the Tengu target. 30 G3 stress outputs changed, and all 30 now match the oracle.
- seed 2 `fuzz_application_profile_distance_m_fz0278-6a1506cd` (G3 wrong): fixed in graphs-g3 61ad5ae (launcher damage-type
  multipliers; the wrong torpedo was picked against armor resists).
- seed 2 `fuzz_damage_distance_m_fz0038-7ba04408` (G2 + G3 wrong, exactly ×2): this is a **stats-engine** difference, not a
  graph one. The source is a Vargur with **Bastion Module I in state `overheated`**. Pyfa's stats oracle (`oracle/pyfa_oracle.py`)
  gives weapon_dps 1356.36. variant-g gives 2712.72 and the volley is identical, so the difference is the rate of fire. With the
  bastion `active`, every variant agrees with Pyfa. variant-c (G2's base) behaves the same as variant-g. This is a candidate for
  the stats corpus (1.9.0 pending), not for graphs. The bastion can't be overheated in game, so the contract may want to state
  how an invalid `overheated` state is handled.

## Differential fuzz 2026-10-03 09:33 CST (seed 3, 600 requests)

Variants: G1 `1c8424c`, G2 `96e612a`, G3 `61ad5ae`. Disagreements 37, confirmed by the oracle 36, oracle errors 1. Wrong answers by variant: {'G2': 36, 'G3': 2}.

- **fuzz_capacitor_time_s_fz0077-cd4f7b37**: capacitor / time_s; features `tgt-ideal cap_start_pct`; wrong: **G2**; matches oracle: G1, G3; 20 fuzz request(s) in this cluster. Example: `{"G2": [{"y": "cap_regen_gj_s", "x": 0, "got": 8.322905474059713, "want": 8.257418583505538}, {"y": "cap_regen_gj_s", "x": 232.4, "got": 2.3115427589107784, "want": 6.242341462255516e-05}, {"y": "cap_regen_gj_s", "x": 489.0, "got": 2.590882779362665, "want": 7.109868249699502e-11}]}`
- **fuzz_application_profile_distance_m_fz0124-7539472f**: application_profile / distance_m; features `tgt-fit ignore_resists=False mobile_drone_mode=follow_attacker ammo_quality atk_speed_pct`; wrong: **G2**; matches oracle: G1, G3; 7 fuzz request(s) in this cluster. Example: `{"G2": [{"y": "dps", "x": 22640.0, "got": 559.5118184702364, "want": 547.7738083027456}, {"y": "dps", "x": 53699.789, "got": 27.519793604708152, "want": 26.942455518245755}, {"y": "dps", "x": 62287.0, "got": 8.58535104635186, "want": 8.405238666572213}]}`
- **fuzz_damage_tgt_sig_m_fz0147-c03434b6**: damage / tgt_sig_m; features `tgt-ideal ignore_drone_control_range=False ignore_resists=True mobile_drone_mode=follow_target atk_angle_deg tgt_angle_deg time_s`; wrong: **G2**; matches oracle: G1, G3; 1 fuzz request(s) in this cluster. Example: `{"G2": [{"y": "damage", "x": 402.7, "got": 3536359.26540667, "want": 3446529.38985375}, {"y": "damage", "x": 843.0, "got": 5350908.4164843755, "want": 5162861.6578125}, {"y": "damage", "x": 2448.6, "got": 7382220.336421875, "want": 6836014.7690625}]}`
- **fuzz_damage_time_s_fz0172-21b85b90**: damage / time_s; features `tgt-fit atk_speed_pct tgt_speed_pct`; wrong: **G2**; matches oracle: G1, G3; 4 fuzz request(s) in this cluster. Example: `{"G2": [{"y": "damage", "x": 112.0, "got": 165473.01363931625, "want": 168213.92629479396}]}`
- **fuzz_damage_time_s_fz0468-9fcc3817**: damage / time_s; features `tgt-fit mobile_drone_mode=auto atk_speed_pct tgt_speed_pct`; wrong: **G2, G3**; matches oracle: G1; 1 fuzz request(s) in this cluster. Example: `{"G2": [{"y": "dps", "x": 0, "got": 145.81439098898534, "want": 141.6898677565503}, {"y": "dps", "x": 0.319, "got": 145.81439098898534, "want": 141.6898677565503}, {"y": "dps", "x": 14.239, "got": 145.81439098898534, "want": 141.6898677565503}], "G3": [{"y": "dps", "x": 0, "got": 145.81439098898534, "want": 141.6898677565503}, {"y": "dps", "x": 0.319, "got": 145.81439098898534, "want": 141.6898677`
- **fuzz_damage_tgt_speed_mps_fz0478-cd1af1f5**: damage / tgt_speed_mps; features `tgt-profile apply_projected=True ignore_drone_control_range=True atk_speed_pct time_s`; wrong: **G2**; matches oracle: G1, G3; 1 fuzz request(s) in this cluster. Example: `{"G2": [{"y": "damage", "x": 397.5, "got": 207257.05284418026, "want": 208421.1990285949}, {"y": "damage", "x": 955.0, "got": 207257.05284418026, "want": 208421.1990285949}, {"y": "damage", "x": 1279.1, "got": 207257.05284418026, "want": 208421.1990285949}]}`
- **fuzz_application_profile_distance_m_fz0518-4c500b6c**: application_profile / distance_m; features `tgt-profile ignore_drone_control_range=False ignore_resists=True ammo_quality atk_speed_pct`; wrong: **G2, G3**; matches oracle: G1; 1 fuzz request(s) in this cluster. Example: `{"G2": [{"y": "dps", "x": 28074.0, "got": 733.8485291773965, "want": 224.75151580257204}, {"y": "dps", "x": 28082.0, "got": 733.4447224376655, "want": 224.5940363177369}, {"y": "dps", "x": 29174.03, "got": 681.2618460617236, "want": 204.64281164846815}], "G3": [{"y": "dps", "x": 28074.0, "got": 733.8485298329051, "want": 224.75151580257204}, {"y": "dps", "x": 28082.0, "got": 733.4447231846699, "wa`
- **fuzz_damage_tgt_sig_pct_fz0523-87d85293**: damage / tgt_sig_pct; features `tgt-fit apply_projected=True ignore_drone_control_range=True ignore_resists=False atk_speed_pct distance_m`; wrong: **G2**; matches oracle: G1, G3; 1 fuzz request(s) in this cluster. Example: `{"G2": [{"y": "dps", "x": 47.0, "got": 256.23878375216253, "want": 248.58986483120353}, {"y": "dps", "x": 62.082, "got": 256.23878375216253, "want": 248.58986483120353}, {"y": "dps", "x": 104.5, "got": 256.23878375216253, "want": 248.58986483120353}]}`

### Adjudication notes, seed 3 (G3 maintainer, 2026-10-03 09:35 CST)

- `fuzz_damage_time_s_fz0468-9fcc3817` (G2 + G3 wrong, G1 right): fixed in graphs-g3 b8c6ef8. A target-fit resistance attribute
  the target type lacks takes its SDE default, as in Pyfa's `getModifiedItemAttr(name, 1)`. Here that is
  `fighterAbilityAntiCapitalMissileResistance` = 0.1 for a Mantis torpedo salvo against a Vexor. G2 shows the same symptom.
- `fuzz_application_profile_distance_m_fz0518-4c500b6c` (G2 + G3 wrong): the same **overheated Bastion Module** stats-engine
  difference as seed 2 fz0038 (variant-g / variant-c rate of fire vs Pyfa). This is a stats candidate, not a graph one.
- G4 wasn't in this run: its branch moved to e1f448d and wasn't rebuilt.
