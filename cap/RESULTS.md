# Capacitor suite — results (2026-10-03 ~09:40 CST, suite 76de49d, informational)

150 cases: **142 scored**, 8 pending. The pending cases request `cap_sim.stagger: false`, which the main bench
treats as ignored; they wait for a ruling (CONTRACT-CAP §9).
A case passes when every scored capacitor metric is within tolerance of Pyfa (CONTRACT-CAP §7).
Engines are the already-built bench binaries (A = eve-dogma-rs 659737b, B c8741b6, C f5ef9d9, D df7dcae, E 3bdb9c6,
F e2f1ef8, G c9e7323, H b1c7852 code (= 6c5c621), I 9a4844a, J 60d86ec, K 4ff7150). Reproduce:
`python3 cap/run_cap.py --work-root <bench checkout>` then `python3 cap/tools/results_md.py`.

| engine | scored cases | pending (stagger off) | failing scored cases |
|---|---|---|---|
| A | **133/142** (93.7 %) | 1/8 | hard_three_void_bombs, hard_void_bomb_bs, in_void_bomb, oh_maller_all, oh_maller_reps, oh_thorax_all, rl_thorax_oh, spool_damavik_oh, st_thorax_ab_rep_oh |
| B | **133/142** (93.7 %) | 1/8 | hard_three_void_bombs, hard_void_bomb_bs, in_void_bomb, oh_maller_all, oh_maller_reps, oh_thorax_all, rl_thorax_oh, spool_damavik_oh, st_thorax_ab_rep_oh |
| C | **133/142** (93.7 %) | 1/8 | hard_three_void_bombs, hard_void_bomb_bs, in_void_bomb, oh_maller_all, oh_maller_reps, oh_thorax_all, rl_thorax_oh, spool_damavik_oh, st_thorax_ab_rep_oh |
| D | **133/142** (93.7 %) | 1/8 | hard_three_void_bombs, hard_void_bomb_bs, in_void_bomb, oh_maller_all, oh_maller_reps, oh_thorax_all, rl_thorax_oh, spool_damavik_oh, st_thorax_ab_rep_oh |
| E | **138/142** (97.2 %) | 1/8 | hard_three_void_bombs, hard_void_bomb_bs, in_void_bomb, so_reload_aar |
| F | **139/142** (97.9 %) | 1/8 | hard_three_void_bombs, hard_void_bomb_bs, in_void_bomb |
| G | **133/142** (93.7 %) | 1/8 | hard_three_void_bombs, hard_void_bomb_bs, in_void_bomb, oh_maller_all, oh_maller_reps, oh_thorax_all, rl_thorax_oh, spool_damavik_oh, st_thorax_ab_rep_oh |
| H | **142/142** (100.0 %) | 1/8 | — |
| I | **133/142** (93.7 %) | 1/8 | hard_three_void_bombs, hard_void_bomb_bs, in_void_bomb, oh_maller_all, oh_maller_reps, oh_thorax_all, rl_thorax_oh, spool_damavik_oh, st_thorax_ab_rep_oh |
| J | **133/142** (93.7 %) | 1/8 | hard_three_void_bombs, hard_void_bomb_bs, in_void_bomb, oh_maller_all, oh_maller_reps, oh_thorax_all, rl_thorax_oh, spool_damavik_oh, st_thorax_ab_rep_oh |
| K | **133/142** (93.7 %) | 1/8 | hard_three_void_bombs, hard_void_bomb_bs, in_void_bomb, oh_maller_all, oh_maller_reps, oh_thorax_all, rl_thorax_oh, spool_damavik_oh, st_thorax_ab_rep_oh |

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
| sim_options | 8/8 | 8/8 | 8/8 | 8/8 | 7/8 | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 |
| spool | 5/6 | 5/6 | 5/6 | 5/6 | 6/6 | 6/6 | 5/6 | 6/6 | 5/6 | 5/6 | 5/6 |
| stagger | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 |

Failure groups:
- **Cycle truncation** (A B C D G I J K: 6 cases). The full cycle (cycle + reactivation) is a double, and overheat
  bonuses produce e.g. 7649.999… ms. The simulator floors it to an integer millisecond (7649); these engines produce
  7650. This is the cause of the "34 all-overheated" H/A differences (CONTRACT-CAP §8).
- **Incoming void bombs** (all but H: 3 cases). The bomb's neutralization is missing from the drain list and from
  `use_gj_s`.
- **E `so_reload_aar`**: with `cap_sim.reload` (reload only in the simulation) E depletes at 67.5 s; Pyfa says 71.25 s.
- **Stagger off** (pending): only `so_stagger_on_reps` passes, because it requests staggering explicitly. Every engine
  always staggers.
