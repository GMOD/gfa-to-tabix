#!/usr/bin/env python3
"""window-oracle.py: what a cut over a window must return, by the rules of
docs/walks-format.md's Reading a window, against what @jbrowse/graph-walks'
cut returns there.

Every tile is decoded by spec8.py, the reader written from the page alone,
which shares no code with graph-walks. For a window [s, e) of sequence S with
context c, D = [max(0, s - c), e + c), every walk kept and expanded or none,
and every budget lifted, the cut must return:

  fragments   For each W or P line, its pieces in the tiles whose extent
              overlaps D, joined where their piece numbers are consecutive.
              Each joined run with a step whose position overlaps D gives one
              fragment, from its first such step to its last, with the bp of
              the run before and after it as trimmedBefore and trimmedAfter.
              Left unexpanded, each run of steps off R in an abridged piece
              is one placeholder of its bp.
  records     Every departure line of S whose extent overlaps D, once, read
              from every departures unit of S, not only those over D.
  computed    Every departure between two consecutive steps on R of one
              piece in those tiles, not adjacent there with holes removed,
              whose stretch from the base beside its leave to the base
              beside its rejoin overlaps the drawn stretch: D widened to
              every position of R in those tiles that overlaps D.
  own steps   A departure whose base beside its leave or its rejoin lies in
              D, with ownBp at most attachBp, carries its own steps: for a
              computed one the steps between its ends, for a record the
              steps of its path's pieces filed in the tiles holding its leave
              and rejoin bases that lie within [hapStart, hapStart + ownBp),
              in contig order. No other departure carries steps.

It does not check gaps, links, breakAt, node tables, contained cuts or the
budgets. The tiles a window reads are the page's rule, so a file whose pieces
lie outside their tiles' extents fails spec8.py, not this check.

  window-oracle.py WALKS GRAPH_WALKS [--seq S ...] [--every-window-up-to L]
                   [--windows N] [--contexts 0,1000] [--attach-bp B] [--seed K]

A sequence of L bp or fewer is cut at every [s, e); a longer one at the
windows either side of and over every tile edge, the whole sequence if it
is --widest bp or shorter, and N more of random starts and widths up to
--widest. --digest compares each list of steps by a hash of its text, for
files whose windows hold millions of steps. Exits 1 on any difference."""
import argparse
import bisect
import collections
import hashlib
import importlib.util
import json
import os
import random
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "spec8", os.path.join(HERE, "..", "docs", "departures", "scripts", "spec8.py"))
spec8 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(spec8)

Step = collections.namedtuple("Step", "node rev ref against bp passes piece")
Piece = collections.namedtuple("Piece", "path frag index hap steps tile")


class Sequence:
    """One reference sequence's tiles, decoded on demand, and its records."""

    def __init__(self, w, seq):
        self.w, self.seq = w, seq
        entries = w.entries(seq)
        self.tiles = sorted((e for e in entries if e.kind == "tile" and e.length > 0), key=lambda e: e.start)
        self.starts = [e.start for e in self.tiles]
        self.details = collections.defaultdict(list)
        for e in entries:
            if e.kind == "detail":
                self.details[int(e.name.split(":")[0])].append(e)
        self.blocks_units = [e for e in entries if e.kind == "departures"]
        self.records = sorted({tuple(c) for e in self.blocks_units for c in w.unit_rows(e)})
        self.holes = sorted(w.holes.get(seq, []))
        self.cache = collections.OrderedDict()

    def decoded(self, e):
        if e.offset in self.cache:
            self.cache.move_to_end(e.offset)
            return self.cache[e.offset]
        t = self.w.read_tile(e)
        cs = int(e.name)

        def steps_of(rs, segs, key):
            return [Step(h >> 1, h & 1, None, 0, rs.node_len[h >> 1], 0, key) if p is None else
                    Step(h >> 1, h & 1, t.off[p], int(h != t.R[p]), t.len[p], t.passes[p], key)
                    for h, p in t.steps(rs, segs)]

        pieces = []
        for r in t.ref_rows:
            key = (r["path"], int(r["frag"]), r["piece"], False)
            steps = [Step(t.R[p] >> 1, t.R[p] & 1, t.off[p], 0, t.len[p], t.passes[p], key)
                     for p in range(r["first"], r["first"] + r["nsteps"])]
            pieces.append(Piece(r["path"], int(r["frag"]), r["piece"], r["hap"], steps, cs))
        for c in t.walks:
            key = (c[4], int(c[5]), int(c[7]), False)
            segs = t.decode(t.rs, c[9], c[10], int(c[8]))
            pieces.append(Piece(c[4], int(c[5]), int(c[7]), int(c[6]), steps_of(t.rs, segs, key), cs))
        moved = {}
        for de in self.details.get(cs, []):
            rs, walks, _, _ = self.w.read_detail(de)
            for c in walks:
                key = (c[4], int(c[5]), int(c[7]), True)
                moved[key[:3]] = steps_of(rs, t.decode(rs, c[9], c[10], int(c[8])), key)
        for c in t.abridged:
            pieces.append(Piece(c[4], int(c[5]), int(c[7]), int(c[6]), moved[(c[4], int(c[5]), int(c[7]))], cs))
        positions = list(zip(t.off, t.end))
        self.cache[e.offset] = (pieces, positions)
        if len(self.cache) > 24:
            self.cache.popitem(last=False)
        return self.cache[e.offset]

    def tile_at(self, base):
        k = bisect.bisect_right(self.starts, base) - 1
        return self.tiles[k] if k >= 0 and self.tiles[k].end > base else None

    def squeeze(self, pos):
        return pos - sum(min(b, pos) - a for a, b in self.holes if a < pos)


