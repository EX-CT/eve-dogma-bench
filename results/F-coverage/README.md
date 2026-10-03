# F coverage: correctness suites × three F refs

Generated 2026-10-03 ~11:15 CST by eve3 with `run_f_coverage.py` (this folder) on the EXCT box. Correctness only, no timing.
Native release builds (`cargo build --release`, `EVE_DOGMA_DATASET=dataset-3569502.json.gz`), one per ref, from
`EX-CT/eve-dogma-lab`. Every request has a 10 s timeout. No crashes or timeouts on any suite × ref.

| F ref | what |
|---|---|
| `bc84e2b` | variant-f round-1 evaluated commit (07:34 CST) |
| `af1c04b` | variant-f head (09:18 CST, formats work) |
| `6e2ebf1` | variant-f-perf head at 11:13 CST fetch (commit 11:09 CST) |

| suite (pinned) | `bc84e2b` | `af1c04b` | `6e2ebf1` |
|---|---|---|---|
| bench `v1.9.0` (d2edf98), 331 cases | 330/331 | 330/331 | 330/331 |
| cap-suite `d80cc38`, 150 | 147/150 | 147/150 | 147/150 |
| mutated-suite `2ac7c00`, 93 stats + EFT 93/99 | 86/93 (EFT exp 85/93, imp 96/99) | 86/93 (EFT exp 85/93, imp 96/99) | 86/93 (EFT exp 85/93, imp 96/99) |
| formats-suite `7c716e7`, FORMATS 0.1, 4779 scored rows | 4773/4779 | 4779/4779 | 4779/4779 |
| graphs-round2 `84f7c2e`, contract 0.2, 178 | 0/178 | 0/178 | 0/178 |
| pending-1.10 `3193689`: 8 `e_fz_*` + 200 legal fuzz fits | e_fz 8/8; fuzz 198/200 | e_fz 8/8; fuzz 198/200 | e_fz 8/8; fuzz 198/200 |

Graphs: none of the three `variant-f` refs has a graph layer (every case → `UNKNOWN_METHOD graph`), so 0/178 is
"no interface", not wrong numbers. F's graph layer lives on `graphs-g4` (`f73ff1c`): official round-2 run
`eve-dogma-bench@graphs-round2 562a201`: **178/178** graph cases via batch, rpc and single, plus stats 1.8.0 326/326.

## Failing case ids

Identical at all three refs unless noted.

**bench v1.9.0 (330/331)**
- `breacher_kestrel`: `weapon_pure_dps` / `weapon_pure_volley` got 0, want 250. Breacher pod "pure" damage (contract 1.4.4) not implemented.

**cap-suite (147/150)**: void bombs are not modelled as a capacitor drain (fix idea: eve-dogma-rs PR #1 / H).
- `hard_three_void_bombs`, `hard_void_bomb_bs`, `in_void_bomb`: `use_gj_s`, `delta_gj_s`, `depletes_in_s` (e.g. in_void_bomb delta −39.07 vs −49.66).

**mutated-suite stats (86/93)**
- `combo_nomad_ab_mwd_exct_damnation`: missile `explosion_radius` 93.75 vs 107.81 (w9–w11).
- `combo_two_boosters_dda_exct_dominix`: armor HP / EHP, `max_velocity`.
- `slot_booster_slot_first_wins_exct_rifter`, `slot_booster_slot_first_wins_rev_exct_rifter`, `slot_booster_three_slots_exct_rifter`: booster slot conflicts (Pyfa's one-booster-per-slot rule not matched; HP, velocity, cap, weapon values).
- `slot_implant_slot_first_wins_exct_rifter` (`align_time_s`), `slot_implant_slot_first_wins_rev_exct_rifter` (`max_velocity`): implant slot conflicts (same family).

**mutated-suite EFT** export 85/93: `combo_two_boosters_dda_exct_dominix`, `drone_bouncer_ii_drones_sentry_dominix`,
`drone_ogre_ii_exct_rattlesnake`, the 5 `slot_*` cases above; import 96/99: `state_lse_offline_exct_nightmare`,
`eftedge_header_base_mismatch`, `eftedge_missing_ref`.

**formats-suite**: `bc84e2b` 4773/4779, failing `edge_export/name_newline.json@import:xml` (name),
`eft_case_names.eft.txt@auto`, `eft_header_empty_name.eft.txt@auto`, `xml_malformed.xml@auto`,
`xml_no_fittings.xml@auto`, `auto_garbage.txt@xml` (Pyfa rejects, F imported). `af1c04b` and `6e2ebf1`: **4779/4779**
(the Pyfa reject-parity work in `b7a4ee3`), gate met.

**pending-1.10**: all 8 `e_fz_*` pass (the A bugs E1–E5 are not present in F). Fuzz 198/200: `lf10_123_28659` and
`lf10_197_28659` (Paladin `align_time_s` 10.29 vs 102.93): known oracle data drift (Pyfa eve.db 3532181 agility 0.858
vs SDE 3569502 0.0858, docs/15 class (a)), not an engine bug. So effectively 200/200.

## Files
- `<suite>__<ref>.json`: pass/total, every failing case with mismatches, crashes, timeouts, suite pin.
- `<suite>__<ref>.csv`: one row per failing case (`suite,f_ref,case_id,kind,detail`).
- `run_f_coverage.py`: the runner (box paths; needs the suite worktrees named in it).
