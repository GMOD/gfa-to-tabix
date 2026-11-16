#!/usr/bin/env bash
# Prints which checkers fail each planted file that breaks C27, a ref row's
# passes, the header's revisited or the #walks line's tags, and each
# unbroken file they were made from, which every checker must pass: one
# line a file, one column a checker, FAILS or passes, a traceback named.
# craft/ holds the file a review of graph-walks' counting call built by
# hand, a route interior holding another tile's once-passed nodes, and the
# writer's file of the same graph.
# Usage: matrix.sh <gfa-to-tabix checkout> <the scratch directory make-broken.sh built its files in>
set -u
R=$(readlink -f "$1")
W=$(readlink -f "$2")
S=$R/docs/departures/scripts
B=$S/broken
D=$R/tests/data
C=$(dirname "$(readlink -f "$0")")/craft
CHECKERS="verify7 claims7 claims7-seqs audit7 expand7 spec8 rebuild"
row() {
  local label=$1 f=$2 g=$3 line=$1 c out rc
  for c in $CHECKERS; do
    case $c in
      verify7) out=$(python3 -I "$S/verify7.py" "$f" 2>&1) ;;
      claims7) out=$(python3 -I "$S/claims7.py" "$f" --own 2>&1) ;;
      claims7-seqs) out=$(bash "$S/claims7-seqs.sh" "$f" --own 2>&1) ;;
      audit7) out=$(python3 -I "$S/audit7.py" "$f" --gfa "$g" --window 64 --point 16 2>&1) ;;
      expand7) out=$(python3 -I "$S/expand7.py" "$f" 2>&1) ;;
      spec8) out=$(python3 -I "$S/spec8.py" "$f" 2>&1) ;;
      rebuild) out=$(python3 -I "$R/scripts/walks-truth.py" rebuild "$f" "$g" 2>&1) ;;
    esac
    rc=$?
    line+=$'\t'$(grep -q Traceback <<< "$out" && echo traceback || { [ $rc = 0 ] && echo passes || echo FAILS; })
  done
  echo "$line"
}
echo "file	${CHECKERS// /	}"
echo "# planted"
row craft/far "$C/far.R.walks.gz" "$C/far.gfa"
while read -r name gfa; do
  row "$name" "$B/$name.walks.gz" "$gfa"
done << EOF2
on-reference-as-interior $B/follow.gfa
on-reference-as-interior-abridged $B/follow.gfa
other-tile-as-interior $B/far.gfa
other-sequence-as-interior $B/far.gfa
other-sequence-as-interior-revisited $B/shared.gfa
passes-once-as-twice $B/repeat.gfa
passes-understated $B/repeat.gfa
passes-second-row $D/walks-repeat.gfa
passes-twice-as-once $D/walks-repeat.gfa
passes-once-per-sequence $B/shared.gfa
revisited-zero $B/tie.gfa
revisited-count $B/repeat.gfa
tag-twice $B/far.gfa
tile-missing $B/far.gfa
EOF2
echo "# unbroken"
row craft/honest "$C/honest.R.walks.gz" "$C/far.gfa"
while read -r name gfa; do
  row "$name" "$W/$name.R.walks.gz" "$gfa"
done << EOF2
far10 $B/far.gfa
shared10 $B/shared.gfa
rp $D/walks-repeat.gfa
repeat100 $B/repeat.gfa
follow100 $B/follow.gfa
follow100a $B/follow.gfa
tie100 $B/tie.gfa
sq $D/walks-sequences.gfa
EOF2
