#!/usr/bin/env python3
# A reader of walk format 8 written from docs/walks-format.md alone, by a
# reviewer who had not read the writer or the other checkers, and a check
# that runs it over a whole file and reports every place the file and the
# page disagree: the directory and tables, file order, each tile's rows,
# routes and walk rows decoded, detail units, each blocks row against its
# detail walk row collapsed and against the tile's ref rows, each W line's
# pieces tiling its contig, and the departure records against the piece
# boundaries computed from the rows. It shares no code with verify7.py,
# claims7.py, audit7.py, expand7.py or walks-truth.py, which is its value;
# keep it so. GUESS-n marks each place the page left the reader a choice.
# A column after a row's fixed ones must be a tag, NAME:T:value, and is not
# read; a unit of a kind the page doesn't give is skipped; a header line of
# an unknown first word is ignored.
# Prints what agreed and what disagreed, and exits 1 on any disagreement.
#
# Usage: spec8.py FILE.walks.gz [--gfa G.gfa] [--tiles A:B] [--dump]
#        spec8.py FILE.walks.gz --tiles A:B --save PART; spec8.py FILE.walks.gz --merge PART...
import bisect
import collections
import gzip
import os
import re
import sys
import time
import zlib


class Refuse(Exception):
    pass


def flip(h):
    return h ^ 1


def delta_tokens(col, prev):
    """Delta tokens to handles; returns (handles, last id)."""
    out = []
    if col != ".":
        for t in col.split(","):
            t = int(t)
            prev += t >> 1
            out.append(2 * prev + (t & 1))
    return out, prev


def ints(col):
    return [] if col == "." else [int(x) for x in col.split(",")]


class Entry:
    __slots__ = ("seq", "start", "end", "kind", "name", "offset", "length")

    def __init__(self, cols):
        self.seq = cols[0]
        self.start = int(cols[1])
        self.end = int(cols[2])
        self.kind = cols[3]
        self.name = cols[4]
        self.offset = int(cols[5])
        self.length = int(cols[6])

    def unit_line(self):
        return f"#unit\t{self.seq}\t{self.start}\t{self.end}\t{self.kind}\t{self.name}"


TAG = re.compile(r"[A-Za-z][A-Za-z0-9]*:[A-Za-z]:[^\t]*")
COLUMNS = {"ref": 12, "nodes": 6, "route": 7, "walk": 11, "abridged": 10, "blocks": 8, "departure": 15}
ROWS_OF = {
    "tile": ("ref", "nodes", "route", "walk", "abridged"),
    "departures": ("departure",),
    "detail": ("nodes", "route", "walk"),
    "blocks": ("blocks",),  # GUESS-15: the page's refusal rule (C155) leaves blocks units out
    "table": (),
}


class RouteSet:
    """The nodes and route rows of a tile or of a detail unit."""

    def __init__(self):
        self.node_len = {}
        self.node_order = []
        self.routes = []  # (entry|None, interior list, exit|None)
        self.ibp = []
        self.prev = 0
        self.has_nodes_row = False

    def add_nodes(self, cols):
        self.has_nodes_row = True
        ids = ints(cols[4])
        lens = ints(cols[5])
        if len(ids) != len(lens):
            raise Refuse("nodes row: ids and lengths differ in count")
        cur = 0
        for d, ln in zip(ids, lens):
            cur += d  # plain differences, as the Example's `nodes 6 6` shows
            self.node_len[cur] = ln
            self.node_order.append(cur)

    def add_route(self, cols):
        e, self.prev = delta_tokens(cols[4], self.prev)
        i, self.prev = delta_tokens(cols[5], self.prev)
        x, self.prev = delta_tokens(cols[6], self.prev)
        if len(e) > 1 or len(x) > 1:
            raise Refuse("route row: entry or exit holds more than one handle")
        self.routes.append((e[0] if e else None, i, x[0] if x else None))
        self.ibp.append(sum(self.node_len[h >> 1] for h in i))

    def taken(self, rid, fl):
        e, i, x = self.routes[rid]
        if fl:
            return (
                None if x is None else flip(x),
                [flip(h) for h in reversed(i)],
                None if e is None else flip(e),
            )
        return e, i, x


