#!/usr/bin/env python3
# Reads each `blocks` row of a walk format 8 file as a reader that has not
# loaded its piece does, against its tile's `ref` rows alone, and checks it
# against the piece's walk row in its detail unit, decoded by the spec's
# rules and collapsed: each step on R kept as its position in R and its
# direction, each maximal run of steps off R replaced by its bp.
# - the row's list expands to the collapsed walk: an item of all digits is
#   a run off R of that many bp, any other a block `<d><+|-><len>`, split at
#   its first `+` or `-` after its first character, which begins `d` bp from
#   where the block before ended, or from 0, and covers whole steps of R,
#   each beginning where the one before ended, for `len` bp along R or
#   against it
# - the collapsed walk, encoded by the spec's rules, gives back the row's
#   `start end` and its list, byte for byte, in eight columns
# - every piece of a detail unit has one blocks row in its tile's blocks
#   unit, and every blocks row is such a piece's
# Reads the file as a stream, holding the R of a sequence's tiles with
# abridged rows until its table, and a tile's collapsed pieces, 8 bytes a
# step, until its blocks unit. Prints each failure, then a count line, and
# exits 1 on any failure.
#
# Usage: expand7.py walks.gz [--shard I/N] [--examples 20]
import argparse
import gzip
import re
import sys
import zlib
from array import array

ap = argparse.ArgumentParser()
ap.add_argument('file')
ap.add_argument('--shard', default='0/1', help='I/N: the paths checked, by a hash of their name')
ap.add_argument('--examples', type=int, default=20)
args = ap.parse_args()
SHARD, SHARDS = map(int, args.shard.split('/'))
CHOICE = re.compile(r'(-?[0-9]+)(?::([0-9]+))?(?:@([0-9]+))?')
DIGITS = re.compile(r'[0-9]+')
failures = []


def fail(message):
    failures.append(message)
    if len(failures) <= args.examples:
        print(message)


def in_shard(path):
    return zlib.crc32(path.encode()) % SHARDS == SHARD


def handles(field, prev):
    out = []
    for token in [] if field == '.' else field.split(','):
        prev += int(token) >> 1
        out.append(2 * prev + (int(token) & 1))
    return out, prev


class Tile:
    def __init__(self):
        self.refs, self.abridged, self.h = [], False, None

    def index(self):
        if self.h is None:
            self.h, self.off, self.len, self.occ, self.at = [], [], [], {}, {}
            for start, hs, lens in sorted(self.refs):
                for h, n in zip(hs, lens):
                    self.occ.setdefault(h >> 1, []).append(len(self.h))
                    self.at[start] = len(self.h)
                    self.h.append(h)
                    self.off.append(start)
                    self.len.append(n)
                    start += n
        return self

    def nearest(self, node, i):
        return min(reversed(self.occ[node]), key=lambda j: abs(j - i))

    def along(self, i, h):
        j = i + 1 if self.h[i] == h else i - 1
        if not 0 <= j < len(self.h):
            raise ValueError(f'a step off the end of R from position {i}')
        return j, self.h[j] if j > i else self.h[j] ^ 1


def decode(tile, routes, c):
    # A walk row's steps as (handle, position in R or None)
    start, _, copy = c[9].partition('@')
    choices, prev = [], 0
    for token in [] if c[10] == '.' else c[10].split(','):
        m = CHOICE.fullmatch(token)
        if m is None:
            raise ValueError(f'route choice {token}')
        prev += int(m.group(1)) >> 1
        entry, interior, leave = routes[prev]
        choices.append(((None if leave is None else leave ^ 1, [g ^ 1 for g in reversed(interior)],
                         None if entry is None else entry ^ 1) if int(m.group(1)) & 1 else (entry, interior, leave))
                       + (m.group(2), m.group(3)))
    steps = []
    if choices and choices[0][0] is None:
        steps = [(g, None) for g in choices[0][1]]
        choices = choices[1:]
    h = int(start)
    i = tile.occ[h >> 1][int(copy) if copy else 0]
    steps.append((h, i))
    ended = False
    for entry, interior, leave, entry_copy, leave_copy in choices:
        if entry is None or ended:
            raise ValueError('a route after the piece left R for good')
        target = tile.occ[entry >> 1][int(entry_copy)] if entry_copy else None
        while (i != target) if entry_copy else (h != entry):
            i, h = tile.along(i, h)
            steps.append((h, i))
        if h != entry:
            raise ValueError('an entry copy read the other way')
        steps += [(g, None) for g in interior]
        if leave is None:
            ended = True
        else:
            h = leave
            i = tile.occ[h >> 1][int(leave_copy)] if leave_copy else tile.nearest(h >> 1, i)
            steps.append((h, i))
    while not ended and len(steps) < int(c[8]):
        i, h = tile.along(i, h)
        steps.append((h, i))
    if len(steps) != int(c[8]):
        raise ValueError(f'{len(steps)} steps decoded, nsteps {c[8]}')
    return steps


