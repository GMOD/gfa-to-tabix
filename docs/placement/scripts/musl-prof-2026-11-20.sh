#!/usr/bin/env bash
# The profile in docs/placement/musl-alloc-pggb-chrY.txt: one chrY index build
# under gdb, a loop sending it SIGINT every 2.5 s, and gdb printing every
# thread's backtrace at each stop (perf is blocked on ada).
# Run from ~/work/musl-alloc on ada: bash prof.sh musl; bash prof.sh glibc
set -uo pipefail
cd ~/work/musl-alloc
mkdir -p prof
v=$1
Y=~/work/scratch/graph-repro/data/pggb/chrY.gfa
{
  echo "set pagination off"
  echo "set confirm off"
  echo "set print thread-events off"
  echo "handle SIGINT stop print nopass"
  echo "handle SIGPIPE nostop noprint pass"
  echo "run $Y --reference GRCh38 -o prof/chrY.$v > prof/chrY.$v.log 2>&1"
  for i in $(seq 1 80); do
    echo "echo ===SAMPLE\\n"
    echo "thread apply all bt 8"
    echo "continue"
  done
} > prof/$v.gdb
(
  sleep 3
  while pgrep -f "o prof/chrY.$v\$" > /dev/null; do
    pkill -INT -f "o prof/chrY.$v\$"
    sleep 2.5
  done
) &
nice -n 10 gdb -batch -nx -x prof/$v.gdb bin/$v > prof/$v.stacks 2>&1
wait
