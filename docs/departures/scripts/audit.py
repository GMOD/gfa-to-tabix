#!/usr/bin/env python3
# Audits a spike walk file (format 6, departure rows under seq~departure):
# departure counts by kind, rows per departure, coverage of every (contig,
# chunk) the contig spans without a piece, per-window cost of the departure
# query against tabix, and a cross-check against informed-2's GFA-derived
# departures. Usage: audit.py file.bed.gz [--truth dep.tsv] [--baseline f5.bed.gz]
import argparse
import bisect
import collections
import gzip
import os
import subprocess
import sys

ap = argparse.ArgumentParser()
ap.add_argument('file')
ap.add_argument('--truth')
ap.add_argument('--baseline')
ap.add_argument('--chunk', type=int, default=65536)
ap.add_argument('--windows', type=int, default=0, help='sample every nth window for tabix (0: all)')
args = ap.parse_args()
C = args.chunk

kinds = collections.Counter()
presence = collections.defaultdict(set)
extent = {}
deps = {}
dep_rows = collections.Counter()
dep_bytes = 0
total_bytes = 0
blocks_by_seq = collections.defaultdict(list)
header = []
with gzip.open(args.file, 'rt') as f:
    for line in f:
        total_bytes += len(line)
        if line[0] == '#':
            header.append(line.rstrip('\n'))
            continue
        c = line.rstrip('\n').split('\t')
        seq = c[0]
        if seq.endswith('~departure'):
            kinds['departure rows'] += 1
            dep_bytes += len(line)
            base = seq[:-len('~departure')]
            a, b = int(c[1]), int(c[2])
            path, frag, hap_start, own_bp, own_steps = c[4], int(c[5]), int(c[6]), int(c[7]), int(c[8])
            key = (path, frag, hap_start)
            dep_rows[key] += 1
            tags = c[17:]
            blocks_by_seq[base].append((a, b, path))
            if key not in deps:
                def end(cols):
                    return None if cols[0] == '.' else (int(cols[0]), int(cols[1]), cols[2], int(cols[3]))
                deps[key] = dict(seq=base, path=path, frag=frag, hap_start=hap_start, own_bp=own_bp, own_steps=own_steps,
                                 leave=end(c[9:13]), rejoin=end(c[13:17]), tags=tags)
        elif '~' in seq:
            kinds['detail rows'] += 1
        else:
            kind = c[3]
            kinds[kind] += 1
            if kind in ('walk', 'abridged'):
                name = c[4]
                cs = int(c[1]) // C
                presence[name].add((seq, cs))
                e = extent.setdefault((name, seq), [cs, cs])
                e[0] = min(e[0], cs)
                e[1] = max(e[1], cs)

print('# header')
print('\n'.join(header[:2]))
print('# rows by kind')
for k, v in sorted(kinds.items()):
    print(f'{v}\t{k}')
size = os.path.getsize(args.file)
print(f'{size}\tfile bytes')
print(f'{dep_bytes}\tdeparture text bytes of {total_bytes} ({100 * dep_bytes / total_bytes:.1f}%)')
if args.baseline:
    base_size = os.path.getsize(args.baseline)
    print(f'{base_size}\tbaseline bytes; delta {size - base_size:+d} ({100 * (size - base_size) / base_size:+.1f}%)')

print('# departures')
n = len(deps)
cnt = collections.Counter()
spans = []
owns = []
rows_hist = collections.Counter()
for key, d in deps.items():
    rows_hist[min(dep_rows[key], 30)] += 1
    l, r = d['leave'], d['rejoin']
    xseq = any(t.startswith(('ls:', 'rs:')) for t in d['tags'])
    if l is None or r is None:
        cnt['one-ended'] += 1
    elif xseq:
        cnt['to another sequence'] += 1
    else:
        lo, hi = min(l[0], r[0]), max(l[0], r[0])
        spans.append(hi - lo)
        if l[2] != r[2]:
            cnt['strand switch'] += 1
        else:
            forward = (r[0] > l[0]) if l[2] == '+' else (r[0] < l[0])
            cnt['same strand, forward along the haplotype' if forward or hi == lo else 'same strand, back'] += 1
            if hi == lo:
                cnt['empty stretch (own sequence between adjacent R steps)'] += 1
        if l[3] > 1 or r[3] > 1:
            cnt['an end on a node R passes more than once'] += 1
        if hi - lo >= 32 * C:
            cnt['stretch >= 32 chunks (prototype cap)'] += 1
    if d['own_bp'] == 0:
        cnt['0 own bp'] += 1
    if d['own_bp'] > 0 and d['own_steps'] == 0:
        cnt['own bp with no steps (sequence the graph lacks)'] += 1
    if d['own_bp'] >= 100000:
        cnt['own >= 100 kb'] += 1
    owns.append(d['own_bp'])
