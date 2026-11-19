#!/usr/bin/env bash
# On ada, after ../scripts/build.sh: does a graph-walks cut of each 64 kb tile,
# every haplotype, context 0 and no budgets, hold each haplotype's visits to
# the tile's reference nodes as the GFA's W and P lines do? truth.py sketches
# the GFA, cut.mjs the cuts, compare.py judges nodes the reference sample
# passes once and reports the others. Two planted breaks (--swap, --plant)
# must fail. sub.mjs then checks 1 kb stretches cut inside a tile against the
# whole tile, and PLANT_SHIFT must make it fail. Logs: results/run.log and
# results/*.sub*.log.
set -uo pipefail
cd ~/work/visits
export PATH=~/.local/node/bin:$PATH
GW=~/work/gfaidx-compare/graph-walks
OUT=~/work/gfaidx-compare/out
IN=~/work/arb-format-opus/in
cap() { systemd-run --user --scope -q -p MemoryMax=$1 -p MemorySwapMax=0 nice -n 10 /usr/bin/time -f "%e s %M kB" "${@:2}"; }
cutrun() { cap 16G node --max-old-space-size=8192 cut.mjs $GW $OUT/$1.GRCh38.walks.gz "$2" 65536 $1 "${@:3}"; }
D=305,306,307,309,310
echo "== pggbY truth, passes over every GRCh38 line"
cap 24G venv/bin/python -I truth.py $IN/pggbY.gfa 'GRCh38#0#chrY' 65536 pggbY --drill $D 2>&1 | grep -v -e Warning -e 'h1 = '
echo "== pggbY cut"
cutrun pggbY 'GRCh38#0#chrY' pggbY/cut.tsv --drill $D 2>&1 | tail -2
venv/bin/python -I compare.py pggbY/truth.tsv pggbY/cut.tsv; echo "compare exit $?"
venv/bin/python -I drill.py pggbY
echo "== mc22 truth, passes over every GRCh38 line"
cap 16G venv/bin/python -I truth.py $IN/mc22.gfa 'GRCh38#0#chr22' 65536 mc22 2>&1 | grep -v -e Warning -e 'h1 = '
echo "== mc22 clean"
cutrun mc22 'GRCh38#0#chr22' mc22/cut.tsv 2>&1 | tail -2
venv/bin/python -I compare.py mc22/truth.tsv mc22/cut.tsv; echo "compare exit $?"
echo "== mc22 planted: one visit credited to another haplotype in window 300"
cutrun mc22 'GRCh38#0#chr22' mc22/cut-swap.tsv --swap 300 2>&1 | tail -1
venv/bin/python -I compare.py mc22/truth.tsv mc22/cut-swap.tsv; echo "compare exit $?"
echo "== mc22 planted: one visit dropped in window 300"
cutrun mc22 'GRCh38#0#chr22' mc22/cut-planted.tsv --plant 300 2>&1 | tail -1
venv/bin/python -I compare.py mc22/truth.tsv mc22/cut-planted.tsv; echo "compare exit $?"
for g in mc22:chr22 pggbY:chrY; do
  cap 16G node --max-old-space-size=8192 sub.mjs $GW $OUT/${g%%:*}.GRCh38.walks.gz "GRCh38#0#${g#*:}" 65536 ${g%%:*} 40 > ${g%%:*}/sub.log 2>&1
done
PLANT_SHIFT=200 cap 16G node --max-old-space-size=8192 sub.mjs $GW $OUT/mc22.GRCh38.walks.gz 'GRCh38#0#chr22' 65536 mc22 40 > mc22/sub-planted.log 2>&1
