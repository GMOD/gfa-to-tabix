#!/usr/bin/env bash
# Genome-wide walk files with blocks units, from the graphs the hosted
# format 7 files were built from: each GBZ converted to GFA, built with the
# blocks-unit writer, its units other than blocks and tables compared with
# the hosted file's, and every blocks row compared with graph-walks' decode
# of its piece's detail row (blocks-check.mjs). One genome at a time, the
# GFA removed after its build.
set -uo pipefail
mkdir -p ~/work/blocks/genome && cd ~/work/blocks/genome
IN=~/work/arb-format-opus/in
B=~/work/blocks/src/target/release/gfa-to-tabix
N=~/.local/node/bin/node
$B --version > version.txt 2>&1
git -C ~/work/blocks/src log --oneline -1 > commit.txt
cap() { systemd-run --user --scope -q -p MemoryMax=$1 -p MemorySwapMax=0 nice -n 10 "${@:2}"; }
waitmem() { while [ "$(free -g | awk '/^Mem:/ {print $7}')" -lt $1 ]; do sleep 60; done; }
strip() { zcat "$1" | awk -F'\t' '$1=="#unit"{skip=($5=="blocks"||$5=="table")} !skip' | md5sum | cut -d' ' -f1; }
for g in chm13:CHM13 grch38:GRCh38; do
  in=${g%%:*}; ref=${g#*:}
  f=hprc-v2.1-mc-$in.$ref.walks.gz
  if [ ! -s $f ]; then
    [ "$(df --output=avail -BG ~ | tail -1 | tr -dc 0-9)" -gt 450 ] || { echo "$in: under 450G free" >> genome.log; continue; }
    waitmem 50
    cap 60G /usr/bin/time -f "convert $in: %e s, %M KB peak" /home/cdiesh/bin/vg convert -f $IN/$in.gbz > $in.gfa 2> convert-$in.log || { echo "convert $in FAILED" >> genome.log; rm -f $in.gfa; continue; }
    ls -l $in.gfa >> genome.log
    waitmem 30
    cap 40G /usr/bin/time -f "build $ref: %e s, %M KB peak" $B $in.gfa --walks --refs $ref -o hprc-v2.1-mc-$in > build-$in.log 2>&1 || { echo "build $in FAILED" >> genome.log; rm -f $in.gfa $f $f.idx; continue; }
    rm -f $in.gfa
  fi
  ls -l $f $f.idx >> genome.log
  echo "$in units but blocks and tables: new $(strip $f) hosted $(strip ~/work/genome7/$f)" >> genome.log
  cap 16G /usr/bin/time -f "blocks-check $in: %e s, %M KB peak" $N ../blocks-check.mjs $PWD/$f > blocks-check-$in.json 2> blocks-check-$in.err
  echo "$in blocks-check exit $?" >> genome.log
  zcat $f | awk -F'\t' '$1=="#entry" && $5=="blocks" {print $2, $6, $8}' > blocks-units-$in.txt
  echo "$in done" >> genome.log
done
echo done > genome.done
