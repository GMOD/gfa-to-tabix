#!/usr/bin/env python3
"""Each abridged row of a walk file against its piece's walk row in its detail unit: how many
rows state a span narrower than the piece, by how much, and whether the detail unit's
extent covers the piece. Usage: python3 -I abridged-span.py <file>.walks.gz"""
import gzip, sys, statistics
ab = {}; det = {}; ext = {}; unit = None
with gzip.open(sys.argv[1], 'rt') as f:
    for line in f:
        c = line.rstrip('\n').split('\t')
        if c[0] == '#unit':
            unit = (c[4], c[5])
            if c[4] == 'detail': ext[(c[1], c[5])] = (int(c[2]), int(c[3]))
            continue
        if line[0] == '#': continue
        if c[3] == 'abridged':
            ab[(c[0], unit[1], c[12], c[4], c[5], c[7])] = (int(c[1]), int(c[2]))
        elif c[3] == 'walk' and unit[0] == 'detail':
            cs, dd = unit[1].split(':')
            det[(c[0], cs, dd, c[4], c[5], c[7])] = (int(c[1]), int(c[2]))
out = []; widen = []; uncovered = 0
for key, (s, e) in ab.items():
    t = det[key]
    x = ext[(key[0], f"{key[1]}:{key[2]}")]
    if not (x[0] <= t[0] and t[1] <= x[1]): uncovered += 1
    widen.append((x[1] - x[0]) - (t[1] - t[0]))
    if t[0] < s or t[1] > e:
        out.append(max(s - t[0], 0) + max(t[1] - e, 0))
out.sort(); widen.sort()
q = lambda v, p: v[min(len(v) - 1, int(p * len(v)))] if v else 0
print(f"{sys.argv[1].split('/')[-1]}: abridged {len(ab)}; narrower {len(out)}, bp outside median {q(out,.5)} p90 {q(out,.9)} max {q(out,1)}; over 10 kb {sum(o>10000 for o in out)}, over 64 kb {sum(o>65536 for o in out)}")
print(f"  detail extent covers the true span: {len(ab)-uncovered} of {len(ab)}; extent minus true span, bp: median {q(widen,.5)} p90 {q(widen,.9)} max {q(widen,1)}; rows where they differ {sum(w>0 for w in widen)}")
