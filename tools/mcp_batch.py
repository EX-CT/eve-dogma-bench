#!/usr/bin/env python3
"""Batch adapter: score eve-fit-mcp's compute_fit through the bench runners (column `mcp` evidence, suite mcp-bench).
Reads JSONL FitRequests on stdin, sends each as an MCP `tools/call` compute_fit {fit: <request>, detail: "full"}
to an eve-fit-mcp stdio server, writes the returned engine output (FitStats) as JSONL, same order. A tool error is
written as {"error": {...}}. Null-valued request keys are dropped (see drop_nulls).
  python3 run.py --name mcp --batch-cmd "python3 tools/mcp_batch.py --mcp-dir DIR" ...
  python3 ext/tools/score.py --batch-cmd "python3 tools/mcp_batch.py --mcp-dir DIR"
  python3 graphs/run_graphs.py --batch-cmd "python3 tools/mcp_batch.py --mcp-dir DIR --tool compute_graph"  (graph requests)
  python3 batch/run_batch.py --transport cli --cmd "python3 tools/mcp_batch.py --mcp-dir DIR --tool compute_batch"
    (CLI emulation: `[--prices FILE] batch --request -` -> compute_batch {request}; `calc` -> compute_fit with the
    FitRequest's price inputs as tool arguments; --prices FILE has no MCP equivalent -> error UNSUPPORTED)
env: EVE_DOGMA_BIN (engine binary the MCP spawns), EVE_DOGMA_DATASET (required by the MCP index)."""
import argparse, json, os, re, subprocess, sys


def drop_nulls(x):
    """The MCP's lenient schema rejects `null` for optional object fields (e.g. modules[].mutation / spool, which the
    contract allows as null); absent == null in the contract, so null-valued keys are dropped before the call."""
    if isinstance(x, dict):
        return {k: drop_nulls(v) for k, v in x.items() if v is not None}
    if isinstance(x, list):
        return [drop_nulls(v) for v in x]
    return x


def graph_args(g):
    """CONTRACT-GRAPHS request -> compute_graph arguments (graphs suite: --tool compute_graph)."""
    x = g.get("x") or {}
    args = {"graph": g.get("graph"), "table": False}
    if g.get("fit") is not None:
        args["fit"] = drop_nulls(g["fit"])
    if x.get("axis"):
        args["x_axis"] = x["axis"]
    if "values" in x:
        args["x"] = {"values": x["values"]}
    for k in ("y", "params", "settings"):
        if g.get(k) is not None:
            args[k] = drop_nulls(g[k])
    t = g.get("target")
    if t:
        # target.profile keeps its nulls (signature_radius null = ideal application; the MCP accepts nullable values)
        args["target"] = {k: (drop_nulls(v) if k == "fit" else v) for k, v in t.items() if v is not None}
    return args


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mcp-dir", required=True, help="eve-fit-mcp checkout with dist/ built (npm ci && npm run build)")
    ap.add_argument("--tool", default="compute_fit")
    a, rest = ap.parse_known_args()
    if a.tool == "compute_batch" and "--prices" in rest:
        sys.stdin.read()
        print(json.dumps({"error": {"code": "UNSUPPORTED", "message": "eve-fit-mcp has no --prices FILE input (engine global option)"}}))
        return
    calc = a.tool == "compute_batch" and "calc" in rest
    p = subprocess.Popen(["node", "dist/main.js"], cwd=a.mcp_dir, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.DEVNULL, text=True, bufsize=1)
    nid = [0]

    def call(method, params, notify=False):
        msg = {"jsonrpc": "2.0", "method": method, "params": params}
        if not notify:
            nid[0] += 1
            msg["id"] = nid[0]
        p.stdin.write(json.dumps(msg) + "\n")
        p.stdin.flush()
        if notify:
            return None
        while True:
            line = p.stdout.readline()
            if not line:
                raise SystemExit("mcp server exited")
            r = json.loads(line)
            if r.get("id") == nid[0]:
                return r

    call("initialize", {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "eve-dogma-bench", "version": "1"}})
    call("notifications/initialized", {}, notify=True)
    data = sys.stdin.read()
    try:  # single mode (run.py --cmd): one pretty-printed request
        reqs = [json.loads(data)]
    except ValueError:  # batch mode: JSONL
        reqs = [json.loads(l) for l in data.splitlines() if l.strip()]
    for req in reqs:
        if calc:
            req = dict(req)
            args = {k: req.pop(k) for k in ("price_overrides", "prices") if k in req}
            if (req.get("options") or {}).get("price") is not None:
                args["price"] = req["options"]["price"]
            r = call("tools/call", {"name": "compute_fit", "arguments": {"fit": drop_nulls(req), "detail": "full", **args}})
        elif a.tool == "compute_batch":
            r = call("tools/call", {"name": "compute_batch", "arguments": {"request": req}})
        else:
            r = call("tools/call", {"name": a.tool, "arguments": graph_args(req) if a.tool == "compute_graph" else
                                    {"fit": drop_nulls(req), "detail": "full"}})
        res = r.get("result") or {}
        if "error" in r or res.get("isError"):
            msg = (r.get("error") or {}).get("message") or " ".join(c.get("text", "") for c in res.get("content", []))
            m = re.match(r"(?:Error: )?([A-Z][A-Z_]+): ", msg)  # tool errors carry the contract code as a prefix
            out = {"error": {"code": m.group(1), "message": msg[:500]} if m else {"message": msg[:500]}}
        else:
            out = res.get("structuredContent")
            if out is None:
                out = json.loads(res["content"][-1]["text"])
        sys.stdout.write(json.dumps(out) + "\n")
        sys.stdout.flush()
    p.stdin.close()
    p.wait(timeout=10)


if __name__ == "__main__":
    main()
