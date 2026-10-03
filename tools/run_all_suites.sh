#!/usr/bin/env bash
# Run every bench suite on one engine binary and write the outputs check_no_regress.py reads.
#   tools/run_all_suites.sh ENGINE OUT [NAME]
# ENGINE: eve-fit binary (calc / batch / serve-stdio). OUT: output dir (created). NAME: result label (default ci).
# core / ext / ext_rpc / batch / effects run from this checkout (pending-1.11). graphs, cap, mutated and formats run from the pinned
# suite commits below, checked out as worktrees under $SUITES_DIR (default OUT/suites); override a checkout with
# SUITE_GRAPHS / SUITE_CAP / SUITE_MUTATED / SUITE_FORMATS=/path.
set -euo pipefail
ENGINE=$(readlink -f "$1"); OUT=$(mkdir -p "$2" && cd "$2" && pwd); N=${3:-ci}
BENCH=$(cd "$(dirname "$0")/.." && pwd)
SUITES_DIR=${SUITES_DIR:-$OUT/suites}
declare -A REF=([graphs]=db81b8c565c86fae5964b76db7932a0cbf177edb   # graphs-round2 = tag graphs-v0.3
                [cap]=d80cc38093416bda0f2f271a5f3b439c45648f1b      # cap-suite
                [mutated]=4533dde70a624a0850bdf43ead198b42d99c5832  # mutated-suite
                [formats]=7c716e707779ffb90c5c9845a66478351d62f583) # formats-suite
declare -A DIR
for s in graphs cap mutated formats; do
  var="SUITE_${s^^}"
  if [[ -n "${!var:-}" ]]; then DIR[$s]=$(readlink -f "${!var}"); continue; fi
  DIR[$s]=$SUITES_DIR/$s
  if [[ ! -d ${DIR[$s]} ]]; then
    git -C "$BENCH" cat-file -e "${REF[$s]}^{commit}" 2>/dev/null || git -C "$BENCH" fetch -q --depth 1 origin "${REF[$s]}"
    git -C "$BENCH" worktree add -q -f --detach "${DIR[$s]}" "${REF[$s]}"
  fi
done
rc=0
step() { local name=$1; shift; echo "== $name"; "$@" > "$OUT/$name.log" 2>&1 || { echo "   (exit $? - see $OUT/$name.log; scored by check_no_regress)"; rc=1; }; }
cd "$BENCH"
step core     python3 run.py --name "$N" --cmd "$ENGINE calc" --batch-cmd "$ENGINE batch" --batch-repeat 1 --latency-n 5
rm -rf "$OUT/core"; cp -r "results/$N" "$OUT/core"; rm -rf "results/$N"
step ext      python3 ext/tools/score.py --batch-cmd "$ENGINE batch" --name "$N" --out "$OUT/ext.json"
step ext_rpc  python3 ext/tools/score_rpc.py --cmd "$ENGINE serve-stdio" --name "$N" --out "$OUT/ext_rpc.json"
step batch    python3 batch/run_batch.py --cmd "$ENGINE" --name "$N" --out "$OUT/batch.json"
step effects  python3 effects/tools/score.py --batch-cmd "$ENGINE batch" --name "$N" --out "$OUT/effects.json"
cd "${DIR[graphs]}"
step graphs   python3 graphs/run_graphs.py --name "$N" --rpc-cmd "$ENGINE serve-stdio"
rm -rf "$OUT/graphs"; cp -r "results/graphs-$N" "$OUT/graphs"
cd "${DIR[cap]}"
step cap      python3 cap/run_cap.py --batch-cmd "$ENGINE batch" --name "$N"
cp "cap/results/$N.json" "$OUT/cap.json"
cd "${DIR[mutated]}"
step mutated  python3 mutated/run_mutated.py --name "$N" --cmd "$ENGINE calc" --batch-cmd "$ENGINE batch" --batch-repeat 1 --latency-n 5
rm -rf "$OUT/mutated"; cp -r "mutated/results/$N" "$OUT/mutated"
cd "${DIR[formats]}"
step formats  python3 tools/evaluate_formats.py --rpc "$ENGINE serve-stdio" --name "$N" --out "$OUT/formats"
python3 - "$OUT" "$BENCH" "${DIR[graphs]}" "${DIR[cap]}" "${DIR[mutated]}" "${DIR[formats]}" <<'PY'
import json, subprocess, sys
out, bench, gr, cap, mut, fmt = sys.argv[1:]
rev = lambda d: subprocess.run(["git", "-C", d, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
roots = {"core": bench, "ext": bench, "ext_rpc": bench, "batch": bench, "effects": bench, "graphs": gr, "cap": cap, "mutated": mut, "formats": fmt}
json.dump({"roots": roots, "refs": {k: rev(v) for k, v in roots.items()}}, open(f"{out}/roots.json", "w"), indent=1)
PY
echo "outputs in $OUT (suite runner exit codes ignored by design; the gate is check_no_regress.py)"
