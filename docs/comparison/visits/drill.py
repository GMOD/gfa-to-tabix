#!/usr/bin/env python3
"""drill.py OUTDIR: per (window, haplotype, node) differences between
drill-truth.tsv and drill-cut.tsv, by whether the reference sample passes
the node once."""

import sys

import numpy as np

d = sys.argv[1]
multi = np.fromfile(f"{d}/multi.bin", dtype=np.uint8)


def load(path):
    out = {}
    with open(path) as f:
        for line in f:
            w, hap, node, c = line.split("\t")
            out[(int(w), hap, int(node))] = int(c)
    return out


truth, cut = load(f"{d}/drill-truth.tsv"), load(f"{d}/drill-cut.tsv")
diff = {"single": [0, 0, 0], "multi": [0, 0, 0]}
examples = []
for key in truth.keys() | cut.keys():
    t, c = truth.get(key, 0), cut.get(key, 0)
    if t != c:
        cls = "multi" if multi[key[2]] else "single"
        diff[cls][0] += 1
        diff[cls][1] += t
        diff[cls][2] += c
        if cls == "single" and len(examples) < 10:
            examples.append((key, t, c))
for cls, (n, t, c) in diff.items():
    print(f"{cls}: differing (window, haplotype, node) {n}, visits truth {t} cut {c}")
for key, t, c in examples:
    print(f"  {key}: truth {t}, cut {c}")
