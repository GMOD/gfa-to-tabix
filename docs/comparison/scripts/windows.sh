#!/usr/bin/env bash
# After build.sh, on ada: what a 64 kb window reads from each tool's files of MC chr22 and pggb chrY (windows.py), with gfaidx's default --mode all and again with --haplotype_gap 10kb, and walks-truth.py cost over every window of the walk files and of the whole-genome format 8 files
set -uo pipefail
cd ~/work/gfaidx-compare
G=$PWD/dl/gfaidx-v2.3.2-linux-x86_64/gfaidx
R=$PWD/results
GENOME=~/work/blocks/genome-5.0.0
mkdir -p mnt tmp
rm -f tmp/pagelog.txt
venv/bin/python pagelog.py $PWD/out $PWD/mnt $PWD/tmp/pagelog.txt > pagelog.out 2>&1 &
sleep 2
cap() { systemd-run --user --scope -q -p MemoryMax=$1 -p MemorySwapMax=0 nice -n 10 "${@:2}"; }
window() {
  cap 24G python3 windows.py $G out/$1.gfaidx.gfa.gz "$2" out/$1.GRCh38.walks.gz out/$1.seq.GRCh38.walks.gz "$3" $R/$1$4 \
    --windows 40 --tmp tmp --mount mnt/$1.gfaidx.gfa.gz --pagelog tmp/pagelog.txt "${@:5}" > $R/$1$4.windows.log 2>&1
}
GAP=(--gfaidx-arg=--haplotype_gap --gfaidx-arg=10kb)
window mc22 chr22 'GRCh38#0#chr22' '' --reference GRCh38
window pggbY 'GRCh38#0#chrY' 'GRCh38#0#chrY' ''
window mc22 chr22 'GRCh38#0#chr22' .gap --reference GRCh38 "${GAP[@]}"
window pggbY 'GRCh38#0#chrY' 'GRCh38#0#chrY' .gap "${GAP[@]}"
fusermount -u mnt
for g in mc22 pggbY; do
  cap 8G python3 -I src/scripts/walks-truth.py cost out/$g.GRCh38.walks.gz > $R/$g.cost.txt 2>&1
done
cat $GENOME/commit.txt $GENOME/version.txt > $R/genome8.commit.txt
stat --printf '%n\t%s\n' $GENOME/*.walks.gz $GENOME/*.walks.gz.idx | sed "s|^$GENOME/||" > $R/genome8.sizes.tsv
for g in grch38 chm13; do
  cp $GENOME/build-$g.log $R/genome8.build-$g.log
  cap 8G python3 -I src/scripts/walks-truth.py cost $GENOME/hprc-v2.1-mc-$g.*.walks.gz > $R/genome8.cost-$g.txt 2>&1
done
echo done > windows.done
