#!/usr/bin/env python3
"""Generate the docs/22 suites (eve-fit-docs docs/22-embedded-sde-and-prices.md, DECIDED 2026-10-03):
  d22/cases/price_rule/*.json   pricing rule `jita_sell_band_weighted` v1 on synthetic order books (updater, eve4)
  d22/cases/sde/*.json          `version` / `provenance` / `--sde` / RPC `sde_override` (engine, F)
  d22/cases/price_inject/*.json price precedence request > --prices / prices_load > embedded, `provenance.price_*`,
                                snapshot / map validation errors (engine, F)
  d22/data/packs/*.edp          synthetic edp v1 packs, each broken in exactly one way (SDE_LOAD_FAILED + reason)
  d22/data/prices/*             eve-price-snapshot v1 files (good, gz, other SDE build, broken) and plain maps
and d22/MANIFEST.json. Deterministic. usage: python3 d22/tools/gen_d22.py"""
import copy, gzip, hashlib, io, json, math, struct, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / "d22"
sys.path.insert(0, str(ROOT / "batch")); sys.path.insert(0, str(D))
import rule as R, prices as P  # noqa: E402

man = {}


def write(suite, cid, case):
    p = D / "cases" / suite / f"{cid}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(case, sort_keys=True, indent=1) + "\n")
    man[f"{suite}/{cid}"] = {"suite": suite, "check": case.get("check", "rule"), "note": case["note"],
                             **({"needs": case["needs"]} if case.get("needs") else {})}


for d in ("cases", "data/packs", "data/prices"):
    (D / d).mkdir(parents=True, exist_ok=True)
for p in (D / "cases").glob("*/*.json"):
    p.unlink()

# ============================================================ price_rule (pure function, synthetic order books)
J, AMARR = 60003760, 60008494
_oid = [1000]


def o(price, units, loc=J, buy=False):
    _oid[0] += 1
    return {"order_id": _oid[0], "type_id": 34, "price": price, "volume_remain": units, "location_id": loc,
            "is_buy_order": buy, "region_id": 10000002}


RULE = [
    ("single_order", [o(100.0, 50)], {}, "one qualifying order: price = p0 = 100", 100.0),
    ("weighted_mean", [o(100.0, 10), o(102.0, 30), o(104.0, 60)], {}, "unit-weighted mean (1000+3060+6240)/100 = 103", 103.0),
    ("small_orders_dropped", [o(90.0, 9), o(95.0, 5), o(100.0, 20), o(103.0, 20)], {},
     "orders with 9 and 5 units (< min_units 10) dropped before p0: p0 100, mean 101.5", 101.5),
    ("min_units_exact_kept", [o(90.0, 10), o(100.0, 100)], {}, "exactly min_units (10) is kept: p0 90, band [90, 94.5]", 90.0),
    ("all_small_missing", [o(100.0, 9), o(101.0, 1)], {}, "every order below min_units -> no price (missing)", None),
    ("outlier_low_small", [o(1.0, 1), o(1000.0, 20), o(1040.0, 20)], {},
     "1-ISK outlier with 1 unit dropped by min_units: p0 1000, mean 1020", 1020.0),
    ("outlier_low_large", [o(1.0, 10), o(1000.0, 500)], {},
     "an outlier with >= min_units sets p0 (rule as written; band [1, 1.05]) -> 1.0", 1.0),
    ("band_edge_inclusive", [o(1000.0, 10), o(1050.0, 30)], {},
     "order exactly at p0*1.05 = 1050.0 is in the band (inclusive): (10000+31500)/40 = 1037.5", 1037.5),
    ("band_edge_just_above", [o(1000.0, 10), o(math.nextafter(1050.0, 2000.0), 30)], {},
     "order one ulp above p0*1.05 is out: price 1000", 1000.0),
    ("band_edge_p0_100", [o(100.0, 10), o(105.0, 10)], {}, "p0 100: band_max = 100*(1+0.05) = 105.0; 105 included -> 102.5", 102.5),
    ("band_above_ignored", [o(100.0, 10), o(106.0, 1000)], {}, "1000 units above the band ignored for the mean, counted in units_considered", 100.0),
    ("other_station_ignored", [o(50.0, 1000, loc=AMARR), o(100.0, 10)], {}, "cheaper Amarr order ignored (location != 60003760)", 100.0),
    ("buy_orders_ignored", [o(200.0, 1000, buy=True), o(90.0, 1000, buy=True), o(100.0, 10)], {},
     "Jita buy orders (above and below) ignored; orders_total counts sell orders only", 100.0),
    ("no_sell_orders", [o(200.0, 1000, buy=True), o(50.0, 1000, loc=AMARR)], {}, "only buy orders / other stations -> missing", None),
    ("no_orders", [], {}, "empty book -> missing", None),
    ("ties_at_p0", [o(100.0, 10), o(100.0, 40), o(101.0, 50)], {}, "several orders at p0: (1000+4000+5050)/100 = 100.5", 100.5),
    ("rounding_cents", [o(100.0, 10), o(100.0, 10), o(101.0, 10)], {}, "mean 100.333.. rounded to 0.01 -> 100.33", 100.33),
    ("params_band0_min1", [o(100.0, 1), o(100.0, 5), o(100.01, 100)], {"min_units": 1, "band": 0.0},
     "min_units 1, band 0: only orders at exactly p0 (units 6, orders 2)", 100.0),
    ("params_band10", [o(1000.0, 10), o(1100.0, 10), o(1101.0, 10)], {"band": 0.10},
     "band 0.10: 1000*1.1 = 1100.0 included, 1101 out -> 1050", 1050.0),
    ("params_min_units_100", [o(90.0, 99), o(100.0, 100), o(104.0, 300)], {"min_units": 100},
     "min_units 100 drops the 99-unit order at 90: (10000+31200)/400 = 103", 103.0),
]
book = [o(round(5000 + 37 * ((i * 7919) % 101), 2), [3, 12, 40, 250, 9, 1000][i % 6], J if i % 7 else AMARR, i % 5 == 0)
        for i in range(60)]
