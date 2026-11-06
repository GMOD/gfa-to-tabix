#!/usr/bin/env bash
# The writer against arbiter A's converter on every walk test GFA, in three
# option sets, and on fuzz graphs (fuzz6-gen.py, and the same generator with
# no node of 0 bp) in four; one TSV line per build: input, tile, options,
# compare7.py's summary, and for files that differ, detailnames.py's.
# summarize.py classes the lines.
# usage: local-compare.sh REPO WRITER GTT3 GRAPH_WALKS_5 OUT.tsv [seeds]
#   GTT3 is a gfa-to-tabix 3.0.0 binary; GRAPH_WALKS_5 a checkout at 5.0.2
set -uo pipefail
HERE=$(dirname "$(readlink -f "$0")")
REPO=$1 W=$(readlink -f "$2") GTT3=$(readlink -f "$3") GW=$4 OUT=$5 SEEDS=${6:-60}
K=$(mktemp -d)
trap 'rm -rf "$K"' EXIT
mkdir -p "$K/scripts" "$K/gw"
cp "$REPO"/docs/walks-container/arbA/scripts/*.mjs "$K/scripts/"
git -C "$GW" archive HEAD src | tar -x -C "$K/gw"
cp "$GTT3" "$K/gtt3"
sed 's/random.choice(\[0, 1, 2, 3, 5, 8, 13, 30\])/random.choice([1, 1, 2, 3, 5, 8, 13, 30])/' \
  "$REPO/docs/departures/scripts/fuzz6-gen.py" > "$K/gen-nozero.py"
one() {
  local name=$1 gfa=$2 ref=$3 tile=$4; shift 4
  local o="$K/out/$name-$tile-$#"
  local r
  r=$("$HERE/both.sh" "$K" "$W" "$gfa" "$ref" "$tile" "$o" "$@" 2>&1 | tail -1)
  local names=.
  grep -q '"differences": {}' <<< "$r" || names=$(python3 -I "$HERE/detailnames.py" "$o/w7.$ref.walks.gz" "$o/s7.walks.gz")
  printf '%s\t%s\t%s\t%s\t%s\n' "$name" "$tile" "$*" "$r" "$names" >> "$OUT"
  rm -rf "$o"
}
: > "$OUT"
for g in "$REPO"/tests/data/*.gfa; do
  ref=$(grep -m1 -oP '^W\t\K[^\t]+' "$g" || grep -m1 -oP '^P\t\K[^#\t]+' "$g" || true)
  [ -z "$ref" ] && continue
  for v in "10:" "7:--abridge-bytes 1" "1000:--abridge-steps 1" "3:--stay 0 --abridge-bytes 300"; do
    one "$(basename "$g" .gfa)" "$g" "$ref" "${v%%:*}" ${v#*:}
  done
done
for gen in fuzz nozero; do
  for seed in $(seq 1 "$SEEDS"); do
    if [ $gen = fuzz ]; then python3 -I "$REPO/docs/departures/scripts/fuzz6-gen.py" "$seed"; else python3 -I "$K/gen-nozero.py" "$seed"; fi > "$K/g.gfa"
    for v in "20:" "16:--stay 8" "32:--abridge-steps 3" "8:--stay 40 --abridge-steps 1"; do
      one "$gen$seed" "$K/g.gfa" R "${v%%:*}" ${v#*:}
    done
  done
done
