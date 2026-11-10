#!/usr/bin/env bash
# The step-for-step check of a genome-wide walk file against the GFA it was
# built from, or the GFA its graph was published as: walks-truth.py rebuild
# over $SHARDS shards of the paths, $JOBS fed by each read of the GFA, all
# under one memory cap. Writes <out>.rebuild.txt with each shard's lines and
# <out>.done, PASSED or FAILED.
# Usage, on ada:
#   [SHARDS=24] [JOBS=8] [MEM=80G] bash genome-check.sh <walks.gz> <gfa or gfa.gz> <out prefix>
set -uo pipefail
F=$1 G=$2 OUT=$3
T=$(cd "$(dirname "$(readlink -f "$0")")/../../../.." && pwd)/scripts/walks-truth.py
systemd-run --user --scope -q -p MemoryMax=${MEM:-80G} -p MemorySwapMax=0 nice -n 10 \
  /usr/bin/time -f "%e s, %M KB peak" -o "$OUT.rebuild.time" \
  python3 -I "$T" rebuild "$F" "$G" --shards ${SHARDS:-24} --jobs ${JOBS:-8} > "$OUT.rebuild.txt" 2>&1
[ $? = 0 ] && ! grep -q Traceback "$OUT.rebuild.txt" && echo PASSED > "$OUT.done" || echo FAILED > "$OUT.done"
cat "$OUT.done"
grep -q PASSED "$OUT.done"