RULE.append(("mixed_book_60", book, {}, "60 mixed orders (sells/buys, Jita/Amarr, small/large)", "ref"))
for cid, orders, params, note, want in RULE:
    exp = R.rule(orders, params)
    if want != "ref":
        assert (exp is None and want is None) or (exp and exp["price"] == want), (cid, exp, want)
    write("price_rule", cid, {"note": note, "params": params, "orders": orders, "expected": exp})

# ============================================================ synthetic edp v1 packs (docs/22 §2.2), one fault each
HDR = struct.Struct("<4sHHIHHq32sQ")      # 64 bytes
DIRE = struct.Struct("<4sIQQ")            # 24 bytes


def pack(magic=b"EDPK", major=1, build=3569502, rev=5, sections=None, dir_override=None):
    sections = sections or {b"META": json.dumps({"format_version": 1, "pipeline": "bench-synthetic"}).encode()}
    tags = sorted(sections)
    off = 64 + DIRE.size * len(tags)
    off += -off % 8
    dirs, blob = [], b""
    for t in tags:
        pos = off + len(blob)
        dirs.append([t, 0, pos, len(sections[t])])
        blob += sections[t] + b"\0" * (-len(sections[t]) % 8)
    if dir_override:
        dir_override(dirs)
    body = b"".join(DIRE.pack(*d) for d in dirs)
    body += b"\0" * (off - 64 - len(body)) + blob
    h = hashlib.sha256(body).digest()
    return HDR.pack(magic, major, 0, build, rev, len(tags), 1759403337, h, 0) + body


good = pack()
flip = bytearray(good); flip[-3] ^= 0xFF
PACKS = {   # name: (bytes, why, SDE_LOAD_FAILED reason)
    "bad_magic": (pack(magic=b"EDPX"), "magic EDPX instead of EDPK", "corrupt"),
    "format_major_2": (pack(major=2), "unknown format_major 2", "incompatible_version"),
    "hash_mismatch": (bytes(flip), "one body byte flipped; header content_sha256 stale", "hash_mismatch"),
    "truncated_header": (good[:40], "file shorter than the 64-byte header", "corrupt"),
    "section_out_of_range": (pack(dir_override=lambda ds: ds[0].__setitem__(3, 1 << 20)),
                             "META directory entry runs past EOF (hash consistent)", "corrupt"),
    "empty": (b"", "zero-byte file", "corrupt"),
}
for k, (b, _, _) in PACKS.items():
    (D / "data" / "packs" / f"{k}.edp").write_bytes(b)

# ============================================================ price files (docs/22 §4, docs/23 §5.3)
BASE = copy.deepcopy(json.loads((ROOT / "cases" / "exct_rifter.json").read_text()))
BASE["cargo"] = [{"type_id": 21898, "quantity": 1000}]
TYPES = sorted({t for _, _, t, _ in P.items(BASE)})


def isk(t, salt):
    return float(500 + (t * 7919 + salt * 104729) % 100000 * 10)


