"""Decode a walk format 6 file into pieces, chunk by chunk, per
docs/walks-format.md. Written for files whose reference passes every node
more than once too: `start@k`, `:k` and `@k` name the copy as the spec says.

A chunk decodes to R, the chunk's reference path, and its pieces. Each piece
is a trace: an optional leading interior, then R segments and interiors in
turn, where an R segment (a, b) follows R from position a to position b
inclusive, backward when b < a.
"""
import gzip
import sys
from collections import defaultdict


def tokens(col):
    return [] if col == "." else [int(t) for t in col.split(",")]


def handles(col, prev=0):
    out = []
    for t in tokens(col):
        prev += t >> 1
        out.append(2 * prev + (t & 1))
    return out, prev


def flip(h):
    return h ^ 1


class Chunk:
    def __init__(self, seq, cs):
        self.seq = seq
        self.cs = cs
        self.ref = []
        self.nodes = {}
        self.routes = []
        self.walks = []
        self.abridged = []
        self.R = None
        self.pos = None
        self.offset = None
        self.nodeLen = None

    def finish(self):
        self.ref.sort(key=lambda r: int(r[6]))
        R, lengths, passes = [], [], []
        for r in self.ref:
            hs, _ = handles(r[9])
            R += hs
            lengths += tokens(r[10])
            passes += tokens(r[11]) if r[11] != "." else [1] * len(hs)
        self.R = R
        self.lengths = lengths
        self.passes = passes
        self.offset = []
        o = int(self.ref[0][6]) if self.ref else 0
        for ln in lengths:
            self.offset.append(o)
            o += ln
        self.end = o
        self.ends = [o + ln for o, ln in zip(self.offset, lengths)]
        self.prefix = [0]
        for ln in lengths:
            self.prefix.append(self.prefix[-1] + ln)
        self.pos = defaultdict(list)
        for i, h in enumerate(R):
            self.pos[h >> 1].append(i)
        self.nodeLen = dict(zip((h >> 1 for h in R), lengths))
        self.nodeLen.update(self.nodes)


def parse_nodes(cols, into):
    ids = tokens(cols[4])
    lens = tokens(cols[5])
    nid = 0
    for d, ln in zip(ids, lens):
        nid += d
        into[nid] = ln


def parse_routes(rows):
    prev = 0
    routes = []
    for cols in rows:
        entry = interior = exit = None
        if cols[4] != ".":
            hs, prev = handles(cols[4], prev)
            entry = hs[0]
        interior, prev = handles(cols[5], prev)
        if cols[6] != ".":
            hs, prev = handles(cols[6], prev)
            exit = hs[0]
        routes.append((entry, interior, exit))
    return routes


def taken(route, f):
    entry, interior, exit = route
    if f:
        return (None if exit is None else flip(exit), [flip(h) for h in reversed(interior)], None if entry is None else flip(entry))
    return route


class Piece:
    __slots__ = ("path", "fragStart", "hapOffset", "piece", "nsteps", "lead", "segments", "interiors", "openEnd")

    def __init__(self, path, fragStart, hapOffset, piece, nsteps):
        self.path = path
        self.fragStart = fragStart
        self.hapOffset = hapOffset
        self.piece = piece
        self.nsteps = nsteps
        self.lead = []
        self.segments = []
        self.interiors = []
        self.openEnd = False


def occurrence(cols_token):
    """Split a token into (text, k-after-colon, k-after-at)."""
    at = colon = None
    t = cols_token
    if "@" in t:
        t, k = t.split("@")
        at = int(k)
    if ":" in t:
        t, k = t.split(":")
        colon = int(k)
    return t, colon, at


