#!/usr/bin/env python3
"""Batch adapter: score eve-fit-mcp's compute_fit through the bench runners (column `mcp` evidence, suite mcp-bench).
Reads JSONL FitRequests on stdin, sends each as an MCP `tools/call` compute_fit {fit: <request>, detail: "full"}
to an eve-fit-mcp stdio server, writes the returned engine output (FitStats) as JSONL, same order. A tool error is
written as {"error": {...}}. Null-valued request keys are dropped (see drop_nulls).
  python3 run.py --name mcp --batch-cmd "python3 tools/mcp_batch.py --mcp-dir DIR" ...
  python3 ext/tools/score.py --batch-cmd "python3 tools/mcp_batch.py --mcp-dir DIR"
env: EVE_DOGMA_BIN (engine binary the MCP spawns), EVE_DOGMA_DATASET (required by the MCP index)."""
import argparse, json, os, subprocess, sys


def drop_nulls(x):
    """The MCP's lenient schema rejects `null` for optional object fields (e.g. modules[].mutation / spool, which the
    contract allows as null); absent == null in the contract, so null-valued keys are dropped before the call."""
    if isinstance(x, dict):
        return {k: drop_nulls(v) for k, v in x.items() if v is not None}
    if isinstance(x, list):
        return [drop_nulls(v) for v in x]
    return x


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mcp-dir", required=True, help="eve-fit-mcp checkout with dist/ built (npm ci && npm run build)")
    ap.add_argument("--tool", default="compute_fit")
    a = ap.parse_args()
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
        r = call("tools/call", {"name": a.tool, "arguments": {"fit": drop_nulls(req), "detail": "full"}})
        res = r.get("result") or {}
        if "error" in r or res.get("isError"):
            out = {"error": r.get("error") or {"message": " ".join(c.get("text", "") for c in res.get("content", []))[:500]}}
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
