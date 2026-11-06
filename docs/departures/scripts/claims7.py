#!/usr/bin/env python3
# Checks walk format 7's normative claims that neither the writer's tests nor
# verify7.py and audit7.py check, on any file the writer builds
# (docs/departures/claims7.md lists every claim and which check covers it).
# Each check prints `<count>\t<id> <claim>`; a count above 0 is a case where
# the file contradicts the claim, with examples below it. Reads the file as
# text a line at a time and decodes each tile's walk rows by the spec's
# decoding rules, holding one sequence's abridged rows and, with
# --own, the steps of the paths in its shard.
#
# Usage: claims7.py walks.gz [--own] [--shard I/N] [--examples 3]
import argparse
import bisect
import collections
import gzip
import sys
import zlib

ap = argparse.ArgumentParser()
ap.add_argument('file')
ap.add_argument('--own', action='store_true',
                help='decode every path of the shard into steps and check each record\'s own steps and ownTiles')
ap.add_argument('--shard', default='0/1', help='I/N: the paths --own checks, by a hash of their name')
ap.add_argument('--examples', type=int, default=3)
args = ap.parse_args()
SHARD, SHARDS = map(int, args.shard.split('/'))

counts = collections.Counter()
examples = collections.defaultdict(list)
CLAIMS = {}


def claim(key, text):
    CLAIMS[key] = text


def bad(key, example):
    counts[key] += 1
    if len(examples[key]) < args.examples:
        examples[key].append(example)


def seen(key):
    counts[key] += 0


def deltas(field, prev=0):
    out = []
    if field == '.':
        return out, prev
    for t in field.split(','):
        t = int(t)
        prev += t >> 1
        out.append(2 * prev + (t & 1))
    return out, prev


def ints(field):
    return [] if field == '.' else [int(x) for x in field.split(',')]


def with_k(token, mark):
    if mark in token:
        a, k = token.split(mark)
        return a, int(k)
    return token, None


class Tile:
    def __init__(self, seq, name, lo, hi):
        self.seq, self.name, self.lo, self.hi = seq, name, lo, hi
        self.refs = []      # (hapOffset, handles, lengths, passes field)
        self.routes = []
        self.route_prev = 0
        self.nodes = {}
        self.kinds = []
        self.h = None

    def index(self):
        if self.h is not None:
            return
        self.h, self.off, self.len = [], [], []
        for start, hs, lens, _ in sorted(self.refs, key=lambda r: r[0]):
            at = start
            for h, n in zip(hs, lens):
                self.h.append(h)
                self.off.append(at)
                self.len.append(n)
                at += n
        self.occ = collections.defaultdict(list)
        for i, h in enumerate(self.h):
            self.occ[h >> 1].append(i)

    def nearest(self, h, i):
        best = None
        for j in self.occ.get(h >> 1, []):
            if best is None or abs(j - i) <= abs(best - i):
                best = j
        return best

    def step(self, i, h):
        if self.h[i] == h:
            return (i + 1, self.h[i + 1]) if i + 1 < len(self.h) else None
        return (i - 1, self.h[i - 1] ^ 1) if i > 0 else None

    def oriented(self, rid, flip):
        e, inter, x = self.routes[rid]
        if not flip:
            return e, inter, x
        return (None if x is None else x ^ 1), [h ^ 1 for h in reversed(inter)], (None if e is None else e ^ 1)


class Undecodable(Exception):
    pass


