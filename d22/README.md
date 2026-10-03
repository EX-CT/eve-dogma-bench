# d22: embedded SDE, price injection and the pricing rule (eve-fit-docs docs/22)

Three suites built from `docs/22-embedded-sde-and-prices.md` (DECIDED 2026-10-03) and docs/23 §5–§6. No engine
implements them yet. The engine / updater surface is **provisional** and lives only in `adapter.py`; once F (engine)
or eve4 (updater) publish a contract, only `adapter.py` changes.

| suite | target | cases | what |
|---|---|---|---|
| `sde` | engine (F) | 23 (5 pending without `SDE_PACK`) | `version` CLI/RPC fields, RPC == CLI, version vs `meta`, `provenance` on calc (CLI/RPC) = version's; `--sde` with 6 broken synthetic edp packs + a missing path, RPC `sde_override` {path / pack_b64} broken or missing → SDE_LOAD_FAILED + reason and the session stays embedded; with `SDE_PACK` = a real edp v1 pack: override version / hash / path, calc identical to embedded, RPC switch + reset, b64, embedded hash = release pack hash |
| `price_inject` | engine (F) | 33 (1 pending) | precedence request `prices` > `--prices` file / RPC `prices_load` > embedded snapshot; `use_snapshot` and the `mode` alias; `provenance` (`price_source` request / file / snapshot / none, `snapshot_time`); price blocks against the batch/prices.py resolver; BAD_PRICES (request and map files), PRICE_SNAPSHOT_VERSION, PRICE_SNAPSHOT_INVALID (hash, invariants); the other-SDE-build warning; session isolation; `--sde` + `--prices` |
| `price_rule` | updater (eve4) | 21 | `jita_sell_band_weighted` v1 on synthetic order books: min_units by units (incl. exactly 10), outlier low prices (small: dropped; large: sets p0), band edges exactly at p0×1.05 (inclusive) and one ulp above, band 0 / 0.10, other stations and buy orders ignored, no sell orders / empty book → missing, ties, cent rounding, a 60-order mixed book. Reference: `rule.py` |

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
  or `null`. `price` is compared to 1e-9 relative after the reference rounds to 0.01 (Python `round`).
