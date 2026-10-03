#!/usr/bin/env python3
"""Build formats/expected/edge_export.jsonl (CONTRACT-FORMATS 0.1 export edge rows + their round-trip imports)
from `oracle/pyfa_formats.py formats/edge_export/*.json` output.

Rows: {"id","case","name","format","options","text"|"error"} (direction export) and
      {"id","case","format","input","fits"|"error"}            (direction import, Pyfa's import of its own export)."""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_formats import EXPORT_OPTIONS  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main(raw):
    n = 0
    with open(os.path.join(ROOT, "formats", "expected", "edge_export.jsonl"), "w") as fd:
        for line in open(raw):
            r = json.loads(line)
            case = "edge_export/" + r["file"]
            src = json.load(open(os.path.join(ROOT, "formats", case)))
            for fmt, v in r["export"].items():
                row = {"id": "%s@export:%s" % (case, fmt), "direction": "export", "case": case, "name": src["name"],
                       "format": fmt, "options": EXPORT_OPTIONS[fmt]}
                row.update({"text": v["ok"]} if "ok" in v else {"error": {"code": "EXPORT_ERROR", "pyfa": v["error"]}})
                fd.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
                n += 1
            for fmt, v in r["import"].items():
                row = {"id": "%s@import:%s" % (case, fmt), "direction": "import", "case": case, "format": fmt,
                       "input": r["export"][fmt]["ok"]}
                fits = [f for f in v.get("ok") or [] if f is not None]
                row.update({"fits": fits} if fits else {"error": {"code": "IMPORT_ERROR", "pyfa": v.get("error", "no fit")}})
                fd.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
                n += 1
    print("edge_export rows %d" % n)


if __name__ == "__main__":
    main(sys.argv[1])
