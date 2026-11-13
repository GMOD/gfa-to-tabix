#!/usr/bin/env bash
# Reader acceptance on the 5.0.0 genome files with graph-walks 8e3d397:
# release-check, real reads against bytesFor, and the equality harness
set -u
export PATH=$HOME/.local/node/bin:$PATH
A=$HOME/work/blocks/accept-5.0.0
G=$HOME/work/blocks/genome-5.0.0
R=$HOME/work/blocks/gw-8e3d397
cap() { m=$1; shift; systemd-run --user --scope -q -p MemoryMax="$m" -p MemorySwapMax=0 nice -n 10 /usr/bin/time -f "%e s, %M KB peak, exit %x" "$@"; }
log() { echo "$(date '+%F %T') $*" >> $A/run.log; }
file() { case $1 in grch38) echo $G/hprc-v2.1-mc-grch38.GRCh38.walks.gz ;; chm13) echo $G/hprc-v2.1-mc-chm13.CHM13.walks.gz ;; esac; }
mkdir -p $A/out
cd $A
log start
for g in grch38 chm13; do
  (cd $R && WALKS=$(file $g) cap 8G node_modules/.bin/vitest run --config release-check/vitest.config.ts > $A/out/release-check-$g.txt 2>&1)
  log "release-check $g exit $?"
done
sed "s#~/work/blocks/graph-walks-blocks#$R#" $HOME/work/blocks/genome-accept/read-scan.ts > $A/read-scan.ts
ln -sf $R/node_modules $A/node_modules
for g in grch38 chm13; do
  cap 8G node $A/read-scan.ts $(file $g) > $A/out/read-scan-$g.txt 2>&1
  log "read-scan $g exit $?"
done
for g in grch38 chm13; do
  for i in 0 1; do
    from=$((500 * i)) to=$((500 * (i + 1)))
    (cd $R && cap 10G node --max-old-space-size=8000 scripts/blocks-equality.ts $(file $g) --windows $to --from $from --seed 1 --haplotypes 64 > $A/out/eq-$g.$i.out 2> $A/out/eq-$g.$i.err; log "equality $g.$i exit $?") &
  done
done
wait
log done
