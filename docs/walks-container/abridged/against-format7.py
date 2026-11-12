#!/usr/bin/env python3
# ADR 0012's comparison of a format 8 walk file with the format 7 file the
# released 4.0.0 writer built from the same graph with the same options.
# It recomputes each format 7 `abridged` row from the format 8 file alone,
# its abridged row, its blocks row and its tile's ref rows:
# - hapOffset moves on by the list's leading run, and bp is the list's
#   items less its leading and trailing runs
# - start and end are the handles of the first block's first step and the
#   last block's last, read from R: a `-` block's first step ends where it
#   begins and runs against R
# - `start end` before `abridged` is the span of those two steps on R
# - start takes @k where its position is not its node's first in R, end
#   where its position is not the one nearest start's, the later on a tie
# Then it reads both files line by line, the format 8 file with its blocks
# units and tables left out, format:i:8 read as format:i:7 and each
# abridged row replaced by the one recomputed, the format 7 file with its
# tables left out, and counts the lines that differ: in the header, in
# abridged rows and elsewhere. Every unit but blocks units and tables, and
# every tile but its abridged rows, must have the format 7 file's bytes,
# and every format 7 abridged row must be recomputed.
# Prints the counts and the first differences, and exits 1 on any.
#
# Usage: against-format7.py new.walks.gz hosted.walks.gz [--examples 20]
import argparse
import gzip
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from itertools import zip_longest

ap = argparse.ArgumentParser()
ap.add_argument('new')
ap.add_argument('hosted')
ap.add_argument('--examples', type=int, default=20)
args = ap.parse_args()
BLOCK = re.compile(rb'(-?[0-9]+)([+-])([0-9]+)')


def lines(path):
    if shutil.which('pigz'):
        with subprocess.Popen(['pigz', '-dc', path], stdout=subprocess.PIPE, bufsize=1 << 24) as proc:
            yield from proc.stdout
        if proc.returncode:
            sys.exit(f'against-format7.py: pigz -dc {path} exited {proc.returncode}')
    else:
        with gzip.open(path, 'rb') as f:
            yield from f


def handles(field):
    out, prev = [], 0
    for token in field.split(b','):
        prev += int(token) >> 1
        out.append(2 * prev + (int(token) & 1))
    return out


class R:
    def __init__(self, refs):
        self.h, self.off, self.len = [], [], []
        for start, hs, lens in sorted(refs):
            for h, n in zip(hs, lens):
                self.h.append(h)
                self.off.append(start)
                self.len.append(n)
                start += n
        self.starting = {o: i for i, o in enumerate(self.off)}
        self.ending = {o + n: i for i, (o, n) in enumerate(zip(self.off, self.len))}
        self.occ = defaultdict(list)
        for i, h in enumerate(self.h):
            self.occ[h >> 1].append(i)


def format7(r, c, items):
    at, spans, runs = 0, [], []
    for x in items:
        m = BLOCK.fullmatch(x)
        if m:
            begin = at + int(m[1])
            at = begin + int(m[3]) if m[2] == b'+' else begin - int(m[3])
            spans.append((begin, at, m[2] == b'+', int(m[3])))
        else:
            runs.append(int(x))
    lead = 0 if BLOCK.fullmatch(items[0]) else int(items[0])
    trail = 0 if BLOCK.fullmatch(items[-1]) else int(items[-1])
    (b0, _, along0, _), (_, e1, along1, _) = spans[0], spans[-1]
    first, flip0 = (r.starting[b0], 0) if along0 else (r.ending[b0], 1)
    last, flip1 = (r.ending[e1], 0) if along1 else (r.starting[e1], 1)
    lo = min(r.off[first], r.off[last])
    hi = max(r.off[first] + r.len[first], r.off[last] + r.len[last])
    occ_first, occ_last = r.occ[r.h[first] >> 1], r.occ[r.h[last] >> 1]
    nearest = min(reversed(occ_last), key=lambda j: abs(j - first))
    start = b'%d' % (r.h[first] ^ flip0) + (b'@%d' % occ_first.index(first) if occ_first[0] != first else b'')
    end = b'%d' % (r.h[last] ^ flip1) + (b'@%d' % occ_last.index(last) if nearest != last else b'')
    bp = sum(runs) + sum(s[3] for s in spans) - lead - trail
    return b'\t'.join([c[0], b'%d' % lo, b'%d' % hi, b'abridged', c[4], c[5], b'%d' % (int(c[6]) + lead), c[7], c[8],
                       b'%d' % bp, start, end, c[10]]) + b'\n'


refs, tile, unit = [], None, None
rs, abridged, listed = {}, defaultdict(list), {}
for line in lines(args.new):
    c = line.rstrip(b'\n').split(b'\t')
    if c[0] == b'#unit':
        unit, refs = c[4], []
        tile = (c[1], c[5])
    elif line[:1] != b'#' and unit == b'tile' and c[3] == b'ref':
        refs.append((int(c[6]), handles(c[9]), [int(x) for x in c[10].split(b',')]))
    elif line[:1] != b'#' and unit == b'tile' and c[3] == b'abridged':
        if tile not in rs:
            rs[tile] = R(refs)
        abridged[tile].append(c[:11])
    elif line[:1] != b'#' and unit == b'blocks':
        listed[(tile, c[4], c[5], c[6])] = c[7].split(b',')
recomputed = {}
missing = 0
for t, rows in abridged.items():
    for c in rows:
        items = listed.get((t, c[4], c[5], c[7]))
        if items is None:
            missing += 1
        else:
            recomputed[(t, c[4], c[5], c[7])] = format7(rs[t], c, items)


def converted():
    unit = tile = None
    for line in lines(args.new):
        c = line.split(b'\t', 8)
        if c[0] == b'#unit':
            unit, tile = c[4], (c[1], c[5].rstrip(b'\n'))
        if unit in (b'blocks', b'table'):
            continue
        if c[0] == b'#walks':
            yield b'header', line.replace(b'\tformat:i:8', b'\tformat:i:7')
        elif unit is None:
            yield b'header', line
        elif line[:1] != b'#' and c[3] == b'abridged':
            yield b'abridged', recomputed.get((tile, c[4], c[5], c[7]), line)
        else:
            yield b'other', line


def hosted():
    unit = None
    for line in lines(args.hosted):
        if line.startswith(b'#unit\t'):
            unit = line.split(b'\t', 5)[4]
        if unit != b'table':
            yield line


differ = defaultdict(int)
compared = shown = 0
for mine, theirs in zip_longest(converted(), hosted(), fillvalue=None):
    compared += 1
    kind = 'length' if mine is None or theirs is None else mine[0].decode()
    if kind == 'length' or mine[1] != theirs:
        differ[kind] += 1
        if shown < args.examples:
            shown += 1
            print(f'line {compared}, {kind}:\n  format 8 as 7: {mine and mine[1][:300]!r}\n  format 7:      {theirs and theirs[:300]!r}')
print(f'{compared} lines; {sum(len(v) for v in abridged.values())} abridged rows in {len(abridged)} tiles, '
      f'{missing} with no blocks row; lines that differ: header {differ["header"]}, abridged rows '
      f'{differ["abridged"]}, other {differ["other"]}, past the end of one file {differ["length"]}')
sys.exit(1 if missing or any(differ.values()) else 0)
