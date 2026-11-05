#!/usr/bin/env bash
# Genome-wide walk files for hosting, gfa-to-tabix 3.0.0: GRCh38 from HPRC
# v2.1's GRCh38-referenced MC graph, CHM13 from its CHM13-referenced one;
# chr22 of each audited, a few windows' departure reads measured
set -uo pipefail
mkdir -p ~/work/genome3 && cd ~/work/genome3
IN=~/work/arb-format-opus/in
S=~/src/gfa-to-tabix-3.0.0
(cd $S && cargo build --release -q) > binary.log 2>&1 || { echo FAILED binary > genome3.done; exit 1; }
B=$S/target/release/gfa-to-tabix
A=$S/docs/departures/scripts/audit6.py
$B --version > version.txt 2>&1
cap() { systemd-run --user --scope -q -p MemoryMax=$1 -p MemorySwapMax=0 "${@:2}"; }
waitmem() { while [ "$(free -g | awk '/^Mem:/ {print $7}')" -lt $1 ]; do sleep 60; done; }
for g in grch38 chm13; do
  waitmem 50
  [ -s $g.gfa ] || cap 60G /usr/bin/time -f "convert $g: %e s, %M KB peak" vg convert -f $IN/$g.gbz > $g.gfa 2> convert-$g.log
done
waitmem 50
cap 80G /usr/bin/time -f "build GRCh38: %e s, %M KB peak" $B grch38.gfa --walks --refs GRCh38 -o hprc-v2.1-mc-grch38 > build-grch38.log 2>&1
waitmem 50
cap 80G /usr/bin/time -f "build CHM13: %e s, %M KB peak" $B chm13.gfa --walks --refs CHM13 -o hprc-v2.1-mc-chm13 > build-chm13.log 2>&1
for f in hprc-v2.1-mc-grch38.GRCh38 hprc-v2.1-mc-chm13.CHM13; do
  tabix -H $f.walks.bed.gz | head -1 > $f.header.txt
  ref=${f##*.}
  waitmem 40
  cap 40G /usr/bin/time -f "audit $f chr22: %e s, %M KB peak" python3 -I $A $f.walks.bed.gz --seq $ref#0#chr22 --top 3 > $f.chr22.audit.txt 2>&1
done
{
  for w in GRCh38:chr22:18600000 GRCh38:chr9:45000000 GRCh38:chr6:160614798 CHM13:chr9:45000000 CHM13:chr9:60000000 CHM13:chr14:13500416 CHM13:chr22:19000000; do
    ref=${w%%:*}; rest=${w#*:}; seq=${rest%:*}; at=${rest#*:}
    f=$( [ $ref = GRCh38 ] && echo hprc-v2.1-mc-grch38.GRCh38 || echo hprc-v2.1-mc-chm13.CHM13 )
    tabix $f.walks.bed.gz "$ref#0#$seq~departure:$((at + 1))-$((at + 65536))" | wc -lc | awk -v w="$w" '{printf "%s\t%d departure rows\t%d text bytes\n", w, $1, $2}'
  done
} > windows.txt
ls -l *.walks.bed.gz* > sizes.txt
echo done > genome3.done
