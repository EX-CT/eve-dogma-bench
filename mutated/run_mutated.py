#!/usr/bin/env python3
"""Score an engine on the mutated suite: the same scorer as run.py (values/metrics/tolerances), cases from
mutated/cases, expected values from mutated/expected, results in mutated/results/<name>/.
usage: python3 mutated/run_mutated.py --name I --cmd "<engine calc>" [--batch-cmd "<engine batch>"]"""
import pathlib, sys

SUITE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(SUITE.parent))
import run  # noqa: E402

run.ROOT = SUITE
if __name__ == "__main__":
    if "--latency-case" not in sys.argv:
        sys.argv += ["--latency-case", "mwd_decayed_random_exct_damnation"]
    run.main()
