# ⚠ DRAFT — graphs contract 0.3 (UNRELEASED)

**Round 2 is scored on 0.2, frozen at bench commit 0397d95** (`graphs/CONTRACT-GRAPHS.md`, `graphs/cases`,
`graphs/expected`, `graphs/run_graphs.py`). Nothing in this directory is read by the 0.2 scorer, and no version
number, tag or default path was changed. Pulling `graphs-round2` still scores exactly 0.2.

```
graphs/draft-0.3/CONTRACT-GRAPHS-0.3-draft.md   full contract text, changes vs 0.2 marked (0.3)
graphs/draft-0.3/CHANGELOG.md                   unreleased entry
graphs/draft-0.3/cases/, expected/              draft corpus = frozen 0.2 corpus + 13 new cases (NEW_CASES.txt)
graphs/draft-0.3/run_draft.py                   scorer: run_graphs.py rules, draft corpus, results/graphs-draft-0.3-<name>/
graphs/draft-0.3/tools/make_draft_cases.py      regenerates cases/ (imports the 0.2 generator read-only)
graphs/draft-0.3/tools/make_draft_expected.py   regenerates expected/ with the unchanged oracle (~50 s)
graphs/draft-0.3/tools/edge_check.py            application_profile interpolation/transition sensitivity check
```

```bash
python3 graphs/draft-0.3/run_draft.py --self-test
python3 graphs/draft-0.3/run_draft.py --name E --batch-cmd "<engine> graph-batch --dataset $D" --cwd <variant dir>
# note: --self-test writes results/graphs-self-test (same as the 0.2 self-test); re-run the 0.2 self-test after it.
```

## Counts

| graph | cases | scored values | new vs 0.2 |
|---|---|---|---|
| application_profile | 14 | 161 | +4 cases / +41 (XL navy tier ×3, Maelstrom arty web+TP sampled off the edges) |
| capacitor | 14 | 173 | – |
| damage | 70 | 1134 | +10 cases / +216 (state ruling: overheated Bastion ×1, sentries follow_target ×2, breacher distance ×2, bomb time ×2, fighters vs fast target ×3) |
| ecm_burst | 11 | 218 | – |
| ewar | 22 | 337 | – |
| lock_time | 7 | 82 | – |
| mobility | 10 | 259 | – |
| remote_reps | 11 | 151 | – |
| shield_regen | 5 | 66 | – |
| warp_time | 8 | 93 | – |
| errors | 20 | 20 | – |
| **total** | **192** | **2694** | +14 cases / +257 values (0.2: 178 / 2437) |

The expected values of all 178 0.2 cases were regenerated with the oracle and are identical to `graphs/expected`
(every scored value; only the informational, tie-dependent charge ids may differ).

## Interpolation-sensitive points (eve's ruling: not scored)

Pyfa's application profile interpolates projected webs/TPs on a `getSampleStep(R)` grid, and its ammo-transition
scan uses the same step. `tools/edge_check.py` re-evaluates every application_profile request with that step
divided by 4 and by 10. A point counts as sensitive if either value differs beyond tolerance.

Result for the draft corpus (2026-10-03): **0 sensitive points in all 14 application_profile cases.** No 0.2 sample
point had to be moved or dropped. The 0.2 app cases sample 0/2/5/10/20/30/… km, and none of them has a source
web/TP edge or a charge crossover inside a grid cell at those points.

The detector itself was checked on a Maelstrom 1400 mm arty + web probe sampled every 50 m at 9–12 km: 13 sensitive
points at the web edge (graphs/pending/probes-0.3.jsonl, `mael_arty_all`). The new
`app_maelstrom_arty_web_tp_off_edge` case uses the same fit plus a TP, sampled only at 0–8 km and 15–100 km.

`damage` evaluates projected effects exactly at each distance (no grid), so it needs no check.
