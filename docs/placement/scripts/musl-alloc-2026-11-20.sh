#!/usr/bin/env bash
# The runs of docs/placement/musl-alloc-pggb-chrY.txt and
# docs/placement/musl-alloc-mc22-walks.txt: builds of one source, the cargo
# build (glibc), the musl build as the release workflow makes it, and musl
# builds with mimalloc or jemalloc as their allocator, interleaved three rounds
# on each input, each run waiting for the 1-minute load to fall below 3, and
# every output file's sha256 recorded.
# bin/glibc is 22bf1de built by cargo build --release --locked, where mimalloc is
# not compiled in. bin/musl is cfbd1a9, bin/mimalloc 22bf1de (mimalloc 0.1.52)
# and bin/jemalloc cfbd1a9 with tikv-jemallocator 0.7.0 wired as in Cargo.toml,
# each built by cargo build --release --locked --target x86_64-unknown-linux-musl
# with musl 1.2.4's musl-gcc on PATH, as the release workflow does with apt's
# musl-tools.
# Run from ~/work/musl-alloc on ada with the binaries in bin/:
#   bash run.sh set1 glibc musl mimalloc
#   bash run.sh set2 glibc musl mimalloc jemalloc
set -uo pipefail
cd ~/work/musl-alloc
set=$1
shift
Y=~/work/scratch/graph-repro/data/pggb/chrY.gfa
M=~/work/perf-1119/out/mc22.gfa.gz
mkdir -p $set/out
cd $set
rm -f out/* chrY.time.txt mc22.time.txt sums.txt done
settle() {
  while [ "$(cut -d. -f1 /proc/loadavg)" -ge 3 ]; do sleep 20; done
  echo "load before: $(cut -d" " -f1-3 /proc/loadavg)" >> "$1"
}
record() {
  (cd out && for o in $1.$2.*; do [ "${o##*.}" = log ] || sha256sum "$o"; done \
    | sed "s/  $1\.$2\./  $1./; s/^/$2 round $3 /") >> sums.txt
}
cat $Y $M > /dev/null
for f in chrY mc22; do
  G=$Y; [ $f = mc22 ] && G=$M
  echo "input: $(sha256sum < $G | cut -c1-16) $(stat -c %s $G) bytes" >> $f.time.txt
done
for round in 1 2 3; do
  for v in "$@"; do
    settle chrY.time.txt
    systemd-run --user --scope -q -p MemoryMax=20G -p MemorySwapMax=0 \
      /usr/bin/time -f "$v round $round: %e s wall, %U s user, %S s system, %M KB peak" -a -o chrY.time.txt \
      nice -n 10 ../bin/$v $Y --reference GRCh38 -o out/chrY.$v > out/chrY.$v.log 2>&1
    record chrY $v $round
  done
done
for round in 1 2 3; do
  for v in "$@"; do
    settle mc22.time.txt
    /usr/bin/time -f "$v round $round: %e s wall, %U s user, %S s system, %M KB peak" -a -o mc22.time.txt \
      nice -n 10 ../bin/$v $M --walks --refs GRCh38 -o out/mc22.$v > out/mc22.$v.log 2>&1
    record mc22 $v $round
  done
done
for f in $(awk '{print $5}' sums.txt | sort -u); do
  awk -v f=$f '$5 == f {print $4}' sums.txt | sort | uniq -c | sed "s/^/$f: runs per sha256: /" >> sums.txt
done
echo "load after: $(cut -d" " -f1-3 /proc/loadavg)" >> mc22.time.txt
touch done
