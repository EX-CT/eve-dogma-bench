# Capacitor suite — results (2026-10-03 ~09:45 CST, informational)

**150 cases, all scored.** Following eve's ruling, `cap_sim.stagger` is deprecated and ignored, so the simulation
always staggers. The 8 cases that send `stagger: false` now expect staggered results.
A case passes when every scored capacitor metric is within tolerance of Pyfa (CONTRACT-CAP §7).
Engines are the already-built bench binaries (A = eve-dogma-rs 659737b, B c8741b6, C f5ef9d9, D df7dcae, E 3bdb9c6,
F e2f1ef8, G c9e7323, H b1c7852 code (= 6c5c621), I 9a4844a, J 60d86ec, K 4ff7150). Reproduce:
`python3 cap/run_cap.py --work-root <bench checkout>` then `python3 cap/tools/results_md.py`.

| engine | cases passed | failing cases |
|---|---|---|
| A | **141/150** (94.0 %) | hard_three_void_bombs, hard_void_bomb_bs, in_void_bomb, oh_maller_all, oh_maller_reps, oh_thorax_all, rl_thorax_oh, spool_damavik_oh, st_thorax_ab_rep_oh |
| B | **141/150** (94.0 %) | hard_three_void_bombs, hard_void_bomb_bs, in_void_bomb, oh_maller_all, oh_maller_reps, oh_thorax_all, rl_thorax_oh, spool_damavik_oh, st_thorax_ab_rep_oh |
| C | **141/150** (94.0 %) | hard_three_void_bombs, hard_void_bomb_bs, in_void_bomb, oh_maller_all, oh_maller_reps, oh_thorax_all, rl_thorax_oh, spool_damavik_oh, st_thorax_ab_rep_oh |
| D | **141/150** (94.0 %) | hard_three_void_bombs, hard_void_bomb_bs, in_void_bomb, oh_maller_all, oh_maller_reps, oh_thorax_all, rl_thorax_oh, spool_damavik_oh, st_thorax_ab_rep_oh |
| E | **145/150** (96.7 %) | hard_three_void_bombs, hard_void_bomb_bs, in_void_bomb, so_reload_aar, so_reload_stagger_off_aar |
| F | **147/150** (98.0 %) | hard_three_void_bombs, hard_void_bomb_bs, in_void_bomb |
| G | **141/150** (94.0 %) | hard_three_void_bombs, hard_void_bomb_bs, in_void_bomb, oh_maller_all, oh_maller_reps, oh_thorax_all, rl_thorax_oh, spool_damavik_oh, st_thorax_ab_rep_oh |
| H | **150/150** (100.0 %) | — |
| I | **141/150** (94.0 %) | hard_three_void_bombs, hard_void_bomb_bs, in_void_bomb, oh_maller_all, oh_maller_reps, oh_thorax_all, rl_thorax_oh, spool_damavik_oh, st_thorax_ab_rep_oh |
| J | **141/150** (94.0 %) | hard_three_void_bombs, hard_void_bomb_bs, in_void_bomb, oh_maller_all, oh_maller_reps, oh_thorax_all, rl_thorax_oh, spool_damavik_oh, st_thorax_ab_rep_oh |
| K | **141/150** (94.0 %) | hard_three_void_bombs, hard_void_bomb_bs, in_void_bomb, oh_maller_all, oh_maller_reps, oh_thorax_all, rl_thorax_oh, spool_damavik_oh, st_thorax_ab_rep_oh |

| category | A | B | C | D | E | F | G | H | I | J | K |
|---|---|---|---|---|---|---|---|---|---|---|---|
| baseline | 12/12 | 12/12 | 12/12 | 12/12 | 12/12 | 12/12 | 12/12 | 12/12 | 12/12 | 12/12 | 12/12 |
| edge | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 |
| hard | 12/14 | 12/14 | 12/14 | 12/14 | 12/14 | 12/14 | 12/14 | 14/14 | 12/14 | 12/14 | 12/14 |
| incoming | 15/16 | 15/16 | 15/16 | 15/16 | 15/16 | 15/16 | 15/16 | 16/16 | 15/16 | 15/16 | 15/16 |
| injectors | 14/14 | 14/14 | 14/14 | 14/14 | 14/14 | 14/14 | 14/14 | 14/14 | 14/14 | 14/14 | 14/14 |
| light | 13/14 | 13/14 | 13/14 | 13/14 | 14/14 | 14/14 | 13/14 | 14/14 | 13/14 | 13/14 | 13/14 |
| modifiers | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 |
| overheat | 12/15 | 12/15 | 12/15 | 12/15 | 15/15 | 15/15 | 12/15 | 15/15 | 12/15 | 12/15 | 12/15 |
| own_neut_nos | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 |
| reload | 7/8 | 7/8 | 7/8 | 7/8 | 8/8 | 8/8 | 7/8 | 8/8 | 7/8 | 7/8 | 7/8 |
| remote_cap | 9/9 | 9/9 | 9/9 | 9/9 | 9/9 | 9/9 | 9/9 | 9/9 | 9/9 | 9/9 | 9/9 |
| sim_options | 16/16 | 16/16 | 16/16 | 16/16 | 14/16 | 16/16 | 16/16 | 16/16 | 16/16 | 16/16 | 16/16 |
| spool | 5/6 | 5/6 | 5/6 | 5/6 | 6/6 | 6/6 | 5/6 | 6/6 | 5/6 | 5/6 | 5/6 |
| stagger | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 |

Failure groups:
- **Cycle truncation** (A B C D G I J K: 6 cases). The full cycle (cycle + reactivation) is a double, and overheat
  bonuses produce e.g. 7649.999… ms. The simulator floors it to an integer millisecond (7649); these engines produce
  7650. This is the cause of the "34 all-overheated" H/A differences (CONTRACT-CAP §8).
- **Incoming void bombs** (all but H: 3 cases). The bomb's neutralization is missing from the drain list and from
  `use_gj_s`.
- **E, `cap_sim.reload` with ancillary repairers** (`so_reload_aar`, `so_reload_stagger_off_aar`): E depletes at
  67.5 s; Pyfa says 71.25 s.

Variant A fix in review: [EX-CT/eve-dogma-rs#1](https://github.com/EX-CT/eve-dogma-rs/pull/1) (branch
`fix/capsim-cycle-floor-void-bomb` @ 6dc39c6) scores **150/150** here; bench 1.8.0 stays 326/326.
