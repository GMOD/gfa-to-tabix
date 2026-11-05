#!/usr/bin/env bash
# How many nodes a graph's reference sample passes more than once, over all
# its paths: what a walk file's header states as revisited:i:. Reads the GBZ
# with vg paths, so it needs no GFA.
# Usage: reference-passes.sh graph.gbz SAMPLE
set -euo pipefail
~/bin/vg paths -x "$1" -A -S "$2" |
  python3 -I -c '
import collections, re, sys
seen = collections.Counter()
paths = steps = 0
for line in sys.stdin:
    if line.startswith("@"):
        continue
    c = line.split("\t", 6)
    paths += 1
    for node in re.findall(r"[<>](\d+)", c[5]):
        seen[int(node)] += 1
        steps += 1
twice = sum(1 for n in seen.values() if n > 1)
print(f"{paths}\tpaths\n{steps}\tsteps\n{len(seen)}\tnodes\n{twice}\tnodes passed more than once")
'
