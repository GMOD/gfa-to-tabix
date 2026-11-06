#!/bin/bash
# The whole real-data check on the writer's format 7 files with ownTiles,
# into res-o/, against 5.0.2, 5.0.2 fixed, and graph-walks 6 before ownTiles
# (gw6old, a6269e4):
# cut comparison, classification of differences, the 5.0.2-attach-extent
# variant on those still differing, and the byte measurement.
cd ~/work/impl-reader
export S7=../impl-writer/own.{d}.GRCh38.walks.gz
d=$1
R=res-o
mkdir -p $R logs-o
run() { systemd-run --user --scope -q -p MemoryMax=20G -p MemorySwapMax=0 node --max-old-space-size=16000 "$@"; }
pick() { python3 -c "
import json,sys
for l in open(sys.argv[1]):
    r=json.loads(l)
    if not all(r[k][\"identical\"] for k in sys.argv[2:]) if \"error\" not in r else True:
        print(json.dumps({\"size\":r[\"size\"],\"i\":r[\"i\"],\"start\":r[\"start\"],\"end\":r[\"start\"]+r[\"size\"],\"tag\":r[\"tag\"]}))
" "$@"; }
for w in random96 targets0; do
  s=${w%96}; s=${s%0}
  run cut7check.mjs $d ../arb-arbA/win/$d.$w.jsonl $R/$d.$w.jsonl >> logs-o/$d.log 2>&1
  pick $R/$d.$w.jsonl vs5 vsFixed vsOld6 > $R/$d.$s.diffwin.jsonl
  run diff7.mjs $d $R/$d.$s.diffwin.jsonl $R/d.$d.$s.jsonl >> logs-o/$d.log 2>&1
  pick $R/d.$d.$s.jsonl vsFixed vsFixed vsFixed > $R/$d.$s.fixeddiff.jsonl
  run diff7v.mjs $d $R/$d.$s.fixeddiff.jsonl $R/dv.$d.$s.jsonl >> logs-o/$d.log 2>&1
done
systemd-run --user --scope -q -p MemoryMax=24G -p MemorySwapMax=0 node --max-old-space-size=20000 measure7.mjs $d $R/m7.$d.jsonl >> logs-o/$d.log 2>&1
echo done >> logs-o/$d.log
