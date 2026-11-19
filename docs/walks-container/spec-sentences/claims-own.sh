#!/usr/bin/env bash
# claims7 --own on 1/64 of the paths, by claims7's name hash: GRCh38 chr21 of the hosted GRCh38 file, and pggb chrY whole, with claims7 at spec-sentences a5d7002
set -u
H=$HOME/work/walks8-gates/agents/spec-green/head/docs/departures/scripts/claims7.py
G=$HOME/work/blocks/genome-5.0.0-hdr/hprc-v2.1-mc-grch38.GRCh38.walks.gz
Y=$HOME/work/blocks/accept-5.0.0/4b14ee3/pggbY/pggbY.GRCh38.walks.gz
run() { name=$1 cap=$2; shift 2
  systemd-run --user --scope -q -p MemoryMax=$cap -p MemorySwapMax=0 nice -n 10 /usr/bin/time -f "%e\t%M" -o $name.time python3 -I $H "$@" > $name.out 2> $name.err
  printf "%s\texit %s\t%s\n" $name $? "$(cat $name.time)"; }
run grch38-chr21-own-0of64 40G $G --own --shard 0/64 --seq GRCh38#0#chr21
run pggbY-own-0of64 60G $Y --own --shard 0/64
