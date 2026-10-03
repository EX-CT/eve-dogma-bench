#!/usr/bin/env python3
"""Run the Pyfa capacitor oracle (oracle/pyfa_cap_oracle.py, GPL test tool) on cap/cases/*.json and write
cap/expected/<case>.json. env: PYFA, PYFA_PY, WX_STUB (defaults: the shared box's /workspace/exct-eve/ref)."""
import json, os, pathlib, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from metrics import expected_from_oracle  # noqa: E402
REF = os.environ.get("EXCT_REF", "/workspace/exct-eve/ref")
PYFA, PY, STUB = os.environ.get("PYFA", f"{REF}/pyfa"), os.environ.get("PYFA_PY", f"{REF}/pyfa-venv/bin/python"), os.environ.get("WX_STUB", f"{REF}/stubs")
files = sorted(str(p) for p in (ROOT / "cases").glob("*.json"))
out = subprocess.run([PY, str(ROOT.parent / "oracle/pyfa_cap_oracle.py"), *files], capture_output=True, text=True, cwd=PYFA,
                     env=dict(os.environ, PYTHONPATH=STUB, PYFA=PYFA))
exp = ROOT / "expected"
exp.mkdir(exist_ok=True)
n = 0
for line in out.stdout.splitlines():
    if not line.startswith("{"):
        continue
    r = json.loads(line)
    name = r["file"][:-5]
    if "error" in r:
        print(f"{name}: oracle error {r['error']}")
        continue
    vals, rep = expected_from_oracle(r["cap"])
    diag = {k: r["cap"].get(k) for k in ("drains", "sim_end_ms", "optimized_repeat", "low_gj", "high_gj")}
    (exp / f"{name}.json").write_text(json.dumps({"case": name, "oracle": "pyfa-eos capSim", "values": vals, "report_only": rep,
                                                  "diagnostics": diag}, indent=1, sort_keys=True) + "\n")
    n += 1
print(f"wrote {n} expected files")