def snapshot(build=3569502, version=1, schema="eve-price-snapshot", tweak=None, rehash=True):
    types = {}
    for t in TYPES:
        p0 = isk(t, 3)
        types[str(t)] = {"price": round(p0 * 1.03, 2), "p0": p0, "band_max": p0 * 1.05, "units": 75, "orders": 3,
                         "units_considered": 400, "orders_considered": 8, "orders_total": 11}
    s = {"schema": schema, "schema_version": version, "snapshot_id": "jita44-20261003T053000Z", "market": "jita44",
         "market_time": "2026-10-03T05:30:00Z", "generated_at": "2026-10-03T05:31:07Z",
         "source": {"kind": "esi", "endpoint": "synthetic (eve-dogma-bench d22/data)", "region_id": 10000002,
                    "location_id": 60003760, "fetched_from": "2026-10-03T05:29:01Z", "fetched_to": "2026-10-03T05:30:00Z"},
         "rule": dict(R.DEFAULT, exact=True), "currency": "ISK", "sde_build": build, "type_count": len(types),
         "types": types, "missing": [], "updater": {"name": "eve-dogma-bench synthetic", "version": "1"}}
    if tweak:
        tweak(s)
    s["content_hash"] = P.canonical_hash(s)
    if not rehash:
        s["types"][str(TYPES[0])]["price"] += 1.0
    return s


PD = D / "data" / "prices"
FILES = {
    "snap-good.json": snapshot(),
    "snap-other-build.json": snapshot(build=3500000),
    "snap-v2.json": snapshot(version=2),
    "snap-schema-other.json": snapshot(schema="eve-price-table"),
    "snap-bad-hash.json": snapshot(rehash=False),
    "snap-bad-invariant.json": snapshot(tweak=lambda s: s["types"][str(TYPES[1])].__setitem__("price", s["types"][str(TYPES[1])]["p0"] - 1)),
    "snap-bad-units.json": snapshot(tweak=lambda s: s["types"][str(TYPES[2])].__setitem__("units", 0)),
    "map-good.json": {str(t): isk(t, 4) for t in TYPES if t != 31015},
    "map-negative.json": {str(TYPES[0]): -1.0, str(TYPES[1]): 10.0},
    "map-nonint-key.json": {"rifter": 1.0, str(TYPES[1]): 10.0},
    "map-string-value.json": {str(TYPES[0]): "12.5"},
}
for k, v in FILES.items():
    (PD / k).write_text(json.dumps(v, sort_keys=True) + "\n")
buf = io.BytesIO()
with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0, filename="") as g:
    g.write((json.dumps(FILES["snap-good.json"], sort_keys=True) + "\n").encode())
(PD / "snap-good.json.gz").write_bytes(buf.getvalue())

# ============================================================ sde suite
FITS = ["exct_rifter", "aoe_web_paint_rifter", "drones_sentry_dominix", "booster_strongblue", "dmgpattern_rah_hyperion"]
write("sde", "version_cli_fields", {"check": "version_fields", "transport": "cli",
      "note": "`version`: engine, sde_build 3569502, sde_revision, sde_release, sde_hash sha256:<64hex>, sde_source embedded, "
              "pack_format 1.0, snapshot_schema_version 1, target native"})
write("sde", "version_rpc_fields", {"check": "version_fields", "transport": "rpc", "note": "RPC `version`: same checks"})
write("sde", "version_rpc_equals_cli", {"check": "version_rpc_equals_cli", "note": "RPC version == CLI version"})
write("sde", "version_matches_meta", {"check": "version_matches_meta",
      "note": "version.sde_build / sde_release == meta.sde_build / sde_release_date (meta keeps its fields)"})
for t in ("cli", "rpc"):
    write("sde", f"provenance_calc_{t}", {"check": "provenance_calc", "transport": t, "fits": FITS,
          "note": f"{t} calc: provenance {{sde_build, sde_hash, price_source, snapshot_time}}; sde_build / sde_hash = version's; "
                  "price_source snapshot or none without price inputs"})
for k, (_, why, rsn) in PACKS.items():
    write("sde", f"sde_invalid_cli_{k}", {"check": "sde_invalid_cli", "pack": f"d22/data/packs/{k}.edp", "reason": rsn,
          "note": f"--sde with a broken pack ({why}) -> SDE_LOAD_FAILED reason {rsn}, no fallback to embedded"})
write("sde", "sde_invalid_cli_missing_file", {"check": "sde_invalid_cli", "pack": "d22/data/packs/does-not-exist.edp", "reason": "not_found",
      "note": "--sde with a path that does not exist -> SDE_LOAD_FAILED reason not_found, no fallback"})
