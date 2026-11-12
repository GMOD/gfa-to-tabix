#!/usr/bin/env bash
# Genome-wide walk files in format 8, from the graphs the hosted format 7
# files were built from: each GBZ converted to GFA and built with the
# format 8 writer; then ADR 0012's comparison with the hosted file
# (against-format7.py): every unit but blocks units and tables has its
# bytes, the header but for its format tag and each abridged tile but for
# its abridged rows, and each hosted abridged row is recomputed from the
# format 8 rows; and every blocks row read as an
# unloaded reader does and checked against its piece's detail row
# (expand7.py). One genome at a time, the GFA removed after its build.
set -uo pipefail
mkdir -p ~/work/blocks/genome && cd ~/work/blocks/genome
IN=~/work/arb-format-opus/in
B=~/work/blocks/src/target/release/gfa-to-tabix
S=~/work/blocks/src
$B --version > version.txt 2>&1
git -C ~/work/blocks/src log --oneline -1 > commit.txt
cap() { systemd-run --user --scope -q -p MemoryMax=$1 -p MemorySwapMax=0 nice -n 10 "${@:2}"; }
waitmem() { while [ "$(free -g | awk '/^Mem:/ {print $7}')" -lt $1 ]; do sleep 60; done; }
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
  cap 16G /usr/bin/time -f "against-format7 $in: %e s, %M KB peak" python3 -I $S/docs/walks-container/abridged/against-format7.py $f ~/work/genome7/$f > against-format7-$in.txt 2>&1
  echo "$in against format 7 exit $?: $(grep 'lines that differ' against-format7-$in.txt)" >> genome.log
  cap 16G /usr/bin/time -f "expand7 $in: %e s, %M KB peak" python3 -I $S/docs/departures/scripts/expand7.py $f > expand7-$in.txt 2>&1
  echo "$in expand7 exit $?: $(grep '^expand7:' expand7-$in.txt)" >> genome.log
  zcat $f | awk -F'\t' '$1=="#entry" && $5=="blocks" {print $2, $6, $8}' > blocks-units-$in.txt
  echo "$in done" >> genome.log
done
echo done > genome.done
