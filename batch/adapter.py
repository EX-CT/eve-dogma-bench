"""batch-suite adapter: the ONLY place that knows the engine's batch request/response shape and transport.

PROVISIONAL (2026-10-03): EX-CT/eve-dogma has no batch contract yet (main d990818: only the JSONL `batch` stream).
The bench shape (CONTRACT-BATCH.md) is sent unchanged:
  rpc (default): `ENGINE serve-stdio`, one line {"id":1,"method":"calc_batch","params":<BatchRequest>} -> {"id":1,"result":<BatchResponse>}
  cli:           `ENGINE calc-batch` with the BatchRequest JSON on stdin -> BatchResponse JSON on stdout
When F publishes its contract, change to_engine() / from_engine() / call() here; semantics.py and the cases stay."""
import json, subprocess

METHOD, CLI_CMD = "calc_batch", "calc-batch"


def to_engine(req):
    return req


def from_engine(resp):
    """engine response -> normalized {"total", "results": [{"index","label","stats"|"error","delta"?}], "base"?}"""
    return resp


def call(engine, req, transport="rpc", timeout=600):
    payload = to_engine(req)
    if transport == "rpc":
        line = json.dumps({"id": 1, "method": METHOD, "params": payload}) + "\n"
        r = subprocess.run(engine.split() + ["serve-stdio"], input=line, capture_output=True, text=True, timeout=timeout)
        for l in r.stdout.splitlines():
            try:
                j = json.loads(l)
            except ValueError:
                continue
            if j.get("id") == 1:
                return from_engine(j["result"]) if "result" in j else {"error": j.get("error")}
        return {"error": {"code": "NO_RESPONSE", "message": (r.stderr or r.stdout)[-300:]}}
    r = subprocess.run(engine.split() + [CLI_CMD], input=json.dumps(payload), capture_output=True, text=True, timeout=timeout)
    try:
        j = json.loads(r.stdout)
    except ValueError:
        return {"error": {"code": "NO_RESPONSE", "message": f"exit {r.returncode}: {(r.stderr or r.stdout)[-300:]}"}}
    return j if "error" in j and "results" not in j else from_engine(j)
