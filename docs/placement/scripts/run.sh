#!/bin/sh
# run.sh NAME INDEX WALKS REFSEQ WINDOWS [MODES]  -> out/NAME.jsonl
set -e
cd "$(dirname "$0")"
mkdir -p out
node --max-old-space-size=8000 crux.mjs --graph "$1" --index "$2" --walks "$3" --ref "$4" \
  --windows "$5" --out "out/$1.jsonl" --modes "${6:-hap8,hap8rows,all,allrows}" 2> "out/$1.log"