class Tile:
    def __init__(self, entry):
        self.entry = entry
        self.seq = entry.seq
        self.name = int(entry.name)
        self.ref_rows = []
        self.R = []
        self.off = []
        self.end = []
        self.len = []
        self.passes = []
        self.cum = [0]  # prefix sums of len
        self.occ = {}
        self.breaks = []  # positions p where end[p] != off[p+1]
        self.rs = RouteSet()
        self.walks = []
        self.abridged = []
        self.row_kinds = []

    def add_ref(self, cols):
        path, frag, hap, piece, nsteps = cols[4], cols[5], int(cols[6]), int(cols[7]), int(cols[8])
        steps, _ = delta_tokens(cols[9], 0)
        lens = ints(cols[10])
        passes = ints(cols[11]) if cols[11] != "." else [1] * len(steps)
        if not (len(steps) == len(lens) == len(passes) == nsteps):
            raise Refuse("ref row: nsteps, steps, lengths and passes differ in count")
        self.ref_rows.append(dict(path=path, frag=frag, hap=hap, piece=piece, nsteps=nsteps,
                                  first=len(self.R), passes_col=cols[11], lens=lens,
                                  start=int(cols[1]), end=int(cols[2])))
        o = hap
        for h, ln, p in zip(steps, lens, passes):
            if self.R and self.end[-1] != o:
                self.breaks.append(len(self.R) - 1)
            self.occ.setdefault(h >> 1, []).append(len(self.R))
            self.R.append(h)
            self.off.append(o)
            o += ln
            self.end.append(o)
            self.len.append(ln)
            self.passes.append(p)
            self.cum.append(self.cum[-1] + ln)

    # ---- Decoding a walk row -------------------------------------------------

    def decode(self, rs, start_col, choices_col, nsteps, notes=None):
        """Returns segments: ('I', rid, flip) or ('R', i, j, d) for R positions
        i..j walked in direction d."""
        R, occ = self.R, self.occ
        if "@" in start_col:
            sh, sk = start_col.split("@")
            sh, sk = int(sh), int(sk)
            if sk == 0 and notes is not None:
                notes.append("start@0 states the default")
        else:
            sh, sk = int(start_col), 0
        choices = []
        rid = 0
        if choices_col != ".":
            for tok in choices_col.split(","):
                m = re.fullmatch(r"(-?\d+)(?::(\d+))?(?:@(\d+))?", tok)
                if not m:
                    raise Refuse(f"choice token {tok!r}")
                t = int(m.group(1))
                rid += t >> 1
                if not 0 <= rid < len(rs.routes):
                    raise Refuse(f"route id {rid} out of range")
                choices.append((rid, t & 1,
                                None if m.group(2) is None else int(m.group(2)),
                                None if m.group(3) is None else int(m.group(3))))
        segs = []
        n = 0
        first = 0
        if choices:
            rid, fl, ck, ak = choices[0]
            e, i, x = rs.taken(rid, fl)  # GUESS-4: "has no entry" means as taken, after the flip
            if e is None:
                first = 1
                if ck is not None or ak is not None:
                    raise Refuse("a route with no entry takes neither :k nor @k")
                if x is None:
                    raise Refuse("route with neither entry nor exit")
                if x != sh:
                    # GUESS-22: the page never says the entry-less route's exit is `start`
                    raise Refuse("first route has no entry and its exit is not the start handle")
                segs.append(("I", rid, fl))
                n += len(i)
        if (sh >> 1) not in occ:
            raise Refuse("start handle's node is not on R")
        if sk >= len(occ[sh >> 1]):
            raise Refuse("start@k names no occurrence")
        pos = occ[sh >> 1][sk]
        h = sh
        seg_from = pos
        n += 1
        ended_off = False
        for ci in range(first, len(choices)):
            rid, fl, ck, ak = choices[ci]
            e, i, x = rs.taken(rid, fl)
            if e is None:
                raise Refuse("a route after the first has no entry")
            if ended_off:
                raise Refuse("a route follows a route with no exit")
            d = 1 if R[pos] == h else -1
            want = e if d == 1 else flip(e)
            eo = occ.get(e >> 1)
            if eo is None:
                raise Refuse("route entry's node is not on R")
            default = None
            if d == 1:
                for p in eo:
                    if p >= pos and R[p] == want:
                        default = p
                        break
            else:
                for p in reversed(eo):
                    if p <= pos and R[p] == want:
                        default = p
                        break
            if ck is not None:
                if ck >= len(eo):
                    raise Refuse(":k names no occurrence")
                j = eo[ck]
                if (j - pos) * d < 0:
                    raise Refuse(":k names an occurrence behind the walk")
                if R[j] != want:
                    raise Refuse(":k names an occurrence held the other way round")
                if j == default and notes is not None:
                    notes.append(":k states the default")
            else:
                if default is None:
                    raise Refuse("stepping along R never reads the route's entry")
                j = default
            n += abs(j - pos)
            segs.append(("R", seg_from, j, d))
            pos = j
            segs.append(("I", rid, fl))
            n += len(i)
            if x is None:
                ended_off = True
                continue
            xo = occ.get(x >> 1)
            if xo is None:
                raise Refuse("route exit's node is not on R")
            best = None
            for p in xo:  # ascending, so `<=` keeps the later one on a tie
                if best is None or abs(p - pos) <= abs(best - pos):
                    best = p  # GUESS-3: "the later one" is the higher position in R
            if ak is not None:
                if ak >= len(xo):
                    raise Refuse("@k names no occurrence")
                j = xo[ak]
                if j == best and notes is not None:
                    notes.append("@k states the default")
            else:
                j = best
            if not i and notes is not None:
                dd = 1 if R[pos] == e else -1
                if j == pos + dd and x == (R[j] if dd == 1 else flip(R[j])):
                    notes.append("an empty route where R's next position is the step's")
            pos = j
            h = x
            seg_from = pos
            n += 1
        if ended_off:
            if n != nsteps:
                raise Refuse(f"piece ends off R with {n} steps, nsteps says {nsteps}")
        else:
            d = 1 if R[pos] == h else -1
            j = pos + d * (nsteps - n)
            if nsteps < n or not 0 <= j < len(R):
                raise Refuse(f"nsteps {nsteps} runs off R or is below the {n} steps decoded")
            segs.append(("R", seg_from, j, d))
        return segs

    # ---- What a decoded piece says ------------------------------------------

    def span(self, segs):
        lo = hi = None
        for s in segs:
            if s[0] == "R":
                a, b = min(s[1], s[2]), max(s[1], s[2])
                lo = self.off[a] if lo is None else min(lo, self.off[a])
                hi = self.end[b] if hi is None else max(hi, self.end[b])
        return lo, hi

    def bp(self, rs, segs):
        t = 0
        for s in segs:
            if s[0] == "R":
                a, b = min(s[1], s[2]), max(s[1], s[2])
                t += self.cum[b + 1] - self.cum[a]
            else:
                t += rs.ibp[s[1]]
        return t

    def nsteps(self, rs, segs):
        return sum(abs(s[2] - s[1]) + 1 if s[0] == "R" else len(rs.routes[s[1]][1]) for s in segs)

    def steps(self, rs, segs):
        """Every step as (handle, position in R or None)."""
        out = []
        for s in segs:
            if s[0] == "R":
                _, i, j, d = s
                for p in range(i, j + d, d):
                    out.append((self.R[p] if d == 1 else flip(self.R[p]), p))
            else:
                out.extend((h, None) for h in rs.taken(s[1], s[2])[1])
        return out

    def r_runs(self, segs):
        """A piece's stretches on R as (a, b, d) position runs, each contiguous in bases."""
        runs = []
        for s in segs:
            if s[0] != "R":
                runs.append(None)
                continue
            _, i, j, d = s
            lo, hi = min(i, j), max(i, j)
            cuts = [p for p in self.breaks if lo <= p < hi]
            parts = []
            a = lo
            for c in cuts:
                parts.append((a, c))
                a = c + 1
            parts.append((a, hi))
            if d == -1:
                parts.reverse()
            runs.extend((a, b, d) for a, b in parts)
        return runs

    def collapse(self, rs, segs):
        """The piece as the blocks section describes it: items and the list text."""
        items = []
        for s in segs:
            if s[0] == "I":
                b = rs.ibp[s[1]]
                if rs.routes[s[1]][1]:
                    if items and items[-1][0] == "U":
                        items[-1][1] += b
                    else:
                        items.append(["U", b])
                continue
            for a, b, d in self.r_runs([s]):
                begin, stop = (self.off[a], self.end[b]) if d == 1 else (self.end[b], self.off[a])
                ln = self.end[b] - self.off[a]
                last = items[-1] if items else None
                # GUESS-6: two reference lines that abut with no gap don't end a block
                if last and last[0] == "B" and last[2] == d and last[4] == begin:
                    last[3] += ln
                    last[4] = stop
                else:
                    items.append(["B", begin, d, ln, stop])
        return items

    @staticmethod
    def list_text(items):
        out = []
        prev_end = 0  # GUESS-2: d counts bases of S, the first block's from base 0 of S
        for it in items:
            if it[0] == "U":
                out.append(str(it[1]))
            else:
                out.append(f"{it[1] - prev_end}{'+' if it[2] == 1 else '-'}{it[3]}")
                prev_end = it[4]
        return ",".join(out)

    def expand_blocks(self, text):
        """A blocks list against R: items as ('U', bp) or ('B', a, b, d, begin, end) with a..b R positions."""
        out = []
        prev_end = 0
        for item in text.split(","):
            m = re.fullmatch(r"(-?\d+)([+-])(\d+)", item)
            if m:
                begin = prev_end + int(m.group(1))
                ln = int(m.group(3))
                d = 1 if m.group(2) == "+" else -1
                stop = begin + d * ln
                lo, hi = min(begin, stop), max(begin, stop)
                a = bisect.bisect_left(self.off, lo)
                b = bisect.bisect_left(self.end, hi)
                if ln == 0:
                    raise Refuse(f"block {item} of 0 bp")
                if a >= len(self.R) or self.off[a] != lo or b >= len(self.R) or self.end[b] != hi or b < a:
                    raise Refuse(f"block {item} at {lo}-{hi} doesn't begin and end on steps of R")
                if any(a <= p < b for p in self.breaks):
                    raise Refuse(f"block {item} at {lo}-{hi} runs over a gap between reference lines")
                out.append(("B", a, b, d, begin, stop))
                prev_end = stop
            elif re.fullmatch(r"\d+", item):
                out.append(("U", int(item)))
            else:
                raise Refuse(f"blocks item {item!r}")
        return out


