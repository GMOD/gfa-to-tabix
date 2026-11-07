#!/bin/bash
cd ~/work/reshape/out
S=~/work/reshape/r1/docs/departures/scripts
for f in r1.pggbY r1.mc22; do
  (ulimit -v 60000000; nice -n 10 /usr/bin/time -f "%e s %M KB" python3 -I $S/verify7.py $f.GRCh38.walks.gz > $f.verify.txt 2>&1)
  (ulimit -v 60000000; nice -n 10 /usr/bin/time -f "%e s %M KB" python3 -I $S/claims7.py $f.GRCh38.walks.gz > $f.claims.txt 2>&1)
done
echo done > checks.done
