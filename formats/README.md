# Import/export format suite (branch `formats-suite`, not part of the frozen 1.8.0 scoring)

> **Round 3:** this suite is now the **FORMATS contract 0.1 (DRAFT)**: `formats/CONTRACT-FORMATS.md`. It is
> scored with `tools/evaluate_formats.py`:
> `python3 tools/evaluate_formats.py --rpc "<variant> serve-stdio" --name X`. The suite has 4793 rows (4782 scored; 4 groups x 25 %): 3260
> export, 1304 round-trip import, 125 export-edge and 104 import-edge (malformed and abnormal; 11 report-only) rows. Edge inputs
> and their expectations are regenerated with `tools/gen_formats_edge.sh <ref>`. It is not frozen or published
> until the round-1 archive. The older `tools/check_formats.py` (16 edge rows) is kept for comparison.

Pyfa-generated expectations for every fit format in Pyfa's `service/port/` package, built from the 326 bench
cases plus hand-written edge inputs. Everything in `formats/expected/` is Pyfa output (client db 3532181) produced
by `oracle/pyfa_formats.py`, which loads Pyfa's own `service/port/*.py` unmodified (GPL-3.0 test tool, see
`oracle/LICENSE-GPL-NOTE`). Only the generated texts/JSON live here; no Pyfa code goes into any variant.

## Formats (Pyfa `service/port/`)

| format | Pyfa module | export | import | rows here |
|---|---|---|---|---|
| EFT text (all options) | `eft.py exportEft / importEft` | yes | yes | export 326, round-trip import 326 |
| EFT text, no options (no charges/implants/boosters/cargo/mutations) | `exportEft` | yes | – | export 326 |
| EFT config file (multi-fit `.cfg`, ship = file stem) | `eft.py importEftCfg` | – | yes | edge `Rifter.cfg` |
| DNA (`ship:mod;n:...::`) | `dna.py exportDna / importDna` | yes | yes | export 326, round-trip import 326 |
| DNA chat link (`<url=fitting:DNA>name</url>`) | `exportDna` (formatting on) / `importAuto` | yes | yes | export 326, edge 1 |
| DNA alt (`DNA:ship:id*n`) | `dna.py importDnaAlt` | – | yes | edge 1 |
| XML (EVE client fittings, multi-fit, mutations) | `xml.py exportXml / importXml` | yes | yes | export 326, round-trip 326, edge 1 (2 fits) |
| ESI fitting JSON (charges/implants/boosters on) | `esi.py exportESI / importESI` | yes | yes | export 326, round-trip 326, edge 1 |
| ESI fitting JSON (options off) | `exportESI` | yes | – | export 326 (2 expected errors: empty fit) |
| Multibuy (all options, no price optimisation) | `multibuy.py exportMultiBuy` | yes | – | export 326 |
| Multibuy (options off) | `exportMultiBuy` | yes | – | export 326 |
| Ship stats text (clipboard "stats") | `shipstats.py exportFitStats` | yes | – | export 326 |
| Mutated item text (single module + mutaplasmid lines) | `muta.py parseMutant` via `importAuto` | – | yes | edge 1 |
| Additions lists (drones/fighters/implants/boosters/cargo pasted into a fit) | `eft.py isValid*Import` via `importAuto` | – | yes | edge 1 |
| Format auto-detection | `port.py Port.importAuto` | – | yes | edge 16 |
| EFS (Eve Fitting Simulator JSON) | `efs.py EfsPort.exportEfs` | not generated (needs Pyfa's GUI fit commands) | – | 0 |

Totals: **3260 export rows** (10 export variants × 326 cases), **1304 round-trip import rows** (EFT, DNA, ESI,
XML × 326), **16 edge rows** (auto-detect + import of hand-written inputs).

## Files

- `formats/expected/export.jsonl` — `{"case","format","options","text"|"error"}`
- `formats/expected/import.jsonl` — `{"case","format","input","fits"|"error","source_overfit","pyfa_reexport_identical"}`.
  `input` is Pyfa's own export of the case; `fits` is what Pyfa's importer builds from it (FitRequest-shaped:
  ship/mode, modules with slot/state/charge/mutation, drones with quantity/active, fighters, implants, boosters,
  cargo, name). `source_overfit` marks the 132 bench fits with more modules than the hull has slots/hardpoints
  (validation cases): Pyfa's importers drop the excess modules, so those rows test that behaviour.
  `pyfa_reexport_identical` records whether Pyfa's own export→import→export is stable.
- `formats/expected/edge.jsonl` + `formats/edge/*` — hand-written inputs: `/offline` + `/OFFLINE`, mutated
  `[n]` blocks, all EFT sections, CRLF + unknown items + charge on a non-charge module, T3D mode line, T3C
  subsystem order, structure + service modules, two fits pasted as one EFT text (Pyfa merges them into one fit),
  EFT config multi-fit, XML multi-fit incl. mutation attributes, DNA chat link / alt / unknown id, ESI with
  unpublished/wrong-flag items, additions list, single mutated item.

## Checker (pre-contract; superseded by `tools/evaluate_formats.py`)

```
python3 tools/check_formats.py --rpc "<variant> serve-stdio" --name F
```

RPC methods (proposed for a later contract revision; nothing in 1.8.0 requires them):

- `format_export {fit, name, format, options}` → `{"text"}`; `format` ∈ `eft, dna, esi, xml, multibuy, shipstats`
  (the `_min` / `_formatted` rows send the base format with the option set shown in the row). Falls back to the
  existing `eft_export` for EFT.
- `format_import {text, format, path?}` → `{"kind", "fits": [FitRequest…]}`; `format` ∈ `eft, dna, esi, xml, auto`.
  Falls back to `eft_parse` for EFT.

Comparison: export text byte-exact (ESI also reports JSON-equal-only; EFT accepts the one known
`[Empty Subsystem slot]` divergence, as `tools/check_eft_export.py`). Import compares ship, modules per rack in
order (type, state, charge, mutation base/mutaplasmid/attributes to 1e-6), and multisets of drones, fighters,
implants, boosters and cargo. Fit name, drone active counts and a T3D mode left null (contract: first mode) are
reported as soft differences. Results: `results/formats/<name>/scorecard.md`, `failures.json`.

## Regenerating

```
R=/path/to/ref; cd $R/pyfa
PYTHONPATH=$R/stubs PYFA=$R/pyfa python oracle/pyfa_formats.py cases/*.json > raw_cases.jsonl
PYTHONPATH=$R/stubs PYFA=$R/pyfa python oracle/pyfa_formats.py --import auto formats/edge/* > raw_edge.jsonl
python3 tools/make_formats.py raw_cases.jsonl raw_edge.jsonl
```
