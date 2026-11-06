#!/usr/bin/env bash
# The writer at the branch's head on MC chr22 and pggb chrY, built, checked
# with arbiter A's verify7.mjs, and compared with arbiter A's converter
# output for the same 3.0.0 builds: units and lines, detail names, which
# detail unit each abridged row reaches, and size by compressor.
set -uo pipefail
W=~/work/impl-writer
cd $W
rm -rf src && git clone -q -b format7-writer writer.bundle src
git -C src log --oneline -1 > final.commit.txt
(cd src && cargo build --release -q) > final.build-binary.log 2>&1 || { echo FAILED > final.done; exit 1; }
B=$W/src/target/release/gfa-to-tabix
IN=~/work/arb-format-opus/in
cap() { systemd-run --user --scope -q -p MemoryMax=$1 -p MemorySwapMax=0 "${@:2}"; }
for d in mc22 pggbY; do
  C7=~/work/arb-arbA/out/$d/s7.walks.gz
  cap 30G /usr/bin/time -f "$d: %e s, %M KB peak" $B $IN/$d.gfa --walks --refs GRCh38 -o final.$d > final.$d.build.log 2>&1
  F=final.$d.GRCh38.walks.gz
  cap 20G node ~/work/arb-arbA/scripts/verify7.mjs $F > final.$d.verify7.txt 2>&1
  cap 30G python3 -I compare7.py $F $C7 > final.$d.compare.txt 2>&1
  cap 20G python3 -I detailnames.py $F $C7 > final.$d.detailnames.txt 2>&1
  for f in $F $C7; do cap 20G python3 -I abridgedcheck.py $f; done > final.$d.abridged.txt 2>&1
  for f in $F $C7; do cap 10G python3 -I reblock.py $f 6; done > final.$d.reblock.txt 2>&1
done
ls -l final.*.walks.gz final.*.walks.gz.idx ~/work/arb-arbA/out/*/s7.walks.gz > final.sizes.txt
echo done > final.done
