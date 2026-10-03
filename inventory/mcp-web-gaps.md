# mcp / web column coverage gaps (draft, for eve4)

**2026-10-03 13:50:** docs/19 (eve-fit-docs) now marks every item listed below as `partial` in that column (have needs
a non-weak test), so check_inventory passes. The lists stay as the work list: an item goes back to `have` when its
test lands and is mapped in tests.yaml. Web items now covered by eve-fit-web 40e6044 (e2e/unit ids) are mapped.

From `tools/check_inventory.py --columns f,mcp,web --root mcp=<eve-fit-mcp> --root web-e2e=<eve-fit-web>` on pending-1.11
(docs/19 = eve-fit-docs a30d016, eve-fit-mcp 8c6b93d, eve-fit-web fafa982). References are exact stable test ids
(`mcp.<file>.<slug>`, `web.e2e.<slug>`), resolved by suite kind `id`; an unknown id fails the gate.

Mapped suites: `mcp` = eve-fit-mcp src/test/*.test.ts (55 ids; guard mcp.unit.test-ids; docs/test-ids.json cross-checked);
`web-e2e` = eve-fit-web tools/e2e.mjs (50 ids incl. the 9 expanded `web.e2e.graph-<kind>`); `web-bench` (bench v1.9.0 corpus) and
`web-graphs` (graphs suite 8c40921) run in headless Chrome against the site wasm-worker (F) in Pages CI. They gate the deploy
only when the F build succeeds (eve4 is making that a hard gate). Of the e2e runs, only ts-worker and the default engine block a
release. eve-fit-web has no unit tests. eve-dogma-lab branches hold no MCP or web suites.

Ref strength (eve4 review): `weak` = does not count as coverage (reported as weak-only), `partial` = counts, reported.
Only proposals are given below. No test ids are invented.

## mcp-bench (feasible)

`tools/mcp-dogma-bench.py` in eve-fit-mcp is feasible: compute_fit accepts a parsed FitRequest, and `detail: "full"` returns the
raw engine output, so bench cases (cases/, ext/) can be sent as-is and scored with the bench tolerances, like eve-fit-web
tools/browser-dogma-bench.py. Registered here as suite `mcp-bench` (column mcp, kind files on the bench corpus) once it runs in CI.

## mcp: 36 uncovered

| id | name | proposed test |
|---|---|---|
| ENG-CORE-002 | Stacking penalties | `mcp-bench` (eve-fit-mcp `tools/mcp-dogma-bench.py`, see below) over this item's f-column bench refs |
| ENG-CORE-003 | Hand-written effects (eos/effects.py, 2402 classes) | `mcp-bench` (eve-fit-mcp `tools/mcp-dogma-bench.py`, see below) over this item's f-column bench refs |
| ENG-MOD-004 | Reload time / factor reload | `mcp-bench` (eve-fit-mcp `tools/mcp-dogma-bench.py`, see below) over this item's f-column bench refs |
| ENG-MOD-006 | Overheat bonuses | `mcp-bench` (eve-fit-mcp `tools/mcp-dogma-bench.py`, see below) over this item's f-column bench refs |
| ENG-MOD-011 | Capacitor use per module | `mcp-bench` (eve-fit-mcp `tools/mcp-dogma-bench.py`, see below) over this item's f-column bench refs |
| ENG-SHIP-003 | Structures / citadels | `mcp-bench` (eve-fit-mcp `tools/mcp-dogma-bench.py`, see below) over this item's f-column bench refs |
| ENG-SHIP-005 | System security | `mcp-bench` (eve-fit-mcp `tools/mcp-dogma-bench.py`, see below) over this item's f-column bench refs |
| ENG-SHIP-006 | Ship traits / role bonuses | blocked: `get_ship` does not return traits yet; the traits are in the r5 data. Add them to get_ship first, then `integration.test.ts` test asserting the hull bonus lines of a T2 hull |
| ENG-DRN-004 | Drone speed/range/sig | `mcp-bench` (eve-fit-mcp `tools/mcp-dogma-bench.py`, see below) over this item's f-column bench refs |
| ENG-FTR-003 | Fighter DPS per effect | `mcp-bench` (eve-fit-mcp `tools/mcp-dogma-bench.py`, see below) over this item's f-column bench refs |
| ENG-CAP-001 | Capacitor capacity/recharge/peak | `mcp-bench` (eve-fit-mcp `tools/mcp-dogma-bench.py`, see below) over this item's f-column bench refs |
| ENG-CAP-002 | Capacitor simulation (stable %, lasts) | `mcp-bench` (eve-fit-mcp `tools/mcp-dogma-bench.py`, see below) over this item's f-column bench refs |
| ENG-CAP-003 | Cap injectors / boosters | `mcp-bench` (eve-fit-mcp `tools/mcp-dogma-bench.py`, see below) over this item's f-column bench refs |
| ENG-CAP-004 | Own neuts/nos in cap sim | `mcp-bench` (eve-fit-mcp `tools/mcp-dogma-bench.py`, see below) over this item's f-column bench refs |
| ENG-CAP-005 | Incoming neut / remote cap in sim | `mcp-bench` (eve-fit-mcp `tools/mcp-dogma-bench.py`, see below) over this item's f-column bench refs |
| ENG-DEF-003 | Tank: active/sustained/reinforced | `mcp-bench` (eve-fit-mcp `tools/mcp-dogma-bench.py`, see below) over this item's f-column bench refs |
| ENG-DEF-004 | Reactive armor hardener sim | `mcp-bench` (eve-fit-mcp `tools/mcp-dogma-bench.py`, see below) over this item's f-column bench refs |
| ENG-DEF-005 | Ancillary repairers (charged) | `mcp-bench` (eve-fit-mcp `tools/mcp-dogma-bench.py`, see below) over this item's f-column bench refs |
| ENG-DEF-006 | Shield recharge peak | `mcp-bench` (eve-fit-mcp `tools/mcp-dogma-bench.py`, see below) over this item's f-column bench refs |
| ENG-DEF-007 | Incoming remote reps in tank | `mcp-bench` (eve-fit-mcp `tools/mcp-dogma-bench.py`, see below) over this item's f-column bench refs |
| ENG-OFF-004 | Doomsdays / superweapons | `mcp-bench` (eve-fit-mcp `tools/mcp-dogma-bench.py`, see below) over this item's f-column bench refs |
| ENG-NAV-002 | Warp speed and max warp distance | `mcp-bench` (eve-fit-mcp `tools/mcp-dogma-bench.py`, see below) over this item's f-column bench refs |
| ENG-NAV-003 | Warp core strength / scram status | `mcp-bench` (eve-fit-mcp `tools/mcp-dogma-bench.py`, see below) over this item's f-column bench refs |
| ENG-TGT-003 | ECM jam chance | `mcp-bench` (eve-fit-mcp `tools/mcp-dogma-bench.py`, see below) over this item's f-column bench refs |
| ENG-TGT-004 | Probe size / scan | bench ext `probe_*` via `mcp-bench` (pointer /targeting/probe_size), or integration test "probe size in targeting section" |
| ENG-TGT-005 | Drone control range | `mcp-bench` (eve-fit-mcp `tools/mcp-dogma-bench.py`, see below) over this item's f-column bench refs |
| ENG-PROJ-004 | Projection range (distance) | `mcp-bench` (eve-fit-mcp `tools/mcp-dogma-bench.py`, see below) over this item's f-column bench refs |
| ENG-PROJ-005 | Burst projectors / AoE / doomsday AoE | `mcp-bench` (eve-fit-mcp `tools/mcp-dogma-bench.py`, see below) over this item's f-column bench refs |
| ENG-VAL-005 | Disable fitting restrictions | `integration.test.ts` "allow_violations computes an illegal fit" (bench ext `val_disable_restrictions_stats`) |
| ENG-VAL-006 | Charge validity | `integration.test.ts` "validate_fit: charge group / size / capacity" (bench ext `val_charge_group`, `val_charge_size`, `val_charge_capacity*`) |
| CHR-007 | Security status on character | **real gap**: `integration.test.ts` test asserting character.security_status reaches the engine (a security-dependent value changes) |
| UI-STAT-RST | Resistances panel | `mcp-bench` (eve-fit-mcp `tools/mcp-dogma-bench.py`, see below) over this item's f-column bench refs |
| UI-STAT-RCH | Recharge panel | `mcp-bench` (eve-fit-mcp `tools/mcp-dogma-bench.py`, see below) over this item's f-column bench refs |
| UI-PREF-ENG | Engine preferences | **real gap**: `features.test.ts` test "options passthrough": factor_reload / default_spool / rah change the numbers |
| ENG-MISC-001 | Smartbombs and bombs | `mcp-bench` (eve-fit-mcp `tools/mcp-dogma-bench.py`, see below) over this item's f-column bench refs |
| ENG-MISC-002 | Utility modules without stats | `mcp-bench` (eve-fit-mcp `tools/mcp-dogma-bench.py`, see below) over this item's f-column bench refs |

## mcp: 4 weak only (not counted as covered)

| id | name | current (weak) | proposed |
|---|---|---|---|
| ENG-FTR-001 | Fighters squadrons | mcp.features.mutated-fighters (weak: fighter assertions skipped silently inside an if) | make the fighter assertions in mcp.features.mutated-fighters unconditional (no silent skip), or add a fighter test; `mcp-bench` fighters_* |
| ENG-DEF-001 | HP and resists per layer | mcp.features.mutated-fighters (weak: no HP/resist value check) | `mcp-bench` over bench HP/resist cases (value check), or assert defense.hp / resists of a known fit |
| SVC-004 | Data update (new SDE) | mcp.integration.engine-info (weak: indirect: reports the dataset, no SDE update tested); mcp.integration.resources-prompts (weak: indirect: reports the dataset, no SDE update tested) | test that a second dataset (EVE_FIT_DATA / engine data dir) changes engine_info and the numbers |
| UI-STAT-CAP | Capacitor panel | mcp.integration.full-detail-sections (weak: section present, no capacitor value check) | `mcp-bench` exct_* (capacitor values), or assert the capacitor section values in mcp.integration.full-detail-sections |

## mcp: 4 partial only (counted as covered)

| id | name | current (partial) |
|---|---|---|
| ENG-NAV-001 | Speed, align, agility, mass, sig | mcp.integration.what-if (partial: velocity only (no align, agility, mass, signature)) |
| ENG-TGT-001 | Targeting stats | mcp.features.compute-graph-stats (partial: lock time agrees with the fit stats; other targeting stats untested) |
| ENG-VAL-001 | Resources overflow | mcp.integration.suggest-modules (partial: cpu_free of suggestions on a CPU-overloaded base (overload not made worse); no overflow violation flagging) |
| ENG-VAL-003 | canFit restrictions | mcp.unit.can-fit (partial: rig size only, no ship restriction) |

## web: 25 uncovered

| id | name | proposed test |
|---|---|---|
| ENG-CORE-003 | Hand-written effects (eos/effects.py, 2402 classes) | Pages CI: run bench `effects/` micro-fits (effects/tools/score.py) through tools/browser-rpc.mjs on the wasm-worker; suite `web-effects` |
| ENG-MOD-009 | Mutation stats view | e2e check "mutation slider shows the mutaplasmid range" |
| ENG-MOD-010 | Module ranges | e2e check "maxRange column shows optimal + falloff" |
| ENG-MOD-011 | Capacitor use per module | e2e check "capacitor use column per module" |
| ENG-MOD-014 | Module position / rack handling | e2e check "module moves between rack positions" |
| ENG-SHIP-006 | Ship traits / role bonuses | e2e check "show info lists ship traits" |
| ENG-DRN-004 | Drone speed/range/sig | e2e check "drone pane shows drone speed / range / signature" |
| ENG-OFF-003 | DPS vs target profile (applied) | Pages CI: bench ext `tp_*` through browser-rpc (suite `web-ext`, ext/tools/score.py); or e2e check "target profile changes applied dps" |
| ENG-NAV-004 | Propulsion mods (AB/MWD/MJD/bastion/siege) | e2e check "MWD active raises speed and signature" |
| ENG-TGT-002 | Lock time vs ship classes | e2e check "lock time per target ship class matches stats" |
| ENG-TGT-004 | Probe size / scan | `web-ext`: bench ext `probe_*` |
| ENG-VAL-001 | Resources overflow | `web-ext`: bench ext `val_cpu_power_overload`, `val_drone_bandwidth` through browser-rpc; e2e check "overfitted CPU/PG shows the overflow in Problems" (replaces web.e2e.no-violations, which only checks a clean fit) |
| ENG-VAL-002 | Slots and hardpoints | `web-ext`: `val_slots_high`, `val_slots_mid_low_rig`, `val_turret_hardpoints`, `val_launcher_hardpoints`; e2e "over-slotted fit shows SLOTS_EXCEEDED in Problems" |
| ENG-VAL-003 | canFit restrictions | `web-ext`: `val_ship_restriction_burst`, `val_rig_size`, `val_max_group_*`, `val_capital_module_subcap`; e2e "rig size problem listed" |
| ENG-VAL-006 | Charge validity | `web-ext`: `val_charge_*`; e2e "charge picker hides invalid charges" |
| CHR-008 | Skill prerequisites tree / requirements view | e2e check "show info lists required skills with levels" |
| FMT-CLIP-001 | Clipboard to/from | e2e check "copy EFT to clipboard and paste import" (puppeteer clipboard permission) |
| DB-004 | Fit links (projected/command fits by reference) | e2e check "projected fit from the library follows its source" |
| PRF-DMG-002 | Damage pattern editor / change | e2e check "custom damage pattern edit changes EHP" |
| PRF-TGT-001 | Built-in target profiles | e2e check "built-in target profile selection changes applied dps" |
| PRF-TGT-002 | Target profile editor (resists, sig, speed, radius) | e2e check "custom target profile (resists, sig, speed) changes applied dps" |
| UI-PANE-001 | Addition panes | e2e check "addition panes (drones, fighters, implants, boosters, projected, fleet) open" |
| UI-PANE-003 | Item amount change/fill/remove | e2e check "change amount / remove item in drone pane" |
| UI-MISC-001 | Fleet/command pane, command link add | e2e check "fleet pane: command fit as booster raises resists" |
| ENG-MISC-002 | Utility modules without stats | e2e check "utility module without stats fits cleanly" (e.g. Salvager I, cloak) |

## web: 5 weak only (not counted as covered)

| id | name | current (weak) | proposed |
|---|---|---|---|
| ENG-MOD-008 | Mutated / abyssal modules | web.e2e.mutated-module-import (weak: text presence of the module name only); web.e2e.eft-export-mutated (weak: EFT export text only, no mutated stat values) | e2e check asserting a mutated attribute value (stats or show info), not only the module name |
| PRC-002 | Price stats panel | web.e2e.fit-price-esi (weak: passes on ESI error or timeout) | e2e check that fails on ESI error / timeout (intercept the price request with a fixed response) |
| DB-001 | Saved fits database | web.e2e.multi-fit-eft-import (weak: no reload, persistence not tested); web.e2e.fit-browser-search (weak: no reload, persistence not tested) | e2e check: save fits, reload the page, assert the fit browser still lists them |
| SVC-004 | Data update (new SDE) | web.e2e.about-page (weak: indirect: reports the dataset, no SDE update tested) | CI check that the site dataset version equals engines.lock / a dataset switch updates the numbers |
| UI-STAT-PRC | Price panel | web.e2e.fit-price-esi (weak: passes on ESI error or timeout) | same fix as PRC-002 (shared check web.e2e.fit-price-esi) |

## web: 1 partial only (counted as covered)

| id | name | current (partial) |
|---|---|---|
| FMT-DNA-001 | DNA import/export (incl. alt, link) | web.e2e.dna-export (partial: export only, no DNA import) |

## Rulings recorded in tests.yaml (eve4 review)

- FMT-ESI-001: `unsupported: [mcp]`. mcp.integration.input-formats-agree tests MCP's own lenient JSON, not ESI. docs/19 still says mcp partial (eve-fit-docs, eve to update).
- ENG-ENV-004 web: web.e2e.environment-beacon only checks for the word "wormhole". Moved to ENG-ENV-001 as weak. ENG-ENV-004 web stays covered by web-bench esf_beacons / esf_location_bonus_not_on_*.
- DB-008 web: web.e2e.custom-character (character clone) instead of web.e2e.implant-set.
- ENG-VAL-001: web.e2e.no-violations dropped (it doesn't test overflow flagging), so web VAL-001 is now uncovered. mcp.integration.suggest-modules is partial.
- ENG-TGT-001 mcp: mcp.features.compute-graph-stats (lock time), partial.
- UI-STAT-PRC web: web.e2e.fit-price-esi is weak, same as PRC-002 (applied for consistency, not in the review list).
- ENG-CAP-006 web: web-graphs cap_time_* (cap over time, browser vs F) added; web.e2e.graph-cap-within-capacity is weak.

## Status notes for eve

MCP items still `partial` in docs/19 (which cites an older eve-fit-mcp) that have dedicated tests on 8c6b93d and are mapped:
ENG-CORE-005, ENG-MOD-008, ENG-PROJ-001, ENG-FLT-001, ENG-ENV-001 (weak), ENG-TGT-002, GRF-*, MKT-001, PRC-001, PRC-002. Whether to upgrade them is eve's call.
