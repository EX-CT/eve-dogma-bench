#!/usr/bin/env python3
"""ext/rpc/expected/<case>.json from the Pyfa lookup oracle (oracle/pyfa_lookup.py).
usage: python3 ext/tools/make_rpc_expected.py [ext/rpc/cases/*.json]"""
import json, os, pathlib, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
REF = os.environ.get("EXCT_REF", "/workspace/exct-eve/ref")
PYFA = os.environ.get("PYFA", f"{REF}/pyfa")
PY = os.environ.get("PYFA_PY", f"{REF}/pyfa-venv/bin/python")
STUB = os.environ.get("WX_STUB", f"{REF}/stubs")
SUITE = ROOT / "ext" / "rpc"
sys.path.insert(0, str(ROOT / "ext" / "tools"))
from score_rpc import parse_backup  # noqa: E402


def main(files):
    files = [str(pathlib.Path(f).resolve()) for f in files] or sorted(str(p) for p in (SUITE / "cases").glob("*.json"))
    man = json.loads((SUITE / "MANIFEST.json").read_text())
    out = subprocess.run([PY, str(ROOT / "oracle/pyfa_lookup.py"), *files], capture_output=True, text=True, cwd=PYFA,
                         env=dict(os.environ, PYTHONPATH=STUB, PYFA=PYFA))
    if out.returncode:
        print(out.stderr[-3000:], file=sys.stderr)
    n = 0
    for line in out.stdout.splitlines():
        if not line.startswith("{"):
            continue
        r = json.loads(line)
        name = r["file"][:-5]
        if "error" in r:
            print(f"{name}: oracle error {r['error']}")
            continue
        exp = {"case": name, "oracle": "pyfa-service", **man[name], "result": r["result"]}
        if man[name]["feature"] == "fits.backup":
            exp["parsed"] = parse_backup(r["result"]["xml"])
        (SUITE / "expected" / f"{name}.json").write_text(json.dumps(exp, indent=1, sort_keys=True) + "\n")
        n += 1
    print(f"wrote {n} expected files")


if __name__ == "__main__":
    main(sys.argv[1:])
