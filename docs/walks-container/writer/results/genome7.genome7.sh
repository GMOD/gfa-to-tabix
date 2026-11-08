#!/usr/bin/env bash
# Genome-wide walk files in format 7 for hosting, with the writer the release check cloned (gfa-to-tabix 4.0.0, 1e698f4): GRCh38 from HPRC v2.1 GRCh38-referenced MC graph, CHM13 from its CHM13-referenced one, both GFAs left by genome3; verify7 on each
set -uo pipefail
cd ~/work/genome7
B=~/work/release/src/target/release/gfa-to-tabix
V=~/work/release/src/docs/departures/scripts/verify7.py
$B --version > version.txt 2>&1
git -C ~/work/release/src log --oneline -1 > commit.txt
cap() { systemd-run --user --scope -q -p MemoryMax=$1 -p MemorySwapMax=0 "${@:2}"; }
status=0
for g in grch38:GRCh38 chm13:CHM13; do
  in=${g%%:*}; ref=${g#*:}
  cap 60G /usr/bin/time -f "build $ref: %e s, %M KB peak" $B ~/work/genome3/$in.gfa --walks --refs $ref -o hprc-v2.1-mc-$in > build-$in.log 2>&1 || { status=1; echo "build $in FAILED" >> genome7.log; continue; }
  f=hprc-v2.1-mc-$in.$ref.walks.gz
  cap 40G /usr/bin/time -f "verify7 $ref: %e s, %M KB peak" python3 -I $V $f > verify7-$in.txt 2>&1 || { status=1; echo "verify7 $in FAILED" >> genome7.log; }
done
ls -l *.walks.gz* > sizes.txt
[ $status = 0 ] && echo PASSED > genome7.done || echo FAILED > genome7.done
