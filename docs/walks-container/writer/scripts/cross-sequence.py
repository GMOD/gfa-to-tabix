#!/usr/bin/env python3
"""Counts, in a walk file, the places a W line's consecutive pieces lie on two
different reference sequences, and the lines whose pieces lie on more than one."""
import gzip, sys, collections
from array import array
seqs = {}; lines = {}
with gzip.open(sys.argv[1], "rt") as f:
    for line in f:
        if line[0] == "#": continue
        c = line.split("\t", 9)
        if c[3] in ("walk", "abridged"):
            key = (c[4], c[5])
            a = lines.get(key)
            if a is None: a = lines[key] = array("q")
            a.append((int(c[7]) << 40) | (seqs.setdefault(c[0], len(seqs)) << 32) | min(int(c[6]) >> 8, (1 << 32) - 1))
names = {v: k for k, v in seqs.items()}
main = lambda s: "_" not in s.split("#")[-1]
cross = collections.Counter(); kinds = collections.Counter(); multi = 0; pieces = 0; pairs = collections.Counter(); ex = []
for key, a in lines.items():
    ps = sorted(a); pieces += len(ps)
    ss = [(p >> 32) & 0xff for p in ps]
    n = sum(1 for i in range(1, len(ss)) if ss[i] != ss[i - 1])
    if len(set(ss)) > 1:
        multi += 1
        for i in range(1, len(ss)):
            if ss[i] != ss[i - 1]:
                a_, b_ = names[ss[i - 1]], names[ss[i]]
                k = ("main" if main(a_) else "other") + "->" + ("main" if main(b_) else "other")
                kinds[k] += 1; pairs[(a_, b_)] += 1
                if len(ex) < 8 and k == "main->main": ex.append((key, a_, b_, (ps[i] & 0xffffffff) << 8))
print(f"{len(lines)} lines with walk rows, {pieces} pieces; {multi} lines have pieces on more than one reference sequence")
print("transitions between consecutive pieces on different sequences:", sum(kinds.values()), dict(kinds))
print("most common pairs:", pairs.most_common(12))
print("examples main->main:", ex)