for k in ("bad_magic", "hash_mismatch", "format_major_2"):
    write("sde", f"sde_invalid_rpc_{k}", {"check": "sde_invalid_rpc", "pack": f"d22/data/packs/{k}.edp", "fit": FITS[0], "reason": PACKS[k][2],
          "note": f"RPC sde_override {{path}} with {k} -> SDE_LOAD_FAILED reason {PACKS[k][2]}; the session stays on the embedded pack"})
write("sde", "sde_invalid_rpc_missing_file", {"check": "sde_invalid_rpc", "pack": "d22/data/packs/does-not-exist.edp", "fit": FITS[0],
      "reason": "not_found", "note": "RPC sde_override {path} that does not exist -> SDE_LOAD_FAILED reason not_found"})
write("sde", "sde_invalid_rpc_b64", {"check": "sde_invalid_rpc", "pack": "d22/data/packs/hash_mismatch.edp", "b64": True, "fit": FITS[0],
      "reason": "hash_mismatch", "note": "RPC sde_override {pack_b64} with a hash mismatch -> SDE_LOAD_FAILED reason hash_mismatch"})
NEEDS = ["SDE_PACK"]
write("sde", "sde_valid_cli_version", {"check": "sde_valid_cli_version", "needs": NEEDS,
      "note": "--sde PACK version: sde_source override, sde_override_path, sde_hash = sha256:<header content_sha256>, sde_build/revision from the header"})
write("sde", "sde_valid_cli_identical", {"check": "sde_valid_cli_identical", "needs": NEEDS, "fits": FITS,
      "note": "--sde PACK calc == embedded calc (minus provenance) on 5 fits; provenance sde_source override"})
write("sde", "sde_valid_rpc_switch_reset", {"check": "sde_valid_rpc", "needs": NEEDS, "fits": FITS[:2],
      "note": "RPC sde_override {path} -> version override; calc identical; {reset:true} -> embedded"})
write("sde", "sde_valid_rpc_b64", {"check": "sde_valid_rpc", "needs": NEEDS, "fits": FITS[:1], "b64": True,
      "note": "RPC sde_override {pack_b64}"})
write("sde", "embedded_hash_matches_release_pack", {"check": "embedded_hash", "needs": NEEDS,
      "note": "embedded version.sde_hash == the release pack's header hash (SDE_PACK = the pack the release embeds)"})

# ============================================================ price_inject suite
FULL = {str(t): isk(t, 5) for t in TYPES}
PART = {str(t): isk(t, 6) for t in TYPES[:6]}
SNAP, MAPF = "d22/data/prices/snap-good.json", "d22/data/prices/map-good.json"
fit = lambda **kw: dict(copy.deepcopy(BASE), **kw)  # noqa: E731
OPT = {"options": {"price": True}}
INJ = [
    ("embedded_only", fit(**OPT), [], "snapshot", "options.price, no inputs: embedded snapshot (structural); provenance.snapshot_time = its time"),
    ("file_snapshot", fit(), ["--prices", SNAP], "file", "--prices snapshot: lines injected, provenance.snapshot_time = the file's market_time"),
    ("file_snapshot_gz", fit(), ["--prices", SNAP + ".gz"], "file", "--prices .json.gz (gzip, mtime 0)"),
    ("file_map", fit(), ["--prices", MAPF], "file", "--prices plain map (one rig unpriced -> missing)"),
    ("request_full", fit(prices={"isk": FULL, "use_snapshot": False}), [], "request", "full request table, use_snapshot false: snapshot_time null"),
    ("request_full_mode_replace", fit(prices={"isk": FULL, "mode": "replace"}), [], "request", "mode replace = use_snapshot false (alias)"),
    ("request_full_over_file", fit(prices={"isk": FULL, "use_snapshot": False}), ["--prices", SNAP], "request", "use_snapshot false ignores --prices"),
    ("request_partial_embedded", fit(prices={"isk": PART}), [], "request", "partial table over the embedded snapshot: price_source request (base table only)"),
    ("request_partial_file", fit(prices={"isk": PART}), ["--prices", SNAP], "request", "partial table over --prices: request wins per type"),
    ("request_partial_mode_override", fit(prices={"isk": PART, "mode": "override"}), ["--prices", SNAP], "request", "mode override = use_snapshot true (alias)"),
    ("request_partial_no_snapshot", fit(prices={"isk": PART, "use_snapshot": False}), ["--prices", SNAP], "request", "partial + use_snapshot false: the rest missing"),
    ("overrides_request_file", fit(prices={"isk": PART}, price_overrides=[{"group_id": 55, "multiplier": 0.5}, {"type_id": 587, "price": 1}]),
     ["--prices", SNAP], "request", "price_overrides > request table > file"),
    ("overrides_only_file", fit(price_overrides=[{"category_id": 7, "multiplier": 2}]), ["--prices", SNAP], "file",
     "overrides + --prices: price_source file (eve's ruling; overrides are not a price table)"),
]
for cid, f, gargs, src, note in INJ:
    write("price_inject", cid, {"check": "inject_calc", "fit": f, "args": gargs, "price_source": src, "note": note})
