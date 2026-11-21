#!/bin/bash
# Times graph-walks 9.0.0 cutting each window of windows.txt from the local copy of the hosted format 8 file, 4 haplotypes, budgets lifted, 3 runs
set -u
D=$(cd "$(dirname "$0")" && pwd)
export PATH=$HOME/.local/node/bin:$PATH
F=${WALKS:-$HOME/work/blocks/genome-5.0.0-hdr/hprc-v2.1-mc-grch38.GRCh38.walks.gz}
H=HG002#1,HG00733#1,NA19240#1,HG00097#1
cd "${GRAPH_WALKS_DIR:?a directory with @jbrowse/graph-walks 9.0.0 installed}"
nice -n 10 systemd-run --user --scope -q -p MemoryMax=16G -p MemorySwapMax=0 \
  node --expose-gc --max-old-space-size=12000 "$D/cut.mjs" "$F" "$1" 3 "$H" $(cat "$D/windows.txt")
