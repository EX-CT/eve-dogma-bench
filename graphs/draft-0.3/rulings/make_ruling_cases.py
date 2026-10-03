#!/usr/bin/env python3
"""DRAFT 0.3: hand-specified cases for eve's module-state ruling (a state the module can't use keeps the requested value).
Writes cases/<name>.json (request as specified) and expected/<name>.json from the unchanged Pyfa graph oracle run on a copy
with `oracle_state_overrides` applied (Pyfa itself downgrades an unusable state to online). Re-run after
tools/make_draft_cases.py, which rewrites cases/. Needs the same Pyfa env as tools/make_draft_expected.py (PYFA, PYTHONPATH).
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
out = subprocess.run([sys.executable, str(ORACLE)] + sorted(str(p) for p in tmp.glob("*.json")), capture_output=True, text=True)
n = 0
for line in out.stdout.splitlines():
    r = json.loads(line)
    name = Path(r.pop("file")).stem
    r.update(case=name, oracle="pyfa-graphs+state-ruling")
    (DRAFT / "expected" / (name + ".json")).write_text(json.dumps(r, indent=1, sort_keys=True) + "\n")
    n += 1
print(n, "ruling cases written")
if n != len(spec):
    sys.stderr.write(out.stderr[-4000:]); sys.exit(1)
