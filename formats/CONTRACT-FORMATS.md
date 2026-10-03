# eve-dogma FORMATS contract (DRAFT, round 3, revision 0.1)

> **Status: draft, not frozen, not published.** It lives on eve-dogma-bench branch `formats-suite` and is not part
> of the frozen 1.8.0 scoring. It will be frozen after the round-1 archive. Until then, cases and wording may change.

Round 3 scores **fit import and export** against Pyfa's actual behaviour (Pyfa `service/port/`, client db 3532181).
It is a black-box contract. Every expected value is Pyfa output, produced by `oracle/pyfa_formats.py`, which loads
Pyfa's own port modules unmodified (a GPL-3.0 test tool, see `oracle/LICENSE-GPL-NOTE`). Only Pyfa's outputs are
stored here. Variants implement the behaviour described below and must not copy Pyfa (GPL) code.

It extends the base contract (`CONTRACT.md` 1.4.3): FitRequest shapes, type ids and the dataset are unchanged.
Dataset: `dataset-3569502` (the round-1 dataset).

## 1. Scope

| format id | name | export | import | Pyfa reference |
|---|---|---|---|---|
| `eft` | EFT text, single fit (multi-fit paste = merged, §4.3) | yes | yes | `eft.py exportEft / importEft` |
| `eftcfg` | EFT config file (`<Ship>.cfg`, multi-fit) | – | yes | `eft.py importEftCfg` |
| `dna` | DNA `ship:mod;n:…::`, and the chat link `<url=fitting:DNA>name</url>` | yes | yes | `dna.py exportDna / importDna` |
| `dna_alt` | `DNA:ship:id*n:…` | – | yes (via `auto`) | `dna.py importDnaAlt` |
| `esi` | ESI fitting JSON | yes | yes | `esi.py exportESI / importESI` |
| `xml` | EVE client fittings XML (multi-fit) | yes | yes | `xml.py exportXml / importXml` |
| `multibuy` | Multibuy list | yes | – | `multibuy.py exportMultiBuy` |
| `shipstats` | Ship stats clipboard text | yes | – | `shipstats.py exportFitStats` |
| `auto` | format auto-detection (fits, mutated item, additions lists) | – | yes | `port.py Port.importAuto` |