class Walks:
    def __init__(self, path):
        self.path = path
        self.f = open(path, "rb")
        self.size = os.path.getsize(path)
        lines = open(path + ".idx", "rb").read().decode().split("\n")
        if lines and lines[-1] == "":
            lines.pop()
        l1 = lines[0].split("\t")
        if l1[0] != "#walks":
            raise Refuse("directory line 1 is not #walks")
        self.tags = {}
        for t in l1[1:]:
            k, ty, v = t.split(":", 2)
            self.tags[k] = int(v) if ty == "i" else v
        if self.tags.get("format") != 8:
            raise Refuse(f"format {self.tags.get('format')}")
        if self.tags.get("bytes") != self.size:
            raise Refuse("directory bytes differs from the data file's length")
        self.tile = self.tags["tile"]
        h = lines[1].split("\t")
        if h[0] != "#header" or h[1] != "0":
            raise Refuse("directory line 2 is not #header 0 <length>")
        self.header_len = int(h[2])
        self.tables = {}
        self.seq_order = []
        for l in lines[2:]:
            s, o, n = l.split("\t")
            self.tables[s] = (int(o), int(n))
            self.seq_order.append(s)
        ht = self.gunzip(0, self.header_len)
        if not ht.endswith("\n"):
            raise Refuse("header doesn't end in a newline")
        hl = ht[:-1].split("\n")
        if hl[0].split("\t") != [x for x in l1 if not x.startswith("bytes:i:")]:
            raise Refuse("directory line 1 differs from the header's #walks line")
        self.header_lines = hl
        self.reference = [l.split("\t")[1] for l in hl if l.startswith("#reference\t")]
        self.haplotypes = [l.split("\t")[1] for l in hl if l.startswith("#haplotype\t")]
        self.holes = {}
        self.hole_list = []
        for l in hl:
            if l.startswith("#hole\t"):
                _, s, a, b = l.split("\t")[:4]
                self.holes.setdefault(s, []).append((int(a), int(b)))
                self.hole_list.append((s, int(a), int(b)))
        self._table = {}

    def gunzip(self, off, length):
        self.f.seek(off)
        return gzip.decompress(self.f.read(length)).decode()

    def table(self, seq):
        if seq not in self._table:
            o, n = self.tables[seq]
            t = self.gunzip(o, n)
            if not t.endswith("\n"):
                raise Refuse("table doesn't end in a newline")
            lines = t[:-1].split("\n")
            u = lines[0].split("\t")
            if u[:3] != ["#unit", seq, "0"] or u[4:] != ["table", "."]:
                raise Refuse(f"table doesn't start with its own #unit line: {lines[0]}")
            entries = []
            for l in lines[1:]:
                c = l.split("\t")
                if c[0] != "#entry":
                    raise Refuse("table holds a line that isn't an #entry")
                entries.append(Entry(c[1:8]))
            self._table[seq] = (int(u[3]), entries)
        return self._table[seq]

    def length(self, seq):
        return self.table(seq)[0]

    def entries(self, seq, kind=None):
        return [e for e in self.table(seq)[1] if kind is None or e.kind == kind]

    def find(self, seq, kind, name):
        return [e for e in self.table(seq)[1] if e.kind == kind and e.name == name]

    def unit_rows(self, e):
        """A unit's rows as column lists, after the page's refusals."""
        t = self.gunzip(e.offset, e.length)
        if not t.endswith("\n"):
            raise Refuse(f"unit {e.kind} {e.name} doesn't end in a newline")
        lines = t[:-1].split("\n")
        if lines[0] != e.unit_line():
            raise Refuse(f"unit's #unit line {lines[0]!r} differs from its entry {e.unit_line()!r}")
        rows = []
        for l in lines[1:]:
            c = l.split("\t")
            if l.startswith("#"):
                raise Refuse(f"# line inside unit {e.kind} {e.name}")
            if c[0] != e.seq:
                raise Refuse(f"row of another sequence in unit {e.kind} {e.name}")
            if e.kind in ROWS_OF and c[3] not in ROWS_OF[e.kind]:
                raise Refuse(f"{c[3]} row in a {e.kind} unit")
            fixed = COLUMNS.get(c[3], len(c))
            if len(c) < fixed or any(not TAG.fullmatch(x) for x in c[fixed:]):
                raise Refuse(f"{c[3]} row without its {fixed} columns, or with a column after them that is no tag")
            rows.append(c[:fixed])
        return rows

    def read_tile(self, e):
        t = Tile(e)
        for c in self.unit_rows(e):
            k = c[3]
            t.row_kinds.append(k)
            if k == "ref":
                t.add_ref(c)
            elif k == "nodes":
                t.rs.add_nodes(c)
            elif k == "route":
                t.rs.add_route(c)
            elif k == "walk":
                t.walks.append(c)
            else:
                t.abridged.append(c)
            if k in ("ref", "nodes", "route"):
                t.rs_rows = getattr(t, "rs_rows", [])
                t.rs_rows.append((k, int(c[1]), int(c[2])))
        return t

    def read_detail(self, e):
        rs = RouteSet()
        walks = []
        kinds = []
        se = []
        for c in self.unit_rows(e):
            k = c[3]
            kinds.append(k)
            if k == "nodes":
                rs.add_nodes(c)
                se.append((k, int(c[1]), int(c[2])))
            elif k == "route":
                rs.add_route(c)
                se.append((k, int(c[1]), int(c[2])))
            else:
                walks.append(c)
        return rs, walks, kinds, se


