#!/usr/bin/env bash
# Shows the file checks fail on the broken files of broken.sh; builds every
# walk fixture under four option sets, and some under options of their
# own, and runs on each file the release checks (verify7.py), the claims
# checks (claims7.py --own), the audit (audit7.py, given the fixture), the
# blocks rows expanded against their tiles' ref rows (expand7.py), the
# reader written from the spec alone (spec8.py) and walks-truth.py's rebuild
# of every line against the GFA; runs them too on files that use the
# format's room for additions, a tag on every row and on the #walks line, a
# unit of an unknown kind, an unknown header line and each legal variant of
# repack.py, on a file whose path names hold bytes that are not UTF-8, and
# on a file where a gzip member cut inside a row begins `#unit<TAB>`, all
# of which must pass; then fuzz7.sh's batch of seeds 1 to $SEEDS (6 by
# default). Each check fails by its exit status. Exits 1 on any failure,
# naming it.
# Usage: scripts/check-walks.sh target/release/gfa-to-tabix
set -u
REPO=$(cd "$(dirname "$0")/.." && pwd)
B=$(readlink -f "${1:?the gfa-to-tabix binary}")
S=$REPO/docs/departures/scripts
dir=$(mktemp -d)
trap 'rm -rf "$dir"' EXIT
failed=0
bash "$S/broken.sh" || failed=1
# runs the six checks on walk file $2, built from the GFA $3
checks() {
  local label=$1 f=$2 gfa=$3 out
  out=$(python3 -I "$S/verify7.py" "$f" 2>&1) || { echo "$label: $out"; failed=1; }
  out=$(python3 -I "$S/claims7.py" "$f" --own 2>&1) ||
    { echo "$label:"; echo "$out" | grep -vE '^0'$'\t'; failed=1; }
  out=$(python3 -I "$S/audit7.py" "$f" --gfa "$gfa" --window 64 --point 16 2>&1) ||
    { echo "$label:"; echo "$out" | sed -n '/^audit7: /,$p'; echo "$out" | grep -E 'Traceback|Error'; failed=1; }
  out=$(python3 -I "$S/expand7.py" "$f" 2>&1) || { echo "$label: $out"; failed=1; }
  out=$(python3 -I "$S/spec8.py" "$f" 2>&1) ||
    { echo "$label: spec8:"; echo "$out" | sed -n '/^== disagreed ==/,$p'; echo "$out" | grep -E 'Traceback|Error|^spec8'; failed=1; }
  out=$(python3 -I "$REPO/scripts/walks-truth.py" rebuild "$f" "$gfa" 2>&1) || { echo "$label: $out"; failed=1; }
}
check() {
  local gfa=$1 refs=$2 label="$1 ${*:3}"
  if ! "$B" "$REPO/tests/data/$gfa" --walks --refs "$refs" "${@:3}" -o "$dir/o" > "$dir/log" 2>&1; then
    echo "$label: BUILD $(tail -1 "$dir/log")"; failed=1; return
  fi
  for r in ${refs//,/ }; do
    checks "$label $r" "$dir/o.$r.walks.gz" "$REPO/tests/data/$gfa"
  done
  rm -f "$dir"/o.*
}
# a file of broken/follow.gfa changed by corrupt.py in a way the format allows, which must pass
addition() {
  local label="addition $1"
  if python3 -I "$S/broken/corrupt.py" "$dir/follow.R.walks.gz" "$dir/addition.walks.gz" "${@:2}" > "$dir/log" 2>&1; then
    checks "$label" "$dir/addition.walks.gz" "$S/broken/follow.gfa"
  else
    echo "$label: $(tail -1 "$dir/log")"; failed=1
  fi
}
for f in "walks-two-refs.gfa GRCh38,Q" "walks-two-refs-p.gfa GRCh38,Q" "walks-repeat.gfa R" "walks-loop.gfa R" \
         "walks-records.gfa R" "walks-contig-ends.gfa R" "walks-skip.gfa R,Q" "walks-sequences.gfa R" \
         "walks-long-jump.gfa R"; do
  read -r gfa refs <<< "$f"
  for opts in "--tile 10" "--tile 7 --stay 0" "--tile 10 --abridge-bytes 1" "--tile 1000 --abridge-steps 1"; do
    read -r -a args <<< "$opts"
    check "$gfa" "$refs" "${args[@]}"
  done
done
check walks-abridge-bytes.gfa R --tile 100 --abridge-bytes 600
check walks-sequences.gfa R --tile 10 --sequences
if "$B" "$S/broken/follow.gfa" --walks --refs R --tile 100 --sequences --abridge-bytes 1 -o "$dir/follow" > "$dir/log" 2>&1; then
  addition tags --tag zz:i:1
  addition unit-kind $'#unit\tR#0#c\t0\t36\ttable\t.\n' $'#unit\tR#0#c\t0\t36\tfuture\tx\nR#0#c\t0\t36\tfuture\tanything\n#unit\tR#0#c\t0\t36\ttable\t.\n'
  addition header-line $'#reference\tR\n' $'#reference\tR\n#future\tx\n'
  mapfile -t legal < <(python3 -I "$S/repack.py" --legal)
  if python3 -I "$S/repack.py" "$dir/follow.R.walks.gz" "$dir/repack" "${legal[@]}" > "$dir/log" 2>&1; then
    for v in "${legal[@]}"; do
      [ -e "$dir/repack/$v/f.walks.gz" ] && checks "addition $v" "$dir/repack/$v/f.walks.gz" "$S/broken/follow.gfa"
    done
  else
    echo "repack.py: $(tail -1 "$dir/log")"; failed=1
  fi
else
  echo "broken/follow.gfa: BUILD $(tail -1 "$dir/log")"; failed=1
fi
# a reference contig named `unit` and rows enough that a gzip member, cut every 0xff00 bytes, begins `#unit<TAB>`
{
  printf 'H\tVN:Z:1.1\nS\t1\tACGT\nS\t2\tACGT\nL\t1\t+\t2\t+\t0M\nW\tR\t0\tunit\t0\t8\t>1>2\n'
  printf 'W\tA%s\t1\tc\t0\t8\t>1>2\n' aaaaaaaaaaaaaaaaaaaaaa
  for i in $(seq 0 1699); do printf 'W\tH%05d\t1\tc\t0\t8\t>1>2\n' "$i"; done
} > "$dir/unitname.gfa"
if "$B" "$dir/unitname.gfa" --walks --refs R --tile 100000 -o "$dir/unitname" > "$dir/log" 2>&1; then
  checks "a contig named unit" "$dir/unitname.R.walks.gz" "$dir/unitname.gfa"
  python3 -I "$S/verify7.py" "$dir/unitname.R.walks.gz" 2>&1 | grep -q '"members_cut_before_unit_text": [1-9]' ||
    { echo "a contig named unit: no gzip member of its file begins #unit<TAB> inside a row any more; pad its GFA until one does"; failed=1; }
else
  echo "a contig named unit: BUILD $(tail -1 "$dir/log")"; failed=1
fi
# path names whose bytes are not UTF-8, beside one that is, all in byte order
{
  printf 'H\tVN:Z:1.1\nS\t1\tAAAAAA\nS\t2\tCCCCCC\nS\t3\tGGGGGG\nS\t4\tTTTT\n'
  printf 'L\t1\t+\t2\t+\t0M\nL\t2\t+\t3\t+\t0M\nL\t1\t+\t4\t+\t0M\nL\t4\t+\t3\t+\t0M\n'
  printf 'W\tR\t0\tchr\376\t0\t18\t>1>2>3\nW\tH\351\t1\tc\377\t0\t16\t>1>4>3\n'
  printf 'W\tH\303\251\t1\tc\t0\t16\t>1>4>3\nW\tHz\t1\tc\t0\t18\t>1>2>3\n'
} > "$dir/bytes.gfa"
for opts in "--tile 10" "--tile 10 --abridge-bytes 1"; do
  read -r -a args <<< "$opts"
  if "$B" "$dir/bytes.gfa" --walks --refs R "${args[@]}" -o "$dir/bytes" > "$dir/log" 2>&1; then
    checks "path names not UTF-8 $opts" "$dir/bytes.R.walks.gz" "$dir/bytes.gfa"
  else
    echo "path names not UTF-8 $opts: BUILD $(tail -1 "$dir/log")"; failed=1
  fi
done
FUZZ_DIR=$dir/fuzz GFA_TO_TABIX=$B bash "$S/fuzz7.sh" 1 "${SEEDS:-6}" || failed=1
exit $failed
