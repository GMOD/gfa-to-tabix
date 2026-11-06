#!/usr/bin/env python3
"""walks-truth.py: score a --walks file against alignments of its haplotypes
to its reference, and measure what a window costs to read.

  walks-truth.py lift ALIGN.paf.gz SEQ [SEQ ...] > lift.tsv
      Keeps the alignments onto the named reference sequences (PanSN names,
      e.g. GRCh38#0#chr22) and cuts each at indels of --gap bp or more into
      blocks: query, qstart, qend, target, tstart, tend, strand.

  walks-truth.py score lift.tsv WALKS [--haps H,H,...] [--regions R.tsv]
      For each haplotype path in both, compares where its pieces are filed
      with where their bases align. A window over tile c, [c, c + tile),
      reads every tile whose extent overlaps it (walk format 7), so a piece
      in tile f is visible where its bases align, at c, when f's extent
      overlaps c's stretch. It prints:
        placement  aligned piece bp visible where they align, and the same
                   over query bases counted once (the truth maps a base to
                   several copies in segmental duplications)
        piece      pieces with aligned bases, and the share of them with some
                   aligned bases visible where filed
        recall     (haplotype, tile) pairs holding --present aligned bp that
                   a window there sees: "listed" when any piece of the
                   haplotype is in a tile it reads, "strict" when such a
                   piece's own bases align into the tile
        lost       strict misses by whether the pair's aligned bases sit in
                   pieces filed out of reach (elsewhere) or in none (absent)
        pieces     pieces per filed (haplotype, tile) pair: 1 when each
                   haplotype enters each tile once
      R.tsv (name, sequence, start, end) repeats the figures per region.

  walks-truth.py cost WALKS
      Per window of one tile at each tile's start: the walk rows and steps of
      the tiles it reads, and the compressed bytes of those tiles and of the
      departure blocks it reads, from the unit tables, against the readers'
      budgets (8 MB, 32 M steps read).

A last piece's length is unknown from the walk rows, so it takes the record's
mean bp per step. Walk files are read whole.
"""

import argparse
import bisect
import gzip
import re
import sys
from collections import defaultdict

CIGAR = re.compile(rb"(\d+)([=XIDM])")
BYTE_BUDGET = 8 << 20
STEP_BUDGET = 32_000_000


def lift(args):
    want = {s.encode() for s in args.seqs}
    out = sys.stdout
    with gzip.open(args.paf, "rb") as f:
        for line in f:
            cols = line.split(b"\t", 12)
            if cols[5] not in want:
                continue
            q, qs, qe, strand, t, ts = cols[0], int(cols[2]), int(cols[3]), cols[4], cols[5], int(cols[7])
            cg = next((c[5:] for c in line.rstrip(b"\n").split(b"\t")[12:] if c.startswith(b"cg:Z:")), None)
            if cg is None:
                continue
            forward = strand == b"+"
            qpos = qs if forward else qe
            tpos = ts
            block = None

            def flush():
                if block and block[1] != block[0]:
                    a, b, ta, tb = block
                    lo, hi = (a, b) if forward else (b, a)
                    out.write(f"{q.decode()}\t{lo}\t{hi}\t{t.decode()}\t{ta}\t{tb}\t{'+' if forward else '-'}\n")

            for n, op in CIGAR.findall(cg):
                n = int(n)
                if op in b"=XM":
                    step = n if forward else -n
                    if block is None:
                        block = [qpos, qpos + step, tpos, tpos + n]
                    else:
                        block[1] = qpos + step
                        block[3] = tpos + n
                    qpos += step
                    tpos += n
                else:
                    big = n >= args.gap
                    if big:
                        flush()
                        block = None
                    if op == b"I":
                        qpos += n if forward else -n
                    else:
                        tpos += n
                    if not big and block is not None:
                        block[1] = qpos
                        block[3] = tpos
            flush()


class Truth:
    """Aligned blocks of one query contig, sorted by query start."""

    def __init__(self):
        self.blocks = []

    def finish(self):
        self.blocks.sort()
        self.starts = [b[0] for b in self.blocks]
        self.longest = max((b[1] - b[0] for b in self.blocks), default=0)

    def spans(self, lo, hi):
        """(qa, qb, target, ta, tb) for each block's share of query lo..hi."""
        k = bisect.bisect_left(self.starts, lo - self.longest)
        while k < len(self.blocks) and self.blocks[k][0] < hi:
            qs, qe, t, ts, te, forward = self.blocks[k]
            k += 1
            a, b = max(lo, qs), min(hi, qe)
            if a >= b:
                continue
            if forward:
                yield a, b, t, ts + (a - qs), ts + (b - qs)
            else:
                yield a, b, t, ts + (qe - b), ts + (qe - a)


