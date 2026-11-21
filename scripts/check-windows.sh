#!/usr/bin/env bash
# Holds graph-walks' cut over windows to window-oracle.py: builds every walk
# fixture under the option sets graph-walks-rebuild.mjs uses, and
# fuzz7-gen.py's random graphs, seeds 1 to $3 (10 by default), under
# fuzz7.sh's variants; runs the oracle over every file with the checkout as
# it is, then shows that each planted reader mistake in MUTANTS makes a file
# that passed there differ. A sequence of 300 bp or fewer is cut at every
# window, a longer one at its tile edges, holes and record ends and 300
# random windows, each with context 0 and 1000, attachBp 6 and 65536,
# expanded and not, comparing fragments, departures and the node table.
# Exits 1 on a difference or on a mutant no file catches, naming it.
# Usage: scripts/check-windows.sh <gfa-to-tabix binary> <graph-walks checkout> [seeds]
set -u
REPO=$(cd "$(dirname "$0")/.." && pwd)
B=$(readlink -f "${1:?the gfa-to-tabix binary}")
GW=$(readlink -f "${2:?a graph-walks checkout with node_modules}")
SEEDS=${3:-10}
dir=$(mktemp -d)
trap 'rm -rf "$dir"' EXIT
failed=0
oracle() {
  python3 -I "$REPO/scripts/window-oracle.py" "$1" "$2" --every-window-up-to 300 --windows 300 --contexts 0,1000 \
    --attach-bp 6,65536 --most 3
}

