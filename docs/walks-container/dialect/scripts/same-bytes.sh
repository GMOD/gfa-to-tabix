#!/usr/bin/env bash
# Builds each GFA given with two binaries, as walk files and as a node and
# link index in both formats, under the reference its first path line names,
# and compares what they write byte for byte: the same exit status and the
# same files, or the line says what differs. Exits 1 if any build differs.
# Usage: same-bytes.sh OLD_BINARY NEW_BINARY gfa...
set -u
OLD=$(readlink -f "$1") NEW=$(readlink -f "$2")
shift 2
dir=$(mktemp -d)
trap 'rm -rf "$dir"' EXIT
differs=0
compare() {
  local label=$1 a b
  shift
  rm -rf "$dir/old" "$dir/new"
  mkdir "$dir/old" "$dir/new"
  (cd "$dir/old" && "$OLD" "$@" -o o > log 2>&1; echo $? > status)
  (cd "$dir/new" && "$NEW" "$@" -o o > log 2>&1; echo $? > status)
  a=$(cd "$dir/old" && ls | grep -v '^log$' | LC_ALL=C sort | xargs sha256sum)
  b=$(cd "$dir/new" && ls | grep -v '^log$' | LC_ALL=C sort | xargs sha256sum)
  if [ "$a" = "$b" ]; then
    echo "same	$label	exit $(cat "$dir/new/status"), $(echo "$b" | grep -vc ' status$') files"
  else
    echo "DIFFERS	$label	old: $(tail -1 "$dir/old/log" | cut -c1-120) | new: $(tail -1 "$dir/new/log" | cut -c1-120)"
    differs=1
  fi
}
for gfa in "$@"; do
  name=$(basename "$gfa")
  line=$(grep -m1 -E '^[PW]	' "$gfa" | cut -f1-2 | cut -c1-200)
  sample=$(echo "$line" | cut -f2 | cut -d'#' -f1 | sed -E 's/(:[0-9]+-[0-9]+|\[[0-9-]+\])$//')
  compare "$name index" "$gfa"
  compare "$name index --format 1" "$gfa" --format 1
  if [ -n "$sample" ]; then
    compare "$name index --reference $sample" "$gfa" --reference "$sample"
    compare "$name index --reference $sample --format 1" "$gfa" --reference "$sample" --format 1
    compare "$name walks --refs $sample" "$gfa" --walks --refs "$sample"
    compare "$name walks --refs $sample --tile 10" "$gfa" --walks --refs "$sample" --tile 10
  fi
done
exit $differs