def decode(t, cols):
    # A walk row's steps as (handle, position in R or None), by the spec's
    # Decoding a walk row, and for each copy mark whether the default would
    # have given the same position
    nsteps = int(cols[8])
    start, sk = with_k(cols[9], '@')
    start = int(start)
    choices = []
    prev = 0
    if cols[10] != '.':
        for tok in cols[10].split(','):
            tok, xk = with_k(tok, '@')
            tok, ek = with_k(tok, ':')
            v = int(tok)
            prev += v >> 1
            choices.append((prev, v & 1, ek, xk))
    redundant = []
    empty_routes_along_r = 0
    steps = []
    q = 0
    if choices:
        e, inter, x = t.oriented(choices[0][0], choices[0][1])
        if e is None:
            steps += [(h, None) for h in inter]
            q = 1
            if choices[0][2] is not None or choices[0][3] is not None:
                redundant.append('a copy on a route with no entry')
    occ = t.occ.get(start >> 1)
    if not occ:
        raise Undecodable('start not on R')
    if sk == 0:
        redundant.append('start@0')
    i = occ[sk if sk is not None else 0]
    h = start
    if t.h[i] not in (h, h ^ 1):
        raise Undecodable('start reads another node')
    steps.append((h, i))
    for rid, flip, ek, xk in choices[q:]:
        e, inter, x = t.oriented(rid, flip)
        if e is None:
            raise Undecodable('an entry-less route inside a row')
        di, dh, guard = i, h, 0
        while dh != e:
            nxt = t.step(di, dh)
            if nxt is None:
                di = None
                break
            di, dh = nxt
        if ek is not None:
            target = t.occ[e >> 1][ek]
            if di == target:
                redundant.append(':k equal to the default')
            while i != target:
                nxt = t.step(i, h)
                if nxt is None or len(steps) > nsteps:
                    raise Undecodable(':k not ahead')
                i, h = nxt
                steps.append((h, i))
        else:
            while h != e:
                nxt = t.step(i, h)
                if nxt is None or len(steps) > nsteps:
                    raise Undecodable('entry not ahead')
                i, h = nxt
                steps.append((h, i))
        if h != e:
            raise Undecodable('entry copy reads another way')
        steps += [(g, None) for g in inter]
        if x is None:
            if xk is not None:
                redundant.append('@k on a route with no exit')
            break
        landing = t.occ[x >> 1][xk] if xk is not None else t.nearest(x, i)
        if xk is not None and t.nearest(x, i) == landing:
            redundant.append('@k equal to the default')
        if not inter and t.step(i, h) == (landing, x):
            empty_routes_along_r += 1
        i, h = landing, x
        if t.h[i] not in (h, h ^ 1):
            raise Undecodable('exit reads another node')
        steps.append((h, i))
    else:
        while len(steps) < nsteps:
            nxt = t.step(i, h)
            if nxt is None:
                raise Undecodable('tail past R')
            i, h = nxt
            steps.append((h, i))
    if len(steps) != nsteps:
        raise Undecodable(f'{len(steps)} steps, nsteps {nsteps}')
    return steps, redundant, empty_routes_along_r, choices


def span(t, positions):
    return min(t.off[i] for i in positions), max(t.off[i] + t.len[i] for i in positions)


claim('U1', 'units in file order: header; sequences in byte order; per sequence its tile and departures '
      'units by start, a tile before the blocks starting there, smaller blocks first; then detail units; then its table')
claim('U2', 'a tile\'s name is its start, a multiple of tile, and every ref step\'s offset lies in [name, name + tile)')
claim('U3', 'a tile\'s extent is its ref rows\' stretches\' union (min to max), or the base beside its point')
claim('U3g', 'a tile\'s ref rows\' stretches are one interval, so their union is the extent '
      '(count: tiles whose ref stretches leave a gap inside the extent)')
claim('U4', 'a unit at a point p takes [p, p+1), or [p-1, p) where p is |S| (|S| from the ref rows); a unit has an extent of at least 1 bp')
claim('U5', 'a tile lists ref rows, then at most one nodes row, then route rows, then walk rows, then abridged rows; '
      'a detail unit holds at most one nodes row, route rows and walk rows')
claim('U6', 'within a departure block lines are in order of start, end, then text')
claim('U7', 'every departure line overlaps each block it is in')
claim('U8', 'a table\'s #unit line is 0 to the largest end of its units, named .')
claim('U9', 'a unit holds only lines of its own kinds: tiles ref/nodes/route/walk/abridged, departure blocks departure')
claim('H1', '#haplotype lists each haplotype with walk or abridged rows, sample#haplotype, once each in byte order, '
      'and no other')
claim('H2', 'revisited:i:0 means no ref row has a pass count above 1 and no walk or abridged row has @k or :k')
claim('R1', 'a ref row\'s lengths and passes have one entry per step, passes . exactly when every count is 1')
claim('R3', 'a tile of S holds ref rows of S only (unstated; graph-walks keeps only those)')
claim('R2', 'a tile\'s ref rows are written in hapOffset order (unstated)')
claim('N1', 'a nodes row lists the nodes the tile\'s route interiors visit, ids strictly ascending, and no other')
claim('N2', 'no route interior holds a node the reference passes once (ADR 0009, nearest-pass placement)')
claim('T1', 'a route is stored the way round whose handles sort first: entry (none first), interior, exit')
claim('T2', 'each distinct route is written once per tile or detail unit, a route and its flip counting as one')
claim('T3', 'a route with no entry or no exit has a non-empty interior (unstated)')
claim('T4', 'a route\'s entry and exit lie on R (unstated)')
claim('W1', 'every walk row decodes by the spec\'s rules to nsteps steps')
claim('W2', 'the tool writes @k and :k only where they differ from the defaults, so a file has one encoding')
claim('W3', 'a walk continues along R where R\'s next position is the step\'s, and takes a route with an empty '
      'interior only where it is not')
