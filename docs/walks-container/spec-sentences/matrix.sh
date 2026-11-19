#!/usr/bin/env bash
# Prints which checkers fail each file ADR 0017's rulings are about: the
# legal files, a writer's file with tags left off its #walks line or both
# budgets stated as 0, and one whose reference is one haplotype of its
# #reference sample, which every checker must pass; and the planted
# files, each breaking one sentence the page gained, or a stated budget.
# One line a file, one column a checker, FAILS or passes, a traceback
# named; then, for each FAILS, what the checker said first.
# The files and fixtures are this checkout's, built by its
# target/release/gfa-to-tabix and its make-broken.sh. The checkers are
# those of the checkout given, so the same files are read by the checkers
# from before the rulings and after.
# Usage: matrix.sh <checkout whose checkers run> <scratch dir>
set -u
R=$(readlink -f "$1")
W=$2
HERE=$(cd "$(dirname "$(readlink -f "$0")")/../../.." && pwd)
S=$R/docs/departures/scripts
B=$HERE/docs/departures/scripts/broken
D=$HERE/tests/data
CHECKERS="verify7 claims7 claims7-seqs audit7 expand7 spec8 rebuild"
mkdir -p "$W"
why=$W/why.txt
: > "$why"
row() {
  local label=$1 f=$2 g=$3 line=$1 c out rc said
  for c in $CHECKERS; do
    case $c in
      verify7) out=$(python3 -I "$S/verify7.py" "$f" 2>&1); rc=$?; said=$out ;;
      claims7) out=$(python3 -I "$S/claims7.py" "$f" --own 2>&1); rc=$?
        said=$(grep -E '^[1-9][0-9]*'$'\t' <<< "$out" | cut -f2 | cut -d' ' -f1 | sort -u | paste -sd' ' -
          grep -m1 '^claims7.py: ' <<< "$out" | sed 's/^claims7.py: [^ ]*: //') ;;
      claims7-seqs) out=$(bash "$S/claims7-seqs.sh" "$f" --own 2>&1); rc=$?
        said=$(grep -E '^[1-9][0-9]*'$'\t' <<< "$out" | cut -f2 | cut -d' ' -f1 | sort -u | paste -sd' ' -
          grep -m1 '^claims7.py: ' <<< "$out" | sed 's/^claims7.py: [^ ]*: //') ;;
      audit7) out=$(python3 -I "$S/audit7.py" "$f" --gfa "$g" --window 64 --point 16 2>&1); rc=$?
        said=$(sed -n '/^audit7: /,$p' <<< "$out" | head -2 | paste -sd' ' -) ;;
      expand7) out=$(python3 -I "$S/expand7.py" "$f" 2>&1); rc=$?; said=$(tail -1 <<< "$out") ;;
      spec8) out=$(python3 -I "$S/spec8.py" "$f" 2>&1); rc=$?
        said=$(grep -E '^spec8' <<< "$out"; sed -n '/^== disagreed ==/,$p' <<< "$out" | sed -n 2,4p) ;;
      rebuild) out=$(python3 -I "$R/scripts/walks-truth.py" rebuild "$f" "$g" 2>&1); rc=$?
        said=$(grep -v 'as the GFA' <<< "$out" | head -2) ;;
    esac
    if grep -q Traceback <<< "$out"; then
      line+=$'\t'traceback
    elif [ $rc = 0 ]; then
      line+=$'\t'passes
    else
      line+=$'\t'FAILS
      echo "$label	$c	$(sed "s|$B/||g" <<< "$said" | tr -s ' \t\r\n' ' ' | LC_ALL=C tr -c '\n -~' '?' | cut -c1-260)" >> "$why"
    fi
  done
  echo "$line"
}
gfa_of() {
  local g
  g=$(awk -F'\t' -v n="$1" '$1==n{print $2}' "$B/cases.tsv")
  [ "${g%%/*}" = broken ] && echo "$HERE/docs/departures/scripts/$g" || echo "$D/$g"
}
BIN=$HERE/target/release/gfa-to-tabix
"$BIN" "$B/follow.gfa" --walks --refs R --tile 100 --sequences --abridge-bytes 1 -o "$W/follow" > /dev/null 2>&1
"$BIN" "$D/walks-repeat.gfa" --walks --refs R --tile 10 -o "$W/repeat" > /dev/null 2>&1
LEGAL="bound-no-writer-tags bound-no-revisited bound-no-stay bound-no-abridge bound-no-abridgebytes bound-budgets-zero"
python3 -I "$HERE/docs/departures/scripts/repack.py" "$W/follow.R.walks.gz" "$W/follow-repack" $LEGAL > /dev/null
python3 -I "$HERE/docs/departures/scripts/repack.py" "$W/repeat.R.walks.gz" "$W/repeat-repack" bound-no-revisited > /dev/null
echo "file	${CHECKERS// /	}"
echo "# legal: broken/follow.gfa built with --tile 100 --sequences --abridge-bytes 1, which states revisited:i:0, then repack.py's variants of it"
row follow "$W/follow.R.walks.gz" "$B/follow.gfa"
for v in $LEGAL; do
  row "$v" "$W/follow-repack/$v/f.walks.gz" "$B/follow.gfa"
