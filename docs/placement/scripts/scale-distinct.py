#!/usr/bin/env python3
"""How many distinct walk rows a tile holds as haplotypes are added.

scale-distinct.py SEQUENCE WINDOWS.tsv SEED NAME=WALKS...

For the tile each WINDOWS.tsv start begins, reads the walk rows of each walk
file's tile unit and counts the rows and the distinct rows, two rows being
the same where everything after the name and the contig stretch (columns 8
on) is. Counted over every haplotype of the file, and, of the real
haplotypes (those not named SYN...), over random subsets of 58, 116, 231 and
462 of them drawn with SEED, and of the synthetic ones over random subsets
of 1536 and 4536 where the file has that many. Prints one row per file,
tile and subset.
"""

import gzip
import random
import sys


def table(walks, sequence):
    with open(walks + ".idx") as f:
        offset, length = next(map(int, line.split("\t")[1:3]) for line in f if line.split("\t")[0] == sequence)
    with open(walks, "rb") as f:
        f.seek(offset)
        text = gzip.decompress(f.read(length)).decode()
    return {
        int(cols[5]): (int(cols[6]), int(cols[7]))
        for cols in (line.split("\t") for line in text.splitlines())
        if cols[0] == "#entry" and cols[4] == "tile"
    }


def walk_rows(walks, offset, length):
    with open(walks, "rb") as f:
        f.seek(offset)
        text = gzip.decompress(f.read(length)).decode()
    rows = {}
    for line in text.splitlines():
        cols = line.split("\t")
        if len(cols) > 7 and cols[3] == "walk":
            hap = "#".join(cols[4].split("#")[:2])
            rows.setdefault(hap, []).append("\t".join(cols[7:]))
    return rows


def main():
    sequence, windows, seed = sys.argv[1], sys.argv[2], int(sys.argv[3])
    with open(windows) as f:
        header = f.readline().rstrip("\n").split("\t")
        starts = [int(line.split("\t")[header.index("start")]) for line in f]
    print("graph\ttile\tsubset\thaplotypes\trows\tdistinct")
    for graph in sys.argv[4:]:
        name, walks = graph.split("=")
        tiles = table(walks, sequence)
        for start in starts:
            rows = walk_rows(walks, *tiles[start])
            real = sorted(h for h in rows if not h.startswith("SYN"))
            synth = sorted(h for h in rows if h.startswith("SYN"))
            rng = random.Random(seed + start)
            subsets = [("all", sorted(rows))]
            subsets += [(f"real{k}", rng.sample(real, k)) for k in (58, 116, 231, 462) if k <= len(real)]
            subsets += [(f"syn{k}", rng.sample(synth, k)) for k in (1536, 4536) if k <= len(synth)]
            for label, haps in subsets:
                picked = [r for h in haps for r in rows[h]]
                print(f"{name}\t{start}\t{label}\t{len(haps)}\t{len(picked)}\t{len(set(picked))}", flush=True)


main()
