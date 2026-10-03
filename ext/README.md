# ext suite: stats-ext, heat, fleet.buffs, overrides (bench 1.10, docs/20 P0-3 / P0-4)

175 cases + 12 hand-derived unit cases (`unit/`). Values are keyed by JSON pointer into the **proposed** FitStats fields of CONTRACT.md "Draft 1.10:
stats-ext" (no engine implements them yet, so a missing pointer is reported as `not_implemented`), plus the bench
metrics (`values`) for every case.

| feature | cases | Pyfa source of the expected values |
|---|---|---|
| mining | 12 (1 with mining fleet buffs) | `fit.minerYield / minerDrain / droneYield / droneDrain` (m³/s; drain = volume removed incl. residue) |
| outgoing | 25 | `fit.getRemoteReps(spoolOptions)` shield / armor / hull HP/s and capacitor GJ/s, at the default spool and spool 0 / 1 (mutadaptive) |
| drone_ehp | 16 | `drone.hp`, `drone.ehp` (fit damage pattern), `calculateShieldRecharge()` per drone, same for fighters |
| bombing | 15 | `gui/builtinStatsViews/bombingViewFull.py` arithmetic: bombs to kill per bomb type (27920 / 27916 / 27912 / 27918), Covert Ops 0–5, red giant `smartbombDamageMultiplier`, signature factor, ceil to 0.1 |
| heat | 30 | `gui/builtinViewColumns/heat.py` `Thermodynamics` (loaded from Pyfa's source): `calcBurnCycles` and burnout time per overheated module |
| fleet.buffs | 12 | explicit `fleet.buffs` through Pyfa command bonuses (oracle `explicit_buffs`), incl. duplicate ids (Minimum / Maximum aggregate), titan generator buffs, a Claymore booster fit with and without an explicit override |
| vs_target_profile | 11 | `DmgTypes.profile` = request target profile on the total weapon + drone + fighter dps / volley (oracle `ORACLE_EXTRA=profile`) |
| probe_size | 10 | `fit.probeSize` |
| validity | 22 + 2 unit | Pyfa fitting checks mapped to contract violation codes (oracle `ORACLE_EXTRA=validity`, CONTRACT.md "Draft 1.11: vs_target_profile, probe_size, validity"); scored: distinct code set + all bench metrics; draft (reported only): module indices, missing skill ids |
| breacher_dc, char_implants, alpha_clone, damage_pattern_builtin, vs_target_profile_builtin, attr_sources, attr_dependants | 4, 6, 5, 6, 6, 6, 4 | docs/19 f-`missing` items (CONTRACT.md "Draft 1.11: missing-f"; oracle `ORACLE_EXTRA=drafts,sources,attrs`); generator `tools/gen_missing.py`; MANIFEST `item` = docs/19 id |
| rpc/ (lookups) | 54 | Pyfa service layer (`oracle/pyfa_lookup.py`): variations, item compare, market tree, jargon search, implant sets, EVEMon import, renamed-item names, XML backup, `type` item stats (attributes/effects, description, traits, required skills: MKT-003 / ENG-SHIP-006 / CHR-008, f partial); `tools/gen_rpc.py`, `tools/make_rpc_expected.py`, `tools/score_rpc.py --cmd "ENGINE serve-stdio"` |
| overrides | 22 + 10 unit | Pyfa attribute overrides (oracle `apply_overrides`); 10 hand-derived unit cases in `unit/` (see below) |

Fits: hand-built reference fits (Venture, Hulk, Covetor, Procurer, Porpoise, Guardian, Basilisk, Oneiros, Scimitar,
Zarmazd, maintenance-bot Vexor / Dominix, ...) and random legal fits from the `oracle/fuzz/gen_legal.py` pool
(`pool_*`, first fit per distinct hull with the feature). 115/116 pass `oracle/fuzz/check_legal.py`; all are Pyfa
buildable.

**overrides** (bench 1.11 draft, CONTRACT.md "Draft 1.11: overrides semantics"): our semantics follow Pyfa, so
the 22 `ovr_*` cases are Pyfa-backed (oracle `apply_overrides` = Pyfa's attribute overrides): the six 1.10 requests
plus duplicates, ship / module / charge / drone / fighter / implant / booster / T3D mode / environment overrides,
mutated modules (rolled vs other attributes), projected modules and fits, a booster fit's charge. What our contract
supports beyond Pyfa (skill types, attributes the type lacks, overrides inside nested FitRequests) is hand-derived:
`unit/cases/unit_ovr_*` + `unit/expected` (feature `overrides-unit`, 10 cases incl. the six 1.10 hand-derived
cases, renamed), each with a `derivation` text. Generator: `tools/gen_overrides.py`.

```
python3 ext/tools/gen_ext.py [POOL_LIST LEGAL_JSONL]   # cases except overrides
python3 ext/tools/gen_overrides.py                      # ovr_* cases + unit/ (hand-derived expected)
python3 ext/tools/gen_val.py                            # tp_* / probe_* / val_* cases + unit_val_*
python3 ext/tools/gen_missing.py                        # brdc_/cimp_/alpha_/dpb_/tpb_/src_/dep_ (docs/19 f-missing)
python3 ext/tools/make_expected.py                       # Pyfa oracle (ORACLE_EXTRA=ext,...) for the rest
python3 ext/tools/gen_rpc.py && python3 ext/tools/make_rpc_expected.py   # ext/rpc lookups
python3 ext/tools/score_rpc.py --cmd "ENGINE serve-stdio" --name X [--out r.json]
python3 ext/tools/score.py --batch-cmd "ENGINE batch" --name X [--out r.json]
```