def collapse(tile, nodes, steps):
    # A step on R as 2 * its position in R, plus 1 against R; a maximal run
    # of steps off R as its bp, negative
    out = array('q')
    for h, i in steps:
        if i is not None:
            out.append(2 * i + (tile.h[i] != h))
        elif out and out[-1] < 0:
            out[-1] -= nodes[h >> 1]
        else:
            out.append(-nodes[h >> 1])
    return out


def expand(tile, field):
    # The collapsed walk a list states, read against R alone, or why it
    # states none
    out, at, unread = array('q'), 0, None
    for item in field.split(','):
        sign = min((k for k in (item.find('+', 1), item.find('-', 1)) if k > 0), default=0)
        if unread is None:
            if DIGITS.fullmatch(item):
                if int(item):
                    out.append(-int(item))
                else:
                    unread = 'a run of 0 bp'
            elif not sign or not re.fullmatch('-?[0-9]+', item[:sign]) or not DIGITS.fullmatch(item[sign + 1:]):
                unread = f'item {item[:30]} is no run and no block'
            else:
                begin = at + int(item[:sign])
                against = item[sign] == '-'
                at = begin + int(item[sign + 1:]) * (-1 if against else 1)
                lo, hi = min(begin, at), max(begin, at)
                first = i = tile.at.get(lo)
                while i is not None and i < len(tile.h) and tile.off[i] == lo and lo < hi:
                    lo += tile.len[i]
                    i += 1
                if first is None:
                    unread = f'block {item[:30]} has no step of R starting at {lo}'
                elif lo != hi or i == first:
                    unread = f'block {item[:30]} leaves the steps of R at {lo}'
                else:
                    out.extend(2 * j + against for j in (range(i - 1, first - 1, -1) if against else range(first, i)))
    return out, unread


def encode(tile, walk):
    # The `start end` and list of the blocks row a collapsed walk makes, or
    # None for a walk with no step on R
    parts = []
    for v in walk:
        last = parts[-1] if parts else None
        if v < 0:
            parts.append(-v)
        else:
            a, b = tile.off[v >> 1], tile.off[v >> 1] + tile.len[v >> 1]
            begin, end = (b, a) if v & 1 else (a, b)
            if isinstance(last, list) and last[1] == begin and (last[0] > last[1]) == bool(v & 1):
                last[1] = end
            else:
                parts.append([begin, end])
    items, at = [], 0
    for part in parts:
        if isinstance(part, list):
            items.append(f'{part[0] - at}{"+" if part[0] < part[1] else "-"}{abs(part[1] - part[0])}')
            at = part[1]
        else:
            items.append(str(part))
    on = [part for part in parts if isinstance(part, list)]
    return (min(min(part) for part in on), max(max(part) for part in on), ','.join(items)) if on else None


def described(v):
    return f'{-v} bp off R' if v < 0 else f'position {v >> 1} of R {"against" if v & 1 else "along"} it'


def clipped(text):
    return text if len(text) <= 80 else text[:77] + '...'


def compare(tile, key, row, walk):
    where = f'{key[0]} tile {key[1]}: {key[2]} line at {key[3]} piece {key[4]}'
    lo, hi, rest = row
    stated = (lo, hi, rest[0]) if len(rest) == 1 else None
    if stated is None:
        fail(f'{where}: its blocks row has {7 + len(rest)} columns, not eight')
    else:
        got, unread = expand(tile, rest[0])
        differs = next((k for k, (a, b) in enumerate(zip(got, walk)) if a != b), min(len(got), len(walk)))
        if unread is not None:
            fail(f'{where}: its blocks row {clipped(rest[0])} does not expand against R: {unread}')
        elif got != walk:
            fail(f'{where}: its blocks row {clipped(rest[0])} expands to {len(got)} steps and runs off R, its detail '
                 f'row collapses to {len(walk)}, and they first differ at {differs}: '
                 f'{described(got[differs]) if differs < len(got) else "nothing"} for '
                 f'{described(walk[differs]) if differs < len(walk) else "nothing"}')
        again = encode(tile, walk)
        if again != stated:
            fail(f'{where}: its blocks row says {lo} {hi} {clipped(rest[0])}, its detail row collapsed encodes to '
                 f'{"no block" if again is None else f"{again[0]} {again[1]} {clipped(again[2])}"}')


