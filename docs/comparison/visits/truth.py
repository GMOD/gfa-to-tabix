#!/usr/bin/env python3
"""truth.py GFA REF TILE OUTDIR [--drill W,W,...]

Visit counts of every haplotype (sample#hap) on the reference's nodes, per
window of TILE bp, straight from the GFA's W and P lines.

Pass 1 reads segment lengths and the lines named REF (PanSN, e.g.
GRCh38#0#chr22; W start column or P :start-end suffix as offset) and maps each
reference node to every window its interval overlaps, at any pass, and its
pass count, counted over every line of REF's sample as the file's `passes`
are. Writes OUTDIR/offsets.bin, wins.bin and multi.bin for cut.mjs, and each
node's start on REF (a pass's, -1 off it) and length for sub.mjs.

Pass 2 sketches, per (window, single|multi pass), the multiset of
(hap, node) visits: n, and two 32-bit sums of a hash of (hap, node), which
are linear in the counts, so lines of one haplotype add up. Writes
OUTDIR/truth.tsv and OUTDIR/haps.txt.

--drill writes OUTDIR/drill-truth.tsv: exact (window, hap, node, count) for
the listed windows.
"""

import gzip
import sys

import numpy as np

U32 = np.uint32


def fmix(h):
    h = h ^ (h >> U32(16))
    h = h * U32(0x85EBCA6B)
    h = h ^ (h >> U32(13))
    h = h * U32(0xC2B2AE35)
    return h ^ (h >> U32(16))


def hashes(hap, node):
    hap = U32(hap)
    node = node.astype(U32)
    h1 = fmix((hap * U32(0x9E3779B1)) ^ node)
    h2 = fmix(((node * U32(0xCC9E2D51)) ^ hap) ^ U32(0x1B873593))
    return h1, h2


def opener(path):
    return gzip.open(path, "rb") if path.endswith(".gz") else open(path, "rb")


W_STRIP = bytes.maketrans(b"<>", b"  ")
P_STRIP = bytes.maketrans(b"+-,", b"   ")


def steps(fields):
    if fields[0] == b"W":
        s = fields[6].translate(W_STRIP)
    else:
        s = fields[2].translate(P_STRIP)
    return np.array(s.split(), dtype=np.int64)


def line_name(fields):
    if fields[0] == b"W":
        return f"{fields[1].decode()}#{fields[2].decode()}#{fields[3].decode()}", int(fields[4])
    name = fields[1].decode()
    base, _, rng = name.rpartition(":")
    if base and "-" in rng and rng.replace("-", "").isdigit():
        return base, int(rng.split("-")[0])
    return name, 0


def hap_of(fields):
    if fields[0] == b"W":
        return f"{fields[1].decode()}#{fields[2].decode()}"
    return "#".join(fields[1].decode().split("#")[:2])


