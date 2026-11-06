#!/usr/bin/env bash
# Builds random graphs in walk format 7, runs the release checks and the
# audit on each; prints any seed whose build, checks or audit fail.
# Usage: FUZZ_DIR=dir GFA_TO_TABIX=binary fuzz7.sh [from] [to]
HERE=$(dirname "$(readlink -f "$0")")
A=$HERE/audit7.py
G=$HERE/fuzz6-gen.py
V=$HERE/../../walks-container/arbA/scripts/verify7.mjs
B=$(readlink -f "$(command -v "${GFA_TO_TABIX:?set GFA_TO_TABIX to the writer binary}")")
cd "${FUZZ_DIR:?set FUZZ_DIR to a scratch directory}"
from=${1:-1}; to=${2:-200}
for seed in $(seq $from $to); do
  python3 -I $G $seed > g$seed.gfa
  if ! grep -q '^S' g$seed.gfa; then echo "seed $seed GENERATE: no graph"; continue; fi
  for v in "a:20:" "b:16:--stay 8" "c:32:--abridge-steps 3" "d:20:--stay 40" "e:64:--abridge-steps 2" "f:8:--stay 40 --abridge-steps 1"; do
    tag=${v%%:*}; rest=${v#*:}; tile=${rest%%:*}; opts=${rest#*:}
    if ! $B g$seed.gfa --walks --refs R --tile $tile $opts -o o$seed.$tag > o$seed.$tag.log 2>&1; then
      echo "seed $seed $tag BUILD: $(grep -v '^\[' o$seed.$tag.log | tail -1)"; continue
    fi
    if ! checks=$(node $V o$seed.$tag.R.walks.gz $tile 2>&1); then
      echo "seed $seed $tag RELEASE CHECKS: $(echo "$checks" | grep -m1 Error)"; continue
    fi
    out=$(python3 -I $A o$seed.$tag.R.walks.gz --window 64 --point 16 2>&1)
    bad=$(echo "$out" | grep -E "MISSING|field mismatch|decode:|differ from|Traceback|Error|^[1-9][0-9]*\s+departures inside a piece reaching|^[1-9][0-9]*\s+records with no|^[1-9][0-9]*\s+bases uncovered|^[1-9][0-9]*\s+.*\(must be 0\)|differs from the row|another sequence|two extents|detail unit of a tile")
    if [ -n "$bad" ]; then echo "seed $seed $tag: $(echo "$bad" | tr '\n' ' ')"; else rm -f o$seed.$tag.*; fi
  done
  [ -z "$(ls o$seed.* 2>/dev/null)" ] && rm -f g$seed.gfa
done
echo done $from-$to
