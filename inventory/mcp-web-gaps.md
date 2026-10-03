# mcp / web column coverage gaps (draft, for eve4)

From `tools/check_inventory.py --columns f,mcp,web --root mcp=<eve-fit-mcp> --root web-e2e=<eve-fit-web> --root web-unit=<eve-fit-web>`
on pending-1.11 (docs/19 = eve-fit-docs a30d016, eve-fit-mcp main 64d6cd6, eve-fit-web main 7e308fb).

Mapped suites: `mcp` = node --test titles in eve-fit-mcp src/test/*.test.ts; `web-e2e` = check names in eve-fit-web tools/e2e.mjs;
`web-bench` = bench v1.9.0 corpus and `web-graphs` = graphs suite 8c40921, both run in headless Chrome against the site wasm-worker
(F) in eve-fit-web Pages CI. eve-fit-web has no unit tests (`web-unit` is empty). eve-dogma-lab branches hold no MCP or web suites.

The items below are `have` for that column in docs/19 and have no existing test. Only a proposed location and form are given. No test ids are invented.

## mcp: 38 uncovered

| id | name | proposed test |
|---|---|---|
| ENG-CORE-002 | Stacking penalties | eve-fit-mcp `tools/mcp-dogma-bench.py` (new, modelled on eve-fit-web tools/browser-dogma-bench.py) + CI step, suite `mcp-bench`: run the bench FitRequests through the MCP `compute_fit` tool (FitRequest passthrough, detail full) and score with bench tolerances; cases = this item's f-column refs in tests.yaml |
| ENG-CORE-003 | Hand-written effects (eos/effects.py, 2402 classes) | eve-fit-mcp `tools/mcp-dogma-bench.py` (new, modelled on eve-fit-web tools/browser-dogma-bench.py) + CI step, suite `mcp-bench`: run the bench FitRequests through the MCP `compute_fit` tool (FitRequest passthrough, detail full) and score with bench tolerances; cases = this item's f-column refs in tests.yaml |
| ENG-MOD-004 | Reload time / factor reload | eve-fit-mcp `tools/mcp-dogma-bench.py` (new, modelled on eve-fit-web tools/browser-dogma-bench.py) + CI step, suite `mcp-bench`: run the bench FitRequests through the MCP `compute_fit` tool (FitRequest passthrough, detail full) and score with bench tolerances; cases = this item's f-column refs in tests.yaml |
| ENG-MOD-006 | Overheat bonuses | eve-fit-mcp `tools/mcp-dogma-bench.py` (new, modelled on eve-fit-web tools/browser-dogma-bench.py) + CI step, suite `mcp-bench`: run the bench FitRequests through the MCP `compute_fit` tool (FitRequest passthrough, detail full) and score with bench tolerances; cases = this item's f-column refs in tests.yaml |
| ENG-MOD-011 | Capacitor use per module | eve-fit-mcp `tools/mcp-dogma-bench.py` (new, modelled on eve-fit-web tools/browser-dogma-bench.py) + CI step, suite `mcp-bench`: run the bench FitRequests through the MCP `compute_fit` tool (FitRequest passthrough, detail full) and score with bench tolerances; cases = this item's f-column refs in tests.yaml |
| ENG-SHIP-003 | Structures / citadels | eve-fit-mcp `tools/mcp-dogma-bench.py` (new, modelled on eve-fit-web tools/browser-dogma-bench.py) + CI step, suite `mcp-bench`: run the bench FitRequests through the MCP `compute_fit` tool (FitRequest passthrough, detail full) and score with bench tolerances; cases = this item's f-column refs in tests.yaml |
| ENG-SHIP-005 | System security | eve-fit-mcp `tools/mcp-dogma-bench.py` (new, modelled on eve-fit-web tools/browser-dogma-bench.py) + CI step, suite `mcp-bench`: run the bench FitRequests through the MCP `compute_fit` tool (FitRequest passthrough, detail full) and score with bench tolerances; cases = this item's f-column refs in tests.yaml |
| ENG-SHIP-006 | Ship traits / role bonuses | `src/test/integration.test.ts` "get_ship: traits / role bonuses" — assert the hull bonus lines of a T2 hull |
| ENG-DRN-004 | Drone speed/range/sig | eve-fit-mcp `tools/mcp-dogma-bench.py` (new, modelled on eve-fit-web tools/browser-dogma-bench.py) + CI step, suite `mcp-bench`: run the bench FitRequests through the MCP `compute_fit` tool (FitRequest passthrough, detail full) and score with bench tolerances; cases = this item's f-column refs in tests.yaml |
| ENG-FTR-003 | Fighter DPS per effect | eve-fit-mcp `tools/mcp-dogma-bench.py` (new, modelled on eve-fit-web tools/browser-dogma-bench.py) + CI step, suite `mcp-bench`: run the bench FitRequests through the MCP `compute_fit` tool (FitRequest passthrough, detail full) and score with bench tolerances; cases = this item's f-column refs in tests.yaml |
| ENG-CAP-001 | Capacitor capacity/recharge/peak | eve-fit-mcp `tools/mcp-dogma-bench.py` (new, modelled on eve-fit-web tools/browser-dogma-bench.py) + CI step, suite `mcp-bench`: run the bench FitRequests through the MCP `compute_fit` tool (FitRequest passthrough, detail full) and score with bench tolerances; cases = this item's f-column refs in tests.yaml |
| ENG-CAP-002 | Capacitor simulation (stable %, lasts) | eve-fit-mcp `tools/mcp-dogma-bench.py` (new, modelled on eve-fit-web tools/browser-dogma-bench.py) + CI step, suite `mcp-bench`: run the bench FitRequests through the MCP `compute_fit` tool (FitRequest passthrough, detail full) and score with bench tolerances; cases = this item's f-column refs in tests.yaml |
| ENG-CAP-003 | Cap injectors / boosters | eve-fit-mcp `tools/mcp-dogma-bench.py` (new, modelled on eve-fit-web tools/browser-dogma-bench.py) + CI step, suite `mcp-bench`: run the bench FitRequests through the MCP `compute_fit` tool (FitRequest passthrough, detail full) and score with bench tolerances; cases = this item's f-column refs in tests.yaml |
| ENG-CAP-004 | Own neuts/nos in cap sim | eve-fit-mcp `tools/mcp-dogma-bench.py` (new, modelled on eve-fit-web tools/browser-dogma-bench.py) + CI step, suite `mcp-bench`: run the bench FitRequests through the MCP `compute_fit` tool (FitRequest passthrough, detail full) and score with bench tolerances; cases = this item's f-column refs in tests.yaml |
| ENG-CAP-005 | Incoming neut / remote cap in sim | eve-fit-mcp `tools/mcp-dogma-bench.py` (new, modelled on eve-fit-web tools/browser-dogma-bench.py) + CI step, suite `mcp-bench`: run the bench FitRequests through the MCP `compute_fit` tool (FitRequest passthrough, detail full) and score with bench tolerances; cases = this item's f-column refs in tests.yaml |
| ENG-DEF-003 | Tank: active/sustained/reinforced | eve-fit-mcp `tools/mcp-dogma-bench.py` (new, modelled on eve-fit-web tools/browser-dogma-bench.py) + CI step, suite `mcp-bench`: run the bench FitRequests through the MCP `compute_fit` tool (FitRequest passthrough, detail full) and score with bench tolerances; cases = this item's f-column refs in tests.yaml |
| ENG-DEF-004 | Reactive armor hardener sim | eve-fit-mcp `tools/mcp-dogma-bench.py` (new, modelled on eve-fit-web tools/browser-dogma-bench.py) + CI step, suite `mcp-bench`: run the bench FitRequests through the MCP `compute_fit` tool (FitRequest passthrough, detail full) and score with bench tolerances; cases = this item's f-column refs in tests.yaml |
| ENG-DEF-005 | Ancillary repairers (charged) | eve-fit-mcp `tools/mcp-dogma-bench.py` (new, modelled on eve-fit-web tools/browser-dogma-bench.py) + CI step, suite `mcp-bench`: run the bench FitRequests through the MCP `compute_fit` tool (FitRequest passthrough, detail full) and score with bench tolerances; cases = this item's f-column refs in tests.yaml |
| ENG-DEF-006 | Shield recharge peak | eve-fit-mcp `tools/mcp-dogma-bench.py` (new, modelled on eve-fit-web tools/browser-dogma-bench.py) + CI step, suite `mcp-bench`: run the bench FitRequests through the MCP `compute_fit` tool (FitRequest passthrough, detail full) and score with bench tolerances; cases = this item's f-column refs in tests.yaml |
| ENG-DEF-007 | Incoming remote reps in tank | eve-fit-mcp `tools/mcp-dogma-bench.py` (new, modelled on eve-fit-web tools/browser-dogma-bench.py) + CI step, suite `mcp-bench`: run the bench FitRequests through the MCP `compute_fit` tool (FitRequest passthrough, detail full) and score with bench tolerances; cases = this item's f-column refs in tests.yaml |
| ENG-OFF-004 | Doomsdays / superweapons | eve-fit-mcp `tools/mcp-dogma-bench.py` (new, modelled on eve-fit-web tools/browser-dogma-bench.py) + CI step, suite `mcp-bench`: run the bench FitRequests through the MCP `compute_fit` tool (FitRequest passthrough, detail full) and score with bench tolerances; cases = this item's f-column refs in tests.yaml |
| ENG-NAV-002 | Warp speed and max warp distance | eve-fit-mcp `tools/mcp-dogma-bench.py` (new, modelled on eve-fit-web tools/browser-dogma-bench.py) + CI step, suite `mcp-bench`: run the bench FitRequests through the MCP `compute_fit` tool (FitRequest passthrough, detail full) and score with bench tolerances; cases = this item's f-column refs in tests.yaml |
| ENG-NAV-003 | Warp core strength / scram status | eve-fit-mcp `tools/mcp-dogma-bench.py` (new, modelled on eve-fit-web tools/browser-dogma-bench.py) + CI step, suite `mcp-bench`: run the bench FitRequests through the MCP `compute_fit` tool (FitRequest passthrough, detail full) and score with bench tolerances; cases = this item's f-column refs in tests.yaml |
| ENG-TGT-001 | Targeting stats | eve-fit-mcp `tools/mcp-dogma-bench.py` (new, modelled on eve-fit-web tools/browser-dogma-bench.py) + CI step, suite `mcp-bench`: run the bench FitRequests through the MCP `compute_fit` tool (FitRequest passthrough, detail full) and score with bench tolerances; cases = this item's f-column refs in tests.yaml |
| ENG-TGT-003 | ECM jam chance | eve-fit-mcp `tools/mcp-dogma-bench.py` (new, modelled on eve-fit-web tools/browser-dogma-bench.py) + CI step, suite `mcp-bench`: run the bench FitRequests through the MCP `compute_fit` tool (FitRequest passthrough, detail full) and score with bench tolerances; cases = this item's f-column refs in tests.yaml |
| ENG-TGT-004 | Probe size / scan | bench ext `probe_*` via `mcp-bench` (pointer /targeting/probe_size), or integration test "probe size in targeting section" |
| ENG-TGT-005 | Drone control range | eve-fit-mcp `tools/mcp-dogma-bench.py` (new, modelled on eve-fit-web tools/browser-dogma-bench.py) + CI step, suite `mcp-bench`: run the bench FitRequests through the MCP `compute_fit` tool (FitRequest passthrough, detail full) and score with bench tolerances; cases = this item's f-column refs in tests.yaml |
| ENG-PROJ-004 | Projection range (distance) | eve-fit-mcp `tools/mcp-dogma-bench.py` (new, modelled on eve-fit-web tools/browser-dogma-bench.py) + CI step, suite `mcp-bench`: run the bench FitRequests through the MCP `compute_fit` tool (FitRequest passthrough, detail full) and score with bench tolerances; cases = this item's f-column refs in tests.yaml |
| ENG-PROJ-005 | Burst projectors / AoE / doomsday AoE | eve-fit-mcp `tools/mcp-dogma-bench.py` (new, modelled on eve-fit-web tools/browser-dogma-bench.py) + CI step, suite `mcp-bench`: run the bench FitRequests through the MCP `compute_fit` tool (FitRequest passthrough, detail full) and score with bench tolerances; cases = this item's f-column refs in tests.yaml |
| ENG-VAL-001 | Resources overflow | `integration.test.ts` "validate_fit: CPU / powergrid / calibration / bandwidth overload" (bench ext `val_cpu_power_overload`, `val_drone_bandwidth`) |
| ENG-VAL-005 | Disable fitting restrictions | `integration.test.ts` "allow_violations computes an illegal fit" (bench ext `val_disable_restrictions_stats`) |
| ENG-VAL-006 | Charge validity | `integration.test.ts` "validate_fit: charge group / size / capacity" (bench ext `val_charge_group`, `val_charge_size`, `val_charge_capacity*`) |
| CHR-007 | Security status on character | `integration.test.ts` "character security status passes through" |
| UI-STAT-RST | Resistances panel | eve-fit-mcp `tools/mcp-dogma-bench.py` (new, modelled on eve-fit-web tools/browser-dogma-bench.py) + CI step, suite `mcp-bench`: run the bench FitRequests through the MCP `compute_fit` tool (FitRequest passthrough, detail full) and score with bench tolerances; cases = this item's f-column refs in tests.yaml |
| UI-STAT-RCH | Recharge panel | eve-fit-mcp `tools/mcp-dogma-bench.py` (new, modelled on eve-fit-web tools/browser-dogma-bench.py) + CI step, suite `mcp-bench`: run the bench FitRequests through the MCP `compute_fit` tool (FitRequest passthrough, detail full) and score with bench tolerances; cases = this item's f-column refs in tests.yaml |
| UI-PREF-ENG | Engine preferences | `src/test/features.test.ts` "options passthrough: factor_reload / default_spool / rah change the numbers" |
| ENG-MISC-001 | Smartbombs and bombs | eve-fit-mcp `tools/mcp-dogma-bench.py` (new, modelled on eve-fit-web tools/browser-dogma-bench.py) + CI step, suite `mcp-bench`: run the bench FitRequests through the MCP `compute_fit` tool (FitRequest passthrough, detail full) and score with bench tolerances; cases = this item's f-column refs in tests.yaml |
| ENG-MISC-002 | Utility modules without stats | eve-fit-mcp `tools/mcp-dogma-bench.py` (new, modelled on eve-fit-web tools/browser-dogma-bench.py) + CI step, suite `mcp-bench`: run the bench FitRequests through the MCP `compute_fit` tool (FitRequest passthrough, detail full) and score with bench tolerances; cases = this item's f-column refs in tests.yaml |

## web: 24 uncovered

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

## Status notes for eve

MCP items still `partial` in docs/19 (statuses cite an older eve-fit-mcp) that now have dedicated tests on main 64d6cd6 and are mapped:
ENG-CORE-005, ENG-MOD-008, ENG-PROJ-001, ENG-FLT-001, ENG-ENV-001, ENG-TGT-002, GRF-* (list_graphs / compute_graph), MKT-001, PRC-001, PRC-002. Whether to upgrade them is eve's call.
