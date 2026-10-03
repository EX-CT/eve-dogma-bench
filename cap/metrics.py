"""Capacitor-suite metrics (CONTRACT-CAP 0.1): metric -> (JSON pointer in FitStats, tolerance kind)."""
REL_TOL, ABS_TOL = 1e-4, 1e-3        # same as the main bench
DEPLETE_ABS_S = 0.0005               # depletion time: the same simulated millisecond

SCORED = {
    "capacity": "/capacitor/capacity",
    "recharge_time_s": "/capacitor/recharge_time_s",
    "peak_recharge_gj_s": "/capacitor/peak_recharge_gj_s",
    "use_gj_s": "/capacitor/use_gj_s",
    "injected_gj_s": "/capacitor/injected_gj_s",
    "delta_gj_s": "/capacitor/delta_gj_s",
    "stable": "/capacitor/stable",
    "stable_percent": "/capacitor/stable_percent",   # only when Pyfa says stable
    "depletes_in_s": "/capacitor/depletes_in_s",     # only when Pyfa says unstable
}
REPORT_ONLY = {"eve_stable_percent": "/capacitor/eve_stable_percent", "sim_iterations": "/capacitor/sim_iterations"}


def ptr(doc, p):
    for k in p.strip("/").split("/"):
        if isinstance(doc, dict) and k in doc:
            doc = doc[k]
        else:
            return None
    return doc


def close(metric, got, want):
    if isinstance(want, bool) or metric == "stable":
        return isinstance(got, bool) and got == want
    if got is None or want is None or isinstance(got, bool):
        return got is None and want is None
    try:
        g, w = float(got), float(want)
    except (TypeError, ValueError):
        return False
    if metric == "depletes_in_s":
        return abs(g - w) <= DEPLETE_ABS_S
    return abs(g - w) <= max(ABS_TOL, REL_TOL * abs(w))


def expected_from_oracle(c):
    """pyfa_cap_oracle.py 'cap' record -> (scored values, report-only values)"""
    vals = {k: c[k] for k in ("capacity", "recharge_time_s", "peak_recharge_gj_s", "use_gj_s", "injected_gj_s", "delta_gj_s", "stable")}
    if c["stable"]:
        vals["stable_percent"] = c["stable_percent"]
    else:
        vals["depletes_in_s"] = c["depletes_in_s"]
    rep = {k: c[k] for k in ("eve_stable_percent", "sim_iterations") if c.get(k) is not None}
    return vals, rep
