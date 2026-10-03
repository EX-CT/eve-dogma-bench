#!/usr/bin/env python3
"""DRAFT 0.3: run the Pyfa graph oracle (unchanged oracle/pyfa_graph_oracle.py) on graphs/draft-0.3/cases
-> graphs/draft-0.3/expected. err_* expected files are written by make_draft_cases.py."""
import json, os, subprocess, sys
from pathlib import Path

DRAFT = Path(__file__).resolve().parents[1]
ROOT = DRAFT.parents[1]
REF = os.environ.get("EXCT_REF", "/workspace/exct-eve/ref")
PYFA = os.environ.get("PYFA", f"{REF}/pyfa")
PY = os.environ.get("PYFA_PY", f"{REF}/pyfa-venv/bin/python")
STUB = os.environ.get("WX_STUB", f"{REF}/stubs")

files = sorted(str(p) for p in (DRAFT / "cases").glob("*.json") if not p.stem.startswith("err_"))
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
    (DRAFT / "expected" / (name + ".json")).write_text(json.dumps(r, indent=1, sort_keys=True) + "\n")
    n += 1
    pts += sum(max(1, len(v)) for k, v in r["series"].items() if not k.endswith("_charge_type_id"))
print(f"{n} expected files, {pts} scored sample values")
if out.returncode:
    sys.stderr.write(out.stderr[-4000:])