claim('W4', 'a walk row\'s start end is the span of all its placed steps')
claim('W4b', 'Terms: a walk row\'s span runs from the first base of its first step on R to the last base of its '
      'last (count: rows where that differs from the span of all its placed steps, which the writer states)')
claim('B1', 'a tile over abridgebytes moves paths out until the rest compress to at most abridgebytes (count: tiles '
      'still holding walk rows whose rows but abridged ones, from kind on, deflate in 65280-byte blocks at level 6 to more)')
claim('B2', 'a tile over abridge moves paths out until the rest cost at most abridge interior steps (count: tiles '
      'still holding walk rows that cost more)')
claim('W5', 'each (path, fragStart, piece) has one walk or abridged row in the file, pieces numbered from 0 '
      'with none missing along one W line')
claim('A1', 'an abridged row\'s start end is the span of its start and end steps on R (walks-format)')
claim('A1b', 'an abridged row\'s start end is the moved piece\'s stretch on the reference path, the span of all its '
      'placed steps (ADR 0010\'s Lines table; count: rows where the two readings differ)')
claim('A2', 'every abridged row names a detail unit cs:d of its tile that exists, and every detail unit is named by one')
claim('A3', 'a path\'s moved pieces in one tile share one detail record (count: tile and path with more than one)')
claim('A4', 'a detail unit holds one path\'s moved pieces (count: detail units with walk rows of several paths, '
      'or of several W lines of one contig)')
claim('A5', 'a tile\'s detail numbers run from 0 with none missing (unstated)')
claim('A6', 'a detail unit holds a nodes row')
claim('D1', 'a departure record\'s ownTiles are tile names of its sequence that exist, in no repeat')
claim('D2', 'a record has at most two ownTiles')
claim('D3', 'a departure record\'s extent holds both breakpoints and is at least the breakpoint stretch')
claim('D4', 'R holds one node ending at a + leave\'s or - rejoin\'s breakpoint and one starting at the other '
      'kind\'s (ADR 0009); count: ends where the file\'s R holds several, or none')
claim('D5', 'a departure line\'s ownBp >= missingBp; strands are + or -; passes >= 1')

# --own
claim('O1', 'ownTiles are the tiles of S holding the record\'s own steps, the steps strictly between its leave step '
      'and its rejoin step, in the path\'s order')
claim('O2', 'own steps after the leave in its W line take the leave\'s tile, own steps leading the next W line the '
      'rejoin\'s (count: own steps on S\'s tiles in neither)')
claim('O3', 'own steps by the bp range [hapStart, hapStart + ownBp) are the steps strictly between leave and rejoin '
      '(W1; count: records where the two definitions give different steps)')
claim('O4', 'an attach fetch of ownTiles finds every own step (count: records with own steps in no tile of S, '
      'such as on another sequence\'s tiles or in a W line with no rows)')

header = {}
haplotypes_listed = []
holes = []
sequences = []          # directory order
path_order = []
seq_end = collections.defaultdict(int)  # |S| from the ref rows
units_of = collections.defaultdict(list)  # seq -> [(kind, name, lo, hi)] in file order
tile_names = collections.defaultdict(set)
tile_tile = {}          # (seq, name) -> Tile, for --own
ref_pass_one = set()
ref_any = set()
interior_nodes = set()
haplotypes_with_rows = set()
pieces = collections.defaultdict(set)   # (path, frag) -> piece numbers
abridged = []           # (seq, tile, path, frag, piece, d, (a, b))
detail_pieces = {}      # (seq, tile, d) -> {(path, frag, piece): span of all placed steps}
detail_paths = collections.defaultdict(set)
records = []
breakpoints = collections.defaultdict(lambda: collections.defaultdict(set))  # seq -> bp -> {('end'|'start', node, pass offset)}
own_steps = collections.defaultdict(list)  # path -> [(frag, hapOffset of step, end, seq, tile, handle, pos, step index)]