def shown(text, digest):
    return hashlib.sha1(text.encode()).hexdigest()[:16] if digest else text


def steps_text(steps, expand, on_r=True):
    out = []
    for s in steps:
        if s.ref is None and s.piece[3] and not expand:
            if out and isinstance(out[-1], list) and out[-1][1] == s.piece:
                out[-1][0] += s.bp
            else:
                out.append([s.bp, s.piece])
        else:
            handle = f"{'<' if s.rev else '>'}{s.node}"
            out.append(f"{s.ref}{'-' if s.against else '+'}{handle}" if on_r and s.ref is not None else handle)
    return " ".join(f"~{x[0]}" if isinstance(x, list) else x for x in out)


def leave_base(pos, reversed_):
    return pos if reversed_ else pos - 1


def rejoin_base(pos, reversed_):
    return pos - 1 if reversed_ else pos


def cut(sq, s, e, context, expand, attach_bp, digest=False):
    d0, d1 = max(0, s - context), e + context
    chosen = [t for t in sq.tiles if t.start < d1 and t.end > d0]
    pieces, lo, hi = [], d0, d1
    for t in chosen:
        ps, positions = sq.decoded(t)
        pieces += ps
        for a, b in positions:
            if a < d1 and b > d0:
                lo, hi = min(lo, a), max(hi, b)

    def on_d(step):
        return step.ref is not None and step.ref < d1 and step.ref + step.bp > d0

    fragments = []
    by_line = collections.defaultdict(list)
    for p in pieces:
        by_line[(p.path, p.frag)].append(p)
    for (path, frag), ps in by_line.items():
        ps.sort(key=lambda p: p.index)
        runs = [[ps[0]]]
        for p in ps[1:]:
            if p.index == runs[-1][-1].index + 1:
                runs[-1].append(p)
            else:
                runs.append([p])
        for run in runs:
            steps = [x for p in run for x in p.steps]
            on = [i for i, x in enumerate(steps) if on_d(x)]
            if on:
                first, last = on[0], on[-1]
                before = sum(x.bp for x in steps[:first])
                held = sum(x.bp for x in steps[first:last + 1])
                after = sum(x.bp for x in steps[last + 1:])
                hap = run[0].hap + before
                fragments.append([path, frag, hap, hap + held, before, after,
                                  shown(steps_text(steps[first:last + 1], expand), digest)])

    def attaches(own_bp, leave, rejoin):
        return own_bp <= attach_bp and any(d0 <= b < d1 for b in (leave, rejoin))

    departures = []
    for c in sq.records:
        if int(c[1]) < d1 and int(c[2]) > d0:
            path, hap_start, own_bp = c[4], int(c[5]), int(c[6])
            lpos, lrev, rpos, rrev = int(c[8]), c[9] == "-", int(c[11]), c[12] == "-"
            lb, rb = leave_base(lpos, lrev), rejoin_base(rpos, rrev)
            steps = None
            if attaches(own_bp, lb, rb):
                own = []
                for t in {sq.tile_at(lb).offset: sq.tile_at(lb), sq.tile_at(rb).offset: sq.tile_at(rb)}.values():
                    for p in sq.decoded(t)[0]:
                        if p.path == path:
                            at = p.hap
                            for x in p.steps:
                                if hap_start <= at and at + x.bp <= hap_start + own_bp:
                                    own.append((at, x))
                                at += x.bp
                steps = steps_text([x for _, x in sorted(own, key=lambda y: y[0])], expand, on_r=False)
                steps = shown(steps, digest) if steps else None
            departures.append([path, hap_start, own_bp, int(c[7]), lpos, lrev, int(c[10]), rpos, rrev,
                               int(c[13]), False, steps])
    for p in pieces:
        at = p.hap
        last = None
        between = []
        for x in p.steps:
            if x.ref is not None:
                if last is not None:
                    a, a_end = last
                    lrev, rrev = bool(a.against), bool(x.against)
                    lpos = a.ref if lrev else a.ref + a.bp
                    rpos = x.ref + x.bp if rrev else x.ref
                    own_bp = sum(y.bp for y in between)
                    adjacent = own_bp == 0 and lrev == rrev and sq.squeeze(lpos) == sq.squeeze(rpos)
                    lb, rb = leave_base(lpos, lrev), rejoin_base(rpos, rrev)
                    if not adjacent and min(lb, rb) < hi and max(lb, rb) + 1 > lo:
                        steps = steps_text(between, expand, on_r=False) if attaches(own_bp, lb, rb) else ""
                        steps = shown(steps, digest) if steps else None
                        departures.append([p.path, a_end, own_bp, 0, lpos, lrev, a.passes, rpos, rrev, x.passes,
                                           True, steps])
                last, between = (x, at + x.bp), []
            elif last is not None:
                between.append(x)
            at += x.bp
    return {"fragments": fragments, "departures": departures}


