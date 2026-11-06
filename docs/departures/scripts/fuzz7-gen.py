#!/usr/bin/env python3
# A random GFA for walk format 7's checks. Reference R has one to three
# sequences, each a path that passes some nodes several times (tandem and
# dispersed copies), in one or more W lines with holes between; a sequence
# can be all 0 bp nodes, so 0 bp long. A second reference, Q, follows
# stretches of R's first sequence with nodes of its own. Haplotypes follow
# stretches of a sequence, jump forward and back, invert, cross to another
# sequence, add nodes of their own, and come in one or more W lines, which
# may abut; some W lines have no steps, some paths visit no node of R or of
# either reference, and some graphs put the path lines before the S lines.
# Usage: fuzz7-gen.py seed > g.gfa
import random
import sys

seed = int(sys.argv[1])
rng = random.Random(seed)
lengths = {}
nid = 1


def node(length):
    global nid
    lengths[nid] = length
    nid += 1
    return nid - 1


def short():
    return rng.choice([0, 1, 2, 3, 5, 8, 13, 30]) if rng.random() < 0.9 else rng.randint(40, 200)


sequences = []
for _ in range(rng.randint(1, 3)):
    if rng.random() < 0.15:
        sequences.append([node(0) for _ in range(rng.randint(1, 3))])
        continue
    ref = []
    for i in [node(short()) for _ in range(rng.randint(10, 60))]:
        ref.append(i)
        if rng.random() < 0.25 and len(ref) > 2:
            k = rng.randint(1, 3)
            for _ in range(rng.randint(1, 3)):
                ref += ref[-k:]
        if rng.random() < 0.1 and len(ref) > 5:
            j = rng.randrange(len(ref) - 1)
            ref += ref[j:j + rng.randint(1, 3)]
    sequences.append(ref)

lines = []


def w(sample, hap, contig, start, steps):
    end = start + sum(lengths[s] for s, _ in steps)
    lines.append(f'W\t{sample}\t{hap}\t{contig}\t{start}\t{end}\t' + ''.join(('<' if r else '>') + str(s) for s, r in steps))
    return end


for k, ref in enumerate(sequences):
    contig = 'chr' if k == 0 else f'chr{k + 1}'
    steps = [(s, False) for s in ref]
    if rng.random() < 0.3 and len(ref) > 4:
        cuts = sorted(rng.sample(range(1, len(ref)), rng.randint(1, min(2, len(ref) - 1))))
        at = rng.choice([0, 0, 5])
        for a, b in zip([0] + cuts, cuts + [len(ref)]):
            at = w('R', 0, contig, at, steps[a:b]) + rng.choice([1, 7, 100])
    else:
        w('R', 0, contig, 0, steps)
    if rng.random() < 0.1:
        lines.append(f'W\tR\t0\tchrE{k}\t0\t0\t')


def walk(ref):
    steps = []
    i = rng.randrange(len(ref) // 3 + 1)
    rev = False
    while len(steps) < rng.randint(5, 3 * len(ref) + 5) and 0 <= i < len(ref):
        steps.append((ref[i], rev))
        r = rng.random()
        if r < 0.06:
            i += rng.randint(2, 30)
        elif r < 0.10:
            i -= rng.randint(1, 20)
        elif r < 0.13:
            for _ in range(rng.randint(1, 4)):
                steps.append((node(rng.choice([0, 1, 4, 20, 300])), False))
            i += 1
        elif r < 0.15:
            rev = not rev
        elif r < 0.17 and len(sequences) > 1:
            other = rng.choice(sequences)
            j = rng.randrange(len(other))
            steps += [(s, False) for s in other[j:j + rng.randint(1, 3)]]
            i += 1
        else:
            i += -1 if rev else 1
    return steps


q = walk(sequences[0])
w('Q', 0, 'chr', 0, q + [(node(short()), False) for _ in range(rng.randint(0, 3))])
for k in range(rng.randint(3, 12)):
    r = rng.random()
    if r < 0.08:
        steps = [(node(short()), False) for _ in range(rng.randint(1, 4))]
    elif r < 0.14:
        steps = [(s, False) for s, _ in q if s not in {x for ref in sequences for x in ref}] or [(node(3), False)]
    else:
        steps = walk(rng.choice(sequences))
    if not steps:
        continue
    contig = 'c'
    if rng.random() < 0.3 and len(steps) > 4:
        cut = rng.randrange(1, len(steps) - 1)
        end = w(f'H{k}', 1, contig, 0, steps[:cut])
        abut = rng.random() < 0.3 and end > 0
        w(f'H{k}', 1, contig, end + (0 if abut else rng.choice([1, 7, 100])), steps[cut:])
        if rng.random() < 0.2:
            lines.append(f'W\tH{k}\t1\t{contig}\t{end}\t{end}\t')
    else:
        start = rng.choice([0, 50])
        end = w(f'H{k}', 1, contig, start, steps)
        if rng.random() < 0.15:
            lines.append(f'W\tH{k}\t1\t{contig}\t{start}\t{start}\t')

segments = [f'S\t{i}\t*\tLN:i:{n}' for i, n in sorted(lengths.items())]
print('H\tVN:Z:1.1')
print('\n'.join(lines + segments if rng.random() < 0.1 else segments + lines))