def in_shard(path):
    return zlib.crc32(path.encode()) % SHARDS == SHARD


tile_size = None
copies_seen = 0
held_tiles = {}   # (seq, tile name) -> Tile, for the tiles with abridged rows


def finish_unit(u):
    if u is None:
        return
    kind = u['kind']
    t = u['tile']
    if kind == 'detail' and t is not None and 'nodes' not in t.kinds:
        bad('A6', (u['seq'], u['name'], t.kinds[:4]))
    if kind in ('tile', 'detail') and t is not None:
        order = ['ref', 'nodes', 'route', 'walk', 'abridged'] if kind == 'tile' else ['nodes', 'route', 'walk']
        if not kinds_in_order(t.kinds, order):
            bad('U5', (u['seq'], kind, u['name'], sorted(set(t.kinds))))
        seen('U5')
    if kind == 'tile' and 'walk' in t.kinds:
        budget = int(header.get('abridgebytes', 0))
        if budget:
            text = ''.join(u['rows']).encode()
            size = 0
            for k in range(0, len(text), 65280):
                z = zlib.compressobj(6, zlib.DEFLATED, -15)
                size += len(z.compress(text[k:k + 65280]) + z.flush())
            if size > budget:
                bad('B1', (u['seq'], u['name'], size, budget))
        cost = int(header.get('abridge', 0))
        if cost and u.get('cost', 0) > 4 * cost:
            bad('B2', (u['seq'], u['name'], u['cost'] / 4, cost))
    seen('B1')
    seen('B2')
    if kind == 'tile':
        if t.refs:
            stretches = sorted((s, s + sum(lens)) for s, _, lens, _ in t.refs)
            lo, hi = stretches[0][0], max(b for _, b in stretches)
            if lo < hi:
                if (t.lo, t.hi) != (lo, hi):
                    bad('U3', (t.seq, t.name, (t.lo, t.hi), (lo, hi)))
            else:
                if (t.lo, t.hi) not in ((lo, lo + 1), (lo - 1, lo)):
                    bad('U3', (t.seq, t.name, (t.lo, t.hi), 'point', lo))
                u['point'] = lo
            reach = stretches[0][1]
            for a, b in stretches[1:]:
                if a > reach:
                    bad('U3g', (t.seq, t.name, stretches[:6]))
                    break
                reach = max(reach, b)
        else:
            bad('U3', (t.seq, t.name, 'no ref row'))
    seen('U3')
    seen('U3g')


def kinds_in_order(kinds, order):
    rank = [order.index(k) if k in order else -1 for k in kinds]
    return -1 not in rank and rank == sorted(rank) and kinds.count('nodes') <= 1


