# Graphs corpus changelog (branch `graphs-round2`)

Scores are only comparable at the same contract revision (`CONTRACT-GRAPHS.md` header).

## 0.3 (2026-10-03 CST)
Released (tag `graphs-v0.3`). Round 2 was scored on 0.2 @ 0397d95. Rulings by eve on graphs/pending.md:

- Scored, with contract wording fixes:
  - (1) sentry drones never follow, even in `follow_target` (cth 1 needs drone speed > 1);
  - (2) breacher pods: missile range chance × target `breacherPodDamageResistance`, applied to the per-tick value;
  - (3) dps/volley are 0 between active cycle segments (reactivationDelay e.g. bombs, reload); damage holds;
  - (4) fighters that don't follow shoot from the attacker's centre (d + r_attacker − r_fighter), no minimum speed;
  - (6) quality tiers defined (Pyfa `filterChargesByQuality`), incl. the XL navy rule (Sansha / Arch Angel / Shadow).
- Not scored, informational only: (5) Pyfa's application-profile grid step `getSampleStep` and linear interpolation of
  projected effects; ammo-switch hysteresis. Sample points are kept off web/TP edges and crossovers
  (`tools/edge_check.py`: 0 sensitive points).
- Module-state correction (contract draft 1.4.5, pending-1.10 `49f7555`; coordinator ruling 2026-10-03 11:19 CST, which
  reverses the 09:49 "keeps the requested value" ruling): an impossible `active` / `overheated` state is corrected to
  `online` as in Pyfa; rigs/subsystems stay online unless `offline` is requested. Contract section under "Graph types".
  Case `dmg_dist_vargur_bastion_overheated_state` (from fuzz fz0038): expected values regenerated with the unchanged
  oracle on the request as written (Bastion → online; `rulings/make_ruling_cases.py`, no state override).
- Corpus: 0.2's 178 cases, unchanged, + 14 new cases (`NEW_CASES.txt`) = 192 cases, 2694 values.
- No change to the oracle or to graphs/run_graphs.py; `graphs/cases` + `graphs/expected` now hold the 0.3 corpus
  (the 178 0.2 cases are unchanged: every scored 0.2 value identical). Generators and the ruling script stay in
  `graphs/draft-0.3/` (`tools/`, `rulings/`).

## 0.2 (2026-10-03 CST)
- Contract 0.2:
  - empty `x.values` → success, `"x": []` and `[]` for every y series;
  - new "Validation and error codes" section (`BAD_REQUEST` / `UNKNOWN_GRAPH` / `BAD_AXIS` / `UNKNOWN_TYPE`; empty `y` is `BAD_REQUEST`;
    `resist_mode`, `mobile_drone_mode`, `ammo_quality` validated);
  - new graph `ecm_burst` (Pyfa's hidden `fitEcmBurstScanresDamps`);
  - damage x axes `tgt_speed_pct`, `tgt_sig_pct` (Pyfa's `%` normalisers), `tgt_sig_m` ≤ 0 → `null`;
  - `target.fit` for `ewar` / `remote_reps` (derived from Pyfa's projected-effect handlers — Pyfa's graphs have no target there:
    resistance attributes, `disallowOffensiveModifiers`, `remoteRepairImpedance`, `disallowAssistance`).
- Corpus: 111 → 158 value cases (+47) and 20 error cases; 1843 → 2437 scored values.
  - +11 `ecm_burst` (218 values), +8 %-axis damage cases, +11 ewar/RR target-fit cases, clamped `resist`,
    boundary cases (time 2500/2500.001, shield/cap % < 0 and > 100, lock sig 0.99/1, warp 0.9999×/1.0001× max range,
    sig ≤ 0), 4 empty-x cases, 20 error cases (`graphs/expected/err_*.json`, `oracle: "contract"`).
- Scorer: empty expected series = 1 "shape" value per y; error cases = 1 value each, group `errors`.
- Oracle: `ecm_point` (Pyfa ECM burst getters), %-axis normalisers, `target_ship_attr` for the target-fit rules.
- Old 0.1 expected values unchanged (re-generated identically; only informational charge-id ties differ run to run).

## 0.1 (2026-10-03 CST)
- First draft: 9 graph types, 111 cases, 1843 values.
