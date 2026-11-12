#!/usr/bin/env bash
# Builds HPRC release 2's pggb chrY with two binaries, as walk files for
# GRCh38 and for CHM13 and as a node and link index in both formats, the two
# binaries side by side, and compares every file they write byte for byte.
# RUN goes before each build, to cap, nice and time it. Exits 1 if a file
# differs or is missing.
# Usage: RUN="cap.sh 12G" same-bytes-pggbY.sh OLD_BINARY NEW_BINARY pggbY.gfa WORK
set -u
OLD=$(readlink -f "$1") NEW=$(readlink -f "$2") G=$(readlink -f "$3") WORK=$4
RUN=${RUN:-}
rm -rf "$WORK/old" "$WORK/new"
mkdir -p "$WORK/old" "$WORK/new"
echo "pggb chrY, $(stat -c %s "$G") bytes, $(grep -c '^P' "$G") P lines"
for mode in "--walks --refs GRCh38" "--walks --refs CHM13" "--reference GRCh38" "--reference GRCh38 --format 1"; do
  tag=$(echo "$mode" | tr -d ' -')
  (cd "$WORK/old" && $RUN "$OLD" "$G" $mode -o "$tag" > "$tag.log" 2>&1; echo "old $mode: $(tail -1 "$tag.log")") &
  (cd "$WORK/new" && $RUN "$NEW" "$G" $mode -o "$tag" > "$tag.log" 2>&1; echo "new $mode: $(tail -1 "$tag.log")") &
  wait
done
differs=0
for f in $( (cd "$WORK/old" && ls; cd "$WORK/new" && ls) | grep -v '\.log$' | LC_ALL=C sort -u); do
  if cmp -s "$WORK/old/$f" "$WORK/new/$f"; then
    echo "identical	$f	$(stat -c %s "$WORK/new/$f") bytes	sha256 $(sha256sum < "$WORK/new/$f" | cut -c1-16)"
  else
    echo "DIFFERS	$f"
    differs=1
  fi
done
exit $differs
