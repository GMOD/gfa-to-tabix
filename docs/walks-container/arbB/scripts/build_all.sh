#!/bin/bash
# Build every candidate file from the shipped format 6 files, in parallel.
set -u
D=/tmp/claude-1001/-home-cdiesh-src-gfa-to-tabix/95217c34-cd76-4f06-8705-ae30877df61b/scratchpad/format-review/arbB
S=$D/scripts
cd $D/data

build() {
  local dir=$1 name=$2 mode=$3 align=$4 index=$5 depcut=$6 src=$7
  (
    bgzip -dc $dir/$src | python3 -I $S/refile.py $mode $align $dir/$name.bed.gz $depcut \
      && if [ "$index" = csi ]; then tabix -C -m 16 -p bed $dir/$name.bed.gz; else tabix -p bed $dir/$name.bed.gz; fi \
      && echo "$dir/$name ok" || echo "$dir/$name FAILED"
  ) &
}

offset() {
  local dir=$1 src=$2
  (
    bgzip -dc $dir/$src | python3 -I $S/build_offset.py $dir/o \
      && sort -k1,1 -k2,2n -k3,3n $dir/o.departures.bed | bgzip -c > $dir/o.departures.bed.gz \
      && tabix -p bed $dir/o.departures.bed.gz \
      && gzip -kf $dir/o.walks.idx \
      && rm $dir/o.departures.bed \
      && echo "$dir/o ok" || echo "$dir/o FAILED"
  ) &
}

build mc22 f6p 1bp 1 tbi 26,23,20,17 f6.bed.gz
build mc22 t64 span 1 csi 28,25,22,19,16 f6.bed.gz
build mc22 t16 span 1 tbi 26,23,20,17 f6c16.bed.gz
offset mc22 f6.bed.gz
build pggbY f6p 1bp 1 tbi 26,23,20,17 f6.bed.gz
build pggbY t64 span 1 csi 28,25,22,19,16 f6.bed.gz
offset pggbY f6.bed.gz
wait
ls -la mc22 pggbY
echo ALL DONE
