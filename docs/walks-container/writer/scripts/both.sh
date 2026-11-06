#!/usr/bin/env bash
# Builds one GFA two ways for one reference, the writer and gfa-to-tabix
# 3.0.0 followed by arbiter A's converter, runs the release checks on the
# writer's file and compares the two. Prints compare7.py's summary last.
# usage: both.sh WORK writer gfa ref tile outdir [extra args]
#   WORK holds gtt3 (a 3.0.0 binary), scripts/ (arbiter A's .mjs files) and
#   gw/src/ (graph-walks 5.0.2's src, which the converter imports)
set -euo pipefail
HERE=$(dirname "$(readlink -f "$0")")
K=$1 W=$2 G=$3 R=$4 T=$5 O=$6
shift 6
mkdir -p "$O"
"$K/gtt3" "$G" --walks --refs "$R" --chunk "$T" "$@" -o "$O/f6" > "$O/f6.log" 2>&1
"$W" "$G" --walks --refs "$R" --tile "$T" "$@" -o "$O/w7" > "$O/w7.log" 2>&1
node "$K/scripts/build.mjs" "$O/f6.$R.walks.bed.gz" "$O" "$T" o > "$O/conv.log" 2>&1
node "$K/scripts/sfinal.mjs" "$O" "$T" >> "$O/conv.log" 2>&1
node "$K/scripts/s7.mjs" "$O" >> "$O/conv.log" 2>&1
node "$K/scripts/verify7.mjs" "$O/w7.$R.walks.gz" "$T" > /dev/null
python3 -I "$HERE/compare7.py" "$O/w7.$R.walks.gz" "$O/s7.walks.gz" --show 0
