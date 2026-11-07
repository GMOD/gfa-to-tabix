#!/usr/bin/env bash
# Runs the file checks on the broken walk files of broken/, each a file the
# writer wrote and then corrupted by hand, or a file showing a writer bug,
# and fails unless every checker cases.tsv names fails it by its exit
# status, without a traceback; audit7 is given the GFA named there, from
# tests/data or broken/. Exits 1 on any check that passes a broken file.
# Usage: broken.sh
set -u
HERE=$(dirname "$(readlink -f "$0")")
DATA=$(readlink -f "$HERE/../../../tests/data")
failed=0
while IFS=$'\t' read -r name gfa checkers what; do
  f=$HERE/broken/$name.walks.gz
  g=$([ "${gfa%%/*}" = broken ] && echo "$HERE/$gfa" || echo "$DATA/$gfa")
  for c in $checkers; do
    case $c in
      verify7) out=$(python3 -I "$HERE/verify7.py" "$f" 2>&1) ;;
      claims7) out=$(python3 -I "$HERE/claims7.py" "$f" --own 2>&1) ;;
      audit7) out=$(python3 -I "$HERE/audit7.py" "$f" --gfa "$g" --window 64 --point 16 2>&1) ;;
    esac
    if [ $? = 0 ] || grep -q Traceback <<< "$out"; then
      echo "$c passes broken/$name ($what)"; failed=1
    fi
  done
done < "$HERE/broken/cases.tsv"
echo "broken.sh: $(wc -l < "$HERE/broken/cases.tsv") broken files"
exit $failed
