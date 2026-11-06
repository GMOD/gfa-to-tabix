#!/usr/bin/env bash
cd ~/work/impl-writer
for l in 6 7 9; do
  LEVEL=$l systemd-run --user --scope -q -p MemoryMax=20G -p MemorySwapMax=0 /usr/bin/time -f "mc22 level $l: %e s, %M KB peak" lv/target/release/gfa-to-tabix ~/work/arb-format-opus/in/mc22.gfa --walks --refs GRCh38 -o lvmc$l > lvmc$l.log 2>&1
  ls -l lvmc$l.GRCh38.walks.gz >> levels-mc.txt; tail -1 lvmc$l.log >> levels-mc.txt
done
echo done >> levels-mc.txt
