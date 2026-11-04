#!/usr/bin/env bash
# Builds and audits random graphs; prints any seed whose build or audit fails.
# Usage: FUZZ_DIR=dir GFA_TO_TABIX=binary fuzz6.sh [from] [to]
cd "${FUZZ_DIR:?set FUZZ_DIR to a scratch directory}"
A=$(dirname "$(readlink -f "$0")")/audit6.py
B=${GFA_TO_TABIX:?set GFA_TO_TABIX to the writer binary}
from=${1:-1}; to=${2:-200}
for seed in $(seq $from $to); do
  python3 -I $(dirname "$(readlink -f "$0")")/fuzz6-gen.py $seed > g$seed.gfa
  for v in "a:--chunk 20" "b:--chunk 16 --stay 8" "c:--chunk 32 --abridge-steps 3" "d:--chunk 20 --stay 40" "e:--chunk 64 --abridge-steps 2" "f:--chunk 8 --stay 40 --abridge-steps 1"; do
    tag=${v%%:*}; opts=${v#*:}
    if ! $B g$seed.gfa --walks --refs R $opts -o o$seed.$tag > o$seed.$tag.log 2>&1; then
      echo "seed $seed $tag BUILD: $(grep -v '^\[' o$seed.$tag.log | tail -1)"; continue
    fi
    out=$(python3 -I $A o$seed.$tag.R.walks.bed.gz --window 64 --point 16 2>&1)
    bad=$(echo "$out" | grep -E "MISSING|field mismatch|decode:|Traceback|Error|^[1-9][0-9]*\s+departures inside a piece reaching|^[1-9][0-9]*\s+records with no|^[1-9][0-9]*\s+bases uncovered|differs from the row")
    if [ -n "$bad" ]; then echo "seed $seed $tag: $(echo "$bad" | tr '\n' ' ')"; else rm -f o$seed.$tag.*; fi
  done
  [ -z "$(ls o$seed.* 2>/dev/null)" ] && rm -f g$seed.gfa
done
echo done $from-$to
