#!/usr/bin/env bash
# The builds of docs/placement/scale-build.txt: the GRCh38 walk file of MC
# chr22 with its 464 real haplotypes and of the 2,000 and 5,000 haplotype
# graphs scale-synth.py makes from it, by gfa-to-tabix 5.0.1's release
# binary, interleaved three rounds, each run under a 64 GB memory cap, pinned
# to 16 CPUs (so 16 threads) and started at a 1-minute load below LOAD_MAX
# (default 3). Each
# round's walk file and .idx sha256 is recorded; round 1's are kept.
# Run from ~/work/handoff-1121/runs/scale on ada, the binary in bin/ and the
# synthetic GFAs in synth/:
#   bash scale-build.sh
set -uo pipefail
cd ~/work/handoff-1121/runs/scale
BIN=bin/gfa-to-tabix-x86_64-unknown-linux-musl/gfa-to-tabix
declare -A GFA=([464]=~/work/perf-1119/out/mc22.gfa.gz [2000]=synth/mc22.2000.gfa.gz [5000]=synth/mc22.5000.gfa.gz)
mkdir -p walks
T=walks/build.time.txt
rm -f $T walks/sums.txt
settle() {
  while [ "$(cut -d. -f1 /proc/loadavg)" -ge "${LOAD_MAX:-3}" ]; do sleep 20; done
  echo "load before: $(cut -d" " -f1-3 /proc/loadavg)" >> $T
}
"$BIN" --version >> $T
sha256sum "$BIN" >> $T
for n in 464 2000 5000; do
  echo "input $n: $(stat -c %s ${GFA[$n]}) bytes" >> $T
done
for round in 1 2 3; do
  for n in 464 2000 5000; do
    settle
    out=walks/mc22.$n.r$round
    systemd-run --user --scope -q -p MemoryMax=64G -p MemorySwapMax=0 \
      /usr/bin/time -f "$n round $round: %e s wall, %U s user, %S s system, %M KB peak" -a -o $T \
      taskset -c 0-15 nice -n 10 $BIN ${GFA[$n]} --walks --refs GRCh38 -o $out > $out.log 2>&1
    for f in $out.GRCh38.walks.gz $out.GRCh38.walks.gz.idx; do
      echo "$n round $round $(stat -c %s $f) $(sha256sum < $f | cut -c1-64) ${f##*.r$round.}" >> walks/sums.txt
    done
    if [ $round -gt 1 ]; then
      rm $out.GRCh38.walks.gz $out.GRCh38.walks.gz.idx
    fi
  done
done
echo "load after: $(cut -d" " -f1-3 /proc/loadavg)" >> $T
touch walks/done
