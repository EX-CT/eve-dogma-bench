# CONTRACT-MUTATED — mutated items and implant/booster combinations (draft 0.1)

Status: **draft 0.1** (2026-10-03, branch `mutated-suite`). This contract is **additive to bench CONTRACT.md 1.4.x**. The
request and response shapes are unchanged: everything here pins down semantics that the 1.x corpus barely exercises
(one mutated case, `esf_mutations`). Expected values come from Pyfa (eos), used as a black-box oracle; see
`mutated/README.md`.

## 1. Request format

A mutated module or drone is an ordinary `modules[]` / `drones[]` entry with a `mutation` object. This is the
same shape as CONTRACT.md 1.x and as the result of Pyfa importing EFT `[Mutated]` notation (§4):

```jsonc
{"type_id": 47408,                        // resulting (abyssal) type, e.g. "50MN Abyssal Microwarpdrive"
 "slot": "mid", "state": "active",
 "mutation": {
   "base_type_id": 12076,                 // the item that was mutated ("50MN Microwarpdrive II"); EFT: the item line
   "mutaplasmid_type_id": 47742,          // "Decayed 50MN Microwarpdrive Mutaplasmid"
   "attributes": {"6": 172.8, "20": 515.1, "30": 160.05, "50": 49.6, "554": 446.5}   // absolute rolled values
 }}
```

* `attributes` keys are dogma attribute ids as strings. Values are **absolute** (the rolled value, not a
  multiplier), exactly what Pyfa stores in `Mutator.value` and what EFT prints.
* `type_id` should be the mutaplasmid's resulting type for `base_type_id`
  (dataset `mutaplasmids[<id>].mapping[].output`). If it differs, the resulting type wins, as in Pyfa
  (`Module(mutaplasmid.resultingItem, baseItem, mutaplasmid)`). `type_id` is then only informational.
* A mutated drone entry is one stack: every drone in `quantity` has the same roll. Differently rolled drones of the
  same base are separate entries.
* `mutation: null` or a missing key means not mutated.

## 2. Semantics of a mutated item (Pyfa `MutatedMixin`, `Mutator`, `getItemWithBaseItemAttribute`)

1. **Attributes.** Start from the base type's attributes and lay the resulting type's own attributes over them
   (`{**base.attributes, **resulting.attributes}`). Mass (attribute 4) comes from the type's `mass` field.
2. **Effects** are those of the resulting type. In SDE 3569502 every resulting type carries all of its bases'
   effects except in one pair: Naiyon's Modified Stasis Webifier (15419) has effect 586 (`decreaseTargetSpeed`), and the
   Abyssal Stasis Webifier (47702) does not. For every other pair, an engine that also merges the base type's
   effects gets identical results. No 0.1 case uses 15419.
3. **Required skills** are those of the resulting type. If it has none, fall back to the base type's.
4. **Mutated attributes.** These are exactly the attributes listed for the mutaplasmid
   (dataset `mutaplasmids[<id>].attrs`, i.e. SDE `dynamicItemAttributes`, as `[min, max]` multipliers). For each one:
   * the start value is the **base type's** value, not the resulting type's, even when the resulting type lists the
     attribute;
   * when `attributes` gives a value `v`, it is validated like Pyfa's `Mutator.validator`. Let `b` be the base
     type's value and `lo = round(min, 3)`, `hi = round(max, 3)`:
     * `b == 0`: the value is `0`;
     * `lo <= v/b <= hi`: `v` is kept;
     * otherwise `v` is clamped to `[min(lo·b, hi·b), max(lo·b, hi·b)]`. This works for negative bases too.
   * an attribute the mutaplasmid lists but `attributes` omits keeps the base type's value
     (cases `partial_*`, `empty_attrs_*`);
   * keys in `attributes` that the mutaplasmid does not list are **ignored** (cases `foreign_attr_*`).
5. The validated value replaces the attribute's **base** value. Every modifier (skills, ship bonuses, implants,
   boosters, stacking penalties, heat, fleet, projected) then applies to it as to any other attribute. Several
   mutated copies of one module are independent items and are stacking-penalised as usual (cases `multi_*`).
6. In Pyfa a mutated value takes precedence over an `overrides[]` entry for the same attribute
   (`mutator > override > base`). No 0.1 case combines the two.

