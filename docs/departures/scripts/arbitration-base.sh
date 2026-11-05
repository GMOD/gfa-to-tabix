#!/usr/bin/env bash
# The same inputs built by main's writer (the port3 binary, 76c9223; no
# writer change since), for sizes against out/
set -uo pipefail
cd ~/work/arb-format-opus
B=~/src/gfa-to-tabix-port3/target/release/gfa-to-tabix
cap() { systemd-run --user --scope -q -p MemoryMax=$1 -p MemorySwapMax=0 "${@:2}"; }
until grep -q "audit mc22:" out/mc22.audit.txt 2>/dev/null; do sleep 60; done
mkdir -p base
for n in pggbY mc22; do
  cap 20G /usr/bin/time -f "base $n: %e s, %M KB peak" $B in/$n.gfa --walks --refs GRCh38 -o base/$n > base/$n.build.log 2>&1
done
for n in pggbY mc22; do
  echo "$n: arb $(stat -c %s out/$n.GRCh38.walks.bed.gz) bytes, base $(stat -c %s base/$n.GRCh38.walks.bed.gz) bytes"
  for f in out base; do
    zcat $f/$n.GRCh38.walks.bed.gz | awk -F'\t' -v f=$f '!/^#/ {n[$4]++; b[$4] += length($0) + 1} END {for (k in n) printf "  %s %s: %d rows, %d text bytes\n", f, k, n[k], b[k]}' | sort
  done
done > sizes.txt
echo done > base.done
