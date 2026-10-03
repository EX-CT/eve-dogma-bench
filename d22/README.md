# d22: embedded SDE, price injection and the pricing rule (eve-fit-docs docs/22)

Three suites built from `docs/22-embedded-sde-and-prices.md` (DECIDED 2026-10-03) and docs/23 §5–§6. No engine
implements them yet. The engine / updater surface is **provisional** and lives only in `adapter.py`; once F (engine)
or eve4 (updater) publish a contract, only `adapter.py` changes.

| suite | target | cases | what |
|---|---|---|---|
| `sde` | engine (F) | 23 (5 pending without `SDE_PACK`) | `version` CLI/RPC fields, RPC == CLI, version vs `meta`, `provenance` on calc (CLI/RPC) = version's; `--sde` with 6 broken synthetic edp packs + a missing path, RPC `sde_override` {path / pack_b64} broken or missing → SDE_LOAD_FAILED + reason and the session stays embedded; with `SDE_PACK` = a real edp v1 pack: override version / hash / path, calc identical to embedded, RPC switch + reset, b64, embedded hash = release pack hash |
| `price_inject` | engine (F) | 33 (1 pending) | precedence request `prices` > `--prices` file / RPC `prices_load` > embedded snapshot; `use_snapshot` and the `mode` alias; `provenance` (`price_source` request / file / snapshot / none, `snapshot_time`); price blocks against the batch/prices.py resolver; BAD_PRICES (request and map files), PRICE_SNAPSHOT_VERSION, PRICE_SNAPSHOT_INVALID (hash, invariants); the other-SDE-build warning; session isolation; `--sde` + `--prices` |
| `price_rule` | updater (eve4) | 42 | `jita_sell_band_weighted` v1 on synthetic order books: min_units by units (incl. exactly 10), outlier low prices (small: dropped; large: sets p0), band edges exactly at p0×1.05 (inclusive) and one ulp above, band 0 / 0.10, other stations and buy orders ignored, no sell orders / empty book → missing, ties, cent rounding, a 60-order mixed book; plus (eve4's behaviour, adopted) decimal half-even rounding (incl. > 10 integer digits: 55174443703.65 -> 55174443703.7), non-positive prices dropped, clamping, 12-digit band_max, 8 invalid rules. Reference: `rule.py` |

```
python3 d22/run_d22.py --suite sde --cmd ENGINE --out sde.json
python3 d22/run_d22.py --suite price_inject --cmd ENGINE --out price_inject.json
python3 d22/run_d22.py --suite price_rule --rule-cmd "$PRICE_RULE_CMD" --out price_rule.json
python3 d22/run_d22.py --suite all --self-test         # bench data check (rule expectations, packs, price files)
SDE_PACK=/path/sde-3569502-r5.edp python3 d22/run_d22.py ...   # enables the 6 pending cases
```

`python3 d22/tools/gen_d22.py` regenerates `cases/`, `data/packs/` (synthetic edp v1 packs, one fault each) and
`data/prices/` (eve-price-snapshot v1 files with a valid `content_hash`, broken variants, plain maps) deterministically.

Provisional choices to confirm (eve / F / eve4):
- `--sde FILE` and `--prices FILE` are global options before the subcommand; RPC `version`, `sde_override`,
  `prices_load` take the params in docs/22 §2.4 / docs/23 §5.3; RPC `calc` params = the FitRequest.
- Lines from a `--prices` file are labelled `injected` (docs/23 §5.2).

eve's rulings (2026-10-03; F updates docs/22 / docs/23, and where F's doc differs it wins and only the adapters change):
- `sde_hash` = the pack's `content_sha256` (docs/22 §2.2), as `sha256:<hex>`.
- Unified `provenance` {`sde_build`, `sde_hash`, `price_source`, `snapshot_time`} on every result and at the batch top
  level; a variant that uses a different price table carries its own.
- `price_source` = the source of the base price table only: `request` > `file` > `snapshot` > `none`. Overrides do
  not count (overrides + `--prices` = `file`); a partial request table over a file is `request`.
- `snapshot_time`: the file's `market_time` (null for a plain map), the embedded snapshot's time, null with
  `use_snapshot: false`.
- Every SDE load failure is `SDE_LOAD_FAILED` with `reason` (`error.reason`, or under `details` / `data`):
  `not_found` | `corrupt` (bad magic, truncated, section out of range, empty) | `hash_mismatch` | `incompatible_version`.
- Global flags go before the subcommand; RPC `calc` params = the FitRequest.
- price_rule transport: `PRICE_RULE_CMD` reads `{"rule": {...}, "orders": [ESI orders]}` and prints the §4.5 entry
  or `null`; an invalid rule must exit non-zero (scored as `RULE_REJECTED`; unparseable output with exit 0 is
  `NO_OUTPUT`, a failure). `price`, `p0` and `band_max` are compared exactly, the counts as integers.

## Pricing rule spec (`jita_sell_band_weighted` v1)

This is the spec for the updater (eve4, eve-market-prices) and for F wherever the engine meets these numbers. It
follows eve4's implementation (eve-market-prices e9781a5, `src/rule.ts`), which eve adopted as the reference;
`d22/rule.py` is the executable form and `d22/cases/price_rule/` the test vectors.

Input: one type's order book (ESI order objects: `price`, `volume_remain`, `location_id`, `is_buy_order`) and the
rule descriptor `{name, version, order_side, location_id, min_units, band, weighting}` (defaults: `jita_sell_band_weighted`,
1, `sell`, 60003760, 10, 0.05, `units`).

0. **Validate the rule.** `name` = `jita_sell_band_weighted`, `version` = 1, `order_side` = `sell`, `weighting` =
   `units`; `min_units` an integer ≥ 1; `band` a finite number in [0, 10]. Otherwise the rule is rejected: the
   updater exits non-zero and writes nothing.
1. **Orders.** Keep sell orders (`is_buy_order` false) at `location_id`. Their count is `orders_total`.
2. **Filter.** Drop orders with `volume_remain < min_units` (per order, by units) and orders whose price is not a
   finite number > 0. What is left is "considered" (`orders_considered`, `units_considered`). Nothing left →
   no price (the type goes to `missing`).
3. **p0** = the lowest considered price, as given.
4. **band_max** = p0 × (1 + band) computed in IEEE double, then taken at **12 significant digits**
   (`float(f"{x:.12g}")`, JS `Number(x.toPrecision(12))`): 1007.56 × 1.05 = 1057.9379999999999 → 1057.938. This
   value is both the output and the edge.
5. **Band** = the considered orders with price ≤ band_max (inclusive; order prices compared as given). `units` and
   `orders` count the band.
6. **Mean** = Σ(price × volume_remain) / Σ volume_remain over the band, summed in ascending (price, volume_remain)
   order so the result does not depend on the input order.
7. **Round** to 0.01 ISK, **half to even, on the 12-significant-digit decimal value** of the mean
   (`Decimal(f"{mean:.12g}").quantize(Decimal("0.01"), ROUND_HALF_EVEN)`): 100.335 → 100.34, 100.345 → 100.34,
   2.675 → 2.68, 4.085 → 4.08. (Python `round()` on the double gives 100.33 and 2.67.)
8. **Clamp** the rounded price into [p0, band_max]; this only matters for sub-cent prices (0.00405 → 0.004).

Output (docs/22 §4.5): `{price, p0, band_max, units, orders, units_considered, orders_considered, orders_total}`, or
`null` for no price. Non-finite prices cannot appear in JSON input, so (2) is tested with 0 and negative prices.
