#!/usr/bin/env bash
# The format arbitration's builds (2026-11-05): MC chr22 and pggb chrY on
# GRCh38 by the arb-format-opus writer, audited; then chr9, chr14 and chr22 of
# the CHM13-referenced MC graph on CHM13, with their departure reads at the
# windows the GRCh38 graph's CHM13 file refused
set -uo pipefail
cd ~/work/arb-format-opus
B=~/src/arb-format-opus/gfa-to-tabix/target/release/gfa-to-tabix
A=~/src/arb-format-opus/gfa-to-tabix/docs/departures/scripts/audit6.py
cap() { systemd-run --user --scope -q -p MemoryMax=$1 -p MemorySwapMax=0 "${@:2}"; }
waitmem() { while [ "$(free -g | awk '/^Mem:/ {print $7}')" -lt $1 ]; do sleep 60; done; }
mkdir -p out
until [ -s in/pggbY.gfa ]; do sleep 30; done
waitmem 30
cap 20G /usr/bin/time -f "pggbY: %e s, %M KB peak" $B in/pggbY.gfa --walks --refs GRCh38 -o out/pggbY > out/pggbY.build.log 2>&1
waitmem 30
cap 40G /usr/bin/time -f "audit pggbY: %e s, %M KB peak" python3 -I $A out/pggbY.GRCh38.walks.bed.gz --top 3 > out/pggbY.audit.txt 2>&1
until grep -q "^mc22 " in/inputs.log 2>/dev/null; do sleep 30; done
waitmem 30
cap 20G /usr/bin/time -f "mc22: %e s, %M KB peak" $B in/mc22.gfa --walks --refs GRCh38 -o out/mc22 > out/mc22.build.log 2>&1
waitmem 30
cap 30G /usr/bin/time -f "audit mc22: %e s, %M KB peak" python3 -I $A out/mc22.GRCh38.walks.bed.gz --top 3 > out/mc22.audit.txt 2>&1
windows() {
  for w in "$@"; do
    seq=${w%:*}; at=${w#*:}
    tabix out/$1.CHM13.walks.bed.gz "CHM13#0#$seq~departure:$((at + 1))-$((at + 65536))" 2>/dev/null | wc -lc | awk -v w="$w" '{printf "%s\t%d rows\t%d text bytes\n", w, $1, $2}'
  done
}
for c in chr9 chr14 chr22; do
  until grep -q "^chm13-$c " in/inputs.log 2>/dev/null; do sleep 30; done
  waitmem 40
  cap 40G /usr/bin/time -f "chm13-$c: %e s, %M KB peak" $B in/chm13-$c.gfa --walks --refs CHM13 -o out/chm13-$c > out/chm13-$c.build.log 2>&1
  tabix -H out/chm13-$c.CHM13.walks.bed.gz | head -1 > out/chm13-$c.header.txt
done
{
  echo "# 64 kb windows' departure reads, CHM13-referenced graph (window: sequence:start)"
  for w in chr9:30000000 chr9:39000000 chr9:45000000 chr9:60000000 chr9:78000000 chr9:85000000; do
    f=chm13-chr9; seq=${w%:*}; at=${w#*:}
    tabix out/$f.CHM13.walks.bed.gz "CHM13#0#$seq~departure:$((at + 1))-$((at + 65536))" | wc -lc | awk -v w="$w" '{printf "%s\t%d rows\t%d text bytes\n", w, $1, $2}'
  done
  for w in chr14:13000000 chr14:13500416; do
    seq=${w%:*}; at=${w#*:}
    tabix out/chm13-chr14.CHM13.walks.bed.gz "CHM13#0#$seq~departure:$((at + 1))-$((at + 65536))" | wc -lc | awk -v w="$w" '{printf "%s\t%d rows\t%d text bytes\n", w, $1, $2}'
  done
} > out/chm13.windows.txt
for c in chr9 chr14 chr22; do
  waitmem 70
  cap 70G /usr/bin/time -f "audit chm13-$c: %e s, %M KB peak" python3 -I $A out/chm13-$c.CHM13.walks.bed.gz --top 3 > out/chm13-$c.audit.txt 2>&1
done
echo done > out/arb.done