write("price_inject", "rpc_prices_load_path", {"check": "inject_rpc", "calls": [["prices_load", {"path": SNAP}], ["calc", fit()]],
      "session_file": SNAP, "price_source": "file", "note": "RPC prices_load {path} then calc = --prices"})
write("price_inject", "rpc_prices_load_isk", {"check": "inject_rpc", "calls": [["prices_load", {"isk": FILES["map-good.json"]}], ["calc", fit()]],
      "session_file": MAPF, "price_source": "file", "note": "RPC prices_load {isk} (a map) then calc"})
write("price_inject", "rpc_prices_load_snapshot", {"check": "inject_rpc", "calls": [["prices_load", {"snapshot": FILES["snap-good.json"]}], ["calc", fit()]],
      "session_file": SNAP, "price_source": "file", "note": "RPC prices_load {snapshot} (inline object)"})
write("price_inject", "rpc_request_over_session", {"check": "inject_rpc", "calls": [["prices_load", {"path": SNAP}], ["calc", fit(prices={"isk": PART})]],
      "session_file": SNAP, "price_source": "request", "note": "request table beats the session snapshot"})
write("price_inject", "rpc_session_isolated", {"check": "inject_rpc_isolated", "fit": fit(**OPT),
      "note": "a prices_load in one serve-stdio process does not leak into a new one (price_source snapshot there)"})
for cid, pr, note in [("bad_prices_negative", {"isk": {str(TYPES[0]): -5.0}}, "negative value"),
                      ("bad_prices_string", {"isk": {str(TYPES[0]): "5"}}, "non-numeric value"),
                      ("bad_prices_key", {"isk": {"rifter": 5.0}}, "non-integer key"),
                      ("bad_prices_mode", {"isk": {str(TYPES[0]): 5.0}, "mode": "merge"}, "unknown mode")]:
    write("price_inject", cid, {"check": "inject_error", "fit": fit(prices=pr), "args": [], "code": "BAD_PRICES",
          "note": f"request prices: {note} -> BAD_PRICES"})
for f, code, note in [("snap-v2.json", "PRICE_SNAPSHOT_VERSION", "schema_version 2"),
                      ("snap-schema-other.json", "PRICE_SNAPSHOT_VERSION", "unknown schema"),
                      ("snap-bad-hash.json", "PRICE_SNAPSHOT_INVALID", "content_hash mismatch"),
                      ("snap-bad-invariant.json", "PRICE_SNAPSHOT_INVALID", "price < p0"),
                      ("snap-bad-units.json", "PRICE_SNAPSHOT_INVALID", "units 0"),
                      ("map-negative.json", "BAD_PRICES", "map with a negative value"),
                      ("map-nonint-key.json", "BAD_PRICES", "map with a non-integer key"),
                      ("map-string-value.json", "BAD_PRICES", "map with a string value")]:
    write("price_inject", "file_" + f.split(".")[0].replace("-", "_"), {"check": "inject_error", "fit": fit(**OPT),
          "args": ["--prices", f"d22/data/prices/{f}"], "code": code, "note": f"--prices {note} -> {code}"})
write("price_inject", "rpc_prices_load_bad_hash", {"check": "inject_rpc_error", "calls": [["prices_load", {"path": "d22/data/prices/snap-bad-hash.json"}]],
      "code": "PRICE_SNAPSHOT_INVALID", "note": "RPC prices_load with a hash mismatch -> PRICE_SNAPSHOT_INVALID"})
write("price_inject", "file_other_sde_build_warns", {"check": "inject_calc", "fit": fit(), "args": ["--prices", "d22/data/prices/snap-other-build.json"],
      "price_source": "file", "warning": "price snapshot for SDE build 3500000, engine data is 3569502",
      "note": "snapshot for another SDE build is accepted with a warning"})
write("price_inject", "sde_and_prices", {"check": "inject_calc", "fit": fit(), "args": ["--sde", "$SDE_PACK", "--prices", SNAP],
      "price_source": "file", "needs": NEEDS, "note": "--sde does not change prices (docs/22 §2.4)"})

(D / "MANIFEST.json").write_text(json.dumps(man, indent=1, sort_keys=True) + "\n")
from collections import Counter  # noqa: E402
print(dict(Counter(v["suite"] for v in man.values())))
