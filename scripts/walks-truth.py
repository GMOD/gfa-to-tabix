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

  walks-truth.py rebuild WALKS GFA
      Rebuilds every W or P line from the file and compares it with the GFA,
      step for step: the file holds exactly the lines with a step on a node
      of the reference's own lines (0 bp segments dropped), each line's
      pieces, walk rows decoded by the spec's rules and abridged pieces from
      their detail units, are numbered from 0 and start where the piece
      before ends, and joined they give the line's handles exactly; the
      reference's own lines likewise from their ref rows, lengths included.
      Each abridged row agrees with its piece in the detail unit it names:
      its start and end are the piece's first and last steps on R, at their
      positions, its hapOffset and bp the piece's stretch from one to the
      other, its nsteps all the piece's steps. Prints each line or abridged
      row that differs and exits 1 if any does.

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
import hashlib
import itertools
import re
import sys
import zlib
from array import array
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
        return sum(self.len[i] if i is not None else self.nodes[h >> 1] for h, i in self.steps(c))

    def nearest(self, node, i):
        """The position of `node` in R nearest position i, the later on a tie."""
        return min(reversed(self.occ[node]), key=lambda j: abs(j - i))

    def ends(self, start, end):
        """An abridged row's start and end as (handle, position in R): start at
        occurrence k with @k, else the first; end at k with @k, else nearest start's."""
        h, _, k = start.partition("@")
        e, _, ke = end.partition("@")
        i = self.occ[int(h) >> 1][int(k) if k else 0]
        return (int(h), i), (int(e), self.occ[int(e) >> 1][int(ke)] if ke else self.nearest(int(e) >> 1, i))

    def steps(self, c):
        """A walk row's steps as (handle, position in R or None), by the spec's decoding rules."""
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
            j = i + 1 if self.h[i] == h else i - 1
            if not 0 <= j < len(self.h):
                raise ValueError(f"a step off the end of R from position {i}")
            return (j, self.h[j]) if j > i else (j, self.h[j] ^ 1)

        out = []
        if choices and oriented(*choices[0][:2])[0] is None:
            out = [(g, None) for g in oriented(*choices[0][:2])[1]]
            choices = choices[1:]
        h = int(start)
        i = self.occ[h >> 1][int(k) if k else 0]
        out.append((h, i))
        for rid, flip, entry_k, exit_k in choices:
            e, inter, x = oriented(rid, flip)
            target = self.occ[e >> 1][int(entry_k)] if entry_k else None
            while (i != target) if entry_k else (h != e):
                i, h = along(i, h)
                out.append((h, i))
            out += [(g, None) for g in inter]
            if x is None:
                break
            i, h = (self.occ[x >> 1][int(exit_k)] if exit_k else self.nearest(x >> 1, i)), x
            out.append((h, i))
        while len(out) < nsteps:
            i, h = along(i, h)
            out.append((h, i))
        return out


def digest(handles, lengths=None):
    return hashlib.blake2b(array("q", handles).tobytes() + (array("q", lengths).tobytes() if lengths else b""),
                           digest_size=16).digest()


class Piece:
    """One row's piece: its line, where it lies, its bp and a digest of its handles
    (and lengths, for a ref row), or why it couldn't be decoded."""

    def __init__(self, c, seq, tile, handles=(), bp=0, lengths=None, error=None):
        self.line = (c[4], int(c[5]))
        self.offset, self.piece, self.nsteps, self.seq, self.tile = int(c[6]), int(c[7]), int(c[8]), seq, tile
        self.bp, self.ref, self.error = bp, lengths is not None, error
        self.decoded, self.ends = len(handles), (handles[0], handles[-1]) if handles else None
        self.digest = digest(handles, lengths)
        self.detail = self.stretch = None

    def key(self):
        return (self.line, self.offset, self.piece)


def stretch(steps, lens, offset):
    """A detail piece's first and last steps on R, its hapOffset at the first
    and the bp from the first to the last, or None with no step on R."""
    on = [k for k, (_, i) in enumerate(steps) if i is not None]
    return (steps[on[0]], steps[on[-1]], offset + sum(lens[:on[0]]), sum(lens[on[0]:on[-1] + 1])) if on else None


class Summary:
    """An abridged row: its start and end on R as (handle, position), its
    hapOffset, nsteps, bp and the detail record it names, or why its start
    or end isn't on R."""

    def __init__(self, c, tile, cs):
        self.line, self.piece, self.tile = (c[4], int(c[5])), int(c[7]), (c[0], cs)
        self.offset, self.nsteps, self.bp, self.detail = int(c[6]), int(c[8]), int(c[9]), int(c[12])
        try:
            self.ends, self.error = tile.ends(c[10], c[11]), None
        except (IndexError, ValueError) as e:
            self.ends, self.error = None, f"{type(e).__name__}: {e}"


