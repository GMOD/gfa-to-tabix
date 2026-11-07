#!/usr/bin/env python3
# A random GFA for walk format 7's checks. Reference R has one to three
# sequences, each a path that passes some nodes several times (tandem and
# dispersed copies), in one or more W lines with holes between, each line
# along the forward strand, the reverse, or a mix. A second reference, Q,
# follows stretches of R's first sequence with nodes of its own.
# Haplotypes follow stretches of a sequence, jump forward and back, invert,
# cross to another sequence, add nodes of their own, and come in one to
# three W lines per contig, which may abut, or as P lines named with their
# start in each form the spec reads; some W lines have no steps, some paths
# visit no node of R or of either reference, and some graphs put the path
# lines before the S lines. Every segment has bases, so --sequences runs.
# With --zero, nodes can have 0 bp, so a sequence can be 0 bp long, and
# those segments are `*` with LN:i:0.
# Usage: fuzz7-gen.py seed [--zero] > g.gfa
import random
import sys

seed = int(sys.argv[1])
zero = '--zero' in sys.argv[2:]
rng = random.Random(seed)
lengths = {}
nid = 1


def node(length):
    global nid
    lengths[nid] = length
    nid += 1
    return nid - 1


def short():
    return rng.choice([0, 1, 2, 3, 5, 8, 13, 30] if zero else [1, 2, 3, 5, 8, 13, 30]) \
        if rng.random() < 0.9 else rng.randint(40, 200)


def strands(ids):
    mode = rng.choice(['forward'] * 6 + ['reverse'] * 2 + ['mixed'] * 2)
    if mode == 'reverse':
        return [(i, True) for i in reversed(ids)]
    return [(i, mode == 'mixed' and rng.random() < 0.5) for i in ids]


sequences = []
for _ in range(rng.randint(1, 3)):
    if zero and rng.random() < 0.15:
        sequences.append(strands([node(0) for _ in range(rng.randint(1, 3))]))
        continue
    ref = []
    for step in strands([node(short()) for _ in range(rng.randint(10, 60))]):
        ref.append(step)
        if rng.random() < 0.25 and len(ref) > 2:
            k = rng.randint(1, 3)
            for _ in range(rng.randint(1, 3)):
                ref += ref[-k:]
        if rng.random() < 0.1 and len(ref) > 5:
            j = rng.randrange(len(ref) - 1)
            ref += ref[j:j + rng.randint(1, 3)]
    sequences.append(ref)
on_reference = {s for ref in sequences for s, _ in ref}

lines = []


def bp(steps):
    return sum(lengths[s] for s, _ in steps)


def w(sample, hap, contig, start, steps):
    end = start + bp(steps)
    lines.append(f'W\t{sample}\t{hap}\t{contig}\t{start}\t{end}\t' + ''.join(('<' if r else '>') + str(s) for s, r in steps))
    return end


def p(name, steps):
    lines.append(f'P\t{name}\t' + ','.join(f'{s}{"-" if r else "+"}' for s, r in steps) + '\t*')


for k, ref in enumerate(sequences):
    contig = 'chr' if k == 0 else f'chr{k + 1}'
    if rng.random() < 0.3 and len(ref) > 4:
        cuts = sorted(rng.sample(range(1, len(ref)), rng.randint(1, min(2, len(ref) - 1))))
        at = rng.choice([0, 0, 5])
        for a, b in zip([0] + cuts, cuts + [len(ref)]):
            at = w('R', 0, contig, at, ref[a:b]) + rng.choice([1, 7, 100])
    else:
        w('R', 0, contig, 0, ref)
    if rng.random() < 0.1:
        lines.append(f'W\tR\t0\tchrE{k}\t0\t0\t')


def own():
    return node(rng.choice([0, 1, 4, 20, 300] if zero else [1, 4, 20, 300]))


def walk(ref):
    steps = []
    i = rng.randrange(len(ref) // 3 + 1)
    rev = False
    while len(steps) < rng.randint(5, 3 * len(ref) + 5) and 0 <= i < len(ref):
        s, r = ref[i]
        steps.append((s, r != rev))
        x = rng.random()
        if x < 0.06:
            i += rng.randint(2, 30)
        elif x < 0.10:
            i -= rng.randint(1, 20)
        elif x < 0.13:
            for _ in range(rng.randint(1, 4)):
                steps.append((own(), rng.random() < 0.3))
            i += 1
        elif x < 0.15:
            rev = not rev
        elif x < 0.17 and len(sequences) > 1:
            other = rng.choice(sequences)
            j = rng.randrange(len(other))
            steps += other[j:j + rng.randint(1, 3)]
            i += 1
        else:
            i += -1 if rev else 1
    return steps


def cut(steps, n):
    at = sorted(rng.sample(range(1, len(steps)), min(n - 1, len(steps) - 1))) if len(steps) > 1 else []
    return [steps[a:b] for a, b in zip([0] + at, at + [len(steps)])]


def p_lines(sample, contig, steps):
    name = f'{sample}#1#{contig}'
    parts = cut(steps, rng.choice([1, 1, 2]))
    if len(parts) == 1:
        start = rng.choice([0, 50])
        end = start + bp(parts[0])
        p(rng.choice([name, f'{name}[{start}]', f'{name}[{start}-{end}]', f'{name}#{start}', f'{name}:{start}-{end}'])
          if start else rng.choice([name, f'{name}[0-{end}]']), parts[0])
        return
    form = rng.choice(['bracket', 'colon'])
    start = rng.choice([0, 20])
    for part in parts:
        end = start + bp(part)
        p(f'{name}[{start}-{end}]' if form == 'bracket' else f'{name}:{start}-{end}', part)
        start = end + rng.choice([0, 1, 7, 100] if end > start else [1, 7, 100])


q = walk(sequences[0])
w('Q', 0, 'chr', 0, q + [(node(short()), False) for _ in range(rng.randint(0, 3))])
for k in range(rng.randint(3, 12)):
    x = rng.random()
    if x < 0.08:
        steps = [(own(), False) for _ in range(rng.randint(1, 4))]
    elif x < 0.14:
        steps = [(s, False) for s, _ in q if s not in on_reference] or [(node(3), False)]
    else:
        steps = walk(rng.choice(sequences))
    if not steps:
        continue
    contig = rng.choice(['c', 'c', 'd'])
    if rng.random() < 0.2:
        p_lines(f'H{k}', contig, steps)
        continue
    parts = cut(steps, rng.choice([1, 1, 2, 3])) if len(steps) > 4 else [steps]
    start = rng.choice([0, 50])
    for n, part in enumerate(parts):
        end = w(f'H{k}', 1, contig, start, part)
        if n + 1 < len(parts) and rng.random() < 0.1:
            lines.append(f'W\tH{k}\t1\t{contig}\t{end}\t{end}\t')
        start = end + (0 if rng.random() < 0.3 and end > start else rng.choice([1, 7, 100]))
    if rng.random() < 0.05:
        lines.append(f'W\tH{k}\t1\t{contig}\t{start}\t{start}\t')


def segment(i, n):
    if n == 0:
        return f'S\t{i}\t*\tLN:i:0'
    bases = ''.join(rng.choice('ACGT') for _ in range(n))
    return f'S\t{i}\t{bases}' + (f'\tLN:i:{n}' if rng.random() < 0.3 else '')


segments = [segment(i, n) for i, n in sorted(lengths.items())]
print('H\tVN:Z:1.1')
print('\n'.join(lines + segments if rng.random() < 0.1 else segments + lines))
