#!/usr/bin/env bash
# parity-fold.sh <gfa-to-tabix binary> [bandage-core version]
# The coarse tier through bandage-core's `bandage-fold`, the fold the graph
# track runs on each cut it draws, and through `gfa-to-tabix fold`. Fails unless
# the rows match byte for byte at several sizes, in both layouts.
# Requires: node (npx), gzip
set -uo pipefail

binary=$1
version=${2:-10.0.1}
data=$(dirname "$0")/../tests/data
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
status=0

while read -r gfa reference; do
  for below in 1 5 50 1000 10000; do
    for layout in contig anchored; do
      npx -y -p "@jbrowse/bandage-core@$version" bandage-fold "$data/$gfa" --below "$below" \
        ${reference:+--reference "$reference"} 2>/dev/null |
        "$binary" - --layout "$layout" -o "$work/js" > /dev/null 2>&1
      "$binary" fold "$data/$gfa" --below "$below" --layout "$layout" \
        ${reference:+--reference "$reference"} -o "$work/rs" > /dev/null 2>&1
      for kind in segs links; do
        if ! cmp -s <(gzip -dc "$work/js.$kind.bed.gz") <(gzip -dc "$work/rs.$kind.bed.gz"); then
          echo "FAIL $kind $gfa $reference below $below $layout"
          diff <(gzip -dc "$work/js.$kind.bed.gz") <(gzip -dc "$work/rs.$kind.bed.gz") | head -4
          status=1
        fi
      done
    done
  done
  [ $status -eq 0 ] && echo "ok   $gfa $reference"
done <<'CASES'
rgfa.gfa
ecoli_rgfa_slice.gfa
cactus.gfa
fold.gfa
ecoli_pggb_subgraph.gfa K12
paths.gfa ref
CASES
exit $status