def read_lift(path, names):
    truth = defaultdict(Truth)
    with open(path) as f:
        for line in f:
            q, qs, qe, t, ts, te, strand = line.rstrip("\n").split("\t")
            if q in names:
                truth[q].blocks.append((int(qs), int(qe), t, int(ts), int(te), strand == "+"))
    for t in truth.values():
        t.finish()
    return truth


def tile_of(line):
    return int(re.search(r"tile:i:(\d+)", line).group(1))


def walk_rows(path, haps):
    """Pieces by path, sorted: [(record start, hapOffset, nsteps, seq, tile start, bp)];
    each tile's extent by (seq, tile start); and the tile size."""
    rows = defaultdict(list)
    extents, size, tile = {}, None, None
    with gzip.open(path, "rt") as f:
        for line in f:
            if line.startswith("#walks"):
                size = tile_of(line)
            if line.startswith("#unit\t"):
                c = line.rstrip("\n").split("\t")
                tile = (c[1], int(c[5])) if c[4] == "tile" else None
                if tile:
                    extents[tile] = (int(c[2]), int(c[3]))
                continue
            if line[0] == "#" or tile is None:
                continue
            c = line.split("\t", 9)
            if c[3] != "walk" or c[4].rsplit("#", 1)[0] not in haps:
                continue
            rows[c[4]].append((int(c[5]), int(c[6]), int(c[8]), c[0], tile[1]))
    pieces = {}
    for name, ps in rows.items():
        ps.sort()
        out = []
        first = 0
        for k, (rec, off, nsteps, seq, cs) in enumerate(ps):
            if k and ps[k - 1][0] != rec:
                first = k
            if k + 1 < len(ps) and ps[k + 1][0] == rec:
                bp = ps[k + 1][1] - off
            else:
                steps = sum(p[2] for p in ps[first:k])
                bp = round(nsteps * (off - ps[first][1]) / steps) if steps else nsteps * 30
            out.append((rec, off, nsteps, seq, cs, bp))
        pieces[name] = out
    return pieces, extents, size


def union(intervals):
    total, end = 0, -1
    for a, b in sorted(intervals):
        if b > end:
            total += b - max(a, end)
            end = b
    return total


def pct(a, b):
    return f"{100 * a / b:.2f}%" if b else "-"


def score(args):
    haps = set(args.haps.split(","))
    pieces, extents, size = walk_rows(args.walks, haps)
    truth = read_lift(args.lift, set(pieces))
    regions = []
    if args.regions:
        for line in open(args.regions):
            if line.strip() and line[0] != "#":
                n, s, a, b = line.split()[:4]
                regions.append((n, s, int(a), int(b)))

    def region_of(seq, cs):
        return next((n for n, s, a, b in regions if s == seq and a < cs + size and cs < b), "elsewhere")

    def visible(seq, filed, tseq, tc):
        lo, hi = extents[(seq, filed)]
        return seq == tseq and lo < tc + size and hi > tc

    total = defaultdict(int)
    by_region = defaultdict(lambda: defaultdict(int))
    for name, ps in pieces.items():
        t = truth.get(name)
        if t is None:
            total["paths without alignments"] += 1
            total["pieces without alignments"] += len(ps)
            continue
        total["paths"] += 1
        filed = defaultdict(set)
        present = defaultdict(int)
        seen_from = defaultdict(int)
        for rec, off, nsteps, seq, cs, bp in ps:
            filed[seq].add(cs)
            aligned = near = 0
            any_q, near_q = [], []
            for a, b, tseq, ta, tb in t.spans(off, off + bp):
                c = ta - ta % size
                while c < tb:
                    n = min(tb, c + size) - max(ta, c)
                    present[(tseq, c)] += n
                    aligned += n
                    if visible(seq, cs, tseq, c):
                        near += n
                        seen_from[(tseq, c)] += n
                    c += size
                any_q.append((a, b))
                if any(visible(seq, cs, tseq, c) for c in range(ta - ta % size, tb, size)):
                    near_q.append((a, b))
            for d in (total, by_region[region_of(seq, cs)]):
                d["pieces"] += 1
                d["piece bp"] += bp
                d["aligned bp"] += aligned
                d["visible bp"] += near
                d["query bp"] += union(any_q)
                d["visible query bp"] += union(near_q)
                d["aligned pieces"] += aligned > 0
                d["visible pieces"] += near > 0
        for (tseq, c), n in present.items():
            if n < args.present:
                continue
            listed = any(visible(tseq, f, tseq, c) for f in filed[tseq])
            strict = seen_from[(tseq, c)] > 0
            for d in (total, by_region[region_of(tseq, c)]):
                d["recall pairs"] += 1
                d["recall listed"] += listed
                d["recall strict"] += strict
                if not strict:
                    d["lost elsewhere"] += 1
        for seq, tiles in filed.items():
            for cs in tiles:
                by_region[region_of(seq, cs)]["filed pairs"] += 1
                total["filed pairs"] += 1

    def report(d, label):
        print(f"  {label:16} placement {pct(d['visible bp'], d['aligned bp']):>7} once {pct(d['visible query bp'], d['query bp']):>7}"
              f" | piece {pct(d['visible pieces'], d['aligned pieces']):>7} of {d['aligned pieces']}"
              f" | recall listed {pct(d['recall listed'], d['recall pairs']):>7} strict {pct(d['recall strict'], d['recall pairs']):>7}"
              f" of {d['recall pairs']}, lost elsewhere {d['lost elsewhere']}"
              f" | pieces {d['pieces'] / max(d['filed pairs'], 1):.2f} per pair")

    print(f"{args.walks}: tile {size}; {total['paths']} haplotype paths scored; "
          f"{total['paths without alignments']} without alignments hold {total['pieces without alignments']} pieces; "
          f"{pct(total['aligned bp'], total['piece bp'])} of scored piece bp align")
    report(total, "all")
    for n, *_ in regions:
        report(by_region[n], n)
    report(by_region["elsewhere"], "elsewhere")