def decode_walk(chunk, cols, routes):
    path, fragStart, hapOffset, piece, nsteps = cols[4], int(cols[5]), int(cols[6]), int(cols[7]), int(cols[8])
    p = Piece(path, fragStart, hapOffset, piece, nsteps)
    R = chunk.R
    pos = chunk.pos
    startText, _, startAt = occurrence(cols[9])
    start = int(startText)
    choices = []
    prev = 0
    for tok in ([] if cols[10] == "." else cols[10].split(",")):
        text, colon, at = occurrence(tok)
        t = int(text)
        prev += t >> 1
        choices.append((taken(routes[prev], t & 1), colon, at))
    cur = pos[start >> 1][startAt or 0]
    steps = 0
    i = 0
    if choices and choices[0][0][0] is None:
        p.lead = choices[0][0][1]
        steps += len(p.lead)
        assert choices[0][0][2] == start, (path, piece)
        i = 1
    direction = 1 if R[cur] == start else -1

    def handle_at(j, d):
        return R[j] if d == 1 else flip(R[j])

    for (entry, interior, exit), colon, at in choices[i:]:
        if colon is not None:
            target = pos[entry >> 1][colon]
        else:
            cands = pos[entry >> 1]
            target = None
            for j in (cands if direction == 1 else reversed(cands)):
                if (j >= cur if direction == 1 else j <= cur) and handle_at(j, direction) == entry:
                    target = j
                    break
            assert target is not None, (path, piece, cur, entry)
        if target != cur:
            d = 1 if target > cur else -1
            assert d == direction, (path, piece, cur, target, direction)
        assert handle_at(target, direction) == entry, (path, piece)
        p.segments.append((cur, target, direction))
        steps += abs(target - cur) + 1
        p.interiors.append(interior)
        steps += len(interior)
        if exit is None:
            p.openEnd = True
            assert steps == nsteps, (path, piece, steps, nsteps)
            return p
        cands = pos[exit >> 1]
        if at is not None:
            cur = cands[at]
        else:
            cur = min(cands, key=lambda j: (abs(j - target), -j))
        direction = 1 if R[cur] == exit else -1
    remaining = nsteps - steps
    assert remaining >= 1, (path, piece, steps, nsteps)
    p.segments.append((cur, cur + direction * (remaining - 1), direction))
    return p


def expand(chunk, p):
    """Explicit steps: (handle, R position or -1) in walk order."""
    out = [(h, -1) for h in p.lead]
    for k, (a, b, d) in enumerate(p.segments):
        for i in range(a, b + d, d):
            h = chunk.R[i]
            out.append((h if d == 1 else flip(h), i))
        if k < len(p.interiors):
            out += [(h, -1) for h in p.interiors[k]]
    return out


def read_chunks(path, seqs=None):
    """Yield decoded chunks of the main sequences, detail records folded in."""
    chunks = {}
    details = defaultdict(list)
    order = []
    with gzip.open(path, "rt") as f:
        for line in f:
            if line[0] == "#":
                continue
            cols = line.rstrip("\n").split("\t")
            seq = cols[0]
            if "~" in seq:
                base, tail = seq.rsplit("~", 1)
                if tail == "departure":
                    continue
                details[(base, int(tail))].append(cols)
                continue
            if seqs and seq not in seqs:
                continue
            key = (seq, int(cols[1]))
            c = chunks.get(key)
            if c is None:
                c = chunks[key] = Chunk(seq, int(cols[1]))
                order.append(key)
            kind = cols[3]
            if kind == "ref":
                c.ref.append(cols)
            elif kind == "nodes":
                parse_nodes(cols, c.nodes)
            elif kind == "route":
                c.routes.append(cols)
            elif kind == "walk":
                c.walks.append(cols)
            elif kind == "abridged":
                c.abridged.append(cols)
    for key in order:
        c = chunks[key]
        c.finish()
        routes = parse_routes(c.routes)
        pieces = [decode_walk(c, cols, routes) for cols in c.walks]
        recs = defaultdict(list)
        for cols in details.get(key, []):
            recs[int(cols[1]) // 16384].append(cols)
        for rec in sorted(recs):
            rows = recs[rec]
            rroutes = parse_routes([r for r in rows if r[3] == "route"])
            for r in rows:
                if r[3] == "nodes":
                    parse_nodes(r, c.nodeLen)
            for r in rows:
                if r[3] == "walk":
                    pieces.append(decode_walk(c, r, rroutes))
        c.pieces = pieces
        yield c


if __name__ == "__main__":
    n = steps = 0
    for c in read_chunks(sys.argv[1]):
        n += len(c.pieces)
        steps += sum(p.nsteps for p in c.pieces)
    print(n, "pieces", steps, "steps")
