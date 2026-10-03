# CONTRACT-CAP 0.1 (draft) — capacitor simulation

Status: **draft for review**, informational suite on branch `cap-suite` (not part of the main bench score).
Extends the main contract (CONTRACT.md, revision 1.4.x): same FitRequest, same dataset, same `capacitor` output
block. The reference is Pyfa's capacitor simulator run as a black box (oracle/pyfa_cap_oracle.py); this document
describes the behaviour engines must reproduce, in our own words.

## 1. Inputs

The ordinary FitRequest. Fields that matter here: module `state`, charges, `projected` (neutralizers, nosferatu,
neutralizer drones, void bombs, remote capacitor transmitters, projected fits), `options.factor_reload` and:

```jsonc
"options": {
  "factor_reload": false,          // reload in averages AND in the simulation (main contract)
  "cap_sim": {
    "stagger": true,               // stagger identical non-turret modules (Pyfa's behaviour); see §6 (default)
    "reload": false,               // reload in the simulation only (averages unchanged)
    "max_time_s": null             // simulated time limit; null = 6 h (21 600 s)
  }
}
```

A module state the module cannot take is kept as requested (main-contract ruling). The suite only overheats modules
that have an overload effect, because the oracle (Pyfa) falls back to online for the others.

## 2. Outputs (scored)

`capacitor.capacity`, `recharge_time_s`, `peak_recharge_gj_s`, `use_gj_s`, `injected_gj_s`, `delta_gj_s` (definitions:
main contract "Semantics"), `stable`, and `stable_percent` when stable or `depletes_in_s` when not.
Report-only: `eve_stable_percent`, `sim_iterations`.

## 3. Simulation input: the drain list

One entry `(duration_ms, need_gj, clip, no_stagger, reload_ms, injector)` per source, the fit's own modules first
(fit order), then incoming effects (request order).

**Own modules** — every module with state ≥ active, modified `capacitorNeed` ≠ 0 and cycle > 0:
- `duration_ms` = ⌊cycle + reactivation delay⌋, where cycle is the module's modified cycle attribute (the largest of
  `speed`, `duration`, `durationHighisGood` and the burst-projector durations) computed in IEEE-754 doubles in the
  attribute-evaluation order of the main contract. The floor applies to the double as computed: an overheated Medium
  Armor Repairer II evaluates to 7649.999… ms and simulates as **7649 ms**, not 7650 (see §8).
- `need_gj` = modified `capacitorNeed` (negative = gain: a capacitor booster's charge bonus, the fit's own nosferatu
  `-powerTransferAmount`).
- `clip` = shots per clip of the loaded charge (ammunition per clip, or crystal shots; 0 for scripts / no charge);
  `reload_ms` = the module's reload time; `no_stagger` = the module is a turret; `injector` = capacitor booster group.

**Incoming** — one entry per source item (each copy of `amount`, each drone of a stack): neutralizers, enemy
nosferatu and neutralizer drones drain (`need` > 0), remote capacitor transmitters fill (`need` < 0):
- `need` = modified amount × target resistance × range factor × min(1, signature radius / neutralizer signature
  resolution) when the source has one. Transmitters beyond their range and neutralizer drones beyond their neutralizer
  optimal range contribute nothing.
- `duration_ms` = ⌊duration⌋ (void bombs: launcher cycle + reactivation delay); `clip` 0; `no_stagger` false
  (identical incoming sources are grouped and staggered like local modules).

No drain at all → `stable` true, `stable_percent` 100, no simulation.

## 4. Preparation

1. Unless reload is simulated (`factor_reload` or `cap_sim.reload`), `clip` and `reload_ms` are cleared for every
   entry except capacitor boosters (boosters always reload).
2. Identical entries are grouped (all six fields equal); `n` = group size.
3. Per group:
   - capacitor boosters: `n` independent events at t = 0, never staggered;
   - staggering on and not a turret, no clip: **one** event with duration ⌊duration / n⌋ (integer division) and the
     unchanged `need`;
   - staggering on and not a turret, with clip: `n` events, the i-th (i = 0…n−1) first firing at
     i × (duration × clip + reload) / (n × clip);
   - otherwise (turret, or staggering off): one event with `need × n`.
4. Period = least common multiple of the event durations; when any event has a clip, there is no period (the run
   only ends by failure, the time limit or an empty queue).

## 5. Event loop

Start full (cap = capacity). Events are processed in order of the tuple (time, duration, need, shot, clip, reload,
injector) — earliest first, ties broken by the following fields in that order. For each event:

1. Time ≥ limit (`max_time_s`, default 6 h) → stop, stable.
2. Recharge from the previous event time: cap = C·(1 + (√(cap/C) − 1)·e^(−Δt/τ))², τ = recharge_time_ms / 5.
3. When time advanced: track the lowest cap seen *before* activations; when the time equals the next period
   boundary, compare: if cap ≥ the cap recorded at the previous boundary (rounded to 1 decimal) and the same
   postponed boosters are waiting, stop (stable); otherwise record and move the boundary one period on.
4. A booster whose injection would overfill the capacitor is postponed (kept waiting) instead of firing.
   Any other event: if it needs more than the current cap and the capacitor is not full, waiting boosters fire first,
   choosing the one that covers the shortfall with the least excess (or, failing that, the largest), until the need
   is covered or the capacitor is full; each booster fired this way is rescheduled from now.
5. Apply the event: cap −= need, capped at C. If cap < 0 → stop, **unstable** at this event's time. Otherwise track the
   lowest cap after activations.
6. Top up: while boosters wait and the capacitor is not full, fire the largest waiting booster that does not overfill.
7. Reschedule the event at time + duration; after the last shot of a clip add the reload time.

## 6. Results

- Unstable: `depletes_in_s` = time of the failing event / 1000 (an exact millisecond count).
- Stable: `stable_percent` = min(100, 100 × (lowest after + lowest before) / (2 × C)).
- `sim_iterations` = events processed. `eve_stable_percent` = 100 × ¼(1 + √(1 − 2·τ·Σ(need/duration)/C))² over the
  final event set (0 if the root is imaginary) — report-only.
- **Default of `cap_sim.stagger`:** this draft proposes **true** when omitted (Pyfa's behaviour, and what every engine
  does today). The main contract's example shows `false`; needs a ruling (§9).

## 7. Tolerances and scoring

- Numbers: |got − want| ≤ max(1e-3, 1e-4 × |want|) (main bench). `depletes_in_s`: ≤ 0.0005 s (the same millisecond).
  `stable`: equal.
- A case passes when every scored metric passes. Suite score = cases passed / cases; reported per category and per
  metric. Informational until adopted; proposed weight if adopted: its own problem score, gated on the main bench.

## 8. The "34 all-overheated" differences (H vs A)

With every module of a bench fit overheated, H and A differed on 34 fits in capacitor-simulation figures only.
Checked against Pyfa (oracle/pyfa_cap_oracle.py): **H matches Pyfa on 34/34, A on 1/34.** The cause is §3: overheat
bonuses make cycle times like 7649.999… ms in double arithmetic; Pyfa (and H) floor that to 7649, A computes 7650.
The suite keeps such cases (category `overheat`); they are now scored.

## 9. Open questions

1. `cap_sim.stagger` default (proposed true, §6).
2. `options.nos_no_target_cap` is not covered (Pyfa has no such switch).
3. Starting capacitor below 100 % is not in the request; the graphs suite covers capacitor over time.
4. `max_time_s` < the first failure → stable, with stable % from the lowest levels inside the window (as Pyfa).
