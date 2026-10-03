"""Reference for the docs/22 §3.2 pricing rule `jita_sell_band_weighted` v1 (implemented by the updater, eve4) and the
§4.5 per-type entry. Pure function: rule(orders, params) -> entry dict, or None (type goes to `missing`).
orders: [{"price", "volume_remain", "location_id", "is_buy_order", ...}] (ESI market order shape).
band_max = p0 * (1 + band) in IEEE double; band edges inclusive; price rounded to 0.01 ISK, round half to even
(decimal rounding of the double's shortest repr, Python round())."""

DEFAULT = {"name": "jita_sell_band_weighted", "version": 1, "order_side": "sell", "location_id": 60003760,
           "min_units": 10, "band": 0.05, "weighting": "units"}


def rule(orders, params=None):
    p = dict(DEFAULT, **(params or {}))
    sells = [o for o in orders if not o.get("is_buy_order") and o.get("location_id") == p["location_id"]]
    kept = [o for o in sells if o["volume_remain"] >= p["min_units"]]
    if not kept:
        return None
    p0 = min(o["price"] for o in kept)
    band_max = p0 * (1 + p["band"])
    band = [o for o in kept if p0 <= o["price"] <= band_max]
    units = sum(o["volume_remain"] for o in band)
    mean = sum(o["price"] * o["volume_remain"] for o in band) / units
    return {"price": round(mean, 2), "p0": p0, "band_max": band_max, "units": units, "orders": len(band),
            "units_considered": sum(o["volume_remain"] for o in kept), "orders_considered": len(kept),
            "orders_total": len(sells)}