class Report:
    def __init__(self):
        self.counts = collections.Counter()
        self.samples = collections.defaultdict(list)
        self.ok = collections.Counter()

    def bad(self, what, where=""):
        self.counts[what] += 1
        if len(self.samples[what]) < 4:
            self.samples[what].append(where)

    def good(self, what, n=1):
        self.ok[what] += n

    def show(self):
        print("== agreed ==")
        for k in sorted(self.ok):
            print(f"  {self.ok[k]:>10}  {k}")
        print("== disagreed ==")
        for k in sorted(self.counts):
            print(f"  {self.counts[k]:>10}  {k}")
            for s in self.samples[k]:
                print(f"              {s}")
        if not self.counts:
            print("  none")


def route_key(r):
    e, i, x = r
    return ((0, 0) if e is None else (1, e), i, (0, 0) if x is None else (1, x))


def flipped(r):
    e, i, x = r
    return (None if x is None else flip(x), [flip(h) for h in reversed(i)], None if e is None else flip(e))


def check_routeset(rep, t, rs, where, used):
    interior_nodes = set()
    for e, i, x in rs.routes:
        interior_nodes.update(h >> 1 for h in i)
    if rs.has_nodes_row != bool(interior_nodes):
        rep.bad("nodes row present without an interior step, or absent with one", where)
    if sorted(interior_nodes) != rs.node_order:
        rep.bad("nodes row is not exactly the interiors' nodes in ascending order", where)
    keys = []
    seen = set()
    for rid, r in enumerate(rs.routes):
        e, i, x = r
        if (e is None or x is None) and not i:
            rep.bad("route with no entry or no exit has no interior step", where)
        if e is None and x is None:
            rep.bad("route with neither entry nor exit", where)
        for hh in (e, x):
            if hh is not None and (hh >> 1) not in t.occ:
                rep.bad("route entry or exit not on R", where)
        if route_key(flipped(r)) < route_key(r):
            rep.bad("route stored the way round that sorts second", f"{where} route {rid}")
        k = (e, tuple(i), x)
        fk = flipped(r)
        fk = (fk[0], tuple(fk[1]), fk[2])
        if k in seen or (fk in seen and fk != k):
            rep.bad("route listed twice", f"{where} route {rid}")
        seen.add(k)
        firsts = [t.occ[hh >> 1][0] for hh in (e, x) if hh is not None and (hh >> 1) in t.occ]
        keys.append(((0, min(firsts)) if firsts else (1, 0), route_key(r)))
        if rid not in used:
            rep.bad("route no walk takes", f"{where} route {rid}")
    if keys != sorted(keys):
        rep.bad("route rows out of the order the page gives", where)
    rep.good("route rows checked (orientation, order, ends on R, used)", len(rs.routes))


def used_routes(choices_col):
    out = set()
    rid = 0
    if choices_col != ".":
        for tok in choices_col.split(","):
            t = int(tok.split(":")[0].split("@")[0])
            rid += t >> 1
            out.add(rid)
    return out


def piece_cost(rs, choices_col, nsteps):
    c = 0
    rid = 0
    if choices_col != ".":
        for tok in choices_col.split(","):
            t = int(tok.split(":")[0].split("@")[0])
            rid += t >> 1
            c += len(rs.routes[rid][1])
    return c + nsteps / 4


def ends_of(t, rs, segs):
    """First and last step on R as (pos, d), and the bp off R before and after them."""
    lead = trail = 0
    first = last = None
    for s in segs:
        if s[0] == "R":
            if first is None:
                first = (s[1], s[3])
            last = (s[2], s[3])
            trail = 0
        else:
            b = rs.ibp[s[1]]
            if first is None:
                lead += b
            trail += b
    return first, last, lead, trail


