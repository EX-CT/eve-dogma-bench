#!/usr/bin/env python3
"""Score an engine on the DRAFT 0.3 corpus (graphs/draft-0.3/cases + expected). Unreleased; round 2 is scored on
0.2 with graphs/run_graphs.py (unchanged). Same flags as run_graphs.py; results go to results/graphs-<name>/.

  python3 graphs/draft-0.3/run_draft.py --name X --batch-cmd "<engine> graph-batch --dataset D"
  python3 graphs/draft-0.3/run_draft.py --self-test"""
import json, pathlib, sys

DRAFT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(DRAFT.parent))
import run_graphs as R  # noqa: E402  (the 0.2 scorer, imported read-only; only its corpus loader is swapped)


def load_draft():
    out = []
    for p in sorted((DRAFT / "cases").glob("*.json")):
        e = DRAFT / "expected" / p.name
        if e.exists():
            out.append((p.stem, json.loads(p.read_text()), json.loads(e.read_text())))
    return out


R.load = load_draft
if "--name" in sys.argv:
    i = sys.argv.index("--name") + 1
    if not sys.argv[i].startswith("draft-0.3-"):
        sys.argv[i] = "draft-0.3-" + sys.argv[i]
R.main()
