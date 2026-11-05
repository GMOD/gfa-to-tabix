#!/usr/bin/env bash
# Release check for gfa-to-tabix 3.0 (main cc797cc): MC chr22 and pggb chrY
# built by the release writer and audited
set -uo pipefail
mkdir -p ~/work/rel3 && cd ~/work/rel3
IN=~/work/arb-format-opus/in
S=~/src/gfa-to-tabix-rel3
(cd $S && cargo build --release -q) > build-binary.log 2>&1 || { echo FAILED > rel3.done; exit 1; }
B=$S/target/release/gfa-to-tabix
A=$S/docs/departures/scripts/audit6.py
cap() { systemd-run --user --scope -q -p MemoryMax=$1 -p MemorySwapMax=0 "${@:2}"; }
waitmem() { while [ "$(free -g | awk '/^Mem:/ {print $7}')" -lt $1 ]; do sleep 60; done; }
waitmem 30
cap 20G /usr/bin/time -f "mc22: %e s, %M KB peak" $B $IN/mc22.gfa --walks --refs GRCh38 -o mc22 > mc22.build.log 2>&1
waitmem 30
cap 30G /usr/bin/time -f "audit mc22: %e s, %M KB peak" python3 -I $A mc22.GRCh38.walks.bed.gz --top 3 > mc22.audit.txt 2>&1
waitmem 30
cap 20G /usr/bin/time -f "pggbY: %e s, %M KB peak" $B $IN/pggbY.gfa --walks --refs GRCh38 -o pggbY > pggbY.build.log 2>&1
waitmem 40
cap 40G /usr/bin/time -f "audit pggbY: %e s, %M KB peak" python3 -I $A pggbY.GRCh38.walks.bed.gz --top 3 > pggbY.audit.txt 2>&1
ls -l *.walks.bed.gz > sizes.txt
echo done > rel3.done