def main():
    args = sys.argv[1:]
    path = args[0]
    gfa = args[args.index("--gfa") + 1] if "--gfa" in args else None
    dump = "--dump" in args
    lo_t, hi_t = 0, 1 << 62
    if "--merge" in args:
        lo_t = hi_t = -1
    if "--tiles" in args:
        a, b = args[args.index("--tiles") + 1].split(":")
        lo_t, hi_t = int(a), int(b)
    rep = Report()
    t0 = time.time()
    try:
        w = Walks(path)
    except Refuse as x:
        sys.exit(f"spec8.py: {path}: refused: {x}")
    tile_bp = w.tile
    pieces = {}  # (path, frag) -> {piece: (hap, bp, seq, tile, kind, firstR, lastR, lead, trail)}
    truth_steps = {}
    departures = set()
    abridge, abytes = w.tags.get("abridge", 0), w.tags.get("abridgebytes", 0)
    stats = collections.Counter()

    hl = w.header_lines
    if any(not l.startswith("#") for l in hl):
        rep.bad("header line not starting with #")
    if w.haplotypes != sorted(set(w.haplotypes), key=lambda s: s.encode()):
        rep.bad("#haplotype lines not once each in byte order")
    if w.hole_list != sorted(w.hole_list, key=lambda h: (h[0].encode(), h[1])):
        rep.bad("#hole lines out of order")
    if w.seq_order != sorted(w.seq_order, key=lambda s: s.encode()):
        rep.bad("directory sequences not in byte order")
    seen_hap = set()
    prev_table_end = w.header_len
    for seq in w.seq_order:
        S, entries = w.table(seq)
        o, n = w.tables[seq]
        pos = prev_table_end
        for e in entries:
            if e.offset != pos or e.length <= 0:
                rep.bad("table entries don't partition the bytes before the table", f"{seq} {e.kind} {e.name}")
            pos = e.offset + e.length
            if e.seq != seq:
                rep.bad("entry of another sequence", f"{seq} {e.kind} {e.name}")
        if pos != o:
            rep.bad("table does not start where its last unit ends", seq)
        prev_table_end = o + n
        names = collections.Counter((e.kind, e.name) for e in entries if e.name != ".")
        if any(v > 1 for v in names.values()):
            rep.bad("two units of a kind share a name", seq)
        kinds = [e.kind for e in entries]
        # file order: tiles and departures by position, then details with blocks, then the table
        known = [e for e in entries if e.kind in ROWS_OF]
        main_part = [e for e in known if e.kind in ("tile", "departures")]
        rest = [e for e in known if e.kind not in ("tile", "departures")]
        if known != main_part + rest:
            rep.bad("a detail or blocks unit before a tile or departures unit", seq)
        def okey(e):
            p = int(e.name) if e.kind == "tile" else e.start
            return (p, 0 if e.kind == "tile" else 1, e.end - e.start)
        if [okey(e) for e in main_part] != sorted(okey(e) for e in main_part):
            rep.bad("tiles and departure blocks out of the page's file order", seq)
        dk = []
        for e in rest:
            if e.kind == "detail":
                cs, d = e.name.split(":")
                dk.append((int(cs), 0, int(d)))
            else:
                dk.append((int(e.name), 1, 0))
        if dk != sorted(dk):
            rep.bad("detail and blocks units out of order (a tile's details, then its blocks)", seq)
        rep.good("table entries", len(entries))

        tiles = [e for e in entries if e.kind == "tile"]
        if not tiles:
            rep.bad("sequence without a tile", seq)
        last_ref_end = 0
        for e in tiles:
            cs = int(e.name)
            if not lo_t <= cs < hi_t:
                continue
            where = f"{seq} tile {e.name}"
            if e.name != str(cs) or cs % tile_bp:
                rep.bad("tile name not a multiple of tile in plain decimal", where)
            try:
                t = w.read_tile(e)
            except Refuse as x:
                rep.bad(f"refused: {x}", where)
                continue
            stats["tiles"] += 1
            order = {"ref": 0, "nodes": 1, "route": 2, "walk": 3, "abridged": 4}
            ks = [order[k] for k in t.row_kinds]
            if ks != sorted(ks) or t.row_kinds.count("nodes") > 1:
                rep.bad("tile rows out of kind order", where)
            if not t.ref_rows:
                rep.bad("tile without a ref row", where)
                continue
            if [r["hap"] for r in t.ref_rows] != sorted(r["hap"] for r in t.ref_rows):
                rep.bad("ref rows out of hapOffset order", where)
            for r in t.ref_rows:
                if r["path"] != seq:
                    rep.bad("ref row of another path than its sequence", where)
                pc = r["passes_col"]
                if (pc == ".") != all(p == 1 for p in t.passes[r["first"]:r["first"] + r["nsteps"]]):
                    rep.bad("passes is . without every pass being 1, or the reverse", where)
                key = (r["path"], r["frag"])
                pieces.setdefault(key, {})
                if r["piece"] in pieces[key]:
                    rep.bad("piece key twice", f"{where} {key} {r['piece']}")
                pieces[key][r["piece"]] = (r["hap"], sum(r["lens"]), seq, cs, "ref", None, None, 0, 0)
            if any(not cs <= o < cs + tile_bp for o in t.off):
                rep.bad("ref step starting outside [name, name+tile)", where)
            if any(a >= b for a, b in zip(t.off, t.off[1:])) or any(t.end[i] > t.off[i + 1] for i in range(len(t.off) - 1)):
                rep.bad("ref rows overlap on S", where)
            if (e.start, e.end) != (t.off[0], t.end[-1]):
                rep.bad("tile extent is not its ref rows' first base to last", f"{where} {e.start}-{e.end} vs {t.off[0]}-{t.end[-1]}")
            if e.end > S:
                rep.bad("tile runs past |S|", where)
            for k, a, b in getattr(t, "rs_rows", []):
                if (a, b) != (e.start, e.end):
                    rep.bad(f"{k} row's start end is not the unit's extent", where)
            if dump:
                print(f"-- {where} R={t.R} off={t.off} len={t.len} routes={t.rs.routes}")
            # walk rows
            used = set()
            cost = 0
            rowbytes = 0
            okeys = []
            for c in t.walks:
                pth, frag, hap, pc, ns = c[4], c[5], int(c[6]), int(c[7]), int(c[8])
                okeys.append((pth.encode(), int(frag), hap, pc))
                wh = f"{where} walk {pth} {frag} {pc}"
                notes = []
                try:
                    segs = t.decode(t.rs, c[9], c[10], ns, notes)
                except Refuse as x:
                    rep.bad(f"walk row refused: {x}", wh)
                    continue
                for nn in notes:
                    rep.bad(f"walk row not in its one encoding: {nn}", wh)
                used |= used_routes(c[10])
                cost += piece_cost(t.rs, c[10], ns)
                if t.span(segs) != (int(c[1]), int(c[2])):
                    rep.bad("walk row's start end is not the span it decodes to", f"{wh} {c[1]}-{c[2]} vs {t.span(segs)}")
                key = (pth, frag)
                pieces.setdefault(key, {})
                if pc in pieces[key]:
                    rep.bad("piece key twice", wh)
                f, l, lead, trail = ends_of(t, t.rs, segs)
                pieces[key][pc] = (hap, t.bp(t.rs, segs), seq, cs, "walk", f, l, lead, trail)
                stats["walk rows"] += 1
                if gfa:
                    truth_steps[(pth, frag, pc)] = [(h, None if p is None else (seq, t.off[p])) for h, p in t.steps(t.rs, segs)]
                if dump:
                    print(f"   walk {pth} {frag} hap={hap} piece={pc} steps={t.steps(t.rs, segs)} list={t.list_text(t.collapse(t.rs, segs))}")
            if okeys != sorted(okeys):
                rep.bad("walk rows out of order (path, fragStart, hapOffset, piece)", where)
            check_routeset(rep, t, t.rs, where, used)
            rep.good("walk rows decoded with matching nsteps and span", len(t.walks))

            # abridged rows
            if not t.abridged:
                if w.find(seq, "blocks", e.name):
                    rep.bad("blocks unit for a tile with no abridged row", where)
                if any(x.name.startswith(e.name + ":") for x in w.entries(seq, "detail")):
                    rep.bad("detail unit for a tile with no abridged row", where)
                if abridge and cost > abridge:
                    rep.bad("unabridged tile costs more than abridge", f"{where} {cost}")
                continue
            stats["abridged tiles"] += 1
            akeys = [(int(c[9]), int(c[6])) for c in t.abridged]
            if akeys != sorted(akeys):
                rep.bad("abridged rows out of order (detail, hapOffset)", where)
            if abridge and cost > abridge and t.walks:
                rep.bad("abridged tile's kept pieces still cost more than abridge", f"{where} {cost}")
            bl = w.find(seq, "blocks", e.name)
            if len(bl) != 1:
                rep.bad("abridged tile without exactly one blocks unit", where)
                continue
            try:
                brow = w.unit_rows(bl[0])
            except Refuse as x:
                rep.bad(f"blocks unit refused: {x}", where)
                continue
            if len(brow) != len(t.abridged):
                rep.bad("blocks rows and abridged rows differ in count", where)
            dnums = sorted(set(int(c[9]) for c in t.abridged))
            if dnums != list(range(len(dnums))):
                rep.bad("detail records not numbered from 0 without a gap", where)
            dunits = [x for x in w.entries(seq, "detail") if x.name.startswith(e.name + ":")]
            if sorted(int(x.name.split(":")[1]) for x in dunits) != dnums:
                rep.bad("detail units of the tile are not those its abridged rows name", where)
            details = {}
            dcost = {}
            for de in dunits:
                d = int(de.name.split(":")[1])
                dw = f"{seq} detail {de.name}"
                try:
                    rs, dwalks, kinds, se = w.read_detail(de)
                except Refuse as x:
                    rep.bad(f"detail unit refused: {x}", dw)
                    continue
                stats["detail units"] += 1
                ko = [{"nodes": 1, "route": 2, "walk": 3}[k] for k in kinds]
                if ko != sorted(ko) or kinds.count("nodes") > 1:
                    rep.bad("detail rows out of kind order", dw)
                for k, a, b in se:
                    if (a, b) != (de.start, de.end):
                        rep.bad(f"detail unit's {k} row's start end is not the unit's extent", dw)
                used = set()
                lo = hi = None
                lines = set()
                c_tot = 0
                for c in dwalks:
                    pth, frag, hap, pc, ns = c[4], c[5], int(c[6]), int(c[7]), int(c[8])
                    lines.add((pth, frag))
                    notes = []
                    try:
                        segs = t.decode(rs, c[9], c[10], ns, notes)
                    except Refuse as x:
                        rep.bad(f"detail walk row refused: {x}", f"{dw} {pth} {frag} {pc}")
                        continue
                    for nn in notes:
                        rep.bad(f"detail walk row not in its one encoding: {nn}", f"{dw} {pth} {frag} {pc}")
                    used |= used_routes(c[10])
                    c_tot += piece_cost(rs, c[10], ns)
                    sp = t.span(segs)
                    if sp != (int(c[1]), int(c[2])):
                        rep.bad("detail walk row's start end is not the span it decodes to", f"{dw} {pth} {pc}")
                    lo = sp[0] if lo is None else min(lo, sp[0])
                    hi = sp[1] if hi is None else max(hi, sp[1])
                    if (pth, frag, pc) in details:
                        rep.bad("moved piece in two detail rows", f"{dw} {pth} {frag} {pc}")
                    details[(pth, frag, pc)] = (d, hap, ns, sp, rs, segs)
                    stats["detail walk rows"] += 1
                    stats["detail steps"] += ns
                    if gfa:
                        truth_steps[(pth, frag, pc)] = [(h, None if p is None else (seq, t.off[p])) for h, p in t.steps(rs, segs)]
                    if dump:
                        print(f"   detail {de.name} {pth} {frag} hap={hap} piece={pc} steps={t.steps(rs, segs)}")
                dcost[d] = c_tot
                if len(lines) != 1:
                    rep.bad("detail unit holds other than one W line", dw)
                if (lo, hi) != (de.start, de.end):
                    rep.bad("detail unit's extent is not its walk rows' spans' first base to last", f"{dw} {de.start}-{de.end} vs {lo}-{hi}")
                check_routeset(rep, t, rs, dw, used)
            cl = [dcost.get(d, 0) for d in dnums]
            if cl != sorted(cl, reverse=True):
                rep.bad("detail records not numbered costliest first", f"{where} {cl[:6]}")
            blo = bhi = None
            keys_seen = set()
            for idx, c in enumerate(t.abridged):
                pth, frag, hap, pc, ns, d = c[4], c[5], int(c[6]), int(c[7]), int(c[8]), int(c[9])
                wh = f"{where} abridged {pth} {frag} {pc}"
                stats["abridged rows"] += 1
                key = (pth, frag)
                pieces.setdefault(key, {})
                if pc in pieces[key]:
                    rep.bad("piece key twice", wh)
                keys_seen.add((pth, frag, pc))
                det = details.get((pth, frag, pc))
                if det is None:
                    rep.bad("abridged row with no walk row in a detail unit of its tile", wh)
                    continue
                dd, dhap, dns, dsp, rs, segs = det
                if dd != d:
                    rep.bad("abridged row's detail is not the record holding its walk row", wh)
                if dhap != hap:
                    rep.bad("abridged hapOffset differs from its walk row's", wh)
                if dns != ns:
                    rep.bad("abridged nsteps differs from its walk row's", wh)
                if dsp != (int(c[1]), int(c[2])):
                    rep.bad("abridged start end differs from its walk row's span", f"{wh} {c[1]}-{c[2]} vs {dsp}")
                f, l, lead, trail = ends_of(t, rs, segs)
                fl_lo = min(t.off[f[0]], t.off[l[0]])
                fl_hi = max(t.end[f[0]], t.end[l[0]])
                if (fl_lo, fl_hi) != dsp:
                    stats["abridged pieces whose span is wider than their first and last steps on R"] += 1
                pieces[key][pc] = (hap, t.bp(rs, segs), seq, cs, "abridged", f, l, lead, trail)
                rep.good("abridged rows equal to their detail walk row (key, hapOffset, nsteps, span, record)")
                if idx >= len(brow):
                    continue
                b = brow[idx]
                if (b[4], b[5], int(b[6])) != (pth, frag, pc):
                    rep.bad("blocks row is not its abridged row's piece, in the tile's order", wh)
                    continue
                if len(b) != 8:
                    rep.bad("blocks row with other than 8 columns", wh)
                want = t.list_text(t.collapse(rs, segs))
                if b[7] != want:
                    rep.bad("blocks list differs from the detail walk row collapsed", f"{wh}\n                 file {b[7][:150]}\n                 mine {want[:150]}")
                else:
                    rep.good("blocks lists equal to the detail walk row collapsed (text)")
                try:
                    ex = t.expand_blocks(b[7])
                except Refuse as x:
                    rep.bad(f"blocks row refused: {x}", wh)
                    continue
                # the detail walk's steps on R as runs of R positions, split where a run off R
                # or a change of direction or a break in bases comes between
                wruns = []
                sep = True
                for s in segs:
                    if s[0] == "I":
                        sep = sep or bool(rs.routes[s[1]][1])
                        continue
                    for a, bb, dr in t.r_runs([s]):
                        last = wruns[-1] if wruns else None
                        joins = last and not sep and last[2] == dr and (
                            (dr == 1 and last[1] + 1 == a and t.end[last[1]] == t.off[a])
                            or (dr == -1 and last[0] - 1 == bb and t.end[bb] == t.off[last[0]]))
                        if joins:
                            wruns[-1] = (min(last[0], a), max(last[1], bb), dr)
                        else:
                            wruns.append((a, bb, dr))
                        sep = False
                bruns = [(x[1], x[2], x[3]) for x in ex if x[0] == "B"]
                wshape = "".join("U" if s[0] == "U" else "B" for s in t.collapse(rs, segs))
                bshape = "".join(x[0] for x in ex)
                if wruns != bruns or wshape != bshape:
                    rep.bad("blocks expanded against R differ from the detail walk's steps on R", wh)
                else:
                    rep.good("blocks expanded against R equal the detail walk's steps on R (positions)")
                wr = [x[1] for x in t.collapse(rs, segs) if x[0] == "U"]
                if wr != [x[1] for x in ex if x[0] == "U"]:
                    rep.bad("blocks runs differ from the detail walk's bp off R", wh)
                total = sum(x[1] if x[0] == "U" else abs(x[5] - x[4]) for x in ex)
                if total != t.bp(rs, segs):
                    rep.bad("blocks items don't add up to the piece's bp", wh)
                lo2 = min(min(x[4], x[5]) for x in ex if x[0] == "B")
                hi2 = max(max(x[4], x[5]) for x in ex if x[0] == "B")
                if (lo2, hi2) != (int(b[1]), int(b[2])):
                    rep.bad("blocks row's start end is not its blocks' span", wh)
                if (b[1], b[2]) != (c[1], c[2]):
                    rep.bad("blocks row's start end differs from its abridged row's", wh)
                blo = lo2 if blo is None else min(blo, lo2)
                bhi = hi2 if bhi is None else max(bhi, hi2)
                kinds2 = [x[0] for x in ex]
                if any(a == b2 == "U" for a, b2 in zip(kinds2, kinds2[1:])):
                    rep.bad("two runs side by side in a list", wh)
                if any(x[0] == "U" and x[1] == 0 for x in ex):
                    rep.bad("run of 0 bp", wh)
                if kinds2[0] == "U" and pc != 0:
                    rep.bad("leading run on a piece that is not its line's first", wh)
                if kinds2[0] == "U":
                    stats["blocks lists with a leading run"] += 1
                if kinds2[-1] == "U":
                    stats["blocks lists with a trailing run"] += 1
                stats["blocks items"] += len(ex)
                if any(x[0] == "B" and x[3] == -1 for x in ex):
                    stats["blocks lists with a block against R"] += 1
            if set(details) != keys_seen:
                rep.bad("detail walk row with no abridged row in its tile", where)
            if blo is not None and (blo, bhi) != (bl[0].start, bl[0].end):
                rep.bad("blocks unit's extent is not its rows' blocks' first base to last", where)
            for b in brow:
                if not (bl[0].start <= int(b[1]) and int(b[2]) <= bl[0].end):
                    rep.bad("blocks row outside its unit's start end", where)

        # departures
        for e in entries:
            if e.kind != "departures":
                continue
            if not (lo_t <= e.start < hi_t):
                continue
            size = e.end - e.start
            L = [tile_bp * 8 ** k for k in range(4)]
            if size not in L or e.start % size:
                rep.bad("departure block not a pyramid block", f"{seq} {e.start}-{e.end}")
            try:
                rows = w.unit_rows(e)
            except Refuse as x:
                rep.bad(f"departures unit refused: {x}", f"{seq} {e.start}")
                continue
            ok = [(int(c[1]), int(c[2]), "\t".join(c)) for c in rows]
            if ok != sorted(ok):
                rep.bad("departure lines out of order in a block", f"{seq} {e.start}-{e.end}")
            for c in rows:
                if not (int(c[1]) < e.end and int(c[2]) > e.start):
                    rep.bad("departure line doesn't overlap its block", f"{seq} {e.start}")
                departures.add(tuple(c))
                stats["departure lines"] += 1
        stats["departure records"] = len(departures)

    # ---- every W line's pieces tile its contig ------------------------------
    whole = lo_t == 0 and hi_t == 1 << 62
    if "--save" in args:
        import pickle
        pickle.dump((pieces, departures, dict(stats)), open(args[args.index("--save") + 1], "wb"))
    if "--merge" in args:
        import pickle
        whole = True
        for fn in args[args.index("--merge") + 1:]:
            p2, d2, s2 = pickle.load(open(fn, "rb"))
            for k, v in p2.items():
                tgt = pieces.setdefault(k, {})
                for pc, val in v.items():
                    if pc in tgt:
                        rep.bad("piece key twice", f"{k} {pc}")
                    tgt[pc] = val
            departures |= d2
            for k, v in s2.items():
                if k != "departure records":
                    stats[k] += v
        stats["departure records"] = len(departures)
    if whole:
        by_path = collections.defaultdict(list)
        for (pth, frag), ps in pieces.items():
            ns = sorted(ps)
            wh = f"{pth} {frag}"
            if ns != list(range(len(ns))):
                rep.bad("a line's pieces are not numbered from 0 without a gap", f"{wh} {ns[:8]}")
                continue
            if ps[0][0] != int(frag):
                rep.bad("a line's first piece doesn't start at fragStart", f"{wh} {ps[0][0]}")
            okay = True
            for k in ns[1:]:
                if ps[k - 1][0] + ps[k - 1][1] != ps[k][0]:
                    okay = False
                    rep.bad("a piece doesn't end where the line's next piece begins", f"{wh} piece {k - 1}: {ps[k - 1][0]}+{ps[k - 1][1]} != {ps[k][0]}")
                if ps[k][7] and ps[k][4] != "ref":
                    rep.bad("a piece that is not its line's first begins off R", f"{wh} piece {k}")
            if okay:
                rep.good("W lines whose pieces tile their contig from fragStart")
            by_path[pth].append((int(frag), frag, ps))
            stats["pieces"] += len(ns)
        stats["W lines"] = len(pieces)
        refs = set(w.reference)
        haps = set()
        for pth in by_path:
            parts = pth.split("#")
            hp = "#".join(parts[:2]) if len(parts) > 2 else pth
            if parts[0] not in refs:
                haps.add(hp)
        if sorted(haps) != sorted(w.haplotypes):
            rep.bad("#haplotype lines are not the other haplotypes with rows", f"{sorted(haps ^ set(w.haplotypes))[:6]}")
        else:
            rep.good("#haplotype lines equal the haplotypes with rows", len(haps))

        # ---- departure records against the pieces ---------------------------
        check_departures(rep, w, by_path, departures, tile_bp, stats)
        if gfa:
            check_gfa(rep, w, gfa, pieces, truth_steps)

    print(f"file {path}: {w.tags}")
    for k in sorted(stats):
        print(f"  {stats[k]:>12}  {k}")
    rep.show()
    print(f"({time.time() - t0:.1f} s)")
    return 1 if rep.counts else 0


