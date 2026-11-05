#!/bin/bash
W=$HOME/src/jb2hubs/website/pangenome-config/checkForms/hprc.windows.tsv
for d in base graph-walks; do for cfg in "50 1" "auto 0" "50 0"; do
  set -- $cfg; tag=$d-f$1-k$2
  (cd $HOME/src/arb-forms-opus/$d && GATE=$HOME/src/arb-forms-opus/gatecache WINDOWS=$W FLOOR=$1 KEEP=$2 OUT=$HOME/src/arb-forms-opus/gate/$tag.jsonl CHECK=$HOME/src/arb-forms-opus/gate/$tag.check.txt npx vitest run src/arb/gateforms.test.ts > $HOME/src/arb-forms-opus/gate/$tag.log 2>&1)
  echo "$tag $(tail -1 $HOME/src/arb-forms-opus/gate/$tag.check.txt)"
done; done > $HOME/src/arb-forms-opus/gate/summary.txt
