#!/usr/bin/env python3
"""Score an engine on the ext/rpc lookup suite (bench 1.11 draft "lookups", CONTRACT.md).
usage: python3 ext/tools/score_rpc.py --cmd "ENGINE serve-stdio" [--name X] [--out results.json] [cases...]
Each case is sent as one JSON-RPC 2.0 request line; the response `result` must equal the Pyfa expectation
(numbers within the bench tolerance, lists of scalars compared sorted, lists of {id...} objects sorted by id;
dicts: the expected keys must match, extra engine keys are ignored).
Expected {"error": ...}: passes when the engine answers with an error (JSON-RPC `error` or `result.error`), other
than UNKNOWN_METHOD. fits.backup: the returned XML is
compared after parsing (fit name, ship, hardware (slot, type, qty)), not byte for byte. An UNKNOWN_METHOD /
method-not-found error is reported as not_implemented (a failure)."""
import argparse, collections, json, pathlib, subprocess, sys
import xml.dom.minidom
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from metrics import close  # noqa: E402
SUITE = ROOT / "ext" / "rpc"


def parse_backup(text):
    doc = xml.dom.minidom.parseString(text)
    out = []
    for f in doc.getElementsByTagName("fitting"):
        hw = sorted([h.getAttribute("slot"), h.getAttribute("type"), int(h.getAttribute("qty") or 1)]
                    for h in f.getElementsByTagName("hardware"))
        out.append({"name": f.getAttribute("name"), "ship": f.getElementsByTagName("shipType")[0].getAttribute("value"), "hardware": hw})
    return out


def same(g, e):
    if isinstance(e, dict):  # expected keys only (an engine may return more fields)
        return isinstance(g, dict) and all(k in g and same(g[k], e[k]) for k in e)
    if isinstance(e, list):
        if not isinstance(g, list) or len(g) != len(e):
            return False
        if e and all(isinstance(x, dict) and "id" in x for x in e) and all(isinstance(x, dict) for x in g):
            g = sorted(g, key=lambda x: str(x.get("id")))
            e = sorted(e, key=lambda x: str(x.get("id")))
        if all(not isinstance(x, (dict, list)) for x in e):
            try:
                return all(close(a, b) for a, b in zip(sorted(g, key=str), sorted(e, key=str)))
            except TypeError:
                return False
        return all(same(a, b) for a, b in zip(g, e))
    if isinstance(e, (int, float)) and not isinstance(e, bool):
        return isinstance(g, (int, float)) and close(g, e)
    return g == e


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cmd", required=True)
    ap.add_argument("--name", default="engine")
    ap.add_argument("--out")
    ap.add_argument("cases", nargs="*")
    a = ap.parse_args()
    files = [pathlib.Path(f).resolve() for f in a.cases] or sorted((SUITE / "cases").glob("*.json"))
    files = [f for f in files if (SUITE / "expected" / f.name).exists()]
    reqs = [json.loads(f.read_text()) for f in files]
    lines = "".join(json.dumps({"jsonrpc": "2.0", "id": i, "method": r["method"], "params": r["params"]}) + "\n"
                    for i, r in enumerate(reqs))
    out = subprocess.run(a.cmd, shell=True, input=lines, capture_output=True, text=True)
    resp = {}
    for l in out.stdout.splitlines():
        try:
            r = json.loads(l)
        except ValueError:
            continue
        if isinstance(r, dict) and "id" in r:
            resp[r["id"]] = r
    res, by = {}, collections.defaultdict(lambda: [0, 0])
    for i, f in enumerate(files):
        exp = json.loads((SUITE / "expected" / f.name).read_text())
        r = resp.get(i) or {}
        err = r.get("error") or (r.get("result") or {}).get("error") if isinstance(r.get("result"), dict) or r.get("error") else None
        if err and "error" not in r:  # eve-fit serve-stdio reports method errors as result.error
            r = {k: v for k, v in r.items() if k != "result"}
        ni = bool(err) and any(s in json.dumps(err) for s in ("UNKNOWN_METHOD", "-32601", "not found"))
        if "error" in exp["result"]:
            ok = bool(err) and not ni
            got = err
        elif err or "result" not in r:
            ok, got = False, err or "no response"
        elif exp["feature"] == "fits.backup":
            try:
                got = parse_backup(r["result"].get("xml", ""))
            except Exception as e:
                got = repr(e)
            ok = same(got, exp["parsed"])
        else:
            got = r["result"]
            ok = same(got, exp["result"])
        res[f.stem] = {"pass": ok, "not_implemented": ni and not ok, "feature": exp["feature"], "item": exp["item"],
                       "got": None if ok else json.dumps(got)[:300]}
        by[exp["feature"]][0] += ok
        by[exp["feature"]][1] += 1
    np = sum(v["pass"] for v in res.values())
    print(f"{a.name}: rpc suite {np}/{len(res)} pass; " + ", ".join(f"{k} {p}/{t}" for k, (p, t) in sorted(by.items())))
    fail = [k for k, v in res.items() if not v["pass"]]
    if fail:
        print("  failing:", " ".join(fail), f"({sum(v['not_implemented'] for v in res.values())} not_implemented)")
    if a.out:
        pathlib.Path(a.out).write_text(json.dumps({"name": a.name, "pass": np, "total": len(res), "cases": res}, indent=1, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
