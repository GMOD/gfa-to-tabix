#!/usr/bin/env bash
# The two cargo builds of docs/placement/pggb-chrY-build.txt: v4/ is a clone at
# f001614 (src identical to v4.0.0) and repo/ one at main, both built in release mode
set -uo pipefail
cd ~/work/loose1111
G=~/work/scratch/graph-repro/data/pggb/chrY.gfa
for round in 1 2; do
  for v in v4 main; do
    bin=v4/target/release/gfa-to-tabix; [ $v = main ] && bin=repo/target/release/gfa-to-tabix
    systemd-run --user --scope -q -p MemoryMax=20G -p MemorySwapMax=0 \
      /usr/bin/time -f "$v (glibc) round $round: %e s, %M KB peak" -a -o iso.time.txt \
      nice -n 10 "$bin" "$G" --reference GRCh38 -o iso.$v > iso.$v.log 2>&1
  done
done
cmp iso.v4.graph.bed.gz iso.main.graph.bed.gz && echo "byte-identical" >> iso.time.txt
echo "load $(cut -d" " -f1-3 /proc/loadavg)" >> iso.time.txt
touch iso.done
