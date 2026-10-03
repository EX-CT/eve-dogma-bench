# Batch compute: PROVISIONAL bench shape (batch_version "0.1-provisional")

**Provisional.** EX-CT/eve-dogma has no batch contract yet; at main d990818 there is only the JSONL `batch` stream
(one FitRequest per line). This is the bench's working shape.
- When F publishes the contract, only `adapter.py` changes (request mapping, transport and response mapping).
- The cases and the semantics checks stay as they are, because the core assertion does not depend on the shape:
  **every batch result is identical to computing the same fit on its own with `calc`**.

## Transport (adapter.py)
- **rpc** (default): `ENGINE serve-stdio`, method `calc_batch`, `params` = BatchRequest, `result` = BatchResponse.
- **cli**: `ENGINE calc-batch` with the BatchRequest JSON on stdin, BatchResponse JSON on stdout.

## BatchRequest
Exactly one source of fits:
| key | meaning |
|---|---|
| `fits: [{label?, fit: FitRequest}]` | independent fits (**multi**) |
| `base: FitRequest` + `variants: [{label?, patch: [JSON Patch]}]` | each variant = base with its patch applied (**variants**) |
| `base` + `product: {axes: [[{label?, patch}]...]}` | Cartesian product. The first axis varies slowest. Patches are concatenated in axis order; the label is the axis labels joined with `×` (**product**) |
| `base` + `sweep: {path: "/json/pointer", values: [...]}` | one fit per value, `{"op":"add","path":path,"value":v}`; the label is `path=<json value>` (**sweep**) |

The patch format is RFC 6902 JSON Patch on the FitRequest, limited to `add`, `remove` and `replace`. Paths are
JSON Pointers, and `/modules/-` appends.

Options:
| key | meaning |
|---|---|
| `fields: ["a.b.c", ...]` | projection. `stats` becomes `{field: value}`, a missing path gives `null`, and numeric segments index lists. Without `fields`, `stats` is the full FitStats |
| `deltas: true` | needs `base` and `fields`. `delta[field] = round(value − base_value, 6)` computed on the emitted (6-decimal) values; `null` if either value is not numeric. The response carries `base.stats` |
| `filter: [{field, op, value, on?}]` | AND of all filters. `op` is one of `< <= > >= == !=`; `on: "delta"` tests the delta. Results with errors or non-numeric values (booleans count as numbers here) are dropped |
| `sort: [{field, order: asc\|desc, on?}]` | multi-key and stable (ties keep expansion order). `null`, non-numeric and errored results go last |
| `limit: n` | applied after filter and sort |

## BatchResponse
```jsonc
{"total": 32,                                   // number of expanded fits (before filter/limit)
 "base": {"stats": {...}},                      // only with deltas
 "results": [{"index": 7,                       // position in the expansion
              "label": "skills3×m2:active",
              "stats": {...},                   // == project(calc(fit_7), fields), byte-identical values
              "delta": {...}}                   // only with deltas
             , {"index": 4, "label": "bad_ship", "error": {"code": "UNKNOWN_TYPE"}}]}  // per-fit errors in place
```

## What is checked (semantics.compare)
- `total` must be equal, and the result `index` sequence must be exactly the expected one. This covers order,
  filter and limit.
- For each result:
  - `label` must be equal.
  - `stats` must be JSON-identical to the one-by-one `calc` output after projection. There is no tolerance.
  - `delta` must be within 1e-6, and its key set must be equal.
  - An `error` code must equal the one-by-one error code.
- `base.stats` must be identical to the one-by-one base fit.