Out of scope in 0.1: EFS export (needs Pyfa's GUI stats tables), Multibuy price optimisation (needs market data),
killmail and ESI network fetches, the `[n]` mutation references inside additions lists.

## 2. Transport

**Required:** the base contract's line RPC (`<variant> serve-stdio`). Each line `{"id","method","params"}` gets one
line `{"id","result"}` back. Errors are returned as `"result": {"error": {"code","message"}}` (a top-level
`"error"` is accepted as well).

**Optional:** a batch CLI (`<variant> format-batch`). It reads one `{"method","params"}` per stdin line and writes
exactly one result object per line, in the same order.

Text is UTF-8 inside JSON strings. Variants must not change the input text (BOM, CR, tabs and trailing whitespace
are part of the case).

## 3. Export

```jsonc
// method "format_export"
{"fit": { /* FitRequest, base contract */ }, "name": "fit name", "format": "eft", "options": {…}}
// -> {"text": "..."}            or {"error": {"code": "EXPORT_ERROR" | "BAD_REQUEST" | "UNSUPPORTED_FORMAT", …}}
```

`format` is one of `eft`, `dna`, `esi`, `xml`, `multibuy`, `shipstats`. The suite also uses option sets as row
names: `eft_min`, `dna_formatted`, `esi_min` and `multibuy_min` are sent as the base format with these options:

| row | options |
|---|---|
| `eft` | `{"implants": true, "mutations": true, "loaded_charges": true, "boosters": true, "cargo": true}` |
| `eft_min` | the same keys, all `false` |
| `dna` / `dna_formatted` | `{"formatting": false}` / `{"formatting": true}` (chat link) |
| `esi` / `esi_min` | `{"charges": true, "implants": true, "boosters": true}` / all `false` |
| `multibuy` / `multibuy_min` | `{"loaded_charges", "cargo", "implants", "boosters"}` all `true` / all `false`, plus `"optimize_prices": false` |
| `xml`, `shipstats` | `{}` |

The `text` must be **byte-identical** to Pyfa's output: same line order and separators, `\n` line ends, no trailing
newline unless Pyfa writes one. `name` is written as given; Pyfa does not escape it except where the format requires
(§4.6). Pyfa refuses some exports, and then the variant must return an error: ESI export of a fit with no items
(`EXPORT_ERROR`, Pyfa "module list cannot be empty").

## 4. Import

```jsonc
// method "format_import"
{"text": "...", "format": "auto" | "eft" | "eftcfg" | "dna" | "dna_alt" | "esi" | "xml", "path": "Rifter.cfg"}
// fits  -> {"kind": "EFT" | "EFT Config" | "DNA" | "XML" | "JSON", "fits": [FitResult, …]}
// items -> {"kind": "FittingItem" | "AdditionsDrones" | "AdditionsFighters" | "AdditionsImplants" |
//                   "AdditionsBoosters" | "AdditionsCargo", "items": [{"type_id", "amount", "mutation"}]}
// error -> {"error": {"code": "UNRECOGNIZED_INPUT" | "IMPORT_ERROR" | "BAD_REQUEST" | "UNSUPPORTED_FORMAT", "message"}}
```

`path` is the file name a file import would pass. Only `auto` uses it, for EFT config detection, and the ship name is
the file stem.

**FitResult** is FitRequest-shaped, using the base contract field names:
- `name`
- `ship {type_id, mode_type_id}`
- `modules [{type_id, slot, state, charge_type_id, mutation}]`, in rack order. `slot` is one of `high`, `mid`,
  `low`, `rig`, `subsystem`, `service`. `state` is one of `offline`, `online`, `active`, `overheated`. `mutation` is
  `{base_type_id, mutaplasmid_type_id, attributes: {attr_id: value}}` and `type_id` is the mutated type.
- `drones [{type_id, quantity, active}]`
- `fighters [{type_id, quantity, active}]`
- `implants [type_id | {type_id}]`, `boosters [{type_id}]`, `cargo [{type_id, quantity}]`
- `notes` (optional)

Empty slots are not listed.

`kind` is the Pyfa import type: `JSON` for ESI and `EFT Config` for `.cfg`. A forced `format` reports the kind of
that format.

### 4.1 Outcomes and error codes

| Pyfa outcome | contract result |
|---|---|
| a fit kind with ≥ 1 fit | `{"kind","fits"}`. Pyfa's `None` fits are left out, keeping the order (XML with one bad `<fitting>`). |
| a non-fit kind (`auto` only) | `{"kind","items"}` |
| `auto`: no format matches, including blank input (Pyfa raises IndexError there) | `UNRECOGNIZED_INPUT` |
| the format is detected or forced but no fit results (parse error, Pyfa exception, `None` fit, zero fits) | `IMPORT_ERROR` |
| unknown `format` name or method | `UNSUPPORTED_FORMAT` / `UNKNOWN_METHOD` (the row counts as *not implemented*) |
| request shape wrong (`text` not a string, …) | `BAD_REQUEST` |

Rows where Pyfa fails with an internal exception (AttributeError, KeyError, TypeError, IndexError, ValueError
"substring not found") are marked `"pyfa_crash": true` in `edge.jsonl`. They are scored as `IMPORT_ERROR` in 0.1
(see §9, open question 1).

### 4.2 Auto-detection order (Pyfa `importAuto`; "first line" = first non-blank line, stripped)

1. The first line starts with `<?xml` → `xml`.
2. The first character of the first line is `{` → `esi`.
3. A `path` is given and the first line matches `^\s*\[.*\]` → `eftcfg` (ship = file stem).
4. The first line matches `^\s*\[.*,.*\]` → `eft`.
5. The first line matches `\d+(:\d+(;\d+))*::` at its start → `dna`.
6. The first line contains `<url=fitting:DNA>name</url>` → `dna` (name = link text; only the **first** link counts).
7. The first line contains `DNA:id(:id(*n)?)*` → `dna_alt`.
8. A mutated item (base type line, mutaplasmid line, attribute line) → `FittingItem`. If only the first line is a
   known item, it is `FittingItem` without a mutation; this is why a pasted implant or booster list is a
   `FittingItem` of its first line.
9. Additions lists, tried in this order: drones, fighters, implants, boosters, cargo.
10. Otherwise → `UNRECOGNIZED_INPUT`.

A UTF-8 BOM is not whitespace, so a BOM-prefixed EFT text is unrecognised. XML without the `<?xml` declaration is
unrecognised under `auto` (a forced `xml` imports it).

### 4.3 EFT (behaviour shown by the cases)

- **Header:** `[Ship, name]`. The name is everything after the first comma, stripped, and may contain commas.
  Leading and trailing whitespace on the line is ignored.
- **Header failures (→ `IMPORT_ERROR`):** an empty name (`[Rifter,]`), an unknown ship, or a type that is not a
  ship. Ship and item names are **case-sensitive**.
- **Renamed items:** old names are resolved through Pyfa's rename table (e.g. `Drone Control Unit I` → `Fighter
  Support Unit I`).
- **Sections:** sections are separated by blank lines. Modules are placed by their slot type, in input order.
  - `[Empty X slot]` lines are skipped.
  - `/offline` (any case) sets the module offline. Other modules get their highest allowed state (`activeStateLimit`).
  - `module, charge` loads the charge only if it fits the module; otherwise the module is loaded with no charge.
  - Unknown lines are ignored, including comments (`#`, `//`) and an unknown item or charge.
  - Modules beyond the hull's slots or hardpoints, and subsystems that don't fit the hull, are dropped.
- **`Name xN` lines:** these are drones, fighters or cargo by category. A module written as `Module xN` goes to
  **cargo**. `x0` drones are kept with quantity 0, and drone stacks of the same type are merged.
- **Mutations:** `Item [n]` references a trailing `[n] Base` block (base type, mutaplasmid, then `attrName value, …`).
  - Unknown attribute names are skipped.
  - Values are taken as written, with no clamping to the mutaplasmid range.
  - If the block is missing, the plain base item is fitted.
- **T3D:** a mode line is not read, and the fit gets the hull's first mode. `mode_type_id` null counts as equal.
- **Line ends and whitespace:** CRLF, CR and mixed line ends are accepted, and so are tabs as whitespace.
- **Multi-fit paste:** a second `[Ship, name]` header in the same text does **not** start a new fit. Its modules
  are merged into the first fit (the first header wins).
- **EFT config (`eftcfg`):** each `[name]` starts a fit for the ship named by the file stem. An unknown stem, or a
  file with no fit lines, gives `IMPORT_ERROR`.

### 4.4 DNA

- **Name:** `"<Ship name> - DNA Imported"`, or the link text for a chat link.
- **Modules:** they get their highest allowed state. A quantity of 0 drops the entry.
- **Charges:** charges go to cargo and are not loaded.
- **Multiple lines or links:** only the first line, or the first link, is read.
- **Errors:** an unknown ship or a non-ship hull gives `IMPORT_ERROR`. Pyfa crashes on an unknown item id, so that
  is an `IMPORT_ERROR` too. A missing `::` gives `UNRECOGNIZED_INPUT` under `auto`, and `IMPORT_ERROR` when `dna`
  is forced.
- **Large quantities** are kept as given.

### 4.5 ESI JSON

- **Required keys:** `ship_type_id` and `description`. A missing `description` makes Pyfa crash (→ `IMPORT_ERROR`).
  A missing or unknown ship, or ids given as strings, give `IMPORT_ERROR`.
- **Items:**
  - Items are placed by `flag`, and unknown flags are skipped.
  - Unknown or unpublished types are skipped.
  - Fighters take the default squadron size.
  - Drones and cargo with quantity 0 are kept with quantity 0.
- **Empty `items`:** a valid, empty fit.
- **Invalid JSON:** `IMPORT_ERROR`.
- **Export:** the name is cut to 47 characters plus `...` when it is longer than 50.

### 4.6 XML

- **Fits:** every `<fitting>` is a fit. A fitting with an unknown ship is skipped and the others are kept. If no fit
  is left (`<fittings count="0">`), the result is `IMPORT_ERROR`.
- **`<description>` is required:** without it, Pyfa crashes (→ `IMPORT_ERROR`).
- **Slots:** slot indices only order the modules within a rack. Unknown slot names and unknown types are skipped.
- **Entities:** they are decoded once, so `&amp;amp;` becomes `&amp;`.
- **Export:** escapes `& < > "` in attributes. The description is limited to 400 characters and newlines become
  `<br>`.

### 4.7 Items payloads (`auto` with non-fit text)

`items` is a list of `{type_id, amount, mutation}` in input order. `FittingItem` has exactly one entry with
`amount` 1. Its `mutation` is null when no mutaplasmid line was recognised. Lists that mix categories are classified
by the first matching additions type (drones, then fighters, implants, boosters, cargo): a drone + charge list is
`AdditionsCargo`.

## 5. Normalisation and comparison

- **Export:** byte-exact text. The one accepted difference is §5.1. ESI rows that are only JSON-equal are reported
  (`info_json_equal_only`) but fail.
- **Import with fits:** the number of fits and their order must match. Per fit, these are compared and **scored**:
  - ship `type_id`
  - `mode_type_id` (null on the variant side = first mode, accepted)
  - modules per rack in order, as (type_id, state, charge_type_id, mutation). Mutation attributes are matched by
    attribute id and value, rounded to 6 decimals.
  - multisets of drones (type, quantity), fighters (type, quantity), implants, boosters and cargo (type, quantity)
  - `name`
  - `kind`, when the row has one

  Reported but **not scored:** drone `active` counts and `notes`.
- **Import with items:** `kind` and the ordered (type_id, amount, mutation) list.
- **Error rows:** pass when the variant returns any error. Whether the code matches is reported (informational in
  0.1).

### 5.1 Dataset note

SDE 3569502 gives T3 cruisers `maxSubSystems` = 5, and Pyfa's db gives 4. One extra `[Empty Subsystem slot]` line in
an EFT export is accepted (`info_known_divergence_subsystem_slot`).

## 6. Case files and counts (`formats/`)

| group | file | rows | content |
|---|---|---|---|
| `export:<fmt>` | `expected/export.jsonl` | **3260** | 326 bench fits (`cases/*.json`, name = file stem) × 10 export rows. 2 expected errors (`esi_min` of an item-less fit). |
| `import:<fmt>` | `expected/import.jsonl` | **1304** | Pyfa's import of its own export: 326 × {eft, dna, esi, xml}. 194 legal fits and 132 over-fitted (Pyfa drops the excess modules). 1 expected error (DNA of a mutated drone: Pyfa crash). |
| `edge_export:*` | `expected/edge_export.jsonl` + `edge_export/*.json` (`{"name","fit"}`) | **125** | 9 hand-written fits × 10 export rows (90, 2 errors) + 35 round-trip imports (1 error). Covers names with `& < > " [ ] , ; :`, unicode, a newline, 120 chars and empty; ship-only, cargo-only, mixed drone stacks, implants + boosters. |
| `edge:<category>` | `expected/edge.jsonl` + `edge/*` + `edge/MANIFEST.json` | **103** | 86 inputs imported with `auto`, plus 17 forced-format rows; 36 expected errors, 8 of them `pyfa_crash`. |

Edge categories (rows / of which errors):

| category | rows | errors | covers |
|---|---|---|---|
| `eft` | 29 | 5 | sections, `/offline` variants, CRLF/mixed line ends, tabs, comments, BOM, empty and comma names, unknown and non-ship hulls, case-sensitivity, renamed item, unknown and wrong-size charges, `x0`/huge quantities, `Module xN`, overfit, wrong-hull subsystem, T3D mode lines, T3C order, structure |
| `mutated` | 4 | 0 | mutated module and drone, unknown attribute, out-of-range values, missing block |
| `multi` | 7 | 0 | EFT 2- and 3-fit pastes (merged), `.cfg` with 2 fits, XML with 2 fits and a mutation, XML with one bad fitting, DNA on two lines, two chat links |
| `eftcfg` | 2 | 2 | empty `.cfg`, unknown ship stem |
| `dna` | 12 | 5 | chat link (alone and inside text), alt form, unknown ids, non-ship hull, `;0`, huge quantities, ship only, leading spaces, missing `::` |
| `esi` | 11 | 5 | wrong/unknown flags, unknown item/ship, quantity 0, long name, pretty-printed, string ids, missing ship/description, invalid JSON, empty items |
| `xml` | 7 | 4 | entities, slot gaps and unknown slot names, unknown module, `qty="0"`, no fittings, no description, malformed, no declaration |
| `items` | 8 | 0 | mutated item, an item without a mutaplasmid, drone/fighter/cargo lists, implant/booster lists (→ `FittingItem`), mixed lists |
| `autodetect` | 6 | 6 | empty, whitespace, prose, a bare number, a JSON array, `[Ship]` without a comma |
| `forced` | 17 | 9 | an explicit `format` on other formats' text or garbage, plus forced controls that succeed |

**Total: 4792 rows.**

Regenerate everything with `tools/gen_formats_edge.sh <ref>` (edge + edge_export). The bench-case rows are
regenerated as described in `formats/README.md`.

## 7. Scoring

`python3 tools/evaluate_formats.py --rpc "<variant> serve-stdio" --name X` (or `--batch-cmd`). Results go to
`results/formats/X/{scorecard.md, scorecard.json, failures.json}`.

- **Headline:** rows passed / 4792. Each row counts 1. Not-implemented formats count as failed and are marked.
- **Breakdown:** per group (`export`, `import`, `edge_export`, `edge`) and per category, plus legal-fit passes for
  round-trip imports, error-code agreement and `pyfa_crash` rows.
- **Tie-break proposal for ranking:** export and import groups first, then edge, then wall time of the full run.
- Exit status 0 only at 100 %.

## 8. Provenance

Inputs in `edge/` and `edge_export/` are hand-written for this suite. Expected values come only from running Pyfa
(`oracle/pyfa_formats.py`, unmodified `service/port/*`) on them. This document describes observed behaviour. It
contains no Pyfa code, and variants must re-implement the behaviour from this description and the cases.

## 9. Open questions (for the freeze)

1. **Pyfa crashes as truth:** should the 8 `pyfa_crash` rows (missing ESI `description`, XML without
   `<description>`, unknown DNA id, …) stay scored as `IMPORT_ERROR`, or become informational? A lenient importer
   currently fails them.
2. **Error codes:** score them in 0.1, or keep them informational until variants converge?
3. **Merged multi-fit EFT paste:** this is Pyfa behaviour and probably surprising to users. Keep it as truth, or
   rule it as "either merged or split"?
4. **Name scoring:** `name` is scored, including Pyfa's `"<Ship> - DNA Imported"`. Keep it, or make it informational
   like `notes`?
5. **Weighting:** the bench-case rows (4564) dominate the edge rows (228). Weight per group (e.g. 25 % each)
   instead of per row?
6. **Batch transport:** make `format-batch` mandatory, for throughput scoring?

## Changelog

- 0.1 (2026-10-03, draft): first revision, built from `formats-suite` dcd9e89 (3260 export / 1304 import / 16 edge
  rows). Adds 70 edge inputs, 17 forced rows, 9 export edge fits, outcome → error-code mapping,
  `tools/evaluate_formats.py`.
