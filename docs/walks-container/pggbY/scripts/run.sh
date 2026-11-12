#!/usr/bin/env bash
# Runs one command capped, niced and timed, detached from the ssh session.
# Usage: run.sh NAME CAP command...   -> NAME.out, NAME.time, NAME.rc
cd ~/work/blocks/pggbY
NAME=$1 CAP=$2
shift 2
free -g | head -2 > $NAME.free
systemd-run --user --scope -q -p MemoryMax=$CAP -p MemorySwapMax=0 \
  nice -n 10 /usr/bin/time -v -o $NAME.time "$@" > $NAME.out 2>&1
echo $? > $NAME.rc
