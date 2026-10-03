# eve-fit-web bench-suites run in the browser (eve3, verified 2026-10-03 15:55 CST)

Run https://github.com/EX-CT/eve-fit-web/actions/runs/37104154159 (push to main, eve-fit-web fdbb014, 2026-10-03 14:46 CST,
success), artifact `bench-suites-wasm-worker` downloaded read-only with `gh run download`. Engine: the site's F wasm worker
in headless Chrome (tools/browser-engine.mjs calc / batch / serve-stdio); engines.lock ENGINE_F_SRC = eve-dogma 20aa425.
Bench suites: pending-1.11 c2229b2 (core / ext / ext_rpc / batch / effects), graphs db81b8c, cap d80cc38, mutated 4533dde,
formats 7c716e7 (roots.json in the artifact).

Per-case results recomputed here with tools/check_no_regress.py collect_suite (case ids from local checkouts of those refs):

| suite | passed / total |
|---|---|
| core | 339/339 |
| ext | 207/239 |
| ext_rpc | 0/54 |
| batch | 0/44 |
| effects | 2353/2378 |
| graphs | 192/192 |
| cap | 150/150 |
| mutated | 93/93 |
| formats | 4779/4779 |

Matches eve4's numbers (core 339, ext 207, effects 2353, graphs 192, cap 150, mutated 93, formats 4779). The CI's own
no-regress output vs baselines/f.json at c2229b2 is in `web-fdbb014/no-regress-ci.txt`; per-suite passed ids in
`web-fdbb014/passed.json`.

ext failures (32): alpha_drake, alpha_kestrel, alpha_omen_skills4, alpha_rifter, alpha_vexor_drones, brdc_rifter_online, cimp_kestrel_char_missiles, cimp_punisher_char_cap, cimp_rifter_char_ignores_fit, cimp_rifter_char_source, dep_kestrel_bcs_skills0, dep_rifter_ab_gyro, dep_thorax_plate_dc, dep_vexor_drones_dda, dpb_drake_abyssal_drifter, dpb_drake_guristas, dpb_rifter_generic_em, dpb_rifter_generic_explosive, dpb_thorax_scourge, dpb_thorax_uniform, src_drake_implants, src_kestrel_bcs_skills0, src_punisher_stacking, src_rifter_ab_gyro, src_thorax_plate_dc, src_vexor_drones_dda, tpb_kestrel_serpentis, tpb_kestrel_t1_shield, tpb_punisher_sleeper, tpb_rifter_t2_amarr_armor, tpb_rifter_uniform50, tpb_vexor_rogue_drones.
These are the F-missing cases (alpha_, cimp_, dep_, dpb_, src_, tpb_) plus brdc_rifter_online (old expectation at c2229b2,
fixed in 583f912; d990818 passes the new one).
effects: 25 failures (wasm F 20aa425 predates the effects fixes in 1ebaa1f), e.g. eff_12127, eff_12246, eff_12556.
