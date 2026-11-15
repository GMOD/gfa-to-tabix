#!/usr/bin/env bash
# ADR 0012's acceptance runs at the release heads: graph-walks 4b14ee3 on
# the 5.0.0 genome files the writer at 9e46a46 built (the hosted -f8
# bytes). One at a time, for clean times: release-check; the worst
# windows' cuts of every haplotype, unloaded and loaded, against
# graph-walks 6.2 on the hosted format 7 file (genome-accept/cost.sh);
# each genome file against the hosted format 7 file (against-format7.py,
# as abridged/genome-blocks.sh ran it); MC chr22 built on all cores and on
# one, compared byte for byte; pggb chrY rebuilt on GRCh38 by the same
# writer and compared with the 5.0.0 build by walks-header-diff.py. Then
# together: the 4 MB read scan (genome-accept/read-scan.ts) and the
# equality harness on pggb chrY GRCh38 and on both genome files, as
# 0350375/run.sh ran it
set -u
export PATH=$HOME/.local/node/bin:$PATH
A=$HOME/work/blocks/accept-5.0.0
F=$A/4b14ee3
G=$HOME/work/blocks/genome-5.0.0-hdr
H=$HOME/work/genome7
R=$HOME/work/review-gw7/gw-4b14ee3
V=$HOME/work/blocks/graph-walks-6.2
W=$G/src/target/release/gfa-to-tabix
IN=$HOME/work/arb-format-opus/in
Y5=$HOME/work/blocks/pggbY-5.0.0/pggbY.GRCh38.walks.gz
Y=$F/pggbY/pggbY.GRCh38.walks.gz
cap() { m=$1; shift; systemd-run --user --scope -q -p MemoryMax="$m" -p MemorySwapMax=0 nice -n 10 /usr/bin/time -f "%e s, %M KB peak, exit %x" "$@"; }
log() { echo "$(date '+%F %T') $*" >> $F/run.log; }
name() { case $1 in grch38) echo hprc-v2.1-mc-grch38.GRCh38.walks.gz ;; chm13) echo hprc-v2.1-mc-chm13.CHM13.walks.gz ;; esac; }
cd $F
log start graph-walks $(git -C $R rev-parse HEAD), $($W --version) at $(git -C $G/src rev-parse HEAD)
cp $HOME/work/blocks/genome-accept/cut-cost.ts $F/cut-cost.ts
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
    log "cost $in gw-4b14ee3 $mode exit $?"
  done
  for mode in unloaded loaded; do
    cap 16G node $F/cut-cost.ts $V $H/$(name $in) $ref#0#$chr $from $to $mode 3 >> $o 2>&1
    log "cost $in graph-walks-6.2 $mode exit $?"
  done
done

for g in grch38 chm13; do
  cap 16G python3 -I $G/src/docs/walks-container/abridged/against-format7.py $G/$(name $g) $H/$(name $g) > $F/against-format7-$g.txt 2>&1
  rc=$?
  log "against-format7 $g exit $rc: $(grep 'lines that differ' $F/against-format7-$g.txt)"
done

mkdir -p $F/threads/all $F/threads/one
(cd $F/threads/all && cap 24G $W $IN/mc22.gfa --walks --refs GRCh38 -o mc22 > ../all.log 2>&1)
rc=$?
log "chr22 build, all cores ($(nproc)) exit $rc"
(cd $F/threads/one && cap 24G taskset -c 0 $W $IN/mc22.gfa --walks --refs GRCh38 -o mc22 > ../one.log 2>&1)
rc=$?
log "chr22 build, one core ($(taskset -c 0 nproc)) exit $rc"
{
  echo "$($W --version), $IN/mc22.gfa --walks --refs GRCh38: all $(nproc) cores, then under taskset -c 0 ($(taskset -c 0 nproc) core)"
  (cd $F/threads && sha256sum all/* one/* && ls -l all one)
  for f in $(ls $F/threads/all); do cmp $F/threads/all/$f $F/threads/one/$f && echo "$f: identical"; done
  echo "all build: $(tail -1 $F/threads/all.log)"
  echo "one build: $(tail -1 $F/threads/one.log)"
} > $F/threads-chr22.txt 2>&1
log "threads: $(grep -c identical $F/threads-chr22.txt) of $(ls $F/threads/all | wc -l) files identical"

mkdir -p $F/pggbY
(cd $F/pggbY && cap 16G $W $IN/pggbY.gfa --walks --refs GRCh38 -o pggbY > build.GRCh38.log 2>&1)
log "pggbY GRCh38 build exit $?"
cap 4G python3 -I $G/walks-header-diff.py $Y5 $Y > $F/pggbY-header-diff.txt 2>&1
log "pggbY header diff exit $?"

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
