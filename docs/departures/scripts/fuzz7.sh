#!/usr/bin/env bash
# Builds fuzz7-gen.py's random graphs under eight option sets, with two
# references, R and Q, and runs on each file the release checks
# (verify7.py), the claims checks (claims7.py --own) and the audit
# (audit7.py); prints every seed whose build or checks fail, and exits 1 if
# any does. Keeps the failing seeds' graphs and outputs.
# Usage: FUZZ_DIR=dir GFA_TO_TABIX=binary fuzz7.sh [from] [to]
set -u
HERE=$(dirname "$(readlink -f "$0")")
B=$(readlink -f "$(command -v "${GFA_TO_TABIX:?set GFA_TO_TABIX to the writer binary}")")
mkdir -p "${FUZZ_DIR:?set FUZZ_DIR to a scratch directory}"
cd "$FUZZ_DIR"
from=${1:-1}; to=${2:-200}
failed=0
for seed in $(seq "$from" "$to"); do
  python3 -I "$HERE/fuzz7-gen.py" "$seed" > "g$seed.gfa"
  kept=0
  for v in "a:20:" "b:16:--stay 8" "c:32:--abridge-steps 3" "d:20:--stay 40" "e:64:--abridge-steps 2" \
           "f:8:--stay 40 --abridge-steps 1" "g:64:--abridge-bytes 300" "h:128:--abridge-bytes 600"; do
    tag=${v%%:*}; rest=${v#*:}; tile=${rest%%:*}; read -r -a opts <<< "${rest#*:}"
    out=o$seed.$tag
    if ! "$B" "g$seed.gfa" --walks --refs R,Q --tile "$tile" "${opts[@]}" -o "$out" > "$out.log" 2>&1; then
      echo "seed $seed $tag BUILD: $(grep -v '^\[' "$out.log" | tail -1)"; failed=1; kept=1; continue
    fi
    bad=""
    for r in R Q; do
      f=$out.$r.walks.gz
      checks=$(python3 -I "$HERE/verify7.py" "$f" 2>&1) || bad="$bad $r verify7: $checks;"
      claims=$(python3 -I "$HERE/claims7.py" "$f" --own 2>&1) || bad="$bad $r claims7: $(echo "$claims" | grep -E '^[1-9][0-9]*'$'\t''|Traceback|Error' | tr '\n' ' ');"
      audit=$(python3 -I "$HERE/audit7.py" "$f" --window 64 --point 16 2>&1)
      found=$(echo "$audit" | grep -E "MISSING|field mismatch|decode:|differ from|Traceback|Error|^[1-9][0-9]*\s+departures inside a piece reaching|^[1-9][0-9]*\s+records with no|^[1-9][0-9]*\s+bases uncovered|^[1-9][0-9]*\s+.*\(must be 0\)|differs from the row|another sequence|two extents|detail unit of a tile|own_tiles")
      [ -n "$found" ] && bad="$bad $r audit7: $(echo "$found" | tr '\n' ' ');"
    done
    if [ -n "$bad" ]; then echo "seed $seed $tag:$bad"; failed=1; kept=1; else rm -f "$out".*; fi
  done
  [ "$kept" = 0 ] && rm -f "g$seed.gfa"
done
echo "done $from-$to"
exit $failed
