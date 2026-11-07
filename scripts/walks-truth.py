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

  walks-truth.py pieces WALKS GFA
      Checks the bp it reads for each piece: every W or P line with rows in
      the file has pieces summing to its length in the GFA. Exits 1 if any
      line's do not.

  walks-truth.py cost WALKS
      Per window of one tile at each tile's start: the walk rows and steps of
      the tiles it reads, and the compressed bytes of those tiles and of the
      departure blocks it reads, from the unit tables, against the readers'
      budgets (8 MB, 32 M steps read).

Each piece's bp is its steps' lengths, from its walk row decoded by the
spec's rules, in its tile or, for an abridged piece, its detail record.
`score` streams the walk file; `cost` reads its units by offset.
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


def handles(field, prev=0):
    out = []
    for token in [] if field == "." else field.split(","):
        prev += int(token) >> 1
        out.append(2 * prev + (int(token) & 1))
    return out, prev


class Tile:
    """A tile's R, routes and route interior lengths, to decode its walk rows."""

    def __init__(self):
        self.refs, self.routes, self.nodes, self.prev, self.abridged = [], [], {}, 0, False

    def add(self, c):
        if c[3] == "ref":
            self.refs.append((int(c[6]), handles(c[9])[0], [int(x) for x in c[10].split(",")]))
        elif c[3] == "nodes":
            ids = [0]
            for d in c[4].split(","):
                ids.append(ids[-1] + int(d))
            self.nodes.update(zip(ids[1:], (int(x) for x in c[5].split(","))))
        elif c[3] == "route":
            ends = []
            for field in c[4:7]:
                hs, self.prev = handles(field, self.prev)
                ends.append(hs)
            self.routes.append((ends[0][0] if ends[0] else None, ends[1], ends[2][0] if ends[2] else None))
        elif c[3] == "abridged":
            self.abridged = True

    def index(self):
        self.h, self.len = [], []
        for _, hs, lens in sorted(self.refs):
            self.h += hs
            self.len += lens
        self.occ = defaultdict(list)
        for i, h in enumerate(self.h):
            self.occ[h >> 1].append(i)
        return self

    def detail(self):
        """A detail record of this tile: its R, with routes of its own."""
        d = Tile()
        if not hasattr(self, "h"):
            self.index()
        d.h, d.len, d.occ = self.h, self.len, self.occ
        return d

    def bp(self, c):
        """The bp of a walk row's steps, by the spec's decoding rules."""
        nsteps = int(c[8])
        start, _, k = c[9].partition("@")
        choices = []
        prev = 0
        for token in [] if c[10] == "." else c[10].split(","):
            token, _, exit_k = token.partition("@")
            token, _, entry_k = token.partition(":")
            prev += int(token) >> 1
            choices.append((prev, int(token) & 1, entry_k, exit_k))

        def oriented(rid, flip):
            e, inter, x = self.routes[rid]
            return (x ^ 1 if x is not None else None, [g ^ 1 for g in reversed(inter)],
                    e ^ 1 if e is not None else None) if flip else (e, inter, x)

        def along(i, h):
            return (i + 1, self.h[i + 1]) if self.h[i] == h else (i - 1, self.h[i - 1] ^ 1)

        total = count = 0
        if choices and oriented(*choices[0][:2])[0] is None:
            inter = oriented(*choices[0][:2])[1]
            total, count, choices = sum(self.nodes[g >> 1] for g in inter), len(inter), choices[1:]
        h = int(start)
        i = self.occ[h >> 1][int(k) if k else 0]
        total, count = total + self.len[i], count + 1
        for rid, flip, entry_k, exit_k in choices:
            e, inter, x = oriented(rid, flip)
            target = self.occ[e >> 1][int(entry_k)] if entry_k else None
            while (i != target) if entry_k else (h != e):
                i, h = along(i, h)
                total, count = total + self.len[i], count + 1
            total, count = total + sum(self.nodes[g >> 1] for g in inter), count + len(inter)
            if x is None:
                break
            near = min(reversed(self.occ[x >> 1]), key=lambda j: abs(j - i))
            i, h = (self.occ[x >> 1][int(exit_k)] if exit_k else near), x
            total, count = total + self.len[i], count + 1
        while count < nsteps:
            i, h = along(i, h)
            total, count = total + self.len[i], count + 1
        return total