done
echo "# legal: walks-repeat.gfa built with --tile 10, which states revisited:i:2, then without that tag"
row repeat "$W/repeat.R.walks.gz" "$D/walks-repeat.gfa"
row "bound-no-revisited" "$W/repeat-repack/bound-no-revisited/f.walks.gz" "$D/walks-repeat.gfa"
echo "# legal: broken/hapref.gfa with HG002#1 alone for its reference: HG002's haplotype 2 built under a stand-in sample, then named HG002#2 again"
sed $'s/^W\tHG002\t2\t/W\tHG002z\t2\t/' "$B/hapref.gfa" > "$W/hapref-standin.gfa"
"$BIN" "$W/hapref-standin.gfa" --walks --refs HG002 --tile 10 -o "$W/hapref" > /dev/null 2>&1
python3 -I "$B/corrupt.py" "$W/hapref.HG002.walks.gz" "$W/hapref-one.walks.gz" --all 'HG002z#2' 'HG002#2' > /dev/null
row "one-haplotype-reference" "$W/hapref-one.walks.gz" "$B/hapref.gfa"
echo "# planted"
for name in revisited-count revisited-zero budget-bytes-over budget-steps-over budget-put-back \
            walks-bytes-tag tag-type-letter tile-zero tile-past-2-40 \
            number-leading-zero number-plus-sign token-minus-zero \
            header-empty-line directory-empty-line field-empty unit-line-inside-unit \
            departures-unit-empty reference-twice reference-haplotype length-zero ref-rows-overlap \
            past-2-53-line-end past-2-53-stated name-space name-cr name-e9 name-del \
            reference-haplotype-walk reference-none default-copy-named default-start-named default-leave-named \
            flip-of-own-flip detail-units-swapped name-hash-rows name-del-rows name-hash-haplotype \
            tile-missing tile-empty detail-unit-empty blocks-unit-empty table-empty \
            number-tag-leading-zero number-tag-minus number-start-leading-zero number-nsteps-space \
            number-length-leading-zero number-unit-leading-zero number-entry-length-leading-zero \
            field-empty-row directory-field-empty tag-graph-i past-2-53-own-end past-2-53-breakpoint \
            unit-line-in-header ref-rows-overlap-tiles \
            reference-short-name-walk reference-haplotype-name-walk route-wrong-way route-rows-swapped route-twice \
            bin-other-size owntiles-twice; do
  row "$name" "$B/$name.walks.gz" "$(gfa_of "$name")"
done
echo "# what each FAILS said first"
cat "$why"
