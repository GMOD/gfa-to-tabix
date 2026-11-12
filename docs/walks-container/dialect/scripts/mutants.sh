#!/usr/bin/env bash
# Shows the checks of how a P line's name is read fail on a broken writer.
# Clones this repository's HEAD into WORK, and for each mutant of mutate.py
# breaks src/gfa.rs one way, runs every test, and runs check-dialect.sh on
# the mutant's binary; then runs check-dialect.sh on the writer of OLD, the
# commit before ADR 0014. Prints what failed, and exits 1 if a broken writer
# passed anything it should fail, or the unbroken one failed.
# RUN, if set, goes before each cargo command, to cap or nice it.
# Usage: mutants.sh WORK [OLD] > ../results/mutants.txt
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=$(cd "$HERE/../../../.." && pwd)
WORK=$(readlink -f "${1:?a directory to build in}")
OLD=${2:-17b5bc5}
RUN=${RUN:-}
escaped=0
clean() { sed -E "s#/tmp/tmp\.[A-Za-z0-9]+/##g; s#$WORK/(mutant/|old/)?##g; s#$REPO/##g" | grep -v ' KB peak, exit ' | cut -c1-330; }
dialect() {
  bash "$REPO/scripts/check-dialect.sh" "$1" > "$WORK/dialect.txt" 2>&1
  code=$?
  echo "$(grep -c '^dialect ' "$WORK/dialect.txt") failures, on $(grep '^dialect ' "$WORK/dialect.txt" | sed -E 's/^dialect ([^:]+):.*/\1/' | sort -u | wc -l) fixtures"
  clean < "$WORK/dialect.txt"
  echo "exit $code"
}
rm -rf "$WORK/mutant" "$WORK/old"
clone() { git -c advice.detachedHead=false clone -q "$REPO" "$1" 2> /dev/null; }
clone "$WORK/mutant" && clone "$WORK/old" && git -C "$WORK/old" checkout -q "$OLD" || exit 1
echo "Each broken writer of P line names against the checks. $(git -C "$WORK/mutant" log -1 --format='HEAD %h'), by"
echo "docs/walks-container/dialect/scripts/mutants.sh."
echo
echo "== the writer unbroken: scripts/check-dialect.sh"
(cd "$WORK/mutant" && $RUN cargo build -q --locked 2>&1 | clean | tail -3)
dialect "$WORK/mutant/target/debug/gfa-to-tabix"
[ "$code" = 0 ] || escaped=1
for m in $(python3 -I "$HERE/mutate.py" --list); do
  cd "$WORK/mutant" || exit 1
  git checkout -q -- src/gfa.rs
  python3 -I "$HERE/mutate.py" "$m" src/gfa.rs || exit 1
  echo
  echo "== mutant $m"
  git diff -U0 src/gfa.rs | grep -E '^[-+][^-+]' | clean
  echo "-- cargo test --no-fail-fast"
  $RUN cargo test --locked --no-fail-fast > "$WORK/test.txt" 2>&1
  tested=$?
  grep -E "^test .*FAILED|^test result: FAILED|assertion .* failed: " "$WORK/test.txt" | clean
  echo "exit $tested"
  echo "-- scripts/check-dialect.sh on its binary"
  dialect "$WORK/mutant/target/debug/gfa-to-tabix"
  [ "$tested" != 0 ] && [ "$code" != 0 ] || { echo "ESCAPED: $m"; escaped=1; }
done
git -C "$WORK/mutant" checkout -q -- src/gfa.rs
# Each reader of P line names checks itself against p-names.tsv as it
# starts: with a row of the clone's table changed, the readers of the
# changed column must exit non-zero, here on a file they otherwise pass
cd "$WORK/mutant" || exit 1
T=docs/walks-container/dialect/p-names.tsv
S=docs/departures/scripts
G=docs/walks-container/dialect/vg-chunk-p.gfa
target/debug/gfa-to-tabix "$G" --walks --refs R -o "$WORK/chunk" > /dev/null 2>&1
# reader LABEL WANT command...: WANT is the exit status, or `fails` for any but 0
reader() {
  local label=$1 want=$2 out status
  shift 2
  out=$("$@" 2>&1)
  status=$?
  echo "$label: exit $status: $(echo "$out" | grep -E 'p-names.tsv|assertion|wrong$|failed checks|^\(' | tail -1 | clean)"
  [ "$want" = "$status" ] || { [ "$want" = fails ] && [ "$status" != 0 ]; } || { echo "ESCAPED: $label"; escaped=1; }
}
# readers START UNDER: what a reader of a path's start, and one of what the
# path is listed under, must exit with; a reader of both fails where either
# does. graph-walks-rebuild.mjs, given no checkout to read, exits 1 at its
# table and otherwise 2, at its usage
readers() {
  local both=0 node=2
  [ "$1$2" = 00 ] || { both=fails; node=1; }
  reader audit7.py "$1" python3 -I $S/audit7.py "$WORK/chunk.R.walks.gz" --gfa "$G"
  reader claims7.py "$2" python3 -I $S/claims7.py "$WORK/chunk.R.walks.gz"
  reader spec8.py $both python3 -I $S/spec8.py "$WORK/chunk.R.walks.gz" --gfa "$G"
  reader walks-truth.py $both python3 -I scripts/walks-truth.py rebuild "$WORK/chunk.R.walks.gz" "$G"
  reader "cargo test, the table" $both $RUN cargo test --locked --bin gfa-to-tabix a_p_line_name_reads_as_the_shared_table_says
  if command -v node > /dev/null; then
    reader graph-walks-rebuild.mjs $node node scripts/graph-walks-rebuild.mjs
  fi
}
echo
echo "== p-names.tsv as committed"
readers 0 0
echo
echo "== p-names.tsv with the start of H#1#c#100[16-22] changed from 116 to 16"
sed -i -E 's/^(H#1#c#100\[16-22\]\t6\tH#1#c\t)116\t/\116\t/' $T
readers fails 0
git checkout -q -- $T
echo
echo "== p-names.tsv with H#c listed under H#c, not H"
sed -i -E 's/^(H#c\t16\tH#c\t0\t)H$/\1H#c/' $T
readers 0 fails
git checkout -q -- $T
echo
echo "== the writer at $OLD, before ADR 0014: scripts/check-dialect.sh"
(cd "$WORK/old" && $RUN cargo build -q --locked 2>&1 | clean | tail -3)
dialect "$WORK/old/target/debug/gfa-to-tabix"
[ "$code" != 0 ] || { echo "ESCAPED: the writer at $OLD"; escaped=1; }
exit $escaped
