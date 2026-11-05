#!/bin/bash
cd $HOME/src/arb-forms-opus
for d in base graph-walks; do for k in 0 1; do for f in auto 50 1000 10000; do
  rm -f r28/$d-k$k-f$f.txt
  (cd $d && KEEP=$k FLOORS=$f WINS="$(cat ../wins.txt)" OUT=../r28/$d-k$k-f$f.txt npx vitest run src/arb/check.test.ts > /dev/null 2>&1)
  echo "$d keep $k floor $f: $(tail -1 r28/$d-k$k-f$f.txt)"
done; done; done > r28/summary.txt
./rungate.sh