build() {
  local label=$1 gfa=$2 refs=$3 out=$dir/f$(wc -l < "$dir/files")
  shift 3
  if "$B" "$gfa" --walks --refs "$refs" "$@" -o "$out" > "$out.log" 2>&1; then
    for r in ${refs//,/ }; do
      echo "$out.$r.walks.gz $label $r" >> "$dir/files"
    done
  else
    echo "$label: BUILD $(tail -1 "$out.log")"
    failed=1
  fi
}

: > "$dir/files"
for fixture in "walks-two-refs.gfa GRCh38,Q" "walks-two-refs-p.gfa GRCh38,Q" "walks-repeat.gfa R" \
  "walks-loop.gfa R" "walks-records.gfa R" "walks-contig-ends.gfa R" "walks-skip.gfa R,Q" \
  "walks-sequences.gfa R" "walks-long-jump.gfa R"; do
  read -r gfa refs <<< "$fixture"
  for opts in "--tile 10" "--tile 7 --stay 0" "--tile 10 --abridge-bytes 1" "--tile 1000 --abridge-steps 1"; do
    read -r -a o <<< "$opts"
    build "$gfa $opts" "$REPO/tests/data/$gfa" "$refs" "${o[@]}"
  done
done
build "walks-abridge-bytes.gfa --tile 100 --abridge-bytes 600" "$REPO/tests/data/walks-abridge-bytes.gfa" R \
  --tile 100 --abridge-bytes 600
for seed in $(seq 1 "$SEEDS"); do
  shapes=()
  [ $((seed % 3)) = 0 ] && shapes+=(--zero)
  [ $((seed % 2)) = 0 ] && shapes+=(--two-haplotypes)
  [ $((seed % 3)) = 1 ] && shapes+=(--hairpins)
  python3 -I "$REPO/docs/departures/scripts/fuzz7-gen.py" "$seed" "${shapes[@]}" > "$dir/g$seed.gfa"
  for v in "20:" "16:--stay 8" "32:--abridge-steps 3" "20:--stay 40" "64:--abridge-steps 2" \
    "8:--stay 40 --abridge-steps 1" "64:--abridge-bytes 300" "128:--abridge-bytes 600" \
    "24:--sequences --abridge-bytes 400" "3:--stay 0 --abridge-bytes 1" "1000:--stay 1000 --abridge-steps 1" \
    "5:--abridge-bytes 1" "2:--stay 1000 --abridge-steps 2"; do
    read -r -a o <<< "${v#*:}"
    build "fuzz7 seed $seed --tile ${v%%:*} ${v#*:}" "$dir/g$seed.gfa" R,Q --tile "${v%%:*}" "${o[@]}"
  done
done

files=0
: > "$dir/passed"
while read -r f label r; do
  files=$((files + 1))
  if out=$(oracle "$f" "$GW" 2>&1); then
    echo "$f $label $r" >> "$dir/passed"
  else
    echo "$label $r:"
    echo "$out"
    failed=1
  fi
done < "$dir/files"
echo "$files files checked, every window agreeing unless named above"

# Each mutant is a file of graph-walks' src, the text it holds once, \n for a
# line break, and what replaces it, joined by %, each a mistake a reader of
# the format could make. A mutant is caught where a file that passed above
# has windows that differ
MUTANTS=(
  "tile-touching%walkReader.ts%unit.start < span.end && unit.end > span.start%unit.start <= span.end && unit.end > span.start"
  "tile-edge-dropped%walkReader.ts%unit.start < span.end && unit.end > span.start%unit.start < span.end && unit.end > span.start + 1"
  "context-short%walkReader.ts%  end: region.end + context,\n})%  end: region.end + Math.max(0, context - 1),\n})"
  "pieces-unjoined%walkRows.ts%pieces[i]!.piece !== pieces[i - 1]!.piece + 1%true"
  "step-touching%walkRows.ts%    if (at < end && to > start) {%    if (at <= end && to > start) {"
  "attach-touching%walkDeparture.ts%const on = (base: number) => base >= span.start && base < span.end%const on = (base: number) => base >= span.start && base <= span.end"
  "attach-below%walkDeparture.ts%d.ownBp <= attachBp && leavesOrRejoinsOn(d, drawn)%d.ownBp < attachBp && leavesOrRejoinsOn(d, drawn)"
  "records-twice%walkReader.ts%for (const line of new Set(lines)) {%for (const line of lines) {"
  "record-touching%walkReader.ts%+cols[2]! > span.start%+cols[2]! >= span.start"
  "computed-edge%walkRows.ts%if (lo < windowEnd && hi > windowStart) {%if (lo < windowEnd && hi > windowStart + 1) {"
  "computed-across-pieces%walkRows.ts%    const bounds = pieceBounds(run)\n    for (let p = 0; p + 1 < bounds.length; p++) {\n      pairs.length = 0%    const bounds = [0, run.ids.length]\n    for (let p = 0; p + 1 < bounds.length; p++) {\n      pairs.length = 0"
  "drawn-from-nodes%walkRows.ts%  let windowStart = drawn?.start ?? Infinity%  let windowStart = Infinity"
  "holes-kept%walkRows.ts%(leavePos === rejoinPos || squeeze(leavePos) === squeeze(rejoinPos))%leavePos === rejoinPos"
  "placement-later-pass%walkRows.ts%(node.refName === held.refName && node.start < held.start))%(node.refName === held.refName && node.start > held.start))"
  "placement-window-ignored%walkRows.ts%  node.onWindow !== held.onWindow\n    ? node.onWindow\n    : node.rank === 0 &&%  false\n    ? node.onWindow\n    : node.rank === 0 &&"
  "off-reference-later-walk%walkRows.ts%            name < held.refName ||%            name > held.refName ||"
)
plant='
import sys
path, old, new = sys.argv[1], sys.argv[2].replace("\\n", "\n"), sys.argv[3].replace("\\n", "\n")
text = open(path).read()
if text.count(old) != 1:
    sys.exit(f"{text.count(old)} places hold {old!r}")
open(path, "w").write(text.replace(old, new))
'
for m in "${MUTANTS[@]}"; do
  IFS='%' read -r name file from to <<< "$m"
  mkdir -p "$dir/gw-$name"
  cp -r "$GW/src" "$GW/package.json" "$dir/gw-$name/"
  ln -s "$GW/node_modules" "$dir/gw-$name/node_modules"
  if ! python3 -I -c "$plant" "$dir/gw-$name/src/$file" "$from" "$to"; then
    echo "mutant $name: its text is not in $file once"
    failed=1
    continue
  fi
  caught=""
  while read -r f label r; do
    oracle "$f" "$dir/gw-$name" > "$dir/m.out" 2>&1
    if grep -qE '; [1-9][0-9]* windows differ$' "$dir/m.out"; then
      caught="$label $r: $(sed -n 1p "$dir/m.out")"
      break
    fi
  done < "$dir/passed"
  rm -rf "$dir/gw-$name"
  if [ -n "$caught" ]; then
    echo "mutant $name caught by $caught"
  else
    echo "mutant $name: no file differs"
    failed=1
  fi
done
exit $failed