unit = None
dep_prev = None
with gzip.open(args.file, 'rt') as f:
    for line in f:
        line = line.rstrip('\n')
        if line.startswith('#'):
            c = line.split('\t')
            if c[0] == '#walks':
                for tag in c[1:]:
                    k, _, v = tag.split(':', 2)
                    header[k] = v
                tile_size = int(header['tile'])
            elif c[0] == '#haplotype':
                haplotypes_listed.append(c[1])
            elif c[0] == '#hole':
                holes.append((c[1], int(c[2]), int(c[3])))
            elif c[0] == '#unit':
                finish_unit(unit)
                seq, lo, hi, kind, name = c[1], int(c[2]), int(c[3]), c[4], c[5]
                if not sequences or sequences[-1] != seq:
                    sequences.append(seq)
                units_of[seq].append((kind, name, lo, hi))
                t = Tile(seq, name, lo, hi)
                unit = dict(kind=kind, name=name, seq=seq, lo=lo, hi=hi, tile=t)
                if kind == 'tile':
                    tile_names[seq].add(name)
                    if args.own:
                        tile_tile[(seq, name)] = None
                    if int(name) % tile_size:
                        bad('U2', (seq, name, 'not a multiple of tile'))
                elif kind == 'detail':
                    cs, d = name.split(':')
                    unit['cs'], unit['d'] = cs, int(d)
                    unit['tile'] = None
                dep_prev = None
            continue
        c = line.split('\t')
        kind = c[3]
        u = unit
        a, b = int(c[1]), int(c[2])
        allowed = dict(tile={'ref', 'nodes', 'route', 'walk', 'abridged'}, departures={'departure'},
                       detail={'nodes', 'route', 'walk'})
        if kind not in allowed.get(u['kind'], set()):
            bad('U9', (u['kind'], u['name'], line[:80]))
        seen('U9')
        if u['kind'] == 'departures':
            key = (a, b, '\t'.join(c[3:]))
            if dep_prev is not None and key < dep_prev:
                bad('U6', (u['seq'], u['lo'], dep_prev[:2], key[:2]))
            seen('U6')
            dep_prev = key
            if not (a < u['hi'] and b > u['lo']):
                bad('U7', (u['seq'], u['lo'], u['hi'], line[:80]))
            seen('U7')
            records.append((u['seq'], u['lo'], c))
            continue
        if u['kind'] == 'detail' and u['tile'] is None:
            t0 = held_tiles.get((u['seq'], u['cs']))
            if t0 is None:
                bad('A2', (u['seq'], u['name'], 'its tile has no abridged row'))
                u['tile'] = Tile(u['seq'], u['name'], u['lo'], u['hi'])
                u['tile'].h = []
                u['tile'].occ = {}
                u['broken'] = True
            else:
                d = Tile(u['seq'], u['name'], u['lo'], u['hi'])
                d.h, d.off, d.len, d.occ = t0.h, t0.off, t0.len, t0.occ
                u['tile'] = d
        t = u['tile']
        t.kinds.append(kind)
        if u['kind'] == 'tile' and kind != 'abridged' and int(header.get('abridgebytes', 0)):
            u.setdefault('rows', []).append('\t'.join(c[3:]) + '\n')
        if kind == 'ref':
            hs, _ = deltas(c[9])
            lens = ints(c[10])
            passes = c[11]
            if len(lens) != len(hs) or int(c[8]) != len(hs):
                bad('R1', line[:80])
            pc = [1] * len(hs) if passes == '.' else ints(passes)
            if len(pc) != len(hs) or (passes != '.' and all(p == 1 for p in pc)):
                bad('R1', line[:80])
            seen('R1')
            if t.refs and int(c[6]) < t.refs[-1][0]:
                bad('R2', (t.seq, t.name))
            seen('R2')
            if c[4] != t.seq:
                bad('R3', (t.seq, t.name, c[4]))
            seen('R3')
            t.refs.append((int(c[6]), hs, lens, passes))
            at = int(c[6])
            for h, n, p in zip(hs, lens, pc):
                if not (int(t.name) <= at < int(t.name) + tile_size):
                    bad('U2', (t.seq, t.name, 'ref step at', at))
                ref_any.add(h >> 1)
                if p == 1:
                    ref_pass_one.add(h >> 1)
                if p > 1 and header.get('revisited') == '0':
                    bad('H2', line[:80])
                breakpoints[t.seq][at].add(('start', h >> 1, at))
                breakpoints[t.seq][at + n].add(('end', h >> 1, at))
                at += n
            seq_end[t.seq] = max(seq_end[t.seq], at)
            seen('U2')
            continue
        if kind == 'nodes':
            ids = []
            for d in ints(c[4]):
                ids.append((ids[-1] if ids else 0) + d)
            if any(x >= y for x, y in zip(ids, ids[1:])):
                bad('N1', (t.seq, t.name, 'ids not strictly ascending'))
            for x, n in zip(ids, ints(c[5])):
                t.nodes[x] = n
            u['nodes_ids'] = ids
            continue
        if kind == 'route':
            e, t.route_prev = deltas(c[4], t.route_prev) if c[4] != '.' else ([None], t.route_prev)
            inter, t.route_prev = deltas(c[5], t.route_prev)
            x, t.route_prev = deltas(c[6], t.route_prev) if c[6] != '.' else ([None], t.route_prev)
            t.routes.append((e[0], inter, x[0]))
            continue
        t.index()
        if 'checked_routes' not in u:
            u['checked_routes'] = True
            keyf = lambda r: ((-1 if r[0] is None else r[0]), tuple(r[1]), (-1 if r[2] is None else r[2]))
            canon = set()
            for rid, r in enumerate(t.routes):
                fl = t.oriented(rid, 1)
                if keyf(fl) < keyf(r):
                    bad('T1', (t.seq, t.name, r))
                k = min(keyf(r), keyf(fl))
                if k in canon:
                    bad('T2', (t.seq, t.name, r))
                canon.add(k)
                if (r[0] is None or r[2] is None) and not r[1]:
                    bad('T3', (t.seq, t.name, r))
                for end in (r[0], r[2]):
                    if end is not None and (end >> 1) not in t.occ:
                        bad('T4', (t.seq, t.name, r))
                for h in r[1]:
                    interior_nodes.add(h >> 1)
            used = sorted({h >> 1 for r in t.routes for h in r[1]})
            if used != u.get('nodes_ids', []):
                bad('N1', (t.seq, t.name, 'nodes row', u.get('nodes_ids', [])[:5], 'interiors', used[:5]))
            for k in ('T1', 'T2', 'T3', 'T4', 'N1'):
                seen(k)
        if kind == 'walk':
            path, frag, piece = c[4], int(c[5]), int(c[7])
            if '@' in c[9] or ':' in c[10] or '@' in c[10]:
                copies_seen += 1
                if header.get('revisited') == '0':
                    bad('H2', line[:80])
            try:
                steps, redundant, along, choices = decode(t, c)
            except (Undecodable, IndexError, KeyError) as e:
                bad('W1', (t.seq, t.name, str(e), line[:100]))
                continue
            seen('W1')
            for r in redundant:
                bad('W2', (t.seq, t.name, r, line[:100]))
            seen('W2')
            if along:
                bad('W3', (t.seq, t.name, line[:100]))
            seen('W3')
            placed = [i for _, i in steps if i is not None]
            if span(t, placed) != (a, b):
                bad('W4', (t.seq, t.name, span(t, placed), line[:100]))
            seen('W4')
            if span(t, [placed[0], placed[-1]]) != (a, b):
                bad('W4b', (t.seq, t.name, 'first and last', span(t, [placed[0], placed[-1]]), 'row', (a, b)))
            seen('W4b')
            if u['kind'] == 'tile':
                u['cost'] = u.get('cost', 0) + len(steps) + 4 * sum(len(t.routes[r][1]) for r, *_ in choices)
            if u['kind'] == 'tile':
                haplotypes_with_rows.add('#'.join(path.split('#')[:2]))
                if piece in pieces[(path, frag)]:
                    bad('W5', ('two rows', path, frag, piece))
                pieces[(path, frag)].add(piece)
            else:
                detail_pieces.setdefault((t.seq, u['cs'], u['d']), {})[(path, frag, piece)] = span(t, placed)
                detail_paths[(t.seq, u['cs'], u['d'])].add((path, frag))
            if args.own and in_shard(path):
                at = int(c[6])
                cs = u['name'] if u['kind'] == 'tile' else u['cs']
                for k, (h, i) in enumerate(steps):
                    n = t.len[i] if i is not None else t.nodes.get(h >> 1)
                    if n is None:
                        bad('W1', (t.seq, t.name, 'interior node with no length', h >> 1))
                        n = 0
                    against = None if i is None else t.h[i] != h
                    own_steps[path].append((frag, piece, k, at, at + n, t.seq, cs, h,
                                            None if i is None else (t.off[i], t.off[i] + t.len[i], against)))
                    at += n
            continue
        if kind == 'abridged':
            path, frag, piece, d = c[4], int(c[5]), int(c[7]), int(c[12])
            haplotypes_with_rows.add('#'.join(path.split('#')[:2]))
            if piece in pieces[(path, frag)]:
                bad('W5', ('two rows', path, frag, piece))
            pieces[(path, frag)].add(piece)
            if '@' in c[10] or '@' in c[11]:
                if header.get('revisited') == '0':
                    bad('H2', line[:80])
            s, sk = with_k(c[10], '@')
            e, ek = with_k(c[11], '@')
            s, e = int(s), int(e)
            si = t.occ[s >> 1][sk or 0]
            ei = t.occ[e >> 1][ek] if ek is not None else t.nearest(e, si)
            if sk == 0 or (ek is not None and t.nearest(e, si) == ei):
                bad('W2', (t.seq, t.name, 'abridged', line[:100]))
            if span(t, [si, ei]) != (a, b):
                bad('A1', (t.seq, t.name, line[:100]))
            seen('A1')
            abridged.append((t.seq, t.name, path, frag, piece, d, (a, b)))
            held_tiles[(t.seq, t.name)] = t
            continue
    finish_unit(unit)

