#!/usr/bin/env bash
# The untimed builds of docs/placement/scale-alt-builds.txt: the synthetic
# graphs written with abridging off (--abridge-steps 0 --abridge-bytes 0) and
# with four times the default budgets (s4m), by gfa-to-tabix 5.0.1's release
# binary pinned to 8 CPUs; the 5,000 haplotype build with abridging off ran
# twice, the first on CPUs 0-7 and the second on CPUs 8-15. scaled is the
# default budgets times 5000/464, the haplotypes over HPRC's.
# Run from ~/work/handoff-1121/runs/scale on ada.
set -uo pipefail
cd ~/work/handoff-1121/runs/scale
BIN=bin/gfa-to-tabix-x86_64-unknown-linux-musl/gfa-to-tabix
mkdir -p alt
build() {
  local name=$1 gfa=$2 cpus=$3 steps=$4 bytes=$5 timefile=$6
  systemd-run --user --scope -q -p MemoryMax=64G -p MemorySwapMax=0 \
    /usr/bin/time -f "$name: %e s wall, %M KB peak" -a -o $timefile \
    taskset -c $cpus nice -n 10 $BIN $gfa --walks --refs GRCh38 \
    --abridge-steps $steps --abridge-bytes $bytes -o alt/mc22.$name > alt/mc22.$name.log 2>&1
}
build 5000.off synth/mc22.5000.gfa.gz 0-7 0 0 alt/time.txt
build 5000.s4m synth/mc22.5000.gfa.gz 0-7 4000000 12000000 alt/time.txt
build 2000.off synth/mc22.2000.gfa.gz 8-15 0 0 alt/time2000.txt
build 5000.off2 synth/mc22.5000.gfa.gz 8-15 0 0 alt/time.txt
build 464.off ~/work/perf-1119/out/mc22.gfa.gz 8-15 0 0 alt/time464.txt
build 5000.scaled synth/mc22.5000.gfa.gz 8-15 10776000 32328000 alt/time.txt