## 3. Implants and boosters

1. **Slots.** An implant occupies `implantness` (attribute 331) and a booster occupies `boosterness` (1087).
   Entries are processed in list order, and an entry whose slot is already taken by an earlier entry **is ignored
   completely**. That means none of its effects and none of its side effects. This is Pyfa's
   `HandledImplantList` / `HandledBoosterList.append` behaviour; EFT import goes through the same path. Cases:
   `slot_*`, `combo_two_boosters_dda_*`.
2. **Side effects.** `boosters[].side_effects` lists the side-effect effect ids to switch on (CONTRACT.md 1.x);
   all other side effects stay off. A side-effect id listed for an ignored booster does nothing.
3. **Pyfa effect overrides that the SDE gets wrong.** Engines must follow Pyfa:
   * `boosterMissileExplosionCloudPenaltyFixed` (effect 2791; Exile and Mindflood side effect). The SDE
     modifier filters on charges requiring skill 3452 (Acceleration Control). Pyfa's handler uses charges requiring
     **Missile Launcher Operation (3319)**, so it raises missile explosion radius
     (case `combo_nomad_ab_mwd_exct_damnation`, weapons 9–11).
4. Implant sets (Snake, Crystal, Halo, Amulet, Ascendancy, Asklepian, Talisman, low-grade Nomad), full and partial,
   plus mixes of two sets, work through ordinary set-bonus modifiers. Cases: `combo_*`.

## 4. EFT `[Mutated]` notation (Pyfa `service/port/eft.py`, `service/port/muta.py`)

**Export** (`eft_export`, byte-identical to Pyfa `exportEft` with all options on):

* A mutated module is written under its **base** name followed by ` [N]`, e.g. `Warp Scrambler II [1]`.
  A charge goes before the reference (`Name, Charge [N]`) and `/OFFLINE` goes after the charge and before ` [N]`.
* A mutated drone stack is written as `Base Name xQ [N]`. Drones are sorted by Pyfa `DRONE_ORDER` market group,
  then unmutated before mutated, then by full name. For a mutated drone the full name is
  `<mutaplasmid short name> <base name>`, so `[N]` numbering follows that order.
* References `N` count from 1 over modules (rack order as exported) and then over drones.
* The last section holds, for each reference in order:
  ```
  [N] Base Name
    Mutaplasmid Name
    attrName value, attrName value, ...
  ```
  * Attribute names are dogma attribute **names** (`maxRange`, `capacitorNeed`), sorted.
  * Values are Pyfa `floatUnerr` of the **validated** value from §2. Out-of-range, omitted and foreign
    attributes therefore print as Pyfa holds them, not as the request gave them.
* Implants and boosters ignored under §3 are not exported.

**Import** (`eft_parse`) must give the fit that Pyfa's `importEft` gives:

* The item line names the **base** type. The `[N] Base Name` header's name is ignored; the line wins
  (`eftedge_header_base_mismatch`).
* The resulting type comes from the mutaplasmid's mapping for that base.
* Attribute names are looked up by dogma name. Unknown names and attributes the mutaplasmid does not list are
  dropped (`eftedge_unknown_attr`). Values go through §2 validation, either at parse time or at calc time; the
  checker compares effective values.
* A block without an attribute line means every mutated attribute keeps its base value (`eftedge_no_attr_line`).
* A reference without a block gives the plain, unmutated base item (`eftedge_missing_ref`).
* One reference used on two lines mutates both modules identically (`eftedge_shared_ref`).
* `Name xQ [N]` mutates the whole drone stack (`eftedge_drone_stack`).
* Implant and booster lines follow §3 (`eftedge_implant_booster_slots`).
* A mutaplasmid that does not belong to the base's family makes Pyfa raise an error. Its behaviour is undefined
  in 0.1 and it is not tested.

## 5. Scoring

| part | what | tool | unit |
|---|---|---|---|
| stats | 93 cases, 6,184 values, same metrics and tolerances as the main corpus | `mutated/run_mutated.py` | cases fully correct, values |
| EFT export | Pyfa export text of every case | `mutated/tools/check_eft.py` | texts byte-identical / 93 |
| EFT import | Pyfa import of 91 of the 93 exports plus 8 edge texts | `mutated/tools/check_eft.py` | fits equal / 99 |
| regression | bench 1.8.0 corpus | `run.py` | must stay 326/326, byte-identical |

