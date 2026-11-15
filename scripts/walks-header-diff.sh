#!/usr/bin/env bash
# Builds walk files with two writers and runs walks-header-diff.py on each
# pair: the walk fixtures of tests/data under four option sets, then each
# extra "GFA REFS" pair given after the binaries under the default options.
# Exits 1 when any pair differs by more than the #walks line's added tags.
# Usage: scripts/walks-header-diff.sh OLD_BINARY NEW_BINARY ["GFA REFS"]...
set -u -o pipefail
REPO=$(cd "$(dirname "$0")/.." && pwd)
OLD=$(readlink -f "${1:?the unchanged writer}")
NEW=$(readlink -f "${2:?the writer that adds the tags}")
dir=$(mktemp -d)
trap 'rm -rf "$dir"' EXIT
failed=0 pairs=0
compare() {
  local gfa=$1 refs=$2
  rm -rf "$dir/old" "$dir/new"
  mkdir -p "$dir/old" "$dir/new"
  if ! "$OLD" "$gfa" --walks --refs "$refs" "${@:3}" -o "$dir/old/o" > "$dir/log" 2>&1 ||
     ! "$NEW" "$gfa" --walks --refs "$refs" "${@:3}" -o "$dir/new/o" > "$dir/log" 2>&1; then
    echo "$gfa ${*:3}: BUILD $(tail -1 "$dir/log")"; failed=1; return
  fi
  for r in ${refs//,/ }; do
    echo "== $(basename "$gfa") $r ${*:3}"
    python3 -I "$REPO/scripts/walks-header-diff.py" "$dir/old/o.$r.walks.gz" "$dir/new/o.$r.walks.gz" |
      sed "s|$dir/new/||" || failed=1
    pairs=$((pairs + 1))
  done
}
for f in "walks-two-refs.gfa GRCh38,Q" "walks-two-refs-p.gfa GRCh38,Q" "walks-repeat.gfa R" "walks-loop.gfa R" \
         "walks-records.gfa R" "walks-contig-ends.gfa R" "walks-skip.gfa R,Q" "walks-sequences.gfa R" \
         "walks-long-jump.gfa R" "walks-abridge-bytes.gfa R"; do
  read -r gfa refs <<< "$f"
  for opts in "--tile 10" "--tile 7 --stay 0" "--tile 10 --abridge-bytes 1" "--tile 1000 --abridge-steps 1"; do
    read -r -a args <<< "$opts"
    compare "$REPO/tests/data/$gfa" "$refs" "${args[@]}"
  done
done
compare "$REPO/tests/data/walks-sequences.gfa" R --tile 10 --sequences
for extra in "${@:3}"; do
  read -r gfa refs <<< "$extra"
  compare "$gfa" "$refs"
done
echo "walks-header-diff: $pairs pairs, $([ $failed = 0 ] && echo none differ || echo SOME DIFFER) beyond the #walks line's tags"
exit $failed
