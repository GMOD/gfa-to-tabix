#!/usr/bin/env bash
# The reader's part of ADR 0012's acceptance runs, again at graph-walks
# 730e752, the head released as 7.0.0, on the same bytes 4b14ee3 read: the
# 5.0.0 genome files the writer at 9e46a46 built (the hosted -f8 bytes) and
# the pggb chrY GRCh38 rebuild of 4b14ee3's run. One at a time, for clean
# times: release-check; the worst windows' cuts of every haplotype,
# unloaded and loaded, against graph-walks 6.2 on the hosted format 7 file
# (genome-accept/cost.sh). Then together: the 4 MB read scan
# (genome-accept/read-scan.ts) and the equality harness on pggb chrY GRCh38
# and on both genome files, as 0350375/run.sh ran it. The writer's runs
# (against-format7.py, byte identity across thread counts, the pggb chrY
# rebuild and header diff) read nothing through graph-walks and are not
# run again
set -u
export PATH=$HOME/.local/node/bin:$PATH
A=$HOME/work/blocks/accept-5.0.0
F=$A/730e752
G=$HOME/work/blocks/genome-5.0.0-hdr
H=$HOME/work/genome7
R=$HOME/work/review-gw7/gw-730e752
V=$HOME/work/blocks/graph-walks-6.2
Y=$A/4b14ee3/pggbY/pggbY.GRCh38.walks.gz
cap() { m=$1; shift; systemd-run --user --scope -q -p MemoryMax="$m" -p MemorySwapMax=0 nice -n 10 /usr/bin/time -f "%e s, %M KB peak, exit %x" "$@"; }
log() { echo "$(date '+%F %T') $*" >> $F/run.log; }
name() { case $1 in grch38) echo hprc-v2.1-mc-grch38.GRCh38.walks.gz ;; chm13) echo hprc-v2.1-mc-chm13.CHM13.walks.gz ;; esac; }
cd $F
log start graph-walks $(git -C $R rev-parse HEAD)
(cd $G && nice -n 10 sha256sum $(name grch38) $(name chm13) && cd $(dirname $Y) && nice -n 10 sha256sum $(basename $Y)) > $F/sha256.txt 2>&1
log "sha256: $(awk '{printf "%s %.12s; ", $2, $1}' $F/sha256.txt)"
cp $A/4b14ee3/cut-cost.ts $F/cut-cost.ts
sed "s#/home/cdiesh/work/blocks/graph-walks-blocks#$R#" $HOME/work/blocks/genome-accept/read-scan.ts > $F/read-scan.ts

for g in grch38 chm13; do
  (cd $R && WALKS=$G/$(name $g) cap 8G node_modules/.bin/vitest run --config release-check/vitest.config.ts > $F/release-check-$g.txt 2>&1)
  log "release-check $g exit $?"
done

for spec in grch38:GRCh38:chr2:91409000:91410000 chm13:CHM13:chr2:92078080:92079080; do
  IFS=: read in ref chr from to <<< "$spec"
  o=$F/cost-$in.txt
  : > $o
  for mode in unloaded loaded; do
    cap 16G node $F/cut-cost.ts $R $G/$(name $in) $ref#0#$chr $from $to $mode 3 >> $o 2>&1
    log "cost $in gw-730e752 $mode exit $?"
  done
  for mode in unloaded loaded; do
    cap 16G node $F/cut-cost.ts $V $H/$(name $in) $ref#0#$chr $from $to $mode 3 >> $o 2>&1
    log "cost $in graph-walks-6.2 $mode exit $?"
  done
done

for g in grch38 chm13; do
  (cap 8G node $F/read-scan.ts $G/$(name $g) > $F/read-scan-$g.txt 2>&1; log "read-scan $g exit $?") &
done
cd $R
(cap 10G node --max-old-space-size=6000 scripts/blocks-equality.ts $Y --windows 24 > $F/eq-pggbY.out 2> $F/eq-pggbY.err; rc=$?; log "equality pggbY exit $rc: $(tail -1 $F/eq-pggbY.err)") &
for g in grch38 chm13; do
  for i in 0 1; do
    from=$((500 * i)) to=$((500 * (i + 1)))
    (cap 10G node --max-old-space-size=8000 scripts/blocks-equality.ts $G/$(name $g) --windows $to --from $from --seed 1 --haplotypes 64 > $F/eq-$g.$i.out 2> $F/eq-$g.$i.err; rc=$?; log "equality $g.$i exit $rc: $(tail -1 $F/eq-$g.$i.err)") &
  done
done
wait
log done
touch $F/done
