#!/usr/bin/env python3
"""Link rows of a node and link index (format 2) on stdin that repeat one link under one
interval, either way round, plus the #samples count, the highest SB:H: bit set and whether
any sample name holds a comma. Usage: zcat f.graph.bed.gz | python3 -I duplicate-links.py <label>"""
import sys, collections
def flip(h): return h[:-1] + ('-' if h[-1] == '+' else '+')
seen = collections.Counter(); links = 0; samples = []; maxbit = -1
for line in sys.stdin:
    if line.startswith('#samples\t'):
        samples = line.rstrip('\n').split('\t')[1].split(','); continue
    if line[0] == '#': continue
    c = line.rstrip('\n').split('\t')
    for tag in c[9:]:
        if tag.startswith('SB:H:'):
            for i, ch in enumerate(tag[5:]):
                v = int(ch, 16)
                if v: maxbit = max(maxbit, 4 * i + v.bit_length() - 1)
    if c[3] != 'L': continue
    links += 1
    s, t = c[4], c[5]
    seen[(c[0], c[1], c[2]) + min((s, t), (flip(t), flip(s)))] += 1
dups = sum(v - 1 for v in seen.values() if v > 1)
print(f"{sys.argv[1]}\tlink rows {links}\tduplicate rows {dups}\tsamples {len(samples)}\thighest bit {maxbit}\tcomma-free {all(',' not in s for s in samples)}")
