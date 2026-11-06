#!/usr/bin/env bash
cd ~/work/impl-writer
for l in 7 8 9; do
  LEVEL=$l systemd-run --user --scope -q -p MemoryMax=30G -p MemorySwapMax=0 /usr/bin/time -f "pggbY level $l: %e s, %M KB peak" lv/target/release/gfa-to-tabix ~/work/arb-format-opus/in/pggbY.gfa --walks --refs GRCh38 -o lv$l > lv$l.log 2>&1
  ls -l lv$l.GRCh38.walks.gz >> levels.txt; tail -1 lv$l.log >> levels.txt
done
echo done >> levels.txt
