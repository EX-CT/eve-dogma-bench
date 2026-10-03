#!/usr/bin/env python3
"""Generate mutated/expected/<case>.json by running the Pyfa oracle (oracle/pyfa_oracle.py, GPL test tool, run as a
separate process: black box) on mutated/cases/<case>.json. Same metrics and format as tools/make_expected.py.
usage: python3 mutated/tools/make_expected.py [mutated/cases/*.json]
env: PYFA, PYFA_PY, WX_STUB as for tools/make_expected.py"""
import json, os, pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from metrics import from_pyfa, METRICS  # noqa: E402

REF = os.environ.get("EXCT_REF", "/workspace/exct-eve/ref")
PYFA = os.environ.get("PYFA", f"{REF}/pyfa")
PY = os.environ.get("PYFA_PY", f"{REF}/pyfa-venv/bin/python")
STUB = os.environ.get("WX_STUB", f"{REF}/stubs")
SUITE = ROOT / "mutated"


def main(files):
    files = [str(pathlib.Path(f).resolve()) for f in files] or sorted(str(p) for p in (SUITE / "cases").glob("*.json"))
    env = dict(os.environ, PYTHONPATH=STUB, ORACLE_REPEAT="0", PYFA=PYFA)
    out = subprocess.run([PY, str(ROOT / "oracle/pyfa_oracle.py"), *files], capture_output=True, text=True, cwd=PYFA, env=env)
    if out.returncode:
        print(out.stderr[-3000:], file=sys.stderr)
    (SUITE / "expected").mkdir(exist_ok=True)
    known = json.loads((ROOT / "expected/known_divergences.json").read_text())
    n, bad = 0, 0
    for line in out.stdout.splitlines():
        if not line.startswith("{"):
            continue
        r = json.loads(line)
        name = r["file"][:-5]
        if "error" in r:
            print(f"{name}: oracle error {r['error']}")
            bad += 1
            continue
        vals = from_pyfa(r["stats"])
        # metrics the main corpus excludes for the source fit (known SDE-vs-Pyfa divergences) stay excluded here
        src = max((s for s in known if name.endswith("_" + s)), key=len, default=None)
        skip = known.get(src, {})
        exp = {"case": name, "oracle": "pyfa-eos", "values": {k: v for k, v in sorted(vals.items()) if k in METRICS and k not in skip},
               "excluded": skip}
        (SUITE / "expected" / f"{name}.json").write_text(json.dumps(exp, indent=1, sort_keys=True, default=str) + "\n")
        n += 1
    print(f"wrote {n} expected files, {bad} oracle errors")


if __name__ == "__main__":
    main(sys.argv[1:])
