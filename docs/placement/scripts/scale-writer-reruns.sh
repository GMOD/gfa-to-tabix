#!/usr/bin/env bash
# The 30 reruns of docs/placement/scale-writer-reruns.tsv: run1.sh below, run in lanes of one binary list per CPU set by lane.sh.
# Binaries: rel501 and rel500 are the musl releases, instr-musl and instr-glibc v5.0.1 with per-run checksums of the external sort's runs,
# positions checked inside their tile and rows checked between merge and encoding (local branch race-instrument, b19a617), glibc500 a cargo build of v5.0.0
# --- lane.sh ---
# # lane.sh CPUS NAME BIN...: runs run1.sh for each BIN in turn on CPUS, stopping when stop exists
# cd ~/work/handoff-1121/runs/writer-race
# cpus=$1 name=$2
# shift 2
# i=0
# for bin in "$@"; do
#   [ -e stop ] && break
#   i=$((i+1))
#   ./run1.sh $bin $cpus $name.$i.$bin
# done
# --- run1.sh ---
set -u
cd ~/work/handoff-1121/runs/writer-race
bin=$1 cpus=$2 tag=$3
shift 3
mkdir -p out
start=$(date +%s)
GTT_RACE_PATH=SYN1288#1#c2 GTT_RACE_LOG=1 GTT_RACE_DUMP=$PWD/dumps systemd-run --user --scope -q -p MemoryMax=64G -p MemorySwapMax=0 \
  /usr/bin/time -f "%e s wall, %M KB peak" -o out/$tag.time \
  taskset -c $cpus nice -n 10 bin/$bin synth/mc22.5000.gfa.gz --walks --refs GRCh38 \
  --abridge-steps 0 --abridge-bytes 0 "$@" -o out/$tag > out/$tag.log 2>&1
code=$?
secs=$(( $(date +%s) - start ))
sha=-
[ $code = 0 ] && sha=$(sha256sum out/$tag.GRCh38.walks.gz | cut -c1-64) && rm -f out/$tag.GRCh38.walks.gz
err=$(grep "error" out/$tag.log | head -1)
printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" "$tag" "$bin" "$cpus" "$code" "$secs" "$sha" "$(date +%T)" "$err" >> results.tsv