def cost(args):
    data = open(args.walks, "rb").read()
    directory = [line.split("\t") for line in open(args.walks + ".idx").read().splitlines()]
    size = tile_of("\t".join(directory[0]))
    units = []
    for seq, offset, length in (c for c in directory[1:] if c[0] != "#header"):
        table = gzip.decompress(data[int(offset) : int(offset) + int(length)]).decode().splitlines()[1:]
        for entry in table:
            _, _, lo, hi, kind, _, at, n = entry.split("\t")
            rows = steps = 0
            if kind == "tile":
                for line in gzip.decompress(data[int(at) : int(at) + int(n)]).decode().splitlines()[1:]:
                    c = line.split("\t", 9)
                    if c[3] == "walk":
                        rows += 1
                        steps += int(c[8])
            if kind in ("tile", "departures"):
                units.append((seq, int(lo), int(hi), kind, int(n), rows, steps))
    by_seq = defaultdict(list)
    for u in units:
        by_seq[u[0]].append(u)
    windows = []
    for seq, us in by_seq.items():
        for _, lo, _, kind, *_ in us:
            if kind != "tile":
                continue
            cs = lo - lo % size
            read = [u for u in us if u[1] < cs + size and u[2] > cs]
            windows.append((sum(u[4] for u in read), sum(u[6] for u in read), sum(u[5] for u in read), seq, cs))
    windows.sort()

    def q(i, p):
        return sorted(w[i] for w in windows)[min(len(windows) - 1, int(p * len(windows)))]

    print(f"{args.walks}: tile {size}; {len(windows)} windows of one tile")
    for i, label in ((2, "walk rows"), (0, "gz bytes"), (1, "steps")):
        print(f"  {label:10} median {q(i, 0.5):>12,}  p90 {q(i, 0.9):>12,}  p99 {q(i, 0.99):>12,}  max {q(i, 1):>14,}")
    print(f"  windows over {BYTE_BUDGET >> 20} MB: {sum(w[0] > BYTE_BUDGET for w in windows)}; "
          f"over {STEP_BUDGET // 1_000_000} M steps: {sum(w[1] > STEP_BUDGET for w in windows)}")
    for w in windows[-args.top:][::-1]:
        print(f"    {w[3]}:{w[4]}  {w[0]:,} gz bytes  {w[1]:,} steps  {w[2]:,} walk rows")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("lift")
    a.add_argument("paf")
    a.add_argument("seqs", nargs="+")
    a.add_argument("--gap", type=int, default=20)
    b = sub.add_parser("score")
    b.add_argument("lift")
    b.add_argument("walks")
    b.add_argument("--haps", required=True, help="PanSN sample#haplotype list")
    b.add_argument("--regions")
    b.add_argument("--present", type=int, default=300)
    c = sub.add_parser("cost")
    c.add_argument("walks")
    c.add_argument("--top", type=int, default=5)
    args = p.parse_args()
    {"lift": lift, "score": score, "cost": cost}[args.cmd](args)


if __name__ == "__main__":
    main()