* Two exports are excluded from the import check (`expected_extra/eft_import_excluded.json`):
  `combo_mindflood_ham_se_exct_ishtar` and `state_web_overheated_exct_tengu`. The cause has been found (§6.1) and is
  not specific to mutation. Pyfa's `importEft` drops every module that does not `fits()` the hull, and both source
  fits have more mid-slot modules than Pyfa gives the hull at import time. The mutated module is the last one in
  the mid rack, so it is the one that gets dropped.
* The import check compares only the ship, the mutated modules (in order), all drones, implants and boosters.
  General EFT import fidelity for unmutated modules belongs to the formats suite.
* Known SDE-vs-Pyfa divergences that the main corpus excludes for a source fit stay excluded in every case built from
  that fit. An example is `warp_scramble_status` with a Networked Sensor Array; see `expected/known_divergences.json`.

### 5.1 Pass rules
* **Stats value:** `|got - want| <= max(1e-3, 1e-4 * |want|)`. Booleans must match exactly, and a missing pointer
  fails. This is the main corpus rule from `tools/metrics.py`. A case passes when every expected value passes and
  the engine reports no error.
* **EFT export row:** the text must be byte-identical. The one exception is the T3C extra
  `[Empty Subsystem slot]` line from the SDE/Pyfa `maxSubSystems` divergence, which is accepted.
* **EFT import row:** the comparison covers the ship, the mutated modules in order (type id, charge, base,
  mutaplasmid, and effective values from §2 within relative 1e-6), all drones as a multiset (type, quantity,
  mutation), and the implants and boosters after the §3.1 slot rule. An RPC error or an unparsable result fails
  the row.
* **Gate:** 326/326 on the 1.8.0 corpus and no engine errors on the suite. Below the gate the suite score is
  reported but not ranked.
* **Score (proposed, open):** 0.6 × stats cases + 0.2 × export rows + 0.2 × import rows, each as a fraction.
  Performance is not scored.

## 6. Open questions (for 0.2)

### 6.1 EFT import drops modules that do not fit
This was found while checking the two excluded rows. Pyfa's `importEft` builds the fit in this order: subsystems,
then a recalculation, then the other racks. It then places each module only if `Module.fits(fit)` is true. That
means a free slot in the rack (counted with the subsystem slot modifiers), `canFitShipGroup/Type`, the capital-size
rule, rig size, and `maxGroupFitted`. A module that fails is **dropped silently**. Within a rack the lines are
placed in order, so an overfull rack loses its last lines.

* `exct_ishtar` lists 5 mid-slot modules, but the Ishtar has 4 mid slots in both Pyfa's eve.db and the dataset
  (`medSlots`). The last mid module, here the mutated 50MN MWD, is dropped. The unmutated text behaves the same way:
  the plain `50MN Microwarpdrive II` is dropped too.
* `exct_tengu` lists 6 mid-slot modules, but at import time Pyfa gives this subsystem set 4 mid slots. The last two
  are dropped: `Warp Disruptor II` and the mutated `Stasis Webifier II`.
* `calc` and `eft_export` do not check slot counts, in Pyfa or in this contract, so the stats and export rows of
  these cases stay valid.

Proposed for 0.2: either make **"import drops modules that do not fit, in line order"** a rule with dedicated rows
(this is general import fidelity, so it may belong in the formats suite), or keep overfitted source fits out of the
generator. Until then the two rows stay excluded.

### 6.2 Other open points
* `overrides[]` combined with a mutation (`mutator > override > base`).
* A mutaplasmid applied to a base outside its family. Pyfa raises an error, so this is undefined.
* Name-keyed `attributes` in requests (EFT style).
* Naiyon's Modified Stasis Webifier (15419): the one base whose effects the resulting type lacks.

## Changelog

* 0.1 (2026-10-03): first draft, with 93 stats cases, 93 export texts and 99 import texts.
* 0.1 (2026-10-03 ~10:00): text only. The cause of the two excluded import rows is identified (§6.1), and the pass rules are written out (§5.1). Status: DRAFT.