def walk_rows(path, haps):
    """Pieces by path, sorted: [(record start, hapOffset, nsteps, seq, tile start, bp)],
    abridged pieces from their detail records; each tile's extent by (seq,
    tile start); and the tile size. Holds a tile's R past the tile only
    where it has abridged rows."""
    rows = defaultdict(list)
    extents, size, tiles = {}, None, {}
    unit = filed = None
    with gzip.open(path, "rt") as f:
        for line in f:
            if line.startswith("#walks"):
                size = tile_of(line)
            if line.startswith("#unit\t"):
                c = line.rstrip("\n").split("\t")
                if filed in tiles and not tiles[filed].abridged:
                    del tiles[filed]
                unit = filed = None
                if c[4] == "tile":
                    filed = (c[1], int(c[5]))
                    extents[filed] = (int(c[2]), int(c[3]))
                    unit = tiles[filed] = Tile()
                elif c[4] == "detail":
                    filed = (c[1], int(c[5].split(":")[0]))
                    unit = tiles[filed].detail()
                continue
            if line[0] == "#" or unit is None:
                continue
            c = line.rstrip("\n").split("\t")
            if c[3] != "walk":
                unit.add(c)
            elif haps is None or c[4].rsplit("#", 1)[0] in haps:
                if not hasattr(unit, "h"):
                    unit.index()
                rows[c[4]].append((int(c[5]), int(c[6]), int(c[8]), c[0], filed[1], unit.bp(c)))
    return {name: sorted(ps) for name, ps in rows.items()}, extents, size


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
    data = open(args.walks, "rb")

    def unit(offset, length):
        data.seek(int(offset))
        return gzip.decompress(data.read(int(length))).decode().splitlines()[1:]

    directory = [line.split("\t") for line in open(args.walks + ".idx").read().splitlines()]
    size = tile_of("\t".join(directory[0]))
    units = []
    for seq, offset, length in (c for c in directory[1:] if c[0] != "#header"):
        for entry in unit(offset, length):
            _, _, lo, hi, kind, _, at, n = entry.split("\t")
            rows = steps = 0
            if kind == "tile":
                for line in unit(at, n):
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


def pieces(args):
    lengths, lines = {}, {}
    with open(args.gfa) as f:
        for line in f:
            c = line.rstrip("\n").split("\t")
            if c[0] == "S":
                lengths[c[1]] = len(c[2]) if c[2] != "*" else int(next(t[5:] for t in c[3:] if t.startswith("LN:i:")))
            elif c[0] == "W":
                lines[(f"{c[1]}#{c[2]}#{c[3]}", int(c[4]))] = re.findall(r"[<>]([^<>]+)", c[6])
            elif c[0] == "P":
                named = (re.fullmatch(r"(.*)\[(\d+)(?:-[^\]]*)?\]", c[1]) or re.fullmatch(r"([^#]*#[^#]*#[^#]*)#(\d+)", c[1])
                         or re.fullmatch(r"(.*):(\d+)-\d+", c[1]))
                key = (named.group(1), int(named.group(2))) if named else (c[1], 0)
                lines[key] = [x.rstrip("+-") for x in c[2].split(",")]
    rows, _, _ = walk_rows(args.walks, None)
    read = defaultdict(int)
    for name, ps in rows.items():
        for rec, _, _, _, _, bp in ps:
            read[(name, rec)] += bp
    with gzip.open(args.walks, "rt") as f:
        for line in f:
            c = line.split("\t", 6)
            if line[0] != "#" and c[3] in ("walk", "abridged") and (c[4], int(c[5])) not in read:
                read[(c[4], int(c[5]))] = 0
    wrong = [(k, n, sum(lengths[x] for x in lines.get(k, []))) for k, n in sorted(read.items())
             if n != sum(lengths[x] for x in lines.get(k, []))]
    for (name, start), n, want in wrong:
        print(f"  {name} line at {start}: pieces hold {n} bp, the line {want}")
    print(f"{args.walks}: {len(read)} W lines with rows, {len(wrong)} whose pieces' bp differ from the line")
    sys.exit(1 if wrong else 0)


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
    d = sub.add_parser("pieces")
    d.add_argument("walks")
    d.add_argument("gfa")
    c = sub.add_parser("cost")
    c.add_argument("walks")
    c.add_argument("--top", type=int, default=5)
    args = p.parse_args()
    {"lift": lift, "score": score, "pieces": pieces, "cost": cost}[args.cmd](args)


if __name__ == "__main__":
    main()
