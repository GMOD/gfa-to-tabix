#!/usr/bin/env python3
# Steps whose tile differs between two builds of one graph, from the pieces
# stats8.py lists (path, fragStart, piece, tile, nsteps, kind): each line's
# steps in order, as runs of one tile, compared run against run. Between a
# build at --stay 0 and one at the default, these are the steps stay moved.
# Usage: staydiff.py A.tsv B.tsv
import collections
import sys


def lines(fn):
    out = collections.defaultdict(list)
    for row in open(fn):
        path, frag, piece, tile, n, _ = row.rstrip('\n').split('\t')
        out[(path, frag)].append((int(piece), tile, int(n)))
    for v in out.values():
        v.sort()
    return out


a, b = lines(sys.argv[1]), lines(sys.argv[2])
moved = total = lines_moved = 0
per_line = []
for key in a.keys() | b.keys():
    ra = [(t, n) for _, t, n in a.get(key, [])]
    rb = [(t, n) for _, t, n in b.get(key, [])]
    sa, sb = sum(n for _, n in ra), sum(n for _, n in rb)
    if sa != sb:
        print('steps differ', key, sa, sb)
    total += sa
    i = j = 0
    la = ra[0][1] if ra else 0
    lb = rb[0][1] if rb else 0
    m = 0
    while i < len(ra) and j < len(rb):
        step = min(la, lb)
        if ra[i][0] != rb[j][0]:
            m += step
        la -= step
        lb -= step
        if la == 0:
            i += 1
            la = ra[i][1] if i < len(ra) else 0
        if lb == 0:
            j += 1
            lb = rb[j][1] if j < len(rb) else 0
    moved += m
    lines_moved += m > 0
    per_line.append(m)
pa, pb = sum(len(v) for v in a.values()), sum(len(v) for v in b.values())
per_line.sort()
print(f'pieces {pa} in A, {pb} in B; steps {total}, in another tile in B: {moved} '
      f'({moved / max(total, 1):.4%}), in {lines_moved} of {len(per_line)} lines; '
      f'per line p50 {per_line[len(per_line) // 2]} max {per_line[-1]}')
