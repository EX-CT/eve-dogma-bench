#!/usr/bin/env python3
"""0.3: hand-specified module-state cases. Rule (contract draft 1.4.5, 2026-10-03 11:19 CST): an impossible active /
overheated state is corrected to online, as Pyfa does. Writes cases/<name>.json (request as specified) and
expected/<name>.json from the unchanged Pyfa graph oracle. `oracle_state_overrides` (now empty for every case) is kept
for cases whose contract state would differ from Pyfa's. Re-run after tools/make_draft_cases.py, which rewrites cases/.
Uses the same Pyfa env as tools/make_draft_expected.py (EXCT_REF / PYFA / PYFA_PY / WX_STUB).
"""
import copy, json, os, subprocess, sys, tempfile
from pathlib import Path

DRAFT = Path(__file__).resolve().parents[1]
ORACLE = DRAFT.parents[1] / "oracle" / "pyfa_graph_oracle.py"
spec = json.loads((DRAFT / "rulings" / "state_ruling_cases.json").read_text())
tmp = Path(tempfile.mkdtemp())
for name, s in spec.items():
    (DRAFT / "cases" / (name + ".json")).write_text(json.dumps(s["request"], indent=1, sort_keys=True) + "\n")
    r = copy.deepcopy(s["request"])
    for o in s["oracle_state_overrides"]:
        m = r["fit"]["modules"][o["module_index"]]
        assert m["type_id"] == o["type_id"], (name, o)
        m["state"] = o["state"]
    (tmp / (name + ".json")).write_text(json.dumps(r))
REF = os.environ.get("EXCT_REF", "/workspace/exct-eve/ref")
PYFA = os.environ.get("PYFA", f"{REF}/pyfa")
PY = os.environ.get("PYFA_PY", f"{REF}/pyfa-venv/bin/python")
env = dict(os.environ, PYTHONPATH=os.environ.get("WX_STUB", f"{REF}/stubs"), PYFA=PYFA)
out = subprocess.run([PY, str(ORACLE)] + sorted(str(p) for p in tmp.glob("*.json")), capture_output=True, text=True,
                     cwd=PYFA, env=env)
n = 0
for line in out.stdout.splitlines():
    r = json.loads(line)
    name = Path(r.pop("file")).stem
    r.update(case=name, oracle="pyfa-graphs+state-override" if spec[name]["oracle_state_overrides"] else "pyfa-graphs")
    (DRAFT / "expected" / (name + ".json")).write_text(json.dumps(r, indent=1, sort_keys=True) + "\n")
    n += 1
print(n, "ruling cases written")
if n != len(spec):
    sys.stderr.write(out.stderr[-4000:]); sys.exit(1)
