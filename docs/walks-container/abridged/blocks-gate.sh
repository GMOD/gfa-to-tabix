#!/usr/bin/env bash
# Gate of ADR 0012: blocks-gate.ts, bundled with esbuild to gate.mjs, over every
# abridged tile (abridged-tiles.py, here specs.py) of both hosted walk files on ada,
# from ~/work/loose1111/gate. Each tile's line is in blocks-gate.<ref>.jsonl
set -uo pipefail
cd ~/work/loose1111/gate
N=~/.local/node/bin/node
for f in hprc-v2.1-mc-grch38.GRCh38 hprc-v2.1-mc-chm13.CHM13; do
  (
    p=~/work/genome7/$f.walks.gz
    python3 -I specs.py "$p" > $f.specs
    rm -f $f.jsonl
    split -l 50 -d $f.specs $f.part.
    for part in $f.part.*; do
      systemd-run --user --scope -q -p MemoryMax=6G -p MemorySwapMax=0 \
        nice -n 10 $N gate.mjs "$p" $f.jsonl $(cat $part) 2>>$f.err || echo "$part FAILED" >> $f.err
    done
    echo "$f: $(wc -l < $f.specs) tiles, $(wc -l < $f.jsonl) measured" >> summary.txt
  ) &
done
wait
touch done
