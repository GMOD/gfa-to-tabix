#!/usr/bin/env bash
# Builds pggb chrY in walk format 8 for one reference, at the default options.
# Usage: build.sh REF CAP
set -uo pipefail
cd ~/work/blocks/pggbY
REF=$1 CAP=$2
B=~/work/blocks/src/target/release/gfa-to-tabix
G=~/work/arb-format-opus/in/pggbY.gfa
free -g > build.$REF.free.txt
systemd-run --user --scope -q -p MemoryMax=$CAP -p MemorySwapMax=0 \
  nice -n 10 /usr/bin/time -v $B $G --walks --refs $REF -o pggbY > build.$REF.log 2>&1
echo $? > build.$REF.rc
ls -l pggbY.$REF.walks.gz pggbY.$REF.walks.gz.idx >> build.$REF.log 2>&1
