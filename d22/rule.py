"""Reference for the docs/22 §3.2 pricing rule `jita_sell_band_weighted` v1 and the §4.5 per-type entry. Pure function:
rule(orders, params) -> entry dict, or None (the type goes to `missing`); raises ValueError for an invalid rule.
Follows eve4's updater (eve-market-prices e9781a5, src/rule.ts), adopted by eve as the reference; the spec is written
out in d22/README.md ("Pricing rule spec").
orders: [{"price", "volume_remain", "location_id", "is_buy_order", ...}] (ESI market order shape)."""
import math
from decimal import Decimal, ROUND_HALF_EVEN

DEFAULT = {"name": "jita_sell_band_weighted", "version": 1, "order_side": "sell", "location_id": 60003760,
           "min_units": 10, "band": 0.05, "weighting": "units"}
FIXED = {"name": "jita_sell_band_weighted", "version": 1, "order_side": "sell", "weighting": "units"}


def sig12(v):
    """the value at 12 significant digits (strips binary noise: 3*1.05 = 3.1500000000000004 -> 3.15)"""
    return float(f"{v:.12g}")


def round_isk(v):
    """0.01 ISK, half to even, on the 12-significant-digit decimal value: 100.335 -> 100.34, 100.345 -> 100.34"""
    return float(Decimal(f"{v:.12g}").quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN))


def validate(params):
    p = dict(DEFAULT, **(params or {}))
    for k, w in FIXED.items():
        if p[k] != w or type(p[k]) is not type(w):
            raise ValueError(f"rule {k} {p[k]!r} != {w!r}")
    mu, band = p["min_units"], p["band"]
    if isinstance(mu, bool) or not isinstance(mu, (int, float)) or mu != int(mu) or mu < 1:
        raise ValueError(f"min_units must be an integer >= 1 (got {mu!r})")
    if isinstance(band, bool) or not isinstance(band, (int, float)) or not math.isfinite(band) or not 0 <= band <= 10:
        raise ValueError(f"band must be a number in [0, 10] (got {band!r})")
    return p


def rule(orders, params=None):
    p = validate(params)
    sells = [o for o in orders if not o.get("is_buy_order") and o.get("location_id") == p["location_id"]]
    kept = sorted((o for o in sells if o["volume_remain"] >= p["min_units"]
                   and isinstance(o["price"], (int, float)) and math.isfinite(o["price"]) and o["price"] > 0),
                  key=lambda o: (o["price"], o["volume_remain"]))       # fixed summation order
    if not kept:
        return None
    p0 = kept[0]["price"]
    band_max = sig12(p0 * (1 + p["band"]))
    units = isk = n = 0
    for o in kept:
        if o["price"] <= band_max:                 # inclusive edge; the order price is compared as given
            units += o["volume_remain"]
            isk += o["price"] * o["volume_remain"]
            n += 1
    price = min(max(round_isk(isk / units), p0), band_max)
    return {"price": price, "p0": p0, "band_max": band_max, "units": units, "orders": n,
            "units_considered": sum(o["volume_remain"] for o in kept), "orders_considered": len(kept),
            "orders_total": len(sells)}
