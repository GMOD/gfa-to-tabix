#!/usr/bin/env python3
# Reads chr9.records.txt (the distinct CHM13 chr9 records of the GRCh38
# graph's CHM13 file, from chm13-chr9-departures.sh) and counts, per path in
# contig order, consecutive record pairs that hop to a copy over 1 Mb away and
# back within 100 kb of where the first landed, with the bp the path walks on
# the far copy between the two, by power of two.
# Usage: chm13-chr9-hops.py chr9.records.txt
import collections
import sys

by_path = collections.defaultdict(list)
with open(sys.argv[1]) as f:
    for line in f:
        c = line.rstrip('\n').split('\t')
        by_path[c[1]].append((int(c[2]), int(c[3]), int(c[5]), int(c[7])))
pairs = hops = 0
dwell = collections.Counter()
for records in by_path.values():
    records.sort()
    for a, b in zip(records, records[1:]):
        pairs += 1
        far = abs(a[2] - a[3]) > 1e6 and abs(b[2] - b[3]) > 1e6 and abs(a[3] - b[2]) < 1e5
        if far:
            hops += 1
            walked = b[0] - (a[0] + a[1])
            dwell[max(walked - 1, 0).bit_length()] += 1
print(f'{len(by_path)}\tpaths')
print(f'{pairs}\tconsecutive record pairs of one path')
print(f'{hops}\tpairs hopping over 1 Mb to a copy and back')
total = 0
for k in sorted(dwell):
    total += dwell[k]
    print(f'{dwell[k]}\thops walking at most 2^{k} bp on the far copy (cumulative {total})')