def walk_rows(path, keep):
    """Pieces by path, for the paths `keep` takes, sorted by hapOffset: walk
    rows decoded, abridged pieces from their detail records; the reference's
    own pieces by path, from the ref rows; the abridged rows by path; the
    reference sample; each tile's extent by (seq, tile start); and the tile
    size. Holds a tile's R past the tile only where it has abridged rows."""
    rows, refs, abridged = defaultdict(list), defaultdict(list), defaultdict(list)
    extents, size, tiles, reference = {}, None, {}, None
    unit = filed = detail = None
    with gzip.open(path, "rt") as f:
        for line in f:
            if line.startswith("#walks"):
                size = tile_of(line)
            if line.startswith("#reference\t"):
                reference = line.rstrip("\n").split("\t")[1]
            if line.startswith("#unit\t"):
                c = line.rstrip("\n").split("\t")
                if filed in tiles and not tiles[filed].abridged:
                    del tiles[filed]
                unit = filed = detail = None
                if c[4] == "tile":
                    filed = (c[1], int(c[5]))
                    extents[filed] = (int(c[2]), int(c[3]))
                    unit = tiles[filed] = Tile()
                elif c[4] == "detail":
                    cs, d = c[5].split(":")
                    filed, detail = (c[1], int(cs)), int(d)
                    unit = tiles[filed].detail()
                continue
            if line[0] == "#" or unit is None:
                continue
            c = line.rstrip("\n").split("\t")
            if c[3] == "ref":
                lengths = [int(x) for x in c[10].split(",")]
                if keep(c[4]):
                    refs[c[4]].append(Piece(c, c[0], filed[1], handles(c[9])[0], sum(lengths), lengths))
            if c[3] != "walk":
                unit.add(c)
            if c[3] in ("walk", "abridged") and keep(c[4]):
                if not hasattr(unit, "h"):
                    unit.index()
                if c[3] == "abridged":
                    abridged[c[4]].append(Summary(c, unit, filed[1]))
                else:
                    try:
                        steps = unit.steps(c)
                        lens = [unit.len[i] if i is not None else unit.nodes[h >> 1] for h, i in steps]
                        piece = Piece(c, c[0], filed[1], [h for h, _ in steps], sum(lens))
                        if detail is not None:
                            piece.detail, piece.stretch = detail, stretch(steps, lens, int(c[6]))
                    except (KeyError, IndexError, ValueError) as e:
                        piece = Piece(c, c[0], filed[1], error=f"{type(e).__name__}: {e}")
                    rows[c[4]].append(piece)
    by_key = lambda ps: sorted(ps, key=Piece.key)
    return ({n: by_key(ps) for n, ps in rows.items()}, {n: by_key(ps) for n, ps in refs.items()},
            dict(abridged), reference, extents, size)


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
    pieces, _, _, _, extents, size = walk_rows(args.walks, lambda name: name.rsplit("#", 1)[0] in haps)
    broken = [p for ps in pieces.values() for p in ps if p.error]
    if broken:
        sys.exit(f"{len(broken)} walk rows don't decode, the first {broken[0].line} piece {broken[0].piece}: {broken[0].error}")
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
        for piece in ps:
            off, seq, cs, bp = piece.offset, piece.seq, piece.tile, piece.bp
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


def gfa_lines(path, reference):
    """The reference sample's lines, then a generator over every other W or P
    line, each as (name, start, handles, lengths), 0 bp segments dropped."""
    lengths, named = {}, {}
    with open(path) as f:
        for line in f:
            if line.startswith("S\t"):
                c = line.rstrip("\n").split("\t")
                lengths[int(c[1])] = len(c[2]) if c[2] != "*" else int(next(t[5:] for t in c[3:] if t.startswith("LN:i:")))

    def parse(line):
        c = line.rstrip("\n").split("\t")
        if c[0] == "W":
            key = (f"{c[1]}#{c[2]}#{c[3]}", int(c[4]))
            hs = [2 * int(x) + (s == "<") for s, x in re.findall(r"([<>])([^<>]+)", c[6])]
        else:
            named = (re.fullmatch(r"(.*)\[(\d+)(?:-[^\]]*)?\]", c[1]) or re.fullmatch(r"([^#]*#[^#]*#[^#]*)#(\d+)", c[1])
                     or re.fullmatch(r"(.*):(\d+)-\d+", c[1]))
            key = (named.group(1), int(named.group(2))) if named else (c[1], 0)
            hs = [2 * int(x[:-1]) + (x[-1] == "-") for x in c[2].split(",")] if c[2] != "*" else []
        hs = [h for h in hs if lengths[h >> 1]]
        return key, hs, [lengths[h >> 1] for h in hs]

    def lines(sample):
        with open(path) as f:
            for line in f:
                if line[0] in "WP" and line[1] == "\t":
                    key, hs, ls = parse(line)
                    if (key[0].split("#")[0] == reference) == sample:
                        yield key, hs, ls

    return list(lines(True)), lines(False)


