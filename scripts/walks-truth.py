#!/usr/bin/env python3
"""walks-truth.py: score a --walks file against alignments of the haplotypes
to its reference.

  walks-truth.py lift ALIGN.paf.gz SEQ [SEQ ...] > lift.tsv
      Keeps the alignments onto the named reference sequences (PanSN names,
      e.g. GRCh38#0#chr22) and cuts each at indels of --gap bp or more into
      blocks: query, qstart, qend, target, tstart, tend, strand.

  walks-truth.py score lift.tsv WALKS [--haps H,H,...] [--regions R.tsv]
      For each haplotype path in both, compares the chunks its pieces are
      filed under with the chunks its aligned bases fall in, and prints:
        placement  piece bp filed within --slack chunks of where they align
        recall     (haplotype, chunk) pairs holding --present bp or more of
                   aligned sequence that the file lists under that chunk or
                   the one before (a reader reads at least one chunk back)
        precision  (haplotype, chunk) pairs the file lists that hold aligned
                   sequence within --slack chunks
        pieces     pieces per filed (haplotype, chunk) pair: 1 when every
                   haplotype enters each chunk once
      R.tsv (name, sequence, start, end) adds recall and precision per region.

A last piece's length is unknown from the walk rows, so it takes the record's
mean bp per step. The walk file is read whole.
"""

import argparse
import bisect
import gzip
import re
import sys
from collections import defaultdict

CIGAR = re.compile(rb"(\d+)([=XIDM])")


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
                if block and block[1] > block[0]:
                    a, b, ta, tb = block
                    lo, hi = (a, b) if forward else (b, a)
                    out.write(f"{q.decode()}\t{lo}\t{hi}\t{t.decode()}\t{ta}\t{tb}\t{'+' if forward else '-'}\n")

            for n, op in CIGAR.findall(cg):
                n = int(n)
                if op in b"=XM":
                    step = n if forward else -n
                    if block is None:
                        block = [qpos, qpos + step, tpos, tpos + n] if forward else [qpos, qpos + step, tpos, tpos + n]
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

    def chunks(self, lo, hi, size):
        """{(target, chunk start): aligned bp} for query bases lo..hi."""
        out = defaultdict(int)
        k = bisect.bisect_left(self.starts, lo - self.longest)
        while k < len(self.blocks) and self.blocks[k][0] < hi:
            qs, qe, t, ts, te, forward = self.blocks[k]
            k += 1
            a, b = max(lo, qs), min(hi, qe)
            if a >= b:
                continue
            if forward:
                ta, tb = ts + (a - qs), ts + (b - qs)
            else:
                ta, tb = ts + (qe - b), ts + (qe - a)
            c = ta - ta % size
            while c < tb:
                out[(t, c)] += min(tb, c + size) - max(ta, c)
                c += size
        return out


def read_lift(path, names):
    truth = defaultdict(Truth)
    with open(path) as f:
        for line in f:
            q, qs, qe, t, ts, te, strand = line.rstrip("\n").split("\t")
            if names is not None and q not in names:
                continue
            truth[q].blocks.append((int(qs), int(qe), t, int(ts), int(te), strand == "+"))
    for t in truth.values():
        t.finish()
    return truth


def walk_rows(path, haps, size):
    """Pieces by path: [(record start, hapOffset, piece, nsteps, seq, chunk start)]; chunk size."""
    pieces = defaultdict(list)
    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, "rt") as f:
        for line in f:
            if line[0] == "#":
                if line.startswith("#walks"):
                    size = int(re.search(r"chunk:i:(\d+)", line).group(1))
                continue
            c = line.split("\t", 9)
            if c[3] != "walk":
                continue
            name = c[4]
            if haps is not None and name.rsplit("#", 1)[0] not in haps:
                continue
            pieces[name].append((int(c[5]), int(c[6]), int(c[7]), int(c[8]), c[0], int(c[1])))
    return pieces, size


