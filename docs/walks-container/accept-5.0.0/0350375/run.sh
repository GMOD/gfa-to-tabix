#!/usr/bin/env bash
# The fixed reader (loaded-links, 0350375): its suite, then the equality
# harness on both 5.0.0 genome files as accept-5.0.0/run.sh ran it, and on
# pggb chrY as attach-breakpoints/queue2b.sh ran it
set -u
export PATH=$HOME/.local/node/bin:$PATH
A=$HOME/work/blocks/accept-5.0.0
F=$A/fix
G=$HOME/work/blocks/genome-5.0.0
R=$HOME/work/blocks/gw-loaded-links
Y=$HOME/work/compare-rtp/pggbY.CHM13.walks.gz
cap() { m=$1; shift; systemd-run --user --scope -q -p MemoryMax="$m" -p MemorySwapMax=0 nice -n 10 /usr/bin/time -f "%e s, %M KB peak, exit %x" "$@"; }
log() { echo "$(date '+%F %T') $*" >> $F/run.log; }
file() { case $1 in grch38) echo $G/hprc-v2.1-mc-grch38.GRCh38.walks.gz ;; chm13) echo $G/hprc-v2.1-mc-chm13.CHM13.walks.gz ;; esac; }
cd $R
log start $(git log --oneline -1)
cap 8G node_modules/.bin/vitest run > $F/suite.txt 2>&1; log "suite exit $?"
cap 8G node_modules/.bin/tsrs --noEmit > $F/typecheck.txt 2>&1; log "typecheck exit $?"
cap 4G node_modules/.bin/oxlint --deny-warnings --report-unused-disable-directives > $F/lint.txt 2>&1; log "lint exit $?"
cap 4G node_modules/.bin/oxfmt --check > $F/format.txt 2>&1; log "format exit $?"
for g in grch38 chm13; do
  WALKS=$(file $g) cap 8G node_modules/.bin/vitest run --config release-check/vitest.config.ts > $F/release-check-$g.txt 2>&1
  log "release-check $g exit $?"
done
for g in grch38 chm13; do
  for i in 0 1; do
    from=$((500 * i)) to=$((500 * (i + 1)))
    (cap 10G node --max-old-space-size=8000 scripts/blocks-equality.ts $(file $g) --windows $to --from $from --seed 1 --haplotypes 64 > $F/eq-$g.$i.out 2> $F/eq-$g.$i.err; log "equality $g.$i exit $?") &
  done
done
(cap 10G node --max-old-space-size=6000 scripts/blocks-equality.ts $Y --windows 24 > $F/eq-pggbY.out 2> $F/eq-pggbY.err; log "equality pggbY exit $?") &
wait
log done
touch $F/done