def holes_before(w, seq, pos):
    return sum(min(b, pos) - a for a, b in w.holes.get(seq, []) if a < pos)


def check_departures(rep, w, by_path, departures, tile_bp, stats):
    order = []
    for pth, lines in by_path.items():
        lines.sort()
        flat = []
        for fragn, frag, ps in lines:
            for k in sorted(ps):
                flat.append((fragn, frag, k) + ps[k])
        order.append((pth, flat))
    refs = set(w.reference)
    bounds = []
    need = collections.defaultdict(set)
    for pth, flat in order:
        if pth.split("#")[0] in refs:
            # the reference's own lines: every piece is a ref row, with no ends kept here
            continue
        for S in sorted(set(p[5] for p in flat)):
            idx = [i for i, p in enumerate(flat) if p[5] == S]
            for a, b in zip(idx, idx[1:]):
                p, q = flat[a], flat[b]
                between = sum(flat[i + 1][3] - (flat[i][3] + flat[i][4]) for i in range(a, b) if flat[i + 1][1] != flat[i][1])
                bounds.append((pth, S, p, q, between))
                need[(S, p[6])].add(p[9][0])
                need[(S, q[6])].add(q[8][0])
    fact = {}
    for (S, cs), poss in need.items():
        t = w.read_tile(w.find(S, "tile", str(cs))[0])
        for i in poss:
            fact[(S, cs, i)] = (t.off[i], t.end[i], t.passes[i])
    want = {}
    for pth, S, p, q, between in bounds:
        (lp, ld), (rp, rd) = p[9], q[8]
        loff, lend, lpass = fact[(S, p[6], lp)]
        roff, rend, rpass = fact[(S, q[6], rp)]
        p_end = p[3] + p[4]
        hap_start = p_end - p[11]
        own = q[3] + q[10] - hap_start
        leave_pos = lend if ld == 1 else loff
        rejoin_pos = roff if rd == 1 else rend
        adjacent = own == 0 and ld == rd and leave_pos - holes_before(w, S, leave_pos) == rejoin_pos - holes_before(w, S, rejoin_pos)
        if adjacent:
            stats["piece boundaries that are adjacent on S (no record)"] += 1
            continue
        st = min(loff, roff)
        en = max(lend, rend)
        own_tiles = []
        if p[11]:
            own_tiles.append(p[6])
        if q[10] and (not own_tiles or own_tiles[-1] != q[6]):
            own_tiles.append(q[6])
        key = (S, st, en, pth, hap_start, own, leave_pos, "+" if ld == 1 else "-", lpass,
               rejoin_pos, "+" if rd == 1 else "-", rpass)
        if key in want:
            rep.bad("two piece boundaries of a path make the same departure line", str(key))
        want[key] = (between, ",".join(str(x) for x in own_tiles) or ".")
    got = {}
    for c in departures:
        key = (c[0], int(c[1]), int(c[2]), c[4], int(c[5]), int(c[6]), int(c[8]), c[9], int(c[10]), int(c[11]), c[12], int(c[13]))
        if key in got:
            rep.bad("two departure records with the same ends", str(key))
        got[key] = (int(c[7]), c[14])
        if len(c) != 15:
            rep.bad("departure row with other than 15 columns", str(key))
    for k in want:
        if k not in got:
            rep.bad("piece boundary that departs from S has no departure record matching it", str(k))
        else:
            between, ot = want[k]
            miss, got_ot = got[k]
            if miss > between:
                rep.bad("missingBp above the bp between the path's W lines", str(k))
            if got_ot != ot:
                rep.bad("ownTiles differs from the tiles holding the own steps", f"{k} file {got_ot} mine {ot}")
            rep.good("departure records equal to a piece boundary computed from the rows")
    for k in got:
        if k not in want:
            rep.bad("departure record matching no piece boundary", str(k))
    # cover
    L = [tile_bp * 8 ** k for k in range(4)]
    blocks = collections.defaultdict(set)
    for seq in w.seq_order:
        for e in w.entries(seq, "departures"):
            for c in w.unit_rows(e):
                blocks[tuple(c)].add((seq, e.start, e.end))
    for c, where in blocks.items():
        st, en = int(c[1]), int(c[2])
        a = st // tile_bp * tile_bp
        z = -(-en // tile_bp) * tile_bp
        cover = set()
        while a < z:
            size = max(s for s in L if a % s == 0 and a + s <= z)
            cover.add((c[0], a, a + size))
            a += size
        if cover != where:
            rep.bad("departure record not in exactly the blocks of its cover", f"{c[:5]} {sorted(where)[:3]} vs {sorted(cover)[:3]}")
        else:
            rep.good("departure records in exactly the blocks of their cover")


def check_gfa(rep, w, gfa, pieces, truth_steps):
    seglen = {}
    lines = []
    for l in open(gfa):
        c = l.rstrip("\n").split("\t")
        if c[0] == "S":
            seglen[int(c[1])] = len(c[2]) if c[2] != "*" else int([x for x in c[3:] if x.startswith("LN:i:")][0][5:])
        elif c[0] == "W":
            steps = [(2 * int(m.group(2)) + (1 if m.group(1) == "<" else 0)) for m in re.finditer(r"([<>])(\d+)", c[6])]
            lines.append((f"{c[1]}#{c[2]}#{c[3]}", c[4], steps))
        elif c[0] == "P":
            steps = [(2 * int(s[:-1]) + (1 if s[-1] == "-" else 0)) for s in c[2].split(",") if s]
            lines.append((c[1], "0", steps))
    for name, frag, steps in lines:
        steps = [h for h in steps if seglen[h >> 1] > 0]
        ps = pieces.get((name, frag))
        if ps is None:
            rep.good("GFA lines with no rows (fine if they have no step on the reference)")
            continue
        got = []
        for k in sorted(ps):
            if ps[k][4] == "ref":
                got = None
                break
            got.extend(truth_steps[(name, frag, k)])
        if got is None:
            continue
        if [h for h, _ in got] != steps:
            rep.bad("pieces joined are not the GFA line's steps", f"{name} {frag}\n   file {[h for h, _ in got]}\n   gfa  {steps}")
        else:
            rep.good("GFA lines back step for step from their pieces")


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (Refuse, EOFError, OSError, zlib.error) as x:
        sys.exit(f"spec8.py: {sys.argv[1]}: refused: {type(x).__name__}: {x}")
