#!/usr/bin/env bash
# The reference intervals an anchored node and link index (format 2) files
# its off-reference nodes under, by width: the distinct intervals and the
# node rows in each bin, over the sequences of SAMPLE, then the rows filed
# under any other sample's sequences.
# Usage: scripts/interval-widths.sh PREFIX.graph.bed.gz SAMPLE
set -euo pipefail
gzip -dc "$1" | awk -F'\t' -v sample="$2" '
  function bin(w) { return w < 1000 ? "1 under 1 kb" : w < 10000 ? "2 1 to 10 kb" : w < 100000 ? "3 10 to 100 kb" : w < 1000000 ? "4 100 kb to 1 Mb" : "5 over 1 Mb" }
  /^#/ { next }
  index($1, sample "#") != 1 { elsewhere[$4]++; next }
  $4 == "N" && $6 > 0 {
    b = bin($3 - $2); rows[b]++; total++
    if (!(($1, $2, $3) in seen)) { seen[$1, $2, $3] = 1; intervals[b]++ }
  }
  END {
    printf "off-reference node rows on %s: %d\n", sample, total
    for (b in rows) printf "%s\t%d intervals\t%d rows\t%.1f%% of rows\n", b, intervals[b], rows[b], 100 * rows[b] / total | "sort"
    close("sort")
    printf "rows filed under another sample: %d nodes, %d links\n", elsewhere["N"], elsewhere["L"]
  }' | sed 's/^[1-5] //'
