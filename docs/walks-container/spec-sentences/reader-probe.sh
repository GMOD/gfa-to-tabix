#!/usr/bin/env bash
# Runs reader-probe.mjs on every planted file of cases.tsv and prints one
# line a file: its name, the checkers cases.tsv says fail it, `reads` or
# `refuses`, and what the reader read or said. A first line names the
# reader's commit, and a last one counts the two.
# Usage: reader-probe.sh <graph-walks checkout> > reader-probe.tsv
set -u
GW=$(readlink -f "$1")
HERE=$(cd "$(dirname "$(readlink -f "$0")")" && pwd)
B=$HERE/../../departures/scripts/broken
echo "# graph-walks $(git -C "$GW" rev-parse HEAD), reader-probe.mjs on each planted file of cases.tsv"
printf 'file\tfails, by cases.tsv\treader\twhat it read or said\n'
while IFS=$'\t' read -r name gfa checkers what; do
  out=$(timeout 60 node --max-old-space-size=2048 "$HERE/reader-probe.mjs" "$GW" "$B/$name.walks.gz" 2>&1 |
    grep -v -E 'ExperimentalWarning|trace-warnings' | LC_ALL=C tr -c '\n\t -~' '?' | cut -c1-400)
  printf '%s\t%s\t%s\n' "$name" "$checkers" "${out:-ends with no output	a crash or a timeout}"
done < "$B/cases.tsv" | tee "${TMPDIR:-/tmp}/reader-probe.$$"
printf '# reads %s, refuses %s, of %s\n' "$(cut -f3 "${TMPDIR:-/tmp}/reader-probe.$$" | grep -c '^reads$')" \
  "$(cut -f3 "${TMPDIR:-/tmp}/reader-probe.$$" | grep -c '^refuses$')" "$(wc -l < "$B/cases.tsv")"
rm -f "${TMPDIR:-/tmp}/reader-probe.$$"