# U1: unit order, U4: points, U8: tables
for seq, us in units_of.items():
    kinds = [k for k, *_ in us]
    if kinds[-1] != 'table' or kinds.count('table') != 1:
        bad('U1', (seq, 'table not last or not one'))
    body = us[:-1]
    first_detail = next((k for k, u in enumerate(body) if u[0] == 'detail'), len(body))
    if any(u[0] != 'detail' for u in body[first_detail:]):
        bad('U1', (seq, 'a tile or block after a detail unit'))
    tb = body[:first_detail]

    def order_key(u):
        kind, name, lo, hi = u
        return (int(name), 0, 0) if kind == 'tile' else (lo, 1, hi - lo)
    keys = [order_key(u) for u in tb]
    if keys != sorted(keys):
        k = next(k for k in range(len(keys) - 1) if keys[k] > keys[k + 1])
        bad('U1', (seq, 'tiles and blocks out of order', tb[k], tb[k + 1]))
    if sequences.index(seq) and sequences[sequences.index(seq) - 1].encode() >= seq.encode():
        bad('U1', (seq, 'sequences not in byte order'))
    t_kind, t_name, t_lo, t_hi = us[-1]
    if (t_lo, t_name) != (0, '.') or t_hi != max((u[3] for u in body), default=0):
        bad('U8', (seq, us[-1]))
    for kind, name, lo, hi in body:
        if hi - lo < 1:
            bad('U4', (seq, kind, name, lo, hi, '|S|', seq_end[seq]))
