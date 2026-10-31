#!/usr/bin/env python3
# Scores a spike walk file's departure records against wfmash all-vs-1
# alignment blocks (walks-truth.py lift output: q lo hi t ta tb strand): for
# each record, where the alignment puts the contig base before the leave
# breakpoint and the base at the rejoin, and whether that agrees with the
# record's ends. Usage: artefact.py walks.bed.gz lift.tsv seq [--tol bp] [--every n]
import argparse
import bisect
import collections
import gzip

ap = argparse.ArgumentParser()
ap.add_argument('walks')
ap.add_argument('lift')
ap.add_argument('seq')
ap.add_argument('--tol', type=int, default=2000)
ap.add_argument('--every', type=int, default=4)
ap.add_argument('--chunk', type=int, default=65536)
args = ap.parse_args()
C = args.chunk

blocks = collections.defaultdict(list)
for line in open(args.lift):
    q, lo, hi, t, ta, tb, strand = line.rstrip('\n').split('\t')
    blocks[q].append((int(lo), int(hi), t, int(ta), int(tb), strand == '+'))
starts = {}
for q, bl in blocks.items():
    bl.sort()
    starts[q] = [b[0] for b in bl]

def target_of(q, x):
    bl = blocks.get(q)
    if not bl:
        return None
    k = bisect.bisect_right(starts[q], x) - 1
    while k >= 0 and bl[k][1] <= x:
        k -= 1
    if k < 0:
        return None
    lo, hi, t, ta, tb, forward = bl[k]
    if not (lo <= x < hi):
        return None
    return (t, ta + (x - lo) if forward else tb - (x - lo), forward)

records = {}
with gzip.open(args.walks, 'rt') as f:
    for line in f:
        if line[0] == '#':
            continue
        c = line.rstrip('\n').split('\t', 4)
        if c[0] != args.seq + '~departure':
            continue
        c = line.rstrip('\n').split('\t')
        key = (c[4], int(c[6]))
        if key in records or c[9] == '.' or c[13] == '.':
            continue
        records[key] = (c[4], int(c[6]), int(c[7]), int(c[9]), c[11], int(c[12]), int(c[13]), c[15], int(c[16]))

cls = collections.Counter()
by_window = collections.defaultdict(collections.Counter)
multi0 = collections.Counter()
for (name, hap_start, own_bp, lbp, lstrand, lpass, rbp, rstrand, rpass) in records.values():
    a = target_of(name, hap_start - 1)
    b = target_of(name, hap_start + own_bp)
    def near(end, bp):
        return end is not None and end[0] == args.seq and abs(end[1] - bp) <= args.tol
    if a is None or b is None:
        kind = 'an end unaligned'
    elif a[0] != args.seq or b[0] != args.seq:
        kind = 'an end aligned to another sequence'
    elif near(a, lbp) and near(b, rbp):
        kind = 'both ends where the alignment puts them'
    elif near(a, lbp) or near(b, rbp):
        kind = 'one end where the alignment puts it'
    else:
        kind = 'neither end where the alignment puts it'
    cls[kind] += 1
    noise = own_bp == 0 and (lpass > 1 or rpass > 1)
    multi0[(kind, noise)] += 1
    lo, hi = min(lbp, rbp), max(lbp, rbp, min(lbp, rbp) + 1)
    for w in range(lo // C, (hi - 1) // C + 1):
        if w % args.every == 0:
            by_window[w][kind] += 1
            by_window[w]['all'] += 1

n = len(records)
print(f'{n}\trecords on {args.seq} with both ends')
for k, v in cls.most_common():
    noise = multi0[(k, True)]
    print(f'{v}\t{k} ({100 * v / n:.1f}%); of them 0 own bp with a multi-pass end: {noise}')
q = lambda v, p: sorted(v)[min(len(v) - 1, int(p * len(v)))] if v else 0
wins = sorted(by_window)
for k in ['all', 'both ends where the alignment puts them']:
    v = [by_window[w][k] for w in wins]
    print(f'per sampled window, {k}: median {q(v, .5)} p95 {q(v, .95)} max {max(v) if v else 0} over {len(v)} windows')