def main():
    gfa, ref, tile, outdir = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
    drill = set()
    if "--drill" in sys.argv:
        drill = {int(w) for w in sys.argv[sys.argv.index("--drill") + 1].split(",")}
    drill_list = np.array(sorted(drill), dtype=np.int64)

    lengths = {}
    ref_lines = []
    sample_lines = []
    sample_prefix = ref.rsplit("#", 1)[0] + "#"
    with opener(gfa) as f:
        for line in f:
            if line[:2] == b"S\t":
                fields = line.split(b"\t", 3)
                lengths[int(fields[1])] = len(fields[2].rstrip(b"\n"))
            elif line[:2] in (b"W\t", b"P\t"):
                fields = line.rstrip(b"\n").split(b"\t")
                name, start = line_name(fields)
                if name == ref:
                    ref_lines.append((start, steps(fields)))
                elif name.startswith(sample_prefix):
                    sample_lines.append(steps(fields))
    maxid = max(lengths)
    length = np.zeros(maxid + 1, dtype=np.int64)
    for k, v in lengths.items():
        length[k] = v
    del lengths
    print(f"pass 1: {len(ref_lines)} lines of {ref}, {len(sample_lines)} other lines of {sample_prefix}, max id {maxid}", file=sys.stderr)

    passes = np.zeros(maxid + 1, dtype=np.int32)
    for ids in sample_lines:
        np.add.at(passes, ids, 1)
    pair_nodes, pair_wins = [], []
    ref_start = np.full(maxid + 1, -1, dtype=np.int64)
    for start, ids in ref_lines:
        lens = length[ids]
        ends = start + np.cumsum(lens)
        begins = ends - lens
        np.add.at(passes, ids, 1)
        ref_start[ids] = begins
        real = lens > 0
        ids, begins, ends = ids[real], begins[real], ends[real]
        first = begins // tile
        last = (ends - 1) // tile
        span = (last - first + 1).astype(np.int64)
        rep_ids = np.repeat(ids, span)
        offs = np.arange(span.sum()) - np.repeat(np.cumsum(span) - span, span)
        pair_nodes.append(rep_ids)
        pair_wins.append(np.repeat(first, span) + offs)
    nodes = np.concatenate(pair_nodes)
    wins = np.concatenate(pair_wins)
    order = np.lexsort((wins, nodes))
    nodes, wins = nodes[order], wins[order]
    keep = np.ones(len(nodes), dtype=bool)
    keep[1:] = (nodes[1:] != nodes[:-1]) | (wins[1:] != wins[:-1])
    nodes, wins = nodes[keep], wins[keep]
    offsets = np.zeros(maxid + 2, dtype=np.int64)
    np.add.at(offsets, nodes + 1, 1)
    offsets = np.cumsum(offsets)
    multi = (passes > 1).astype(np.uint8)
    offsets.astype("<i4").tofile(f"{outdir}/offsets.bin")
    wins.astype("<i4").tofile(f"{outdir}/wins.bin")
    multi.tofile(f"{outdir}/multi.bin")
    ref_start.astype("<f8").tofile(f"{outdir}/start.bin")
    length.astype("<f8").tofile(f"{outdir}/length.bin")
    nwin = int(wins.max()) + 1
    print(
        f"reference nodes {int((passes > 0).sum())}, multi-pass {int(multi.sum())}, "
        f"node-window pairs {len(wins)}, windows {len(np.unique(wins))}",
        file=sys.stderr,
    )

    counts = np.zeros(2 * nwin, dtype=np.float64)
    sums = [np.zeros(2 * nwin, dtype=np.float64) for _ in range(4)]
    haps = {}
    drill_counts = {}
    nwin_of = offsets[1:] - offsets[:-1]
    with opener(gfa) as f:
        for line in f:
            if line[:2] not in (b"W\t", b"P\t"):
                continue
            fields = line.rstrip(b"\n").split(b"\t")
            hap = haps.setdefault(hap_of(fields), len(haps))
            ids = steps(fields)
            ids = ids[ids <= maxid]
            k = nwin_of[ids]
            ids = ids[k > 0]
            k = k[k > 0]
            if len(ids) == 0:
                continue
            rep = np.repeat(ids, k)
            within = np.arange(k.sum()) - np.repeat(np.cumsum(k) - k, k)
            w = wins[np.repeat(offsets[ids], k) + within].astype(np.int64)
            slot = 2 * w + multi[rep]
            h1, h2 = hashes(hap, rep)
            counts += np.bincount(slot, minlength=2 * nwin)
            for i, part in enumerate(
                (h1 & U32(0xFFFF), h1 >> U32(16), h2 & U32(0xFFFF), h2 >> U32(16))
            ):
                sums[i] += np.bincount(slot, weights=part.astype(np.float64), minlength=2 * nwin)
            if drill:
                sel = np.isin(w, drill_list)
                for wi, node in zip(w[sel].tolist(), rep[sel].tolist()):
                    if True:
                        key = (wi, hap, node)
                        drill_counts[key] = drill_counts.get(key, 0) + 1

    with open(f"{outdir}/haps.txt", "w") as out:
        for name in sorted(haps, key=haps.get):
            out.write(name + "\n")
    with open(f"{outdir}/truth.tsv", "w") as out:
        out.write("window\tpasses\tn\ts1\ts2\n")
        for slot in range(2 * nwin):
            if counts[slot] == 0:
                continue
            s1 = (int(sums[0][slot]) + (int(sums[1][slot]) << 16)) % 2**32
            s2 = (int(sums[2][slot]) + (int(sums[3][slot]) << 16)) % 2**32
            out.write(f"{slot // 2}\t{'multi' if slot % 2 else 'single'}\t{int(counts[slot])}\t{s1}\t{s2}\n")
    if drill:
        names = sorted(haps, key=haps.get)
        with open(f"{outdir}/drill-truth.tsv", "w") as out:
            for (wi, hap, node), c in sorted(drill_counts.items()):
                out.write(f"{wi}\t{names[hap]}\t{node}\t{c}\n")
    print(f"haplotypes {len(haps)}", file=sys.stderr)


main()
