#!/usr/bin/env bash
# Builds every GFA of docs/walks-container/dialect as walk files and as a
# node and link index, and holds each to its row of expected.tsv there: the
# lines its rows name, as `path@fragStart`, and its #haplotype lines; or the
# refusal, or `built` where the file checks can't read the file; the fixture
# whose walk file and directory it must equal byte for
# byte, the same paths in W lines; and what the index makes of it. On each
# walk file it runs the file checks of check-walks.sh, audit7.py, spec8.py
# and walks-truth.py given the GFA, each of which reads the P line names for
# itself. Each check fails by its exit status. Exits 1 on any failure,
# naming it.
# Usage: scripts/check-dialect.sh target/release/gfa-to-tabix
set -u
REPO=$(cd "$(dirname "$0")/.." && pwd)
B=$(readlink -f "${1:?the gfa-to-tabix binary}")
S=$REPO/docs/departures/scripts
D=$REPO/docs/walks-container/dialect
dir=$(mktemp -d)
trap 'rm -rf "$dir"' EXIT
failed=0
fail() { echo "dialect $1"; failed=1; }
checks() {
  local label=$1 f=$2 gfa=$3 out
  out=$(python3 -I "$S/verify7.py" "$f" 2>&1) || fail "$label: verify7: $out"
  out=$(python3 -I "$S/claims7.py" "$f" --own 2>&1) || fail "$label: claims7: $(echo "$out" | grep -vE '^0'$'\t' | head -5)"
  out=$(python3 -I "$S/audit7.py" "$f" --gfa "$gfa" --window 64 --point 16 2>&1) ||
    fail "$label: $(echo "$out" | sed -n '/^audit7: /,$p' | head -5) $(echo "$out" | grep -E 'Traceback|Error' | head -3)"
  out=$(python3 -I "$S/expand7.py" "$f" 2>&1) || fail "$label: expand7: $out"
  out=$(python3 -I "$S/spec8.py" "$f" --gfa "$gfa" 2>&1) ||
    fail "$label: spec8: $(echo "$out" | sed -n '/^== disagreed ==/,$p' | head -6) $(echo "$out" | grep -E 'Traceback|Error|^spec8' | head -3)"
  out=$(python3 -I "$REPO/scripts/walks-truth.py" rebuild "$f" "$gfa" 2>&1) || fail "$label: walks-truth: $(echo "$out" | head -6)"
}
walks() {
  "$B" "$D/$1" --walks --refs "$2" --tile 10 -o "$dir/$1" > "$dir/$1.log" 2>&1
}
ls "$D" | grep '\.gfa$' | LC_ALL=C sort > "$dir/have"
tail -n +2 "$D/expected.tsv" | cut -f1 | LC_ALL=C sort > "$dir/listed"
cmp -s "$dir/have" "$dir/listed" || fail "expected.tsv doesn't list the fixtures of $D, one row each"
while IFS=$'\t' read -r fixture refs result rows haplotypes index twin; do
  [ "$result" = skip ] && continue
  f=$dir/$fixture.$refs.walks.gz
  if walks "$fixture" "$refs"; then
    if [ "$result" = refused ]; then
      fail "$fixture: built, where it should be refused: $rows"
    else
      if [ "$result" = ok ] && [ "$rows" != . ]; then
        got=$(zcat "$f" | awk -F'\t' '$4=="ref"||$4=="walk"||$4=="abridged"{print $5"@"$6}' |
          LC_ALL=C sort -t@ -k1,1 -k2,2n -u | paste -sd' ' -)
        [ "$got" = "$rows" ] || fail "$fixture: rows name the lines $got, not $rows"
        got=$(zcat "$f" | awk -F'\t' '$1=="#haplotype"{print $2}' | paste -sd, -)
        [ "${got:--}" = "$haplotypes" ] || fail "$fixture: #haplotype lists ${got:--}, not $haplotypes"
      fi
      [ "$result" = ok ] && checks "$fixture" "$f" "$D/$fixture"
      if [ "$twin" != . ]; then
        twin_refs=$(awk -F'\t' -v t="$twin" '$1==t{print $2}' "$D/expected.tsv")
        if walks "$twin" "$twin_refs"; then
          cmp -s "$f" "$dir/$twin.$twin_refs.walks.gz" || fail "$fixture: its walk file differs from $twin's"
          cmp -s "$f.idx" "$dir/$twin.$twin_refs.walks.gz.idx" || fail "$fixture: its directory differs from $twin's"
        else
          fail "$twin: BUILD $(tail -1 "$dir/$twin.log")"
        fi
      fi
    fi
  elif [ "$result" = refused ]; then
    grep -qF -- "$rows" "$dir/$fixture.log" || fail "$fixture: refused as $(tail -1 "$dir/$fixture.log"), not as: $rows"
    [ ! -e "$f" ] || fail "$fixture: refused, and left a file"
  else
    fail "$fixture: BUILD $(tail -1 "$dir/$fixture.log")"
  fi
  if "$B" "$D/$fixture" --reference "$refs" -o "$dir/$fixture.index" > "$dir/$fixture.index.log" 2>&1; then
    [ "$index" = ok ] || fail "$fixture: its index built, where it should be refused: $index"
  elif [ "$index" = ok ]; then
    fail "$fixture: index BUILD $(tail -1 "$dir/$fixture.index.log")"
  else
    grep -qF -- "$index" "$dir/$fixture.index.log" ||
      fail "$fixture: its index is refused as $(tail -1 "$dir/$fixture.index.log"), not as: $index"
  fi
done < <(tail -n +2 "$D/expected.tsv")
exit $failed