def score(args):
    haps = set(args.haps.split(",")) if args.haps else None
    pieces, size = walk_rows(args.walks, haps, args.chunk)
    truth = read_lift(args.lift, set(pieces))
    regions = []
    if args.regions:
        for line in open(args.regions):
            if line.strip() and line[0] != "#":
                n, s, a, b = line.split()[:4]
                regions.append((n, s, int(a), int(b)))
    slack = args.slack * size
    total = defaultdict(int)
    by_region = defaultdict(lambda: defaultdict(int))
    lost = defaultdict(int)
    for name, ps in pieces.items():
        t = truth.get(name)
        if t is None:
            total["paths without alignments"] += 1
            continue
        total["paths"] += 1
        ps.sort()
        filed = set()
        present = defaultdict(int)
        for k, (rec, off, piece, nsteps, seq, cs) in enumerate(ps):
            same = k + 1 < len(ps) and ps[k + 1][0] == rec
            if same:
                bp = ps[k + 1][1] - off
            else:
                first = next(j for j in range(k, -1, -1) if j == 0 or ps[j - 1][0] != rec)
                done = off - ps[first][1]
                steps = sum(p[3] for p in ps[first:k])
                bp = round(nsteps * done / steps) if steps else nsteps * 30
            filed.add((seq, cs))
            aligned = t.chunks(off, off + bp, size)
            for key, n in aligned.items():
                present[key] += n
            near = sum(n for (tq, tc), n in aligned.items() if tq == seq and abs(tc - cs) <= slack)
            total["piece bp"] += bp
            total["piece bp aligned"] += sum(aligned.values())
            total["piece bp aligned near"] += near
        truth_cells = {key for key, n in present.items() if n >= args.present}
        for seq, cs in truth_cells:
            hit = (seq, cs) in filed or (seq, cs - size) in filed
            total["recall pairs"] += 1
            total["recall hit"] += hit
            if not hit:
                lost[(seq, cs)] += 1
            for n, s, a, b in regions:
                if s == seq and a < cs + size and cs < b:
                    by_region[n]["recall pairs"] += 1
                    by_region[n]["recall hit"] += hit
        for seq, cs in filed:
            ok = any((seq, cs + d * size) in present for d in range(-args.slack, args.slack + 1))
            total["filed pairs"] += 1
            total["filed ok"] += ok
            for n, s, a, b in regions:
                if s == seq and a < cs + size and cs < b:
                    by_region[n]["filed pairs"] += 1
                    by_region[n]["filed ok"] += ok
        total["pieces"] += len(ps)

    def pct(a, b):
        return f"{100 * a / b:.2f}%" if b else "-"

    print(f"walks {args.walks}: {total['paths']} haplotype paths scored, {total['paths without alignments']} without alignments")
    print(f"  placement  {pct(total['piece bp aligned near'], total['piece bp aligned'])} of aligned piece bp within {args.slack} chunk(s); "
          f"{pct(total['piece bp aligned'], total['piece bp'])} of piece bp aligned")
    print(f"  recall     {pct(total['recall hit'], total['recall pairs'])} of {total['recall pairs']} (haplotype, chunk) pairs with >= {args.present} aligned bp")
    print(f"  precision  {pct(total['filed ok'], total['filed pairs'])} of {total['filed pairs']} filed (haplotype, chunk) pairs")
    print(f"  pieces     {total['pieces']}, {total['pieces'] / max(total['filed pairs'], 1):.2f} per filed pair")
    for n, s, a, b in regions:
        r = by_region[n]
        print(f"  {n:24} {s}:{a}-{b}  recall {pct(r['recall hit'], r['recall pairs'])} of {r['recall pairs']}  precision {pct(r['filed ok'], r['filed pairs'])} of {r['filed pairs']}")
    if args.lost:
        with open(args.lost, "w") as f:
            for (seq, cs), n in sorted(lost.items()):
                f.write(f"{seq}\t{cs}\t{n}\n")


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
    b.add_argument("--haps", help="PanSN sample#haplotype list")
    b.add_argument("--chunk", type=int, default=65536, help="chunk size when WALKS has no header")
    b.add_argument("--regions")
    b.add_argument("--slack", type=int, default=1)
    b.add_argument("--present", type=int, default=300)
    b.add_argument("--lost", help="write chunks where recall fails, with counts")
    args = p.parse_args()
    lift(args) if args.cmd == "lift" else score(args)


if __name__ == "__main__":
    main()
