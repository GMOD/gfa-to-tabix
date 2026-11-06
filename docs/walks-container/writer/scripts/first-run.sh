#!/usr/bin/env bash
# The format 7 writer on MC chr22 and pggb chrY, verified and compared with
# arbiter A's converter output for the same 3.0.0 builds.
set -uo pipefail
W=~/work/impl-writer
cd $W
IN=~/work/arb-format-opus/in
(cd src && cargo build --release -q) > build-binary.log 2>&1 || { echo FAILED > run.done; exit 1; }
B=$W/src/target/release/gfa-to-tabix
cap() { systemd-run --user --scope -q -p MemoryMax=$1 -p MemorySwapMax=0 "${@:2}"; }
waitmem() { while [ "$(free -g | awk '/^Mem:/ {print $7}')" -lt $1 ]; do sleep 60; done; }
for d in mc22 pggbY; do
  waitmem 30
  cap 30G /usr/bin/time -f "$d: %e s, %M KB peak" $B $IN/$d.gfa --walks --refs GRCh38 -o $d > $d.build.log 2>&1
  cap 20G node ~/work/arb-arbA/scripts/verify7.mjs $d.GRCh38.walks.gz > $d.verify7.txt 2>&1
  cap 30G python3 -I compare7.py $d.GRCh38.walks.gz ~/work/arb-arbA/out/$d/s7.walks.gz > $d.compare.txt 2>&1
done
ls -l *.walks.gz *.walks.gz.idx ~/work/arb-arbA/out/*/s7.walks.gz > sizes.txt
echo done > run.done
