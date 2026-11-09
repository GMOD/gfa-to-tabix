#!/usr/bin/env bash
# The W lines of a GFA that a walk file built from it leaves out, having no
# step on a node of the reference, and the bp they hold.
# Usage: left-out.sh <walks.gz> <gfa.gz>
set -euo pipefail
dir=$(mktemp -d)
trap 'rm -rf "$dir"' EXIT
pigz -dc "$2" | grep -a '^[WP]' | cut -f1-6 > "$dir/lines.tsv"
gzip -dc "$1" | awk -F'\t' '$4 == "walk" || $4 == "abridged" || $4 == "ref" { k = $5 "\t" $6; if (!(k in s)) { s[k] = 1; print k } }' > "$dir/held.tsv"
awk -F'\t' '
  NR == FNR { have[$1 "\t" $2] = 1; next }
  $1 == "P" { p++ }
  $1 == "W" {
    n++; bp += $6 - $5; k = $2 "#" $3 "#" $4 "\t" $5
    if (!(k in have)) { out++; outbp += $6 - $5; if ($6 - $5 > 100000) big++; if ($6 - $5 > longest) { longest = $6 - $5; which = k } }
  }
  END { printf "W lines %d holding %.0f bp; P lines %d; left out of the walk file: %d lines, %.0f bp (%.4f%%), %d over 100 kb, the longest %d bp (%s)\n", n, bp, p, out, outbp, 100 * outbp / bp, big, longest, which }
' "$dir/held.tsv" "$dir/lines.tsv"
