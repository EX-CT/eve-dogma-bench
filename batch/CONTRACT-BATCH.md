# Batch compute: the contract the bench checks

**Source of truth: eve-fit-docs `docs/23-batch-api-and-prices.md`** (DRAFT 8b1e6cf, 2026-10-03 14:29 CST).
- The cases are written in that shape: `batch_version` 1; `fits`, `base` + `variants`, `product.axes[].options` and
  `sweep`; `fields`, `deltas`, `filter`, `sort_by`, `top_n`.
- The bench's earlier provisional shape (batch_version "0.1-provisional": `sort`, `limit`, axes as plain lists) was
  replaced at 14:55 CST; docs/23 kept its semantics.
- Transport is in `adapter.py`: RPC method `batch` on `serve-stdio` (default), or CLI `batch --request -`.

What `semantics.py` checks (docs/23 §2–§4, §7):
- **Expansion and ids** (§2):
  - fits: `id` defaults to the index as a string, `label` defaults to `id`.
  - variants: `id` defaults to `v<k>` (1-based).
  - product: `id` = option ids joined with `|`; `label` = option labels joined with ` × `. The first axis varies
    slowest.
  - sweep: one option per value, with id and label `path=<json value>`.
- **Identity** (§3): every result's `stats` must be JSON-identical to `calc` of the same expanded FitRequest run on
  its own, after `fields` projection. There is no tolerance.
- **Deltas** (§4.2):
  - `delta = round6(value − ref)` from the emitted values.
  - `delta_pct = round6(delta / |ref| × 100)`, or `null` if ref is 0.
  - Non-numeric values (booleans included) give `null`.
  - Both are compared within 1e-6. `base.stats` must be identical to the base fit computed on its own.
- **filter / sort_by / top_n** (§4.3):
  - Filters are ANDed and can use `on: value | delta | delta_pct`.
  - In filter and sort, booleans compare as 0/1.
  - Sort is stable and multi-key; nulls and errors go last.
  - Order of operations: filter → sort → top_n. `total` and `matched` must be equal, and the `index` order must be
    exact.
- **Per-fit errors** (§8): an error stays in place with the same `code` as when the fit is computed on its own.

Not covered yet: the `in` and `not_null` filter ops, `delta_ref` (form 1), numeric sweeps `from`/`to`/`step` (the
expansion supports them), `swap_type`, `BATCH_TOO_LARGE`, and the price block and `price_overrides` (§5/§6: next
step, `price_*` cases).
