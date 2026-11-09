#!/usr/bin/env bash
# The step-for-step check of a genome-wide walk file against the GFA it was
# built from, or the GFA its graph was published as: walks-truth.py rebuild
# over every shard of the paths, $AT_ONCE at once, each under a memory cap.
# A shard that already passed is not run again, so a stopped run resumes.
# Writes <out>.rebuild.<i>.txt per shard, <out>.rebuild.txt with each
# shard's last line, and <out>.done, PASSED or FAILED.
# Usage, on ada:
#   [SHARDS=24] [AT_ONCE=3] bash genome-check.sh <walks.gz> <gfa or gfa.gz> <out prefix>
set -uo pipefail
F=$1 G=$2 OUT=$3
SHARDS=${SHARDS:-24} AT_ONCE=${AT_ONCE:-3}
T=$(cd "$(dirname "$(readlink -f "$0")")/../../../.." && pwd)/scripts/walks-truth.py
cap() { systemd-run --user --scope -q -p MemoryMax=$1 -p MemorySwapMax=0 nice -n 10 "${@:2}"; }
running=0
for i in $(seq 0 $((SHARDS - 1))); do
  out=$OUT.rebuild.$i.txt
  [ "$(cat "$out.rc" 2>/dev/null)" = 0 ] && continue
  (cap 28G /usr/bin/time -f "shard $i: %e s, %M KB peak" -o "$out.time" python3 -I "$T" rebuild "$F" "$G" --shard $i/$SHARDS > "$out" 2>&1; echo $? > "$out.rc") &
  running=$((running + 1))
  [ $((running % AT_ONCE)) = 0 ] && wait
done
wait
failed=0
for i in $(seq 0 $((SHARDS - 1))); do
  [ "$(cat "$OUT.rebuild.$i.txt.rc")" = 0 ] && ! grep -q Traceback "$OUT.rebuild.$i.txt" || failed=$((failed + 1))
done
{
  echo "# rebuild of $F against $G, $SHARDS shards, $failed failed; a shard's exit status, then its last line"
  for i in $(seq 0 $((SHARDS - 1))); do echo "shard $i: exit $(cat "$OUT.rebuild.$i.txt.rc"): $(tail -1 "$OUT.rebuild.$i.txt")"; done
  echo "# lines of any shard that aren't a summary:"
  grep -hvE '^\S+: shard' "$OUT".rebuild.[0-9]*.txt | sort | uniq -c | sort -rn | head -40
} > "$OUT.rebuild.txt"
[ $failed = 0 ] && echo PASSED > "$OUT.done" || echo FAILED > "$OUT.done"
cat "$OUT.done"
[ $failed = 0 ]
