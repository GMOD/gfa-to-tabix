#!/usr/bin/env bash
# The writer with ownTiles on MC chr22 and pggb chrY: built; checked by
# verify7.py and verify7.mjs; audited by audit7.py, which checks every
# record's ownTiles against its decoded own steps and every unit name; and
# its lines compared with final-run.sh's build (the commit before ownTiles)
# with the ownTiles column and the tables' entries left out.
set -uo pipefail
W=~/work/impl-writer
cd $W
rm -rf src && git clone -q -b format7-writer writer.bundle src
git -C src log --oneline -1 > own.commit.txt
(cd src && cargo build --release -q) > own.build-binary.log 2>&1 || { echo FAILED > own.done; exit 1; }
B=$W/src/target/release/gfa-to-tabix
S=$W/src/docs/departures/scripts
IN=~/work/arb-format-opus/in
cap() { systemd-run --user --scope -q -p MemoryMax=$1 -p MemorySwapMax=0 "${@:2}"; }
lines() { zcat "$1" | awk -F'\t' -v strip=$2 'BEGIN {OFS = "\t"} $1 == "#entry" {next} strip && $4 == "departure" {NF--} {print}' | sha256sum; }
for d in mc22 pggbY; do
  cap 30G /usr/bin/time -f "$d: %e s, %M KB peak" $B $IN/$d.gfa --walks --refs GRCh38 -o own.$d > own.$d.build.log 2>&1
  F=own.$d.GRCh38.walks.gz
  cap 10G python3 -I $S/verify7.py $F > own.$d.verify7py.txt 2>&1
  cap 20G node ~/work/arb-arbA/scripts/verify7.mjs $F > own.$d.verify7mjs.txt 2>&1
  cap 60G python3 -I $S/audit7.py $F --top 3 > own.$d.audit.txt 2>&1
  { echo "with ownTiles left out: $(lines $F 1)"; echo "final-run.sh's build:  $(lines final.$d.GRCh38.walks.gz 0)"; } > own.$d.lines.txt
done
ls -l own.*.walks.gz own.*.walks.gz.idx > own.sizes.txt
echo done > own.done
