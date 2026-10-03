#!/bin/bash
# Regenerate formats/expected/edge.jsonl with Pyfa (oracle/pyfa_formats.py). usage: tools/gen_formats_edge.sh /path/to/ref
# ref layout: $R/pyfa (Pyfa checkout), $R/stubs, $R/pyfa-venv (python with Pyfa's deps)
set -e
R=${1:?ref dir}; B=$(cd "$(dirname "$0")/.." && pwd); E=$B/formats/edge; T=$(mktemp -d)
run() { (cd "$R/pyfa" && PYTHONPATH=$R/stubs PYFA=$R/pyfa "$R/pyfa-venv/bin/python" "$B/oracle/pyfa_formats.py" --import "$@" 2>/dev/null); }
run auto $(ls -d "$E"/* | grep -v MANIFEST.json) > "$T/raw_auto.jsonl"
python3 -c "
import json,collections
m=json.load(open('$E/MANIFEST.json'));g=collections.defaultdict(list)
for x in m['forced']: g[x['format']].append(x['file'])
for k,v in g.items(): print(k,' '.join(v))" | while read -r fmt files; do
  run "$fmt" $(for f in $files; do echo "$E/$f"; done) > "$T/raw_$fmt.jsonl"
done
python3 "$B/tools/make_formats_edge.py" "$T"/raw_*.jsonl
