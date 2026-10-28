"""Writes a synthetic plain GFA: a reference path REF#0#chr1 through SNP
bubbles, H haplotypes that take each alternate allele at random, and optionally
pggb-style collapsed repeats, where the reference passes the same four nodes at
several distant positions.

usage: synthetic-gfa.py OUT.gfa [--bp N] [--haps H] [--repeats FAMILIES] [--copies C] [--seed S]

`--bp 20000000 --haps 20 --repeats 2000 --copies 3` puts 15% of the reference's
steps on a later pass over a node (23% counting the first pass too); ADR 0001
reports 28% for pggb's GRCh38 chr22.
"""

import argparse
import random

p = argparse.ArgumentParser()
p.add_argument("out")
p.add_argument("--bp", type=int, default=20_000_000)
p.add_argument("--haps", type=int, default=20)
p.add_argument("--repeats", type=int, default=0)
p.add_argument("--copies", type=int, default=3)
p.add_argument("--seed", type=int, default=1)
a = p.parse_args()
rng = random.Random(a.seed)

lengths = {}


def node(length):
    lengths[len(lengths) + 1] = length
    return len(lengths)


# each family is a 1 kb repeat element of four 250 bp nodes
families = [[node(250) for _ in range(4)] for _ in range(a.repeats)]
slots = {}
for f in range(a.repeats):
    for _ in range(a.copies):
        slots[rng.randrange(0, a.bp) // 1000 * 1000] = f

# (reference node, its alternate allele or None)
reference = []
pos = 0
pending = sorted(slots)
while pos < a.bp:
    if pending and pending[0] <= pos:
        reference.extend((n, None) for n in families[slots[pending.pop(0)]])
        pos += 1000
        continue
    n = node(rng.randint(50, 400))
    reference.append((n, node(1) if rng.random() < 0.5 else None))
    pos += lengths[n]

walks = []
for h in range(a.haps + 1):
    steps = []
    for n, alt in reference:
        steps.append(n)
        if alt is not None and h > 0 and rng.random() < 0.3:
            steps.append(alt)
    walks.append(steps)
links = sorted({pair for steps in walks for pair in zip(steps, steps[1:])})

with open(a.out, "w") as out:
    out.write("H\tVN:Z:1.1\n")
    for i, length in lengths.items():
        out.write(f"S\t{i}\t*\tLN:i:{length}\n")
    for x, y in links:
        out.write(f"L\t{x}\t+\t{y}\t+\t0M\n")
    for h, steps in enumerate(walks):
        sample, hap = ("REF", 0) if h == 0 else (f"S{h:05d}", 1)
        end = sum(lengths[s] for s in steps)
        out.write(f"W\t{sample}\t{hap}\tchr1\t0\t{end}\t" + "".join(f">{s}" for s in steps) + "\n")