print(f'{n}\tdepartures; {sum(dep_rows.values())} rows; {sum(dep_rows.values()) / max(n, 1):.2f} rows per departure')
for k, v in sorted(cnt.items(), key=lambda kv: -kv[1]):
    print(f'{v}\t{k}')
q = lambda v, p: sorted(v)[min(len(v) - 1, int(p * len(v)))] if v else 0
print(f'stretch bp median {q(spans, .5)} p90 {q(spans, .9)} p99 {q(spans, .99)} max {max(spans) if spans else 0}')
print(f'own bp median {q(owns, .5)} p90 {q(owns, .9)} p99 {q(owns, .99)} max {max(owns) if owns else 0}')
print('rows per departure:', ' '.join(f'{k}:{v}' for k, v in sorted(rows_hist.items())))

print('# coverage: (contig, chunk) inside the contig extent with no piece')
covered = collections.defaultdict(set)
for key, d in deps.items():
    l, r = d['leave'], d['rejoin']
    if l is None or r is None or any(t.startswith(('ls:', 'rs:')) for t in d['tags']):
        continue
    lo, hi = min(l[0], r[0]), max(l[0], r[0], min(l[0], r[0]) + 1)
    for cc in range(lo // C, (hi - 1) // C + 1):
        covered[d['path']].add((d['seq'], cc))
absent = 0
miss = 0
miss_examples = []
for (name, seq), (lo, hi) in extent.items():
    for cc in range(lo, hi + 1):
        if (seq, cc) in presence[name]:
            continue
        absent += 1
        if (seq, cc) not in covered[name]:
            miss += 1
            if len(miss_examples) < 8:
                miss_examples.append((name, seq, cc * C))
print(f'{absent}\tabsent (contig, chunk) pairs inside contig extents')
print(f'{miss}\t  with no departure block of that contig over the chunk')
for m in miss_examples:
    print('   miss', *m)

print('# per-window cost of the departure query (tabix), 64 kb windows')
for seq, blocks in blocks_by_seq.items():
    blocks.sort()
    starts = [a for a, _, _ in blocks]
    length = max(b for _, b, _ in blocks)
    wins = list(range(0, length, C))
    if args.windows:
        wins = wins[::args.windows]
    returned, overlapping, haps = [], [], []
    for w in wins:
        out = subprocess.run(['tabix', args.file, f'{seq}~departure:{w + 1}-{w + C}'], capture_output=True, text=True).stdout
        rows = [ln for ln in out.split('\n') if ln]
        returned.append(len(rows))
        haps.append(len({ln.split('\t')[4] for ln in rows}))
        i = bisect.bisect_left(starts, w + C)
        overlapping.append(sum(1 for a, b, _ in blocks[:i] if b > w))
    over = [r - o for r, o in zip(returned, overlapping)]
    print(f'{seq}: {len(wins)} windows; rows returned median {q(returned, .5)} p95 {q(returned, .95)} max {max(returned)}; '
          f'truly overlapping median {q(overlapping, .5)} p95 {q(overlapping, .95)} max {max(overlapping)}; '
          f'over-read rows median {q(over, .5)} p95 {q(over, .95)} max {max(over)}; '
          f'haplotypes with a record median {q(haps, .5)} p95 {q(haps, .95)} max {max(haps)}')

if args.truth:
    print('# cross-check against GFA-derived departures (informed-2 dep.rs)')
    # name start kind seqa:ca seqb:cb rs re order L own_bp own hapStart inva invb multi
    by_key = {(d['path'], d['hap_start']): d for d in deps.values()}
    tot = collections.Counter()
    bad = []
    for line in open(args.truth):
        c = line.rstrip('\n').split('\t')
        name, kind = c[0], c[2]
        rs, re_, own_bp, own, hap_start = int(c[5]), int(c[6]), int(c[9]), int(c[10]), int(c[11])
        inva, invb, multi = c[12] == '1', c[13] == '1', c[14] == '1'
        tot[kind] += 1
        d = by_key.get((name, hap_start))
        if d is None:
            tot[f'{kind}: no record'] += 1
            continue
        l, r = d['leave'], d['rejoin']
        ok = d['own_bp'] == own_bp and d['own_steps'] == own
        if ok and l and r and kind in ('jump', 'ins'):
            lo, hi = min(l[0], r[0]), max(l[0], r[0])
            ok = (lo, hi) == (rs, re_) and (l[2] == '-') == inva and (r[2] == '-') == invb
        tot[f'{kind}: {"match" if ok else "MISMATCH"}'] += 1
        if not ok and len(bad) < 6:
            bad.append((c, d))
    for k, v in sorted(tot.items()):
        print(f'{v}\t{k}')
    for c, d in bad:
        print('   truth', c)
        print('   spike', d)
