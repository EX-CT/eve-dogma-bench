#!/usr/bin/env python3
"""Build the import/export format suite (formats/expected/*.jsonl) from raw Pyfa oracle output.

  oracle/pyfa_formats.py cases/*.json            > raw_cases.jsonl     (exports + round-trip imports per case)
  oracle/pyfa_formats.py --import auto formats/edge/* > raw_edge.jsonl (Pyfa Port.importAuto on hand-written inputs)
  python3 tools/make_formats.py raw_cases.jsonl raw_edge.jsonl

Outputs (one JSON object per line, all values are Pyfa's own output):
  formats/expected/export.jsonl   {"case","format","options","text"|"error"}
  formats/expected/import.jsonl   {"case","format","input","fits"|"error","source_overfit","pyfa_reexport_identical"}
  formats/expected/edge.jsonl     {"file","kind","fits"|"payload"|"error"}
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "formats", "expected")

EXPORT_OPTIONS = {
    "eft": {"implants": True, "mutations": True, "loaded_charges": True, "boosters": True, "cargo": True},
    "eft_min": {"implants": False, "mutations": False, "loaded_charges": False, "boosters": False, "cargo": False},
    "dna": {"formatting": False},
    "dna_formatted": {"formatting": True},
    "esi": {"charges": True, "implants": True, "boosters": True},
    "esi_min": {"charges": False, "implants": False, "boosters": False},
    "xml": {},
    "multibuy": {"loaded_charges": True, "cargo": True, "implants": True, "boosters": True, "optimize_prices": False},
    "multibuy_min": {"loaded_charges": False, "cargo": False, "implants": False, "boosters": False, "optimize_prices": False},
    "shipstats": {},
}


def mods_key(fit):
    return sorted((m["type_id"], m["slot"]) for m in fit["modules"])


def main(raw_cases, raw_edge):
    os.makedirs(OUT, exist_ok=True)
    n_ex = n_im = n_edge = 0
    with open(os.path.join(OUT, "export.jsonl"), "w") as fe, open(os.path.join(OUT, "import.jsonl"), "w") as fi:
        for line in open(raw_cases):
            r = json.loads(line)
            if "error" in r:
                continue
            case = r["file"]
            # Pyfa drops modules beyond the hull's slot/hardpoint counts on import; many bench fits are deliberately
            # over-fitted (validation cases). Decided once per case from the EFT import (which keeps every legal
            # module) and applied to every format, for the checker's breakdown.
            eft_imp = r["import"].get("eft", {}).get("ok", [None])[0]
            overfit = eft_imp is None or len(eft_imp["modules"]) < len(r["source"]["modules"])
            for fmt, v in r["export"].items():
                row = {"case": case, "format": fmt, "options": EXPORT_OPTIONS[fmt]}
                row.update({"text": v["ok"]} if "ok" in v else {"error": v["error"]})
                fe.write(json.dumps(row, sort_keys=True) + "\n")
                n_ex += 1
            for fmt, v in r["import"].items():
                row = {"case": case, "format": fmt, "input": r["export"][fmt]["ok"]}
                if "ok" in v:
                    row["fits"] = v["ok"]
                    row["source_overfit"] = overfit
                    row["pyfa_reexport_identical"] = v.get("reexport_identical")
                else:
                    row["error"] = v["error"]
                    row["source_overfit"] = overfit
                fi.write(json.dumps(row, sort_keys=True) + "\n")
                n_im += 1
    with open(os.path.join(OUT, "edge.jsonl"), "w") as fd:
        for line in open(raw_edge):
            r = json.loads(line)
            row = {"file": r["file"], "kind": r.get("kind")}
            if "error" in r:
                row["error"] = r["error"]
            elif r.get("kind") in ("XML", "JSON", "EFT", "EFT Config", "DNA"):
                row["fits"] = r["ok"]
            else:
                row["payload"] = r["ok"]
            fd.write(json.dumps(row, sort_keys=True) + "\n")
            n_edge += 1
    print("export rows %d, import rows %d, edge rows %d" % (n_ex, n_im, n_edge))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
