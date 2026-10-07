#!/usr/bin/env bash
# parity-fixtures.sh <jbrowse-components/scripts dir> <gfa-to-tabix binary>
# Every fixture through the JBrowse shell scripts and through this tool.
set -uo pipefail

here=$(dirname "$0")
data=$here/../tests/data
status=0
while read -r route gfa reference; do
  "$here/parity.sh" "$1" "$2" "$route" "$data/$gfa" $reference || status=1
done <<'CASES'
rgfa rgfa.gfa
rgfa ecoli_rgfa_slice.gfa
paths paths.gfa
paths paths.gfa alt
paths walks.gfa
paths walks.gfa ref#1
paths ecoli_pggb_subgraph.gfa
paths ecoli_pggb_subgraph.gfa Sakai
paths cactus.gfa
paths cactus.gfa ref
CASES
exit $status
