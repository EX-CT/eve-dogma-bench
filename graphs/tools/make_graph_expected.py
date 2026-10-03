#!/usr/bin/env python3
"""Generate graphs/expected/<case>.json by running oracle/pyfa_graph_oracle.py (GPL test tool) on graphs/cases/."""
import json, os, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REF = os.environ.get("EXCT_REF", "/workspace/exct-eve/ref")
PYFA = os.environ.get("PYFA", f"{REF}/pyfa")
PY = os.environ.get("PYFA_PY", f"{REF}/pyfa-venv/bin/python")
STUB = os.environ.get("WX_STUB", f"{REF}/stubs")


def main():
    # err_* cases are contract-defined error cases; their expected files are written by make_graph_cases.py
    files = sorted(str(p) for p in (ROOT / "graphs/cases").glob("*.json") if not p.stem.startswith("err_"))
    if len(sys.argv) > 1:
        files = [f for f in files if Path(f).stem in sys.argv[1:]]
    env = dict(os.environ, PYTHONPATH=STUB, PYFA=PYFA)
    out = subprocess.run([PY, str(ROOT / "oracle/pyfa_graph_oracle.py"), *files], capture_output=True, text=True, cwd=PYFA, env=env)
    n = pts = 0
    for line in out.stdout.splitlines():
        r = json.loads(line)
        name = r.pop("file")[:-5]
        if "error" in r:
            print(f"{name}: oracle error {r['error']}")
            continue
        r = {"case": name, "oracle": "pyfa-graphs", **r}
        (ROOT / "graphs/expected" / (name + ".json")).write_text(json.dumps(r, indent=1, sort_keys=True) + "\n")
        n += 1
        pts += sum(max(1, len(v)) for v in r["series"].values())
    print(f"{n} expected files, {pts} sample values")
    if out.returncode:
        sys.stderr.write(out.stderr[-4000:])


if __name__ == "__main__":
    main()
