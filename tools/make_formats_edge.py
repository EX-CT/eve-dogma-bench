#!/usr/bin/env python3
"""Build formats/expected/edge.jsonl (CONTRACT-FORMATS 0.1 edge rows) from raw oracle output.

  # 1. raw Pyfa results (oracle/pyfa_formats.py --import FMT FILE..., one run per format, see formats/README.md)
  # 2. python3 tools/make_formats_edge.py raw_auto.jsonl [raw_<fmt>.jsonl ...]

Each raw line is {"file","format", "kind"?, "ok"|"error"}. Rows are written for every file in
formats/edge/MANIFEST.json (format auto) and every "forced" entry. Pyfa outcome -> contract expectation:
  ok with >= 1 non-null fit (fit kinds)      -> {"kind", "fits": [...]}   (null fits dropped, order kept)
  ok, non-fit kind (FittingItem/Additions*)  -> {"kind", "items": [{"type_id","amount","mutation"}]}
  Unrecognized (no format matched / blank)   -> {"error": {"code": "UNRECOGNIZED_INPUT", "pyfa": ...}}
  any exception, or no non-null fit          -> {"error": {"code": "IMPORT_ERROR", "pyfa": ...}}
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FORCED_KIND = {"eft": "EFT", "eftcfg": "EFT Config", "dna": "DNA", "dna_alt": "DNA", "xml": "XML", "esi": "JSON"}
FIT_KINDS = ("EFT", "EFT Config", "DNA", "XML", "JSON")


def items_of(kind, payload):
    if kind == "FittingItem":
        out = []
        for base, muta, attrs in payload:
            mu = None
            if muta is not None:
                mu = {"base_type_id": base["type_id"], "mutaplasmid_type_id": muta["mutaplasmid_type_id"],
                      "attributes": attrs}
            out.append({"type_id": base["type_id"], "amount": 1, "mutation": mu})
        return out
    (lst,) = payload
    return [{"type_id": t["type_id"], "amount": n, "mutation": m} for t, n, m in lst]


CRASH = ("AttributeError", "KeyError", "TypeError", "IndexError")


def pyfa_crash(msg):
    """Pyfa failed with an internal exception rather than a parse/validation error (flagged for review)."""
    return msg.startswith(CRASH) or "substring not found" in msg


def expect(raw):
    if "error" in raw:
        code = "UNRECOGNIZED_INPUT" if raw["error"].startswith("Unrecognized") else "IMPORT_ERROR"
        r = {"error": {"code": code, "pyfa": raw["error"]}}
        if pyfa_crash(raw["error"]):
            r["pyfa_crash"] = True
        return r
    kind = raw.get("kind")
    ok = raw["ok"]
    if kind is None or kind in FIT_KINDS:
        fits = [f for f in ok if f is not None]
        if not fits:
            return {"kind": kind, "error": {"code": "IMPORT_ERROR", "pyfa": "no fit produced (%d null)" % len(ok)}}
        r = {"fits": fits}
        if kind:
            r["kind"] = kind
        if len(fits) != len(ok):
            r["pyfa_null_fits_dropped"] = len(ok) - len(fits)
        return r
    return {"kind": kind, "items": items_of(kind, ok)}


def main(paths):
    raw = {}
    for p in paths:
        for line in open(p):
            r = json.loads(line)
            raw[(r["file"], r["format"])] = r
    man = json.load(open(os.path.join(ROOT, "formats", "edge", "MANIFEST.json")))
    rows = [(f, "auto", m["category"]) for f, m in sorted(man["files"].items())]
    rows += [(x["file"], x["format"], "forced") for x in man["forced"]]
    n = 0
    with open(os.path.join(ROOT, "formats", "expected", "edge.jsonl"), "w") as fd:
        for f, fmt, cat in rows:
            r = raw[(f, fmt)]
            row = {"id": "%s@%s" % (f, fmt), "file": f, "format": fmt, "category": cat}
            if f.endswith(".cfg"):
                row["path"] = f
            exp = expect(r)
            if f in man.get("unscored", {}):
                exp["scored"] = False
                exp["unscored_reason"] = man["unscored"][f]
            elif exp.get("pyfa_crash"):
                exp["scored"] = False
                exp["unscored_reason"] = "ruling 1: Pyfa itself crashes (oracle invalid); report-only"
            if fmt != "auto" and exp.get("kind") is None:
                exp["kind"] = FORCED_KIND[fmt]
            row.update(exp)
            fd.write(json.dumps(row, sort_keys=True) + "\n")
            n += 1
    print("edge rows %d" % n)


if __name__ == "__main__":
    main(sys.argv[1:])