def windows(sq, length, tile, every, n, widest, rng):
    if every:
        for s in range(length):
            for e in range(s + 1, length + 1):
                yield s, e
        return
    if length <= widest:
        yield 0, length
    for t in sq.tiles:
        for b in (t.start, t.end):
            for s, e in ((b - 1, b), (b, b + 1), (b - 1, b + 1), (b - tile // 2, b + tile // 2)):
                s, e = max(0, s), min(length, e)
                if s < e:
                    yield s, e
    for _ in range(n):
        width = max(1, min(widest, int(10 ** rng.uniform(0, 6.5))))
        s = rng.randrange(max(1, length))
        yield s, min(length, s + width) if s < length else length


def canonical(result):
    return (sorted(json.dumps(f) for f in result["fragments"]),
            sorted(json.dumps(d) for d in result["departures"]))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("walks")
    ap.add_argument("graph_walks")
    ap.add_argument("--seq", action="append")
    ap.add_argument("--every-window-up-to", type=int, default=0)
    ap.add_argument("--windows", type=int, default=200)
    ap.add_argument("--widest", type=int, default=2_000_000)
    ap.add_argument("--digest", action="store_true")
    ap.add_argument("--contexts", default="0,1000")
    ap.add_argument("--attach-bp", type=int, default=65536)
    ap.add_argument("--expand", default="yes,no")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--most", type=int, default=10, help="differences printed in full")
    args = ap.parse_args()
    w = spec8.Walks(args.walks)
    rng = random.Random(args.seed)
    contexts = [int(x) for x in args.contexts.split(",")]
    expands = [x == "yes" for x in args.expand.split(",")]
    node = subprocess.Popen(
        ["node", os.path.join(HERE, "window-cuts.mjs"), args.graph_walks, args.walks, str(args.attach_bp),
         "1" if args.digest else "0"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    counts = collections.Counter()
    shown = 0
    for seq in args.seq or w.seq_order:
        sq = Sequence(w, seq)
        length = w.length(seq)
        for s, e in windows(sq, length, w.tile, length <= args.every_window_up_to, args.windows, args.widest, rng):
            for context in contexts:
                for expand in expands:
                    query = {"seq": seq, "start": s, "end": e, "context": context, "expand": expand}
                    node.stdin.write(json.dumps(query) + "\n")
                    node.stdin.flush()
                    got = json.loads(node.stdout.readline())
                    want = cut(sq, s, e, context, expand, args.attach_bp, args.digest)
                    counts["windows"] += 1
                    counts["fragments"] += len(want["fragments"])
                    counts["departures"] += len(want["departures"])
                    if "error" in got:
                        counts["differ"] += 1
                        if shown < args.most:
                            shown += 1
                            print(f"{seq}:{s}-{e} context {context} expand {expand}: graph-walks threw {got['error']}")
                        continue
                    (wf, wd), (gf, gd) = canonical(want), canonical(got)
                    if (wf, wd) != (gf, gd):
                        counts["differ"] += 1
                        if shown < args.most:
                            shown += 1
                            print(f"{seq}:{s}-{e} context {context} expand {expand}:")
                            for label, a, b in (("fragment", wf, gf), ("departure", wd, gd)):
                                ca, cb = collections.Counter(a), collections.Counter(b)
                                for k in sorted((ca - cb).keys()):
                                    print(f"  {label} expected, not returned: {k[:400]}")
                                for k in sorted((cb - ca).keys()):
                                    print(f"  {label} returned, not expected: {k[:400]}")
    node.stdin.close()
    node.wait()
    print(f"{args.walks}: {counts['windows']} windows, {counts['fragments']} fragments, "
          f"{counts['departures']} departures expected; {counts['differ']} windows differ")
    return 1 if counts["differ"] else 0


if __name__ == "__main__":
    sys.exit(main())
