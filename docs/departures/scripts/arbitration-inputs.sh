#!/usr/bin/env bash
# Inputs for the format arbitration's builds, under ~/work/arb-format-opus/in:
# HPRC release 2 pggb chrY, HPRC v2.1 MC chr22 cut from the GRCh38 GBZ (as
# ~/work/mc22.sh did), and chr9, chr14 and chr22 cut from the CHM13 GBZ
set -uo pipefail
mkdir -p ~/work/arb-format-opus/in && cd ~/work/arb-format-opus/in
VG=~/bin/vg
S3=https://s3-us-west-2.amazonaws.com/human-pangenomics/pangenomes/freeze/release2
[ -s pggbY.gfa ] || { wget -q -O pggbY.gfa.zst $S3/pggb/gfas/by-chromosome/20251014_hprc25272.p98-k311.chrY.gfa.zst && zstd -q -d pggbY.gfa.zst -o pggbY.gfa && rm pggbY.gfa.zst; }
echo "pggbY $(date -u +%T)" >> inputs.log
for g in grch38 chm13; do
  [ -s $g.gbz ] || wget -q -O $g.gbz $S3/minigraph-cactus/v2.1/hprc-v2.1-mc-$g/hprc-v2.1-mc-$g.gbz
  echo "$g.gbz $(date -u +%T)" >> inputs.log
done
cut() {
  [ -s $1.gfa ] && return
  /usr/bin/time -f "chunk $1: %e s, %M KB" $VG chunk --gbz -x $2.gbz --contig $3 -b $1.chunk >> chunk.log 2>&1
  /usr/bin/time -f "convert $1: %e s, %M KB" $VG convert -f $1.chunk*.gbz > $1.gfa 2>> chunk.log
  rm -f $1.chunk*.gbz
  echo "$1 $(date -u +%T)" >> inputs.log
}
cut mc22 grch38 chr22
cut chm13-chr9 chm13 chr9
cut chm13-chr14 chm13 chr14
cut chm13-chr22 chm13 chr22
echo done > inputs.done
