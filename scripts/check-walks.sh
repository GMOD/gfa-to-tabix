#!/usr/bin/env bash
# Shows the file checks fail on the broken files of broken.sh; builds every
# walk fixture under four option sets, and some under options of their
# own, and runs on each file the release checks (verify7.py), the claims
# checks (claims7.py --own), the audit (audit7.py, given the fixture) and
# walks-truth.py's rebuild of every line against the GFA; then fuzz7.sh's batch of seeds 1 to $SEEDS (6
# by default). Each check fails by its exit status. Exits 1 on any
# failure, naming it.
# Usage: scripts/check-walks.sh target/release/gfa-to-tabix
set -u
REPO=$(cd "$(dirname "$0")/.." && pwd)
B=$(readlink -f "${1:?the gfa-to-tabix binary}")
S=$REPO/docs/departures/scripts
dir=$(mktemp -d)
trap 'rm -rf "$dir"' EXIT
failed=0
bash "$S/broken.sh" || failed=1
check() {
  local gfa=$1 refs=$2 label="$1 ${*:3}"
  if ! "$B" "$REPO/tests/data/$gfa" --walks --refs "$refs" "${@:3}" -o "$dir/o" > "$dir/log" 2>&1; then
    echo "$label: BUILD $(tail -1 "$dir/log")"; failed=1; return
  fi
  for r in ${refs//,/ }; do
    local f=$dir/o.$r.walks.gz out
    out=$(python3 -I "$S/verify7.py" "$f" 2>&1) || { echo "$label $r: $out"; failed=1; }
    out=$(python3 -I "$S/claims7.py" "$f" --own 2>&1) ||
      { echo "$label $r:"; echo "$out" | grep -vE '^0'$'\t'; failed=1; }
    out=$(python3 -I "$S/audit7.py" "$f" --gfa "$REPO/tests/data/$gfa" --window 64 --point 16 2>&1) ||
      { echo "$label $r:"; echo "$out" | sed -n '/^audit7: /,$p'; echo "$out" | grep -E 'Traceback|Error'; failed=1; }
    out=$(python3 -I "$REPO/scripts/walks-truth.py" rebuild "$f" "$REPO/tests/data/$gfa" 2>&1) ||
      { echo "$label $r: $out"; failed=1; }
  done
  rm -f "$dir"/o.*
}
for f in "walks-two-refs.gfa GRCh38,Q" "walks-two-refs-p.gfa GRCh38,Q" "walks-repeat.gfa R" "walks-loop.gfa R" \
         "walks-records.gfa R" "walks-contig-ends.gfa R" "walks-skip.gfa R,Q" "walks-sequences.gfa R" \
         "walks-long-jump.gfa R"; do
  read -r gfa refs <<< "$f"
  for opts in "--tile 10" "--tile 7 --stay 0" "--tile 10 --abridge-bytes 1" "--tile 1000 --abridge-steps 1"; do
    read -r -a args <<< "$opts"
    check "$gfa" "$refs" "${args[@]}"
  done
done
check walks-abridge-bytes.gfa R --tile 100 --abridge-bytes 600
check walks-sequences.gfa R --tile 10 --sequences
FUZZ_DIR=$dir/fuzz GFA_TO_TABIX=$B bash "$S/fuzz7.sh" 1 "${SEEDS:-6}" || failed=1
exit $failed
