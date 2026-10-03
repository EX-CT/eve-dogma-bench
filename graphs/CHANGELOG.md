# Graphs corpus changelog (branch `graphs-round2`)

Scores are only comparable at the same contract revision (`CONTRACT-GRAPHS.md` header).

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
