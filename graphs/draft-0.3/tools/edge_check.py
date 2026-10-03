#!/usr/bin/env python3
"""Find interpolation-sensitive application_profile sample points (draft 0.3, GPL test tool like the oracle).

Pyfa's application profile samples the target's projected speed/sig (source webs/TPs/scram) on a grid of
getSampleStep(R) metres and interpolates linearly; its ammo-transition scan uses the same step (+10 m bisection).
Neither is contract behaviour (0.3 ruling), so a scored sample point must not depend on it. This tool re-evaluates
every application_profile request with Pyfa's step divided by 4 and by 10; a point is *sensitive* if either value
differs from the default-step value beyond the corpus tolerance.

usage: PYFA=.. PYTHONPATH=<wx stub> python edge_check.py CASE.json [...]  -> one JSON line per file
       {"file", "sensitive": [[y, x, default, fine4, fine10], ...]}"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "../../.."))
sys.path.insert(0, os.path.join(ROOT, "oracle"))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import pyfa_graph_oracle as G  # noqa: E402
from metrics import close  # noqa: E402
import graphs.data.fitApplicationProfile.getter as AG  # noqa: E402
import graphs.data.fitApplicationProfile.calc.launcher as AL  # noqa: E402
import graphs.data.fitApplicationProfile.calc.optimize_ammo as AO  # noqa: E402
import graphs.data.fitApplicationProfile.calc.projected as AP  # noqa: E402

ORIG = AP.getSampleStep


def patch(div):
    f = ORIG if div == 1 else (lambda d, minStep=100, targetPoints=300: max(10, ORIG(d, minStep, targetPoints) / div))
    for m in (AG, AL, AO, AP):
        m.getSampleStep = f


def run(req, div):
    patch(div)
    try:
        return G.run(req)["series"]
    finally:
        patch(1)


def main():
    for path in sys.argv[1:]:
        req = json.load(open(path))
        if req.get("graph") != "application_profile":
            continue
        base, f4, f10 = run(req, 1), run(req, 4), run(req, 10)
        bad = []
        for y in req["y"]:
            for i, x in enumerate(req["x"]["values"]):
                a, b, c = base[y][i], f4[y][i], f10[y][i]
                if not (close(b, a) and close(c, a)):
                    bad.append([y, x, a, b, c])
        print(json.dumps({"file": os.path.basename(path), "sensitive": bad}))
        sys.stdout.flush()


if __name__ == "__main__":
    main()
