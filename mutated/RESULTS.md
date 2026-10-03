# Mutated suite 0.1: first scores (2026-10-03 ~09:17 CST)

These are informational, not official. The binaries are the ones already built in the bench's `work/` clones (from each
variant's last `bench.py` run, so they may be older than the branch heads) and in `/workspace/exct-eve/eve-dogma-rs` for A.
Variant I is at 349c6fd, the reference implementation of this contract.

| variant | commit | stats cases | values | EFT export | EFT import | failing stats cases |
|---|---|---|---|---|---|---|
| I | 349c6fd | 93/93 | 6184/6184 | 93/93 | 99/99 | — |
| A | 5faa35c | 86/93 | 6148/6184 | 73/93 | 96/99 | combo_nomad_ab_mwd_exct_damnation, combo_two_boosters_dda_exct_dominix, slot_booster_slot_first_wins_exct_rifter, slot_booster_slot_first_wins_rev_exct_rifter, slot_booster_three_slots_exct_rifter, slot_implant_slot_first_wins_exct_rifter, slot_implant_slot_first_wins_rev_exct_rifter |
| B | c8741b6 | 84/93 | 6146/6184 | 73/93 | 96/99 | combo_nomad_ab_mwd_exct_damnation, combo_two_boosters_dda_exct_dominix, mm_ancillary_shield_booster_esf_ancillary_repair_2, mm_propulsion_module_exct_crucifier, slot_booster_slot_first_wins_exct_rifter, slot_booster_slot_first_wins_rev_exct_rifter, slot_booster_three_slots_exct_rifter, slot_implant_slot_first_wins_exct_rifter, slot_implant_slot_first_wins_rev_exct_rifter |
| C | f5ef9d9 | 86/93 | 6148/6184 | 73/93 | 96/99 | combo_nomad_ab_mwd_exct_damnation, combo_two_boosters_dda_exct_dominix, slot_booster_slot_first_wins_exct_rifter, slot_booster_slot_first_wins_rev_exct_rifter, slot_booster_three_slots_exct_rifter, slot_implant_slot_first_wins_exct_rifter, slot_implant_slot_first_wins_rev_exct_rifter |
| D | df7dcae | 86/93 | 6148/6184 | 83/93 | 96/99 | combo_nomad_ab_mwd_exct_damnation, combo_two_boosters_dda_exct_dominix, slot_booster_slot_first_wins_exct_rifter, slot_booster_slot_first_wins_rev_exct_rifter, slot_booster_three_slots_exct_rifter, slot_implant_slot_first_wins_exct_rifter, slot_implant_slot_first_wins_rev_exct_rifter |
| E | 3bdb9c6 | 87/93 | 6151/6184 | 85/93 | 0/99 | combo_two_boosters_dda_exct_dominix, slot_booster_slot_first_wins_exct_rifter, slot_booster_slot_first_wins_rev_exct_rifter, slot_booster_three_slots_exct_rifter, slot_implant_slot_first_wins_exct_rifter, slot_implant_slot_first_wins_rev_exct_rifter |
| F | e2f1ef8 | 86/93 | 6148/6184 | 85/93 | 96/99 | combo_nomad_ab_mwd_exct_damnation, combo_two_boosters_dda_exct_dominix, slot_booster_slot_first_wins_exct_rifter, slot_booster_slot_first_wins_rev_exct_rifter, slot_booster_three_slots_exct_rifter, slot_implant_slot_first_wins_exct_rifter, slot_implant_slot_first_wins_rev_exct_rifter |
| G | c9e7323 | 86/93 | 6148/6184 | 73/93 | 96/99 | combo_nomad_ab_mwd_exct_damnation, combo_two_boosters_dda_exct_dominix, slot_booster_slot_first_wins_exct_rifter, slot_booster_slot_first_wins_rev_exct_rifter, slot_booster_three_slots_exct_rifter, slot_implant_slot_first_wins_exct_rifter, slot_implant_slot_first_wins_rev_exct_rifter |
| H | 6c5c621 | 86/93 | 6148/6184 | 81/93 | 98/99 | combo_nomad_ab_mwd_exct_damnation, combo_two_boosters_dda_exct_dominix, slot_booster_slot_first_wins_exct_rifter, slot_booster_slot_first_wins_rev_exct_rifter, slot_booster_three_slots_exct_rifter, slot_implant_slot_first_wins_exct_rifter, slot_implant_slot_first_wins_rev_exct_rifter |
| J | 60d86ec | 86/93 | 6148/6184 | 73/93 | 96/99 | combo_nomad_ab_mwd_exct_damnation, combo_two_boosters_dda_exct_dominix, slot_booster_slot_first_wins_exct_rifter, slot_booster_slot_first_wins_rev_exct_rifter, slot_booster_three_slots_exct_rifter, slot_implant_slot_first_wins_exct_rifter, slot_implant_slot_first_wins_rev_exct_rifter |
| K | 4ff7150 | 86/93 | 6148/6184 | 73/93 | 93/99 | combo_nomad_ab_mwd_exct_damnation, combo_two_boosters_dda_exct_dominix, slot_booster_slot_first_wins_exct_rifter, slot_booster_slot_first_wins_rev_exct_rifter, slot_booster_three_slots_exct_rifter, slot_implant_slot_first_wins_exct_rifter, slot_implant_slot_first_wins_rev_exct_rifter |

Common gaps:
* Every variant ignores the §3.1 implant/booster slot rule, so it fails the `slot_*` cases and `combo_two_boosters_dda_*`.
* Every variant except E fails the §3.3 effect 2791 override (`combo_nomad_ab_mwd_*`).
* EFT export: most variants print the request's raw values, not the validated ones (over/under/partial/foreign/empty cases), and do not follow Pyfa's drone full-name order.
* EFT import: the usual failure is a mutated module with `/offline` before ` [N]`; E has no `eft_parse`.
