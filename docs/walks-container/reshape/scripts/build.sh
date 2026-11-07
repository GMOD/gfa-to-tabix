#!/bin/bash
cd ~/work/reshape/out
IN=~/work/arb-format-opus/in
cap() { systemd-run --user --scope -q -p MemoryMax=100G -p MemorySwapMax=0 nice -n 10 "$@"; }
for g in mc22 pggbY; do
  for v in base r1; do
    cap /usr/bin/time -f "$v $g: %e s, %M KB peak" ../$v/target/release/gfa-to-tabix $IN/$g.gfa --walks --refs GRCh38 -o $v.$g > $v.$g.log 2>&1
  done
done
cap /usr/bin/time -f "r1stay0 pggbY: %e s, %M KB peak" ../r1/target/release/gfa-to-tabix $IN/pggbY.gfa --walks --refs GRCh38 --stay 0 -o r1stay0.pggbY > r1stay0.pggbY.log 2>&1
echo done > build.done
