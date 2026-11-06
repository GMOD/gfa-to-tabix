#!/usr/bin/env bash
# Builds every walk fixture under four option sets and runs the release
# checks (verify7.py) and the claims checks (claims7.py --own) on each file,
# then fuzz7.sh's batch of seeds 1 to $SEEDS (6 by default). Exits 1 on any
# failure, naming it.
# Usage: scripts/check-walks.sh target/release/gfa-to-tabix
set -u
REPO=$(cd "$(dirname "$0")/.." && pwd)
B=$(readlink -f "${1:?the gfa-to-tabix binary}")
S=$REPO/docs/departures/scripts
dir=$(mktemp -d)
trap 'rm -rf "$dir"' EXIT
failed=0
for f in "walks-two-refs.gfa GRCh38,Q" "walks-two-refs-p.gfa GRCh38,Q" "walks-repeat.gfa R" "walks-loop.gfa R" \
         "walks-records.gfa R" "walks-contig-ends.gfa R" "walks-skip.gfa R,Q"; do
  read -r gfa refs <<< "$f"
  for opts in "--tile 10" "--tile 7 --stay 0" "--tile 10 --abridge-bytes 1" "--tile 1000 --abridge-steps 1"; do
    read -r -a args <<< "$opts"
    if ! "$B" "$REPO/tests/data/$gfa" --walks --refs "$refs" "${args[@]}" -o "$dir/o" > "$dir/log" 2>&1; then
      echo "$gfa $opts: BUILD $(tail -1 "$dir/log")"; failed=1; continue
    fi
    for r in ${refs//,/ }; do
      out=$(python3 -I "$S/verify7.py" "$dir/o.$r.walks.gz" 2>&1) || { echo "$gfa $opts $r: $out"; failed=1; }
      out=$(python3 -I "$S/claims7.py" "$dir/o.$r.walks.gz" --own 2>&1) ||
        { echo "$gfa $opts $r:"; echo "$out" | grep -vE '^0'$'\t'; failed=1; }
    done
    rm -f "$dir"/o.*
  done
done
FUZZ_DIR=$dir/fuzz GFA_TO_TABIX=$B bash "$S/fuzz7.sh" 1 "${SEEDS:-6}" || failed=1
exit $failed
