# Graphs draft changelog

## 0.3-draft — UNRELEASED (2026-10-03 CST)

Not a release; round 2 is scored on 0.2 @ 0397d95. Rulings by eve on graphs/pending.md:

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
- No change to the oracle or to graphs/run_graphs.py. The draft scorer is `run_draft.py`.
