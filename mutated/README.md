# Mutated suite (mutaplasmids, abyssal modules/drones, implant/booster combinations)

This suite is separate from the frozen main corpus, which stays at 1.8.0. The contract is
[CONTRACT-MUTATED.md](CONTRACT-MUTATED.md) (draft 0.1).

| path | content |
|---|---|
| `cases/*.json` | 93 FitRequests built from main-corpus fits (`tools/gen_cases.py`, deterministic seed) |
| `index.json` | one line per case: what it tests |
| `expected/*.json` | Pyfa oracle values (`tools/make_expected.py`, same metrics as the main corpus) |
| `eft/*.eft.txt` | hand-written EFT `[Mutated]` edge texts |
| `expected_extra/eft_export.jsonl` | Pyfa `exportEft` text per case |
| `expected_extra/eft_import.jsonl` | Pyfa `importEft` result for each export text and each edge text |
| `run_mutated.py` | stats scorer (`run.py` on this suite) |
| `tools/check_eft.py` | EFT export and import checker |

Case families:

* `mm_*`: one rolled module per mutable module group (26 groups).
* `mwd_*`: every mutaplasmid tier on the 50MN MWD, plus min/max/over/under rolls.
* `edge_*`: min, max and over-range rolls on a damage control, a large shield extender and a medium armor repairer.
* `partial_*`, `empty_attrs_*`, `foreign_attr_*`: §2.4.
* `multi_*`: several rolled copies of one module.
* `state_*`: overheated or offline mutated modules.
* `drone_*`: mutated drones next to unmutated drones.
* `combo_*`: implant sets, hardwirings and boosters with side effects, mostly together with a mutated module.
* `slot_*`: implant and booster slot conflicts.

```sh
# stats
python3 mutated/run_mutated.py --name X --cmd "<engine> calc --dataset D" --batch-cmd "<engine> batch --dataset D"
# EFT export and import
python3 mutated/tools/check_eft.py --rpc-cmd "<engine> serve-stdio --dataset D" --dataset D
# regenerate (needs the Pyfa checkout + venv, see tools/make_expected.py)
python3 mutated/tools/gen_cases.py && python3 mutated/tools/make_expected.py
```

The oracle is used as a black box. `oracle/pyfa_oracle.py`, `oracle/pyfa_eft_export.py`, `oracle/pyfa_formats.py`
(taken from `formats-suite`) and `oracle/pyfa_mutated_import.py` are GPL-3.0-or-later test tools that import an
unmodified Pyfa checkout and run as separate processes; see `oracle/LICENSE-GPL-NOTE`. No Pyfa code is copied into
the bench. The generator, the scorers and the case and expected files contain no Pyfa code. The generator reads only
the EXCT dataset and the bench's own cases.

## Results (reference implementation)

| engine | stats | EFT export | EFT import | 1.8.0 regression |
|---|---|---|---|---|
| Variant I `variant-i` @ 349c6fd | 93/93 cases, 6,184/6,184 values | 93/93 | 99/99 | 326/326, byte-identical |
| Variant I before the port (9a4844a) | 81/86 at the first 86-case draft | 73/93 | 66/101 | — |
