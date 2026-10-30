#!/usr/bin/env bash
# parity-fixtures.sh <jbrowse-components/scripts dir> <gfa-to-tabix binary>
# Every fixture through the JBrowse shell scripts and through this tool, except
# the path GFAs whose placing path reads a segment reversed: this tool flips
# those segments (0.12.0) and the retired scripts do not.
set -uo pipefail

here=$(dirname "$0")
data=$here/../tests/data
status=0
while read -r route gfa reference; do
  "$here/parity.sh" "$1" "$2" "$route" "$data/$gfa" $reference || status=1
done <<'CASES'
rgfa rgfa.gfa
rgfa ecoli_rgfa_slice.gfa
paths paths.gfa ref
paths paths.gfa alt
paths walks.gfa alt
paths walks.gfa ref#1
paths cactus.gfa ref
CASES
exit $status