tiles = {}    # (seq, tile name) -> Tile, of the sequence being read
walks = {}    # (seq, tile name, path, fragStart, piece) -> the piece's collapsed walk, until its blocks row
early = {}    # the same -> (start, end, columns after piece) of a blocks row read before its piece
stats = dict(pieces=0, rows=0)
unit = tile = None
routes, route_prev, nodes = [], 0, {}
with gzip.open(args.file, 'rt') as f:
    for line in f:
        c = line.rstrip('\n').split('\t')
        if c[0] == '#walks' and c[1:2] != ['format:i:8']:
            sys.exit(f'expand7.py: {args.file}: {" ".join(c[1:2])}, not walk format 8')
        if c[0] == '#unit':
            if unit is not None and unit[1] == 'tile' and not tiles[(unit[0], unit[2])].abridged:
                del tiles[(unit[0], unit[2])]
            unit = (c[1], c[4], c[5])
            cs = c[5].split(':')[0]
            routes, route_prev, nodes = [], 0, {}
            if c[4] == 'tile':
                tile = tiles[(c[1], c[5])] = Tile()
            elif c[4] == 'detail':
                tile = tiles.get((c[1], cs))
                if tile is None:
                    fail(f'{c[1]}: detail unit {c[5]} of a tile with no abridged row')
            elif c[4] == 'table':
                for key in walks:
                    fail(f'{key[0]} tile {key[1]}: {key[2]} line at {key[3]} piece {key[4]}: no blocks row in the '
                         f'tile\'s blocks unit')
                for key in early:
                    fail(f'{key[0]} tile {key[1]}: {key[2]} line at {key[3]} piece {key[4]}: a blocks row of no piece '
                         f'in the tile\'s detail units, or a second row of one')
                tiles, walks, early = {}, {}, {}
        elif line[0] != '#' and unit is not None:
            seq, kind, name = unit
            if kind == 'tile' and c[3] == 'ref':
                tile.refs.append((int(c[6]), handles(c[9], 0)[0], [int(x) for x in c[10].split(',')]))
            elif kind == 'tile' and c[3] == 'abridged':
                tile.abridged = True
            elif kind == 'detail' and c[3] == 'nodes':
                at = 0
                for d, n in zip(c[4].split(','), c[5].split(',')):
                    at += int(d)
                    nodes[at] = int(n)
            elif kind == 'detail' and c[3] == 'route':
                ends = []
                for field in c[4:7]:
                    hs, route_prev = handles(field, route_prev)
                    ends.append(hs)
                routes.append((ends[0][0] if ends[0] else None, ends[1], ends[2][0] if ends[2] else None))
            elif kind == 'detail' and c[3] == 'walk' and tile is not None and in_shard(c[4]):
                key = (seq, cs, c[4], c[5], c[7])
                stats['pieces'] += 1
                try:
                    walk = collapse(tile.index(), nodes, decode(tile.index(), routes, c))
                except (IndexError, KeyError, ValueError) as e:
                    walk = None
                    fail(f'{seq} tile {cs}: {c[4]} line at {c[5]} piece {c[7]}: its walk row in detail unit {name} '
                         f'does not decode: {type(e).__name__}: {e}')
                if walk is not None and key in early:
                    compare(tile, key, early.pop(key), walk)
                elif walk is not None:
                    walks[key] = walk
            elif kind == 'blocks' and c[3] == 'blocks' and in_shard(c[4]):
                key = (seq, name, c[4], c[5], c[6])
                row = (int(c[1]), int(c[2]), c[7:])
                stats['rows'] += 1
                if key in walks:
                    compare(tiles[(seq, name)].index(), key, row, walks.pop(key))
                elif key in early:
                    fail(f'{seq} tile {name}: {c[4]} line at {c[5]} piece {c[6]}: two blocks rows')
                else:
                    early[key] = row
if len(failures) > args.examples:
    print(f'... and {len(failures) - args.examples} more')
print(f'expand7: {args.file}: {stats["rows"]} blocks rows, {stats["pieces"]} pieces in detail units, '
      f'{len(failures)} failures')
sys.exit(1 if failures else 0)