seen('U1')
seen('U4')
seen('U8')

# U4: point extents against |S|; the unit lines don't say whether a tile is a point, so recheck from tiles
# whose extent is 1 bp and whose ref stretches are all empty
# (finish_unit recorded mismatches; here only the end rule)

# H1
if haplotypes_listed != sorted(set(haplotypes_listed), key=lambda s: s.encode()):
    bad('H1', ('not unique or not in byte order', haplotypes_listed[:5]))
if set(haplotypes_listed) != haplotypes_with_rows:
    bad('H1', ('listed without rows', sorted(set(haplotypes_listed) - haplotypes_with_rows)[:5],
               'rows not listed', sorted(haplotypes_with_rows - set(haplotypes_listed))[:5]))
seen('H1')
seen('H2')

# N2
for n in interior_nodes & ref_pass_one:
    bad('N2', n)
seen('N2')

# W5: piece numbering
for (path, frag), ps in pieces.items():
    if sorted(ps) != list(range(len(ps))):
        bad('W5', (path, frag, sorted(ps)[:10]))
seen('W5')

# A1b, A2-A6
named = collections.defaultdict(set)
for seq, cs, path, frag, piece, d, (a, b) in abridged:
    named[(seq, cs)].add(d)
    held = detail_pieces.get((seq, cs, d))
    if held is None or (path, frag, piece) not in held:
        bad('A2', (seq, cs, d, path, piece))
        continue
    if held[(path, frag, piece)] != (a, b):
        bad('A1b', (seq, cs, path, piece, 'abridged', (a, b), 'all placed steps', held[(path, frag, piece)]))
for key in detail_pieces:
    if key[2] not in named.get(key[:2], ()):
        bad('A2', ('detail unit no abridged row names', key))
by_tile_path = collections.defaultdict(set)
for seq, cs, path, frag, piece, d, _ in abridged:
    by_tile_path[(seq, cs, path)].add(d)
for key, ds in by_tile_path.items():
    if len(ds) > 1:
        bad('A3', (key, sorted(ds)))
for key, paths in detail_paths.items():
    if len({p for p, _ in paths}) > 1 or len(paths) > 1:
        bad('A4', (key, sorted(paths)[:4]))
for key, ds in named.items():
    if sorted(ds) != list(range(len(ds))):
        bad('A5', (key, sorted(ds)))
for k in ('A1b', 'A2', 'A3', 'A4', 'A5', 'A6'):
    seen(k)

# D1-D5
recs = {}
for seq, block, c in records:
    recs.setdefault((seq, '\t'.join(c)), c)
