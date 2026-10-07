#!/usr/bin/env bash
# parity.sh <jbrowse-components/scripts dir> <gfa-to-tabix binary> <rgfa|paths> <gfa> [reference]
# Builds the two BED files with the JBrowse shell scripts and with this tool,
# and fails unless the rows match byte for byte and htslib's tabix returns the
# same rows from both indexes for every sequence.
# Requires: gfatools, gawk, python3, sort, bgzip, tabix
set -euo pipefail

scripts=$1
binary=$2
route=$3
gfa=$4
reference=${5:-}

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

case "$route" in
  rgfa) bash "$scripts/build_rgfa_tabix.sh" "$gfa" "$work/old" >/dev/null 2>&1 ;;
  paths) bash "$scripts/build_pggb_tabix.sh" "$gfa" "$work/old" ${reference:+"$reference"} >/dev/null 2>&1 ;;
  *) echo "route is rgfa or paths" >&2; exit 2 ;;
esac
"$binary" "$gfa" --layout contig -o "$work/new" ${reference:+--reference "$reference"} 2>/dev/null

status=0
for kind in segs links; do
  if ! cmp -s <(gzip -dc "$work/old.$kind.bed.gz") <(gzip -dc "$work/new.$kind.bed.gz"); then
    echo "FAIL $kind rows differ: $gfa $reference"
    diff <(gzip -dc "$work/old.$kind.bed.gz") <(gzip -dc "$work/new.$kind.bed.gz") | head -6
    status=1
  fi
  if ! cmp -s <(tabix -l "$work/old.$kind.bed.gz") <(tabix -l "$work/new.$kind.bed.gz"); then
    echo "FAIL $kind index sequence names differ: $gfa $reference"
    status=1
  fi
  while read -r name; do
    for region in "$name" "$name:1-1000" "$name:5000-20000" "$name:100000-2000000"; do
      if ! cmp -s <(tabix "$work/old.$kind.bed.gz" "$region") <(tabix "$work/new.$kind.bed.gz" "$region"); then
        echo "FAIL $kind query $region differs: $gfa $reference"
        status=1
      fi
    done
  done < <(tabix -l "$work/old.$kind.bed.gz")
done
[ $status -eq 0 ] && echo "ok   $(basename "$gfa") $reference ($(gzip -dc "$work/new.segs.bed.gz" | wc -l) nodes, $(gzip -dc "$work/new.links.bed.gz" | wc -l) link rows)"
exit $status
