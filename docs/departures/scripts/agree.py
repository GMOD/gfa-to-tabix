#!/usr/bin/env python3
# Scores a pggb walk file's placement against the Minigraph-Cactus walk file
# of the same assemblies on the same reference, an independent projection:
# for every pggb walk piece, where MC puts the same contig position on R.
# A piece anchors at (hapOffset, R position of its `start` handle at the
# pass nearest its chunk); MC's anchors are read the same way and a contig
# position between two MC anchors is extrapolated from the earlier one.
# Also scores each departure record's two ends the same way.
# Usage: agree.py mc.walks.bed.gz pggb.walks.bed.gz seq [--tol bp]
import argparse
import bisect
import collections
import gzip

ap = argparse.ArgumentParser()
ap.add_argument('mc')
ap.add_argument('pggb')
ap.add_argument('seq')
ap.add_argument('--tol', type=int, default=10000)
ap.add_argument('--chunk', type=int, default=65536)
args = ap.parse_args()
C = args.chunk


def read(path):
    passes = collections.defaultdict(list)
    pieces = collections.defaultdict(list)
    records = []
    with gzip.open(path, 'rt') as f:
        for line in f:
            if line[0] == '#':
                continue
            c = line.rstrip('\n').split('\t')
            seq = c[0]
            if seq == args.seq + '~departure':
                if c[9] != '.' and c[13] != '.':
                    records.append((c[4], int(c[6]), int(c[7]), int(c[9]), int(c[13])))
                continue
            if '~' in seq or seq != args.seq:
                continue
            if c[3] == 'ref':
                at = int(c[6])
                node = 0
                for tok, length in zip(c[9].split(','), c[10].split(',')):
                    node += int(tok) >> 1
                    passes[node].append(at)
                    at += int(length)
            elif c[3] == 'walk':
                pieces[c[4]].append((int(c[6]), int(c[1]), int(c[9]) >> 1))
    for v in passes.values():
        v.sort()
    anchors = {}
    for name, ps in pieces.items():
        ps.sort()
        rows = []
        for hap, cs, node in ps:
            offs = passes.get(node)
            if not offs:
                continue
            k = bisect.bisect_left(offs, cs)
            near = min(offs[max(0, k - 1):k + 1], key=lambda o: abs(o - cs))
            rows.append((hap, near))
        if rows:
            anchors[name] = rows
    return anchors, records


mc_anchors, _ = read(args.mc)
pg_anchors, pg_records = read(args.pggb)


def mc_position(name, x):
    rows = mc_anchors.get(name)
    if not rows:
        return None
    k = bisect.bisect_right(rows, (x, float('inf'))) - 1
    if k < 0:
        return None
    hap, r = rows[k]
    if x - hap > 4 * C:
        return None
    return r + (x - hap)


shared = 0
agree = 0
checked = 0
no_mc = 0
by_region = collections.defaultdict(lambda: [0, 0])
for name, rows in pg_anchors.items():
    if name not in mc_anchors:
        no_mc += 1
        continue
    shared += 1
    for hap, r in rows:
        m = mc_position(name, hap)
        if m is None:
            continue
        checked += 1
        ok = abs(m - r) <= args.tol
        agree += ok
        region = 'Yp11/Yq11' if 2_781_480 <= m < 26_673_000 and not (10_000_000 <= m < 11_000_000) else 'other'
        by_region[region][0] += 1
        by_region[region][1] += ok
print(f'{len(pg_anchors)} pggb contigs with pieces, {shared} also in MC, {no_mc} not')
print(f'{checked} pggb pieces with an MC position for their contig start; {agree} ({100 * agree / max(checked, 1):.1f}%) within {args.tol} bp of it')
for region, (n, ok) in sorted(by_region.items()):
    print(f'  {region}: {ok} of {n} ({100 * ok / max(n, 1):.1f}%)')

both = one = none = unknown = 0
for name, hap_start, own_bp, lbp, rbp in pg_records:
    a = mc_position(name, hap_start - 1)
    b = mc_position(name, hap_start + own_bp)
    if a is None or b is None:
        unknown += 1
        continue
    hits = (abs(a - lbp) <= args.tol) + (abs(b - rbp) <= args.tol)
    if hits == 2:
        both += 1
    elif hits == 1:
        one += 1
    else:
        none += 1
n = len(pg_records)
print(f'{n} departure records: both ends where MC puts them {both} ({100 * both / max(n, 1):.1f}%), one {one}, neither {none}, no MC position {unknown}')