for (seq, _), c in recs.items():
    a, b = int(c[1]), int(c[2])
    own, missing = int(c[6]), int(c[7])
    lp, ls, lpass, rp, rs, rpass = int(c[8]), c[9], int(c[10]), int(c[11]), c[12], int(c[13])
    tiles = [] if c[14] == '.' else c[14].split(',')
    if len(set(tiles)) != len(tiles) or any(t not in tile_names[seq] for t in tiles):
        bad('D1', (seq, c[3:]))
    if len(tiles) > 2:
        bad('D2', (seq, c[3:]))
    S = seq_end[seq]

    def beside(bp, at_end):
        x = bp - 1 if at_end else bp
        return min(max(x, 0), max(S - 1, 0))
    if not (a <= min(lp, rp) and max(lp, rp) <= b):
        bad('D3', (seq, 'breakpoint outside', c[:9]))
    if own < missing or ls not in '+-' or rs not in '+-' or lpass < 1 or rpass < 1:
        bad('D5', (seq, c[3:]))
    for bp, strand, leave in ((lp, ls, True), (rp, rs, False)):
        side = 'end' if (strand == '+') == leave else 'start'
        held = {x for x in breakpoints[seq].get(bp, ()) if x[0] == side}
        if len(held) != 1:
            bad('D4', (seq, bp, strand, 'leave' if leave else 'rejoin', sorted(held)[:4]))
for k in ('D1', 'D2', 'D3', 'D4', 'D5'):
    seen(k)

# O1-O4: own steps from the decoded rows of the shard's paths
if args.own:
    index = {}
    for path, steps in own_steps.items():
        steps.sort()
        ends = collections.defaultdict(list)
        starts = collections.defaultdict(list)
        on_s = collections.defaultdict(list)
        for k, st in enumerate(steps):
            if st[8] is not None:
                ends[(st[5], st[4])].append(k)
                starts[(st[5], st[3])].append(k)
                on_s[st[5]].append(k)
        index[path] = (ends, starts, on_s, [st[3] for st in steps], [st[4] for st in steps])

    def bp_of(st, leave):
        lo, hi, against = st[8]
        return lo if against == leave else hi

    def strand(st):
        return '-' if st[8][2] else '+'
    for (seq, _), c in recs.items():
        path = c[4]
        if not in_shard(path) or path not in index:
            continue
        steps = own_steps[path]
        ends, starts, on_s, at_lo, at_hi = index[path]
        hs, own = int(c[5]), int(c[6])
        lp, ls, rp, rs = int(c[8]), c[9], int(c[11]), c[12]
        leave = [k for k in ends.get((seq, hs), []) if bp_of(steps[k], True) == lp and strand(steps[k]) == ls]
        rejoin = [k for k in starts.get((seq, hs + own), []) if bp_of(steps[k], False) == rp and strand(steps[k]) == rs]
        pair = None
        S_steps = on_s[seq]
        for li in reversed(leave):
            nxt = bisect.bisect_right(S_steps, li)
            if nxt < len(S_steps) and S_steps[nxt] in rejoin:
                pair = (li, S_steps[nxt])
                break
        if pair is None:
            bad('O1', ('leave or rejoin step not found among decoded rows', seq, c[4:15]))
            continue
        li, ri = pair
        between = steps[li + 1:ri]
        tiles = []
        for st in between:
            if st[5] == seq and st[6] not in tiles:
                tiles.append(st[6])
        stated = [] if c[14] == '.' else c[14].split(',')
        if stated != tiles:
            bad('O1', (seq, c[4:15], 'decoded', tiles))
        lo = bisect.bisect_left(at_lo, hs)
        hi = bisect.bisect_right(at_hi, hs + own)
        by_bp = [k for k in range(lo, hi) if hs <= at_lo[k] and at_hi[k] <= hs + own]
        if by_bp != list(range(li + 1, ri)):
            bad('O3', (seq, c[4:15], 'strictly between', ri - li - 1, 'by bp', len(by_bp)))
        sides = {steps[li][6], steps[ri][6]}
        if any(st[5] == seq and st[6] not in sides for st in between):
            bad('O2', (seq, c[4:15]))
        decoded_bp = sum(st[4] - st[3] for st in between)
        if any(st[5] != seq for st in between) or decoded_bp < own - int(c[7]):
            bad('O4', (seq, c[4:15], 'own bp', own, 'missing', c[7], 'decoded own bp', decoded_bp,
                       'on other sequences', sum(1 for st in between if st[5] != seq)))
    for k in ('O1', 'O2', 'O3', 'O4'):
        seen(k)

print(f'# {args.file}: {sum(len(v) for v in units_of.values())} units, {len(recs)} departure records, '
      f'{len(abridged)} abridged rows, {copies_seen} walk rows with copies')
for key in CLAIMS:
    if key in counts:
        print(f'{counts[key]}\t{key} {CLAIMS[key]}')
        for e in examples[key]:
            print('   ', e)
