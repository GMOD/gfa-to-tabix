#!/usr/bin/env python3
# Counts the departure records of a walk format 7 file that stand for a
# bubble a tile edge cut: both ends on nodes the reference passes once, on
# the same strand, the rejoin at or after the leave along S, no bp missing
# between W lines, and the leave's node starting in another tile than the
# rejoin's. Inside one tile the same bubble is a route of one piece and has
# no record (ADR 0009). Prints those records by the bp between the ends, and
# against all records.
# Usage: bubbles7.py walks.gz
import collections
import gzip
import sys

path = sys.argv[1]
tile = None
seen = set()
total = 0
edge = collections.Counter()
own = collections.Counter()
with gzip.open(path, 'rt') as f:
    for line in f:
        if line.startswith('#walks'):
            tile = int(next(t for t in line.split('\t') if t.startswith('tile:i:'))[7:])
            continue
        if line[0] == '#':
            continue
        c = line.rstrip('\n').split('\t')
        if c[3] != 'departure':
            continue
        key = '\t'.join(c)
        if key in seen:
            continue
        seen.add(key)
        total += 1
        start = int(c[1])
        own_bp, missing = int(c[6]), int(c[7])
        lp, ls, lpass, rp, rs, rpass = int(c[8]), c[9], int(c[10]), int(c[11]), c[12], int(c[13])
        forward = rp >= lp if ls == '+' else rp <= lp
        if ls != rs or lpass != 1 or rpass != 1 or missing or not forward:
            continue
        leave_node = start if ls == '+' else lp
        rejoin_node = rp if rs == '+' else rp - 1
        if leave_node // tile == rejoin_node // tile:
            continue
        gap = abs(rp - lp)
        size = '0' if gap == 0 else '1-50' if gap <= 50 else '51-1000' if gap <= 1000 else '1001-10000' if gap <= 10000 else '>10000'
        edge[size] += 1
        own['ownBp 0' if own_bp == 0 else 'ownBp > 0'] += 1
n = sum(edge.values())
print(f'{path}: {total} departure records; {n} ({100 * n / max(total, 1):.1f}%) are a bubble across a tile edge')
for k in ('0', '1-50', '51-1000', '1001-10000', '>10000'):
    print(f'  reference bp between the ends {k}: {edge[k]}')
for k, v in sorted(own.items()):
    print(f'  {k}: {v}')
