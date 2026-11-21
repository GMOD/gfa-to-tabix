#!/usr/bin/env bash
# After windows.sh, on ada: how long gfaidx and graph-walks take on the same windows of MC chr22 and pggb chrY (window-time.mjs), the cases interleaved, three runs each, each window timed only while the 1-minute load is under 3; for chr22 also from jbrowse.org's whole-genome file
set -uo pipefail
cd ~/work/gfaidx-compare
G=$PWD/dl/gfaidx-v2.3.2-linux-x86_64/gfaidx
R=$PWD/results
export PATH=~/.local/node/bin:$PATH
cap() { systemd-run --user --scope -q -p MemoryMax=$1 -p MemorySwapMax=0 nice -n 10 "${@:2}"; }
cat graph-walks.commit > $R/graph-walks.commit.txt
node --version >> $R/graph-walks.commit.txt
cap 16G node --max-old-space-size=8192 window-time.mjs graph-walks $R/mc22.windows.tsv 'GRCh38#0#chr22' $R/mc22.times.tsv \
  --walks out/mc22.GRCh38.walks.gz --walks-bases out/mc22.seq.GRCh38.walks.gz \
  --http https://jbrowse.org/demos/hprc/hprc-v2.1-mc-grch38-f8.GRCh38.walks.gz \
  --gfaidx $G out/mc22.gfaidx.gfa.gz chr22 --reference GRCh38 > $R/mc22.times.log 2>&1
cap 16G node --max-old-space-size=8192 window-time.mjs graph-walks $R/pggbY.windows.tsv 'GRCh38#0#chrY' $R/pggbY.times.tsv \
  --walks out/pggbY.GRCh38.walks.gz --walks-bases out/pggbY.seq.GRCh38.walks.gz \
  --gfaidx $G out/pggbY.gfaidx.gfa.gz 'GRCh38#0#chrY' > $R/pggbY.times.log 2>&1
echo done > times.done
