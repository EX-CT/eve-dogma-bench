#!/usr/bin/env python3
"""Pyfa EFT-import oracle for the mutated suite (GPL-3.0-or-later, test tool only; see LICENSE-GPL-NOTE).
Imports EFT texts with Pyfa's own service/port/eft.py importEft (loaded unmodified by pyfa_formats.py) and prints
what an importer must produce, including mutated drones (pyfa_formats.norm only covers mutated modules).
usage: python pyfa_mutated_import.py FILE.eft.txt [...]   or   --jsonl FILE.jsonl (lines {"name","text"})"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pyfa_formats as pf  # noqa: E402


def mut(x):
    if not getattr(x, "isMutated", False):
        return None
    return {"base_type_id": x.baseItem.ID, "mutaplasmid_type_id": x.mutaplasmid.ID,
            "attributes": {str(k): v.value for k, v in sorted(x.mutators.items())}}


def norm(fit):
    out = pf.norm(fit)
    out["drones"] = [{"type_id": d.item.ID, "quantity": d.amount, "mutation": mut(d)} for d in fit.drones]
    return out


def run(name, text):
    res = pf._try(lambda: [norm(f) for f in [pf.eft.importEft(text.splitlines())]])
    print(json.dumps({"name": name, "text": text, **res}))


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["--jsonl"]:
        for line in open(a[1], encoding="utf-8"):
            o = json.loads(line)
            run(o["name"], o["text"])
    else:
        for p in a:
            run(os.path.basename(p).split(".")[0], open(p, encoding="utf-8").read())
