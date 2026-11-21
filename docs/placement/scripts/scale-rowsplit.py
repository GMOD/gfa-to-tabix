#!/usr/bin/env python3
"""What per-group units would cut from a tile: its rows split by kind and group.

scale-rowsplit.py SEQUENCE WINDOWS.tsv GROUPS KEEP NAME=WALKS...

For the tile each WINDOWS.tsv start begins, gunzips each walk file's tile
unit and deflates (zlib level 6, as BGZF does, in one stream) the whole
tile; its shared rows (ref, nodes, route); its walk and abridged rows
together; and those rows cut into GROUPS units, the haplotypes in the
header's order dealt into GROUPS runs of consecutive haplotypes. Also the
groups holding the comma-separated sample#hap names of KEEP, so the bytes a
reader keeping them would fetch: the shared rows plus those groups. Prints
one row per file and tile, bytes compressed.
"""

import gzip
import sys
import zlib


def deflated(lines):
    return len(zlib.compress("".join(lines).encode(), 6)) if lines else 0


def directory(walks, sequence):
    with open(walks + ".idx") as f:
        rows = [line.rstrip("\n").split("\t") for line in f]
    header = next(r for r in rows if r[0] == "#header")
    table = next(r for r in rows if r[0] == sequence)
    return (int(header[1]), int(header[2])), (int(table[1]), int(table[2]))


def unit(walks, offset, length):
    with open(walks, "rb") as f:
        f.seek(offset)
        return gzip.decompress(f.read(length)).decode()


def main():
    sequence, windows, groups, keep = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4].split(",")
    with open(windows) as f:
        head = f.readline().rstrip("\n").split("\t")
        starts = [int(line.split("\t")[head.index("start")]) for line in f]
    print("graph\ttile\ttile_bytes\tshared_bytes\twalk_bytes\tgrouped_walk_bytes\tkept_groups\tkept_bytes\trows\tabridged_rows")
    for graph in sys.argv[5:]:
        name, walks = graph.split("=")
        header, table = directory(walks, sequence)
        haplotypes = [line.split("\t")[1] for line in unit(walks, *header).splitlines() if line.startswith("#haplotype\t")]
        group_of = {h: i * groups // len(haplotypes) for i, h in enumerate(haplotypes)}
        kept = {group_of[h] for h in keep if h in group_of}
        tiles = {
            int(c[5]): (int(c[6]), int(c[7]))
            for c in (line.split("\t") for line in unit(walks, *table).splitlines())
            if c[0] == "#entry" and c[4] == "tile"
        }
        for start in starts:
            if start in tiles:
                lines = unit(walks, *tiles[start]).splitlines(keepends=True)
                shared, walk, by_group = [], [], [[] for _ in range(groups)]
                abridged = 0
                for line in lines:
                    cols = line.split("\t", 6)
                    kind = cols[3] if len(cols) > 3 else ""
                    if kind in ("walk", "abridged"):
                        walk.append(line)
                        hap = "#".join(cols[4].split("#")[:2])
                        by_group[group_of.get(hap, 0)].append(line)
                        abridged += kind == "abridged"
                    else:
                        shared.append(line)
                grouped = [deflated(g) for g in by_group]
                kept_bytes = deflated(shared) + sum(grouped[g] for g in kept)
                print(
                    f"{name}\t{start}\t{deflated(lines)}\t{deflated(shared)}\t{deflated(walk)}\t{sum(grouped)}"
                    f"\t{len(kept)}\t{kept_bytes}\t{len(walk)}\t{abridged}",
                    flush=True,
                )


main()
