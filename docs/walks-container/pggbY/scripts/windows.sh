#!/usr/bin/env bash
# Cuts each window of a list with graph-walks' format 8 branch (the snapshot
# in gw/), one node process per window, each capped, and logs its metrics.
# Usage: windows.sh FILE LIST OUT CAP [win.ts flags...]
#   LIST: label<TAB>seq:start-end per line
cd ~/work/blocks/pggbY
FILE=$1 LIST=$2 OUT=$3 CAP=$4
shift 4
: > $OUT.log
while IFS=$'\t' read -r label at; do
  echo "== $label $at $(date +%T) $(free -g | awk '/Mem:/{print "avail", $7}')" >> $OUT.log
  systemd-run --user --scope -q -p MemoryMax=$CAP -p MemorySwapMax=0 \
    nice -n 10 /usr/bin/time -f "TIME %e s, %M KB peak, exit %x" \
    ~/.local/node/bin/node --max-old-space-size=14000 gw/scripts/win.ts $FILE --at "$at" --label "$label" "$@" \
    >> $OUT.log 2>&1 < /dev/null
done < $LIST
echo DONE >> $OUT.log
