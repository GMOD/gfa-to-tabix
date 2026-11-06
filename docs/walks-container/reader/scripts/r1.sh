#!/bin/bash
# pggb chrY targeted windows with the R1 fix: vsOld6 here is graph-walks 6 at
# 17ed0a6 (gw6prev), so it isolates the fix; then the differing windows
# classified
cd ~/work/impl-reader
export S7=../impl-writer/own.{d}.GRCh38.walks.gz
R=res-r1; mkdir -p $R
run() { systemd-run --user --scope -q -p MemoryMax=20G -p MemorySwapMax=0 node --max-old-space-size=16000 "$@"; }
run cut7checkp.mjs pggbY ../arb-arbA/win/pggbY.targets0.jsonl $R/pggbY.targets0.jsonl >> logs-o/r1.log 2>&1
python3 -c "
import json
for l in open(\"$R/pggbY.targets0.jsonl\"):
    r=json.loads(l)
    if not all(r[k][\"identical\"] for k in (\"vs5\",\"vsFixed\",\"vsOld6\")):
        print(json.dumps({\"size\":r[\"size\"],\"i\":r[\"i\"],\"start\":r[\"start\"],\"end\":r[\"start\"]+r[\"size\"],\"tag\":r[\"tag\"]}))
" > $R/pggbY.targets.diffwin.jsonl
run diff7p.mjs pggbY $R/pggbY.targets.diffwin.jsonl $R/d.pggbY.targets.jsonl >> logs-o/r1.log 2>&1
echo done >> logs-o/r1.log
