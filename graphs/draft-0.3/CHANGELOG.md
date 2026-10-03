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
- Module-state ruling (eve, 2026-10-03, also in the stats contract; A and H agree): a module whose requested state it
  can't use (not overheatable / not activatable) keeps the requested value, with no downgrade to online. Contract section
  under "Graph types"; +1 hand-specified case `dmg_dist_vargur_bastion_overheated_state` (from fuzz fz0038), with
  expected values from the oracle run with the Bastion active (`rulings/make_ruling_cases.py`; run it again after
  `tools/make_draft_cases.py`, which rewrites cases/).
- Corpus: 0.2's 178 cases, unchanged, + 14 new cases (`NEW_CASES.txt`) = 192 cases, 2694 values.
- No change to the oracle or to graphs/run_graphs.py. The draft scorer is `run_draft.py`.