def handle_text(h):
    return ("<" if h & 1 else ">") + str(h >> 1)


def place(step):
    return f"{handle_text(step[0])} at {step[1]}"


def rebuild(args):
    shard, shards = map(int, args.shard.split("/"))
    keep = lambda name: zlib.crc32(name.encode()) % shards == shard
    rows, refs, abridged, reference, _, _ = walk_rows(args.walks, keep)
    for name in abridged:
        rows.setdefault(name, [])
    held = defaultdict(list)
    for ps in list(rows.values()) + list(refs.values()):
        for p in ps:
            held[p.line].append(p)
    reference_lines, other_lines = gfa_lines(args.gfa, reference)
    on_reference = {h >> 1 for _, hs, _ in reference_lines for h in hs}
    wrong, expected, seen = [], 0, set()
    for (name, start), want, lengths in itertools.chain(reference_lines, other_lines):
        if not keep(name) or not any(h >> 1 in on_reference for h in want):
            continue
        expected += 1
        seen.add((name, start))
        ps = sorted(held.get((name, start), []), key=lambda p: p.piece)
        if not ps:
            wrong.append(f"{name} line at {start}: on the reference, with no rows")
            continue
        at, n, faults = start, 0, []
        if [p.piece for p in ps] != list(range(len(ps))):
            faults.append(f"pieces numbered {[p.piece for p in ps]}")
        for p in ps:
            where = f"piece {p.piece} in tile {p.seq}:{p.tile}"
            if p.error:
                faults.append(f"{where} doesn't decode: {p.error}")
            elif p.nsteps != p.decoded:
                faults.append(f"{where} says {p.nsteps} steps and decodes to {p.decoded}")
            if p.offset != at:
                faults.append(f"{where} starts at {p.offset}, the piece before ends at {at}")
            if not p.error and p.digest != digest(want[n:n + p.decoded], lengths[n:n + p.decoded] if p.ref else None):
                gfa = f"the GFA's steps {n} to {n + p.decoded} run {handle_text(want[n])} to {handle_text(want[min(n + p.decoded, len(want)) - 1])}" if n < len(want) else "the GFA's line has ended"
                faults.append(f"{where} runs {handle_text(p.ends[0])} to {handle_text(p.ends[1])}, {gfa}")
            n += p.decoded
            at = p.offset + p.bp
        if n != len(want) and not faults:
            faults.append(f"{n} steps rebuilt, the GFA's line has {len(want)}")
        if faults:
            wrong.append(f"{name} line at {start}: " + "; ".join(faults[:3]))
    for name, start in sorted(set(held) - seen):
        wrong.append(f"{name} line at {start}: rows for a line not on the reference, or not in the GFA")
    detailed = {(p.line, p.piece): p for ps in rows.values() for p in ps if p.detail is not None}
    summaries = [s for ss in abridged.values() for s in ss]
    for s in summaries:
        where = f"{s.line[0]} line at {s.line[1]}: abridged row of piece {s.piece} in tile {s.tile[0]}:{s.tile[1]}"
        p = detailed.get((s.line, s.piece))
        if s.error:
            wrong.append(f"{where} has a start or end not on R: {s.error}")
        elif p is None:
            wrong.append(f"{where} has no walk row in a detail unit")
        elif p.stretch is None:
            if not p.error:
                wrong.append(f"{where}: its walk row in detail unit {p.detail} has no step on R")
        else:
            first, last, offset, bp = p.stretch
            differs = [(what, a, b) for what, a, b in (("start", place(s.ends[0]), place(first)), ("end", place(s.ends[1]), place(last)),
                                                       ("hapOffset", s.offset, offset), ("nsteps", s.nsteps, p.decoded),
                                                       ("bp", s.bp, bp), ("detail", s.detail, p.detail)) if a != b]
            if differs:
                wrong.append(f"{where} says {', '.join(f'{w} {a}' for w, a, _ in differs)}; "
                             f"its piece in detail unit {p.detail} has {', '.join(f'{w} {b}' for w, _, b in differs)}")
    for w in wrong:
        print("  " + w)
    print(f"{args.walks}: shard {args.shard}: {len(held)} lines with rows, {expected} on the reference in the GFA, "
          f"{len(summaries)} abridged rows, {len(wrong)} wrong")
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
    d = sub.add_parser("rebuild")
    d.add_argument("walks")
    d.add_argument("gfa")
    d.add_argument("--shard", default="0/1", help="I/N: check the lines whose path name hashes to I of N")
    c = sub.add_parser("cost")
    c.add_argument("walks")
    c.add_argument("--top", type=int, default=5)
    args = p.parse_args()
    {"lift": lift, "score": score, "rebuild": rebuild, "cost": cost}[args.cmd](args)


if __name__ == "__main__":
    main()
