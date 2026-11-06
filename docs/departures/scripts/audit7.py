#!/usr/bin/env python3
# Audits a walk format 7 file as a reader sees it. Decodes every walk row,
# detail ones included, to positions on its sequence by the decoding rules
# (`@k` and `:k` copies), and checks each walk and abridged row's `start
# end` against the span its steps decode to. Recomputes every departure from
# those positions, and checks them against the departure records: each
# departure that needs a record has one with the same fields, and no record
# lacks a departure, each end's pass count included; that each `ref` row's
# pass counts are how often the file's `ref` rows hold the node, and the
# header's `revisited` how many nodes they hold more than once; and that
# each `abridged` row states its own piece of its detail unit: its steps,
# its stretch from its first step on R to its last as hapOffset and bp, and
# those steps' handles and positions in R as start and end; and that every
# base of a path from its first step on a sequence to its last lies in one
# piece's stretch on R or one record's own bp. Then checks the reader
# promise (every base of a record's stretch where its path has no piece lies
# under a block of the record), that a departure inside a piece lies within
# its tile's extent, so any window over it reads the tile, and costs each
# window as format 7 reads it: the tiles and departure blocks whose extents
# overlap it, from the unit tables, in requests of touching byte ranges.
#
# Usage: audit7.py walks.gz [--seq NAME] [--window 65536] [--point 1024] [--top 1]
import argparse
import bisect
import collections
import gzip
import os
import struct
import zlib

ap = argparse.ArgumentParser()
ap.add_argument('file')
ap.add_argument('--window', type=int, default=65536)
ap.add_argument('--point', type=int, default=1024, help='spacing of the 1 bp windows')
ap.add_argument('--top', type=int, default=1, help='windows to break down')
ap.add_argument('--examples', type=int, default=5)
ap.add_argument('--truth', help="dep.rs's dep.tsv for the same graph and reference")
ap.add_argument('--seq', help='audit one reference sequence and its siblings only, so a genome-wide file fits in '
                'memory; a departure across sequences then counts the bp on the others as unseen')
ap.add_argument('--shard', default='0/1', help='I/N: check only the paths whose name hashes to I of N; '
                'shard 0 also costs the windows')
args = ap.parse_args()
SHARD, SHARDS = map(int, args.shard.split('/'))


def in_shard(path):
    return zlib.crc32(path.encode()) % SHARDS == SHARD

def handles(field, prev):
    out = []
    if field == '.':
        return out, prev
    for v in field.split(','):
        v = int(v)
        r = v & 1
        prev += (v - r) // 2
        out.append(2 * prev + r)
    return out, prev


def ints(field):
    return [] if field == '.' else [int(x) for x in field.split(',')]


def with_k(token):
    if '@' in token:
        a, k = token.split('@')
        return a, int(k)
    return token, None


class R:
    def __init__(self, seq, start):
        self.seq, self.start = seq, start
        self.h, self.off, self.len = [], [], []
        self.nodes = {}

    def add(self, offset, hs, lengths):
        for h, n in zip(hs, lengths):
            self.h.append(h)
            self.off.append(offset)
            self.len.append(n)
            offset += n

    def index(self):
        # bp of R's steps before each, so that a run's bp leaves out the
        # holes it crosses
        self.cum = [0]
        for n in self.len:
            self.cum.append(self.cum[-1] + n)
        self.at = collections.defaultdict(list)
        self.copies = collections.defaultdict(list)
        for i, h in enumerate(self.h):
            self.at[h].append(i)
            self.copies[h >> 1].append(i)

    def copy(self, h, k):
        c = self.copies.get(h >> 1)
        return None if c is None or k >= len(c) else c[k]

    def nearest(self, h, i):
        c = self.copies.get(h >> 1)
        if not c:
            return None
        best = c[0]
        for j in c:
            if abs(j - i) <= abs(best - i):
                best = j
        return best


class Bad(Exception):
    pass


def decode(r, routes, cols):
    # A walk row's steps as runs along R, (first index, last index, against),
    # and route interiors, ('I', handles)
    count = int(cols[8])
    start, sk = with_k(cols[9])
    start = int(start)
    choices = []
    prev = 0
    if cols[10] != '.':
        for tok in cols[10].split(','):
            tok, k = with_k(tok)
            ke = None
            if ':' in tok:
                tok, ke = tok.split(':')
                ke = int(ke)
            v = int(tok)
            flip = v & 1
            prev += (v - flip) // 2
            choices.append((prev, flip, ke, k))
    segs = []
    emitted = 0

    def oriented(rank, flip):
        e, inter, x = routes[rank]
        if not flip:
            return e, inter, x
        return (None if x is None else x ^ 1), [h ^ 1 for h in reversed(inter)], (None if e is None else e ^ 1)

    q = 0
    if choices:
        e, inter, x = oriented(choices[0][0], choices[0][1])
        if e is None:
            segs.append(('I', inter))
            emitted += len(inter)
            q = 1
    h = start
    i = r.copy(h, sk) if sk is not None else r.copy(h, 0)
    if i is None:
        raise Bad('start not on R')
    run = [i, i, h != r.h[i]]

    def follow(h, i, target, ke):
        # along R from i, reading it the way h does, to the first position
        # reading `target`, or to occurrence ke of its node
        forward = r.h[i] == h
        if ke is not None:
            j = r.copy(target, ke)
            if j is None or (j < i if forward else j > i):
                raise Bad('entry copy not ahead')
            if (r.h[j] if forward else r.h[j] ^ 1) != target:
                raise Bad('entry copy reads another way')
            return target, j
        if h == target:
            return h, i
        if forward:
            at = r.at.get(target, [])
            p = bisect.bisect_right(at, i)
            if p == len(at):
                raise Bad('entry not ahead')
            return target, at[p]
        at = r.at.get(target ^ 1, [])
        p = bisect.bisect_left(at, i) - 1
        if p < 0:
            raise Bad('entry not behind')
        return target, at[p]

    for rank, flip, ke, k in choices[q:]:
        e, inter, x = oriented(rank, flip)
        if e is None:
            raise Bad('entry-less route inside a row')
        h, j = follow(h, i, e, ke)
        if h != e:
            raise Bad('entry mismatch')
        run[1] = j
        i = j
        segs.append(('R', run[0], run[1], run[2]))
        emitted += abs(run[1] - run[0]) + 1
        segs.append(('I', inter))
        emitted += len(inter)
        if x is None:
            return segs
        h = x
        i = r.copy(h, k) if k is not None else r.nearest(h, i)
        if i is None:
            raise Bad('exit not on R')
        run = [i, i, h != r.h[i]]
    tail = count - emitted - 1
    if tail < 0:
        raise Bad('more steps than the row counts')
    j = i + tail if r.h[i] == h else i - tail
    if j < 0 or j >= len(r.h):
        raise Bad('tail past R')
    run[1] = j
    segs.append(('R', run[0], run[1], run[2]))
    return segs


ref_nodes = set()
pieces = collections.defaultdict(list)   # path -> [(frag, offset, piece, steps)]
detail_of = {}   # (path, frag, piece) -> (seq, cs, detail) for a piece in a detail record
detail_ends = {}   # (path, frag, piece) -> its first and last steps on R, (position in R, handle)
records = []
dep_rows = []   # (seq, block start, block end, record index, line bytes)
rec_extent = {}   # record index -> its line's start and end
tile_extent = {}   # (seq, tile start) -> its unit's start and end
unit_names = collections.Counter()   # (seq, kind, name) of tile and detail units
header = {}
holes = collections.defaultdict(list)
kinds = collections.Counter()
text_bytes = collections.Counter()
seq_len = collections.Counter()
bad = collections.Counter()
bad_examples = []
abridged_rows = []   # (path, frag, offset, piece, steps, bp, (start, end), (seq, cs, detail))
stated_passes = {}   # node -> the count its ref rows state
held_passes = collections.Counter()   # node -> positions of the file's ref rows holding it
keep_r = {}
record_index = {}


def steps_of(r, segs, nodes):
    # A piece's steps as runs on R with their positions, and interiors as
    # (steps, bp)
    out = []
    for s in segs:
        if s[0] == 'I':
            bp = 0
            for h in s[1]:
                n = nodes.get(h >> 1)
                if n is None:
                    raise Bad('interior node without a length')
                bp += n
            out.append(('I', len(s[1]), bp, r.seq, r.start))
        else:
            _, i0, i1, against = s
            lo, hi = min(i0, i1), max(i0, i1)
            first = (r.h[i0] >> 1, r.off[i0], r.len[i0])
            last = (r.h[i1] >> 1, r.off[i1], r.len[i1])
            out.append(('R', r.seq, r.start, first, last, against, hi - lo + 1,
                        r.cum[hi + 1] - r.cum[lo], r.off[lo], r.off[hi] + r.len[hi]))
    return out


def take_walk(r, routes, nodes, cols, origin=None):
    if not in_shard(cols[4]):
        return
    try:
        segs = decode(r, routes, cols)
        steps = steps_of(r, segs, nodes)
    except Bad as e:
        bad[f'decode: {e}'] += 1
        if len(bad_examples) < args.examples:
            bad_examples.append(('decode', str(e), cols[:12]))
        return
    n = sum(s[6] if s[0] == 'R' else s[1] for s in steps)
    if n != int(cols[8]):
        bad['decoded step count differs from the row'] += 1
    on_r = [s for s in steps if s[0] == 'R']
    if (min(s[8] for s in on_r), max(s[9] for s in on_r)) != (int(cols[1]), int(cols[2])):
        bad['walk row: start end differ from the span its steps decode to'] += 1
        if len(bad_examples) < args.examples:
            bad_examples.append(('span', cols[:12]))
    pieces[cols[4]].append((int(cols[5]), int(cols[6]), int(cols[7]), steps))
    if origin is not None:
        key = (cols[4], int(cols[5]), int(cols[7]))
        detail_of[key] = origin
        runs = [x for x in segs if x[0] == 'R']
        detail_ends[key] = ((runs[0][1], r.h[runs[0][1]] ^ runs[0][3]), (runs[-1][2], r.h[runs[-1][2]] ^ runs[-1][3]))


def abridged_ends(r, start, end):
    # The positions in R and handles an abridged row's start and end name:
    # start at occurrence k with `@k`, else the first; end at occurrence k
    # with `@k`, else the one nearest start's position, the later on a tie
    h, k = with_k(start)
    h = int(h)
    i = r.copy(h, 0 if k is None else k)
    e, ke = with_k(end)
    e = int(e)
    j = None if i is None else r.nearest(e, i) if ke is None else r.copy(e, ke)
    return (i, h), (j, e)


unit = None   # (seq, kind, name, start, end) of the unit being read
r = None
routes = []
route_prev = 0
nodes = {}
with gzip.open(args.file, 'rt') as f:
    for line in f:
        if line[0] == '#':
            c = line.rstrip('\n').split('\t')
            if c[0] == '#walks':
                for t in c[1:]:
                    k, _, v = t.split(':', 2)
                    header[k] = v
            elif c[0] == '#hole':
                holes[c[1]].append((int(c[2]), int(c[3])))
            elif c[0] == '#unit':
                unit = None if args.seq is not None and c[1] != args.seq else (c[1], c[4], c[5], int(c[2]), int(c[3]))
                if unit is not None and unit[1] in ('tile', 'detail'):
                    unit_names[unit[:3]] += 1
                if unit is None or unit[1] in ('departures', 'table'):
                    continue
                routes, route_prev, nodes = [], 0, {}
                if unit[1] == 'tile':
                    cs = int(unit[2])
                    tile_extent[(unit[0], cs)] = unit[3:]
                    r = R(unit[0], cs)
                    indexed = False
                else:
                    cs, d = map(int, unit[2].split(':'))
                    r = keep_r.get((unit[0], cs))
                    if r is None:
                        bad['detail unit of a tile with no abridged row'] += 1
            continue
        if unit is None or unit[1] == 'table':
            continue
        c = line.rstrip('\n').split('\t')
        seq, a, b = c[0], int(c[1]), int(c[2])
        kind = c[3]
        if seq != unit[0]:
            bad['a line of another sequence than its unit'] += 1
        text_bytes[kind] += len(line)
        if unit[1] == 'departures':
            kinds['departure lines'] += 1
            body = '\t'.join(c[3:])
            k = record_index.get(body)
            if k is None:
                k = record_index[body] = len(records)
                records.append(c[3:])
                rec_extent[k] = (a, b)
            elif rec_extent[k] != (a, b):
                bad['one record with two extents'] += 1
            dep_rows.append((seq, unit[3], unit[4], k, len(line)))
            continue
        if unit[1] == 'detail':
            kinds[f'detail {kind} rows'] += 1
            if r is None:
                continue
            if kind == 'nodes':
                prev = 0
                for d_, n in zip(ints(c[4]), ints(c[5])):
                    prev += d_
                    nodes[prev] = n
            elif kind == 'route':
                e, route_prev = handles(c[4], route_prev) if c[4] != '.' else ([None], route_prev)
                inter, route_prev = handles(c[5], route_prev)
                x, route_prev = handles(c[6], route_prev) if c[6] != '.' else ([None], route_prev)
                routes.append((e[0], inter, x[0]))
            elif kind == 'walk':
                cs, d = map(int, unit[2].split(':'))
                take_walk(r, routes, nodes, c, (seq, cs, d))
            continue
        kinds[f'{kind} rows'] += 1
        cs = int(unit[2])
        if kind == 'ref':
            hs, _ = handles(c[9], 0)
            lengths = ints(c[10])
            counts = [1] * len(hs) if c[11] == '.' else ints(c[11])
            if len(counts) != len(hs):
                bad['ref row: pass counts not one per step'] += 1
            for h, n in zip(hs, counts):
                held_passes[h >> 1] += 1
                if stated_passes.setdefault(h >> 1, n) != n:
                    bad['ref rows: one node with two pass counts'] += 1
            r.add(int(c[6]), hs, lengths)
            seq_len[seq] = max(seq_len[seq], r.off[-1] + r.len[-1])
            for h in hs:
                ref_nodes.add((seq, h >> 1))
            continue
        if not indexed:
            r.index()
            indexed = True
        if kind == 'nodes':
            prev = 0
            for d_, n in zip(ints(c[4]), ints(c[5])):
                prev += d_
                nodes[prev] = n
        elif kind == 'route':
            e, route_prev = handles(c[4], route_prev) if c[4] != '.' else ([None], route_prev)
            inter, route_prev = handles(c[5], route_prev)
            x, route_prev = handles(c[6], route_prev) if c[6] != '.' else ([None], route_prev)
            routes.append((e[0], inter, x[0]))
        elif kind == 'walk':
            take_walk(r, routes, nodes, c)
        elif kind == 'abridged':
            # abridged path frag offset piece steps bp start end detail
            keep_r[(seq, cs)] = r
            if in_shard(c[4]):
                ends = abridged_ends(r, c[10], c[11])
                if None in (ends[0][0], ends[1][0]):
                    bad['abridged row: start or end not on R'] += 1
                else:
                    i, j = ends[0][0], ends[1][0]
                    span = (min(r.off[i], r.off[j]), max(r.off[i] + r.len[i], r.off[j] + r.len[j]))
                    if span != (a, b):
                        bad['abridged row: start end differ from its start and end steps\' span'] += 1
                abridged_rows.append((c[4], int(c[5]), int(c[6]), int(c[7]), int(c[8]), int(c[9]),
                                      ends, (seq, cs, int(c[12]))))
print('# header')
print('\t'.join(f'{k}:{v}' for k, v in header.items()))
print('# rows by kind')
for k, v in sorted(kinds.items()):
    print(f'{v}\t{k}')
print('# text bytes by kind')
total = sum(text_bytes.values())
for k, v in sorted(text_bytes.items(), key=lambda kv: -kv[1]):
    print(f'{v}\t{k} ({100 * v / total:.2f}%)')
size = os.path.getsize(args.file)
print(f'{size}\tfile bytes; {os.path.getsize(args.file + ".idx")} directory bytes')
print(f'{sum(len(v) for v in holes.values())}\t#hole lines')
shared = sum(n for n in unit_names.values() if n > 1)
print(f'{shared}\ttile and detail units sharing a name with another of their sequence (must be 0)')
for k in [k for k, n in unit_names.items() if n > 1][:args.examples]:
    print('   shared name', k)

tile_size = int(header['tile'])
unreachable = []


def squeeze(seq, bp):
    return bp - sum(b - a for a, b in holes.get(seq, []) if b <= bp)


# Departures recomputed from the decoded rows, per path and sequence. An end
# is (breakpoint, strand) as the record states it, then what the audit knows
# beside: the node and the chunk the step's piece is filed under
def end_of(step, against, leave, chunk):
    node, off, length = step
    on_start = against == leave
    bp = off if on_start else off + length
    return (bp, '-' if against else '+', stated_passes.get(node), node, chunk)


def parse_record(rec):
    # departure path hapStart ownBp missingBp leavePos leaveStrand leavePasses rejoinPos rejoinStrand
    # rejoinPasses ownTiles [tags]
    return dict(path=rec[1], hap_start=int(rec[2]), own_bp=int(rec[3]), missing=int(rec[4]),
                leave=(int(rec[5]), rec[6], int(rec[7])), rejoin=(int(rec[8]), rec[9], int(rec[10])),
                own_tiles=[] if rec[11] == '.' else [int(t) for t in rec[11].split(',')])


parsed = [parse_record(rec) for rec in records]
rec_seq = {}
for seq, a, b, k, _ in dep_rows:
    rec_seq[k] = seq
by_key = collections.defaultdict(list)
for k, d in enumerate(parsed):
    by_key[(d['path'], d['hap_start'], d['leave'][0], d['rejoin'][0])].append(k)

truth_keys = set()
if args.truth:
    for line in open(args.truth):
        c_ = line.split('\t', 12)
        truth_keys.add((c_[0], int(c_[11])))
quiet = collections.Counter()


def emit(path, S, d, needs):
    # keeps a departure only where a record or a truth row may match it
    key = (path, d['hap_start'], d['leave'][0], d['rejoin'][0])
    if needs or key in by_key or (path, d['hap_start']) in truth_keys:
        computed.append((path, S, d, needs))
    else:
        kind = 'across a record gap' if d['gap'] else 'within a record'
        quiet[f'{kind}: computed by the reader, no record'] += 1


def reachable(seq, cs, lo, hi):
    # whether every window over [lo, hi) reads tile `cs`, a unit read when
    # its extent overlaps the window: when the extent holds the stretch. For
    # a departure at a point, the caller asks for either base beside it
    a, b = tile_extent[(seq, cs)]
    return a <= lo and hi <= b


computed = []   # (path, seq, fields dict, kind)
coverage = collections.defaultdict(list)
for path, ps in pieces.items():
    ps.sort()
    # the contig's record extents from its pieces: frag start, and the end of its last step
    stream = []
    for frag, offset, piece, steps in ps:
        at = offset
        for s in steps:
            if s[0] == 'I':
                stream.append(('I', frag, at, s[1], s[2], s[3], s[4]))
                at += s[2]
            else:
                _, seq, cs, first, last, against, n, bp, lo, hi = s
                stream.append(('R', frag, at, seq, cs, first, last, against, n, bp, (frag, offset, piece)))
                coverage[(path, seq)].append((lo, hi))
                at += bp
    seqs = {s[3] for s in stream if s[0] == 'R'}
    for S in seqs:
        leave = None   # (end tuple, hap after, frag, piece key)
        own_bp = missing = 0
        own_tiles = []
        hap = None
        for s in stream:
            if s[0] == 'I':
                if hap is not None and s[2] != hap:
                    own_bp += s[2] - hap
                    missing += s[2] - hap
                own_bp += s[4]
                hap = s[2] + s[4]
                if s[5] == S and s[6] not in own_tiles:
                    own_tiles.append(s[6])
                continue
            _, frag, at, seq, cs, first, last, against, n, bp, key = s
            if hap is not None and at != hap:
                own_bp += at - hap
                missing += at - hap
            if seq != S:
                own_bp += bp
                hap = at + bp
                continue
            rejoin = end_of(first, against, False, cs)
            if leave is not None:
                lend, after, lfrag, lkey = leave
                adjacent = own_bp == 0 and lend[1] == rejoin[1] and squeeze(S, lend[0]) == squeeze(S, rejoin[0])
                if not adjacent:
                    lo, hi = min(lend[0], rejoin[0]), max(lend[0], rejoin[0], min(lend[0], rejoin[0]) + 1)
                    needs = lkey != key
                    empty = lend[0] == rejoin[0]
                    ok = (reachable(S, lend[4], lo, lo + 1) or reachable(S, lend[4], lo - 1, lo)) if empty else reachable(S, lend[4], lo, hi)
                    if not needs and not ok:
                        unreachable.append((path, lend, rejoin))
                    emit(path, S, dict(hap_start=after, own_bp=own_bp, leave=lend, rejoin=rejoin,
                                       missing=missing, own_tiles=own_tiles, gap=lfrag != frag),
                         needs or lfrag != frag)
            leave = (end_of(last, against, True, cs), at + bp, frag, key)
            own_bp = missing = 0
            own_tiles = []
            hap = at + bp
for v in coverage.values():
    v.sort()
    merged = []
    for a, b in v:
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    v[:] = [tuple(x) for x in merged]


print('# departures recomputed from the decoded rows, against the records')
tally = collections.Counter(quiet)
matched = set()


def differences(rec, d):
    diffs = [f for f in ('own_bp', 'missing', 'own_tiles') if rec[f] != d[f]]
    for side in ('leave', 'rejoin'):
        names = ['Pos', 'Strand', 'Passes']
        diffs += [side + names[i] for i in range(3) if rec[side][i] != d[side][i]]
    return diffs


def key_of(d):
    return (d['hap_start'], d['leave'][0], d['rejoin'][0])


exact = set()
for path, S, d, needs in computed:
    for k in by_key.get((path,) + key_of(d), []):
        if not differences(parsed[k], d):
            exact.add(k)
for path, S, d, needs in computed:
    ks = by_key.get((path,) + key_of(d), [])
    kind = 'across a record gap' if d['gap'] else 'within a record'
    if not ks:
        tally[f'{kind}: {"MISSING RECORD" if needs else "computed by the reader, no record"}'] += 1
        if needs and len(bad_examples) < 3 * args.examples:
            bad_examples.append(('missing', path, d))
        continue
    if len(ks) > 1:
        tally['records sharing the key (path, hapStart, leavePos, rejoinPos)'] += 1
    k = min(ks, key=lambda k: len(differences(parsed[k], d)))
    rec = parsed[k]
    diffs = differences(rec, d)
    if diffs and not needs and k in exact:
        tally[f'{kind}: computed by the reader, its key shared with a recorded departure'] += 1
        continue
    matched.add(k)
    if not needs:
        tally[f'{kind}: recorded though the reader computes it'] += 1
    if diffs and set(diffs) <= {'missing'} and rec['missing'] < d['missing']:
        tally[f'{kind}: over a W line the file holds no row of (steps unseen)'] += 1
    elif diffs:
        tally[f'{kind}: field mismatch'] += 1
        for x in diffs:
            tally[f'   mismatch in {x}'] += 1
        if len(bad_examples) < 3 * args.examples:
            bad_examples.append(('fields', diffs, d, rec))
    else:
        tally[f'{kind}: match'] += 1
unmatched = [k for k, d in enumerate(parsed) if k not in matched and in_shard(d['path'])]
tally['records with no recomputed departure'] = len(unmatched)
for k in unmatched[:args.examples]:
    bad_examples.append(('unmatched record', parsed[k]))
for k, v in sorted(tally.items()):
    print(f'{v}\t{k}')
print(f'{len(unreachable)}\tdepartures inside a piece reaching past its tile\'s extent (must be 0)')
print('# pass counts and abridged rows')
under = sum(1 for node, n in stated_passes.items() if n < held_passes[node])
over = sum(1 for node, n in stated_passes.items() if n > held_passes[node])
print(f'{under}\tnodes whose ref rows state fewer passes than the file\'s ref rows hold (must be 0)')
print(f'{over}\tnodes whose ref rows state more passes than the {"sequence" if args.seq else "file"}\'s ref rows hold'
      + ('' if args.seq else ' (must be 0)'))
revisited = sum(1 for n in stated_passes.values() if n > 1)
print(f'{revisited}\tnodes stated as passed more than once; the header says {header.get("revisited")}')
if args.seq is None and str(revisited) != header.get('revisited'):
    print('1\theader revisited differs from the ref rows (must be 0)')
# each piece's offset and bp trimmed to its stretch from its first step on R
# to its last, and its steps; and by sequence and path those stretches and
# the records' own bp
held_pieces = {}
stretches = collections.defaultdict(list)
for path, ps in pieces.items():
    for frag, offset, piece, steps in ps:
        n = sum(x[6] if x[0] == 'R' else x[1] for x in steps)
        bp = sum(x[7] if x[0] == 'R' else x[2] for x in steps)
        on = [k for k, x in enumerate(steps) if x[0] == 'R']
        lead = sum(x[2] for x in steps[:on[0]])
        tail = sum(x[2] for x in steps[on[-1] + 1:])
        held_pieces[(path, frag, piece)] = (offset + lead, n, bp - lead - tail)
        stretches[(steps[on[0]][1], path)].append((offset + lead, offset + bp - tail))
record_seq = {row[3]: row[0] for row in dep_rows}
for k, rec in enumerate(records):
    if in_shard(rec[1]):
        stretches[(record_seq[k], rec[1])].append((int(rec[2]), int(rec[2]) + int(rec[3])))
untiled = []
for key, spans in stretches.items():
    spans.sort()
    if any(a[1] != b[0] for a, b in zip(spans, spans[1:])):
        untiled.append((key, spans))
stray = [row for row in abridged_rows if held_pieces.get(row[:2] + row[3:4]) != (row[2], row[4], row[5])]
print(f'{len(stray)}\tabridged rows unlike the stretch on R and the steps of the piece their detail record holds (must be 0)')
for row in stray[:args.examples]:
    print('   abridged', row, held_pieces.get(row[:2] + row[3:4]))
misplaced = [row for row in abridged_rows if detail_of.get(row[:2] + row[3:4]) != row[7]]
print(f'{len(misplaced)}\tabridged rows whose piece is not in the detail record they name (must be 0)')
for row in misplaced[:args.examples]:
    print('   misplaced', row, detail_of.get(row[:2] + row[3:4]))
wrong_ends = [row for row in abridged_rows
              if row[:2] + row[3:4] in detail_ends and detail_ends[row[:2] + row[3:4]] != row[6]]
print(f'{len(wrong_ends)}\tabridged rows whose start or end is not their piece\'s first or last step on R, '
      'by position in R and strand (must be 0)')
for row in wrong_ends[:args.examples]:
    print('   ends', row, detail_ends[row[:2] + row[3:4]])
rowed = {row[:2] + row[3:4] for row in abridged_rows}
unrowed = [k for k in detail_of if k not in rowed]
print(f'{len(unrowed)}\tdetail pieces with no abridged row (must be 0)')
for k in unrowed[:args.examples]:
    print('   unrowed', k)
print(f'{len(untiled)}\tpaths on a sequence whose bases from their first step on it to their last are not each in '
      'one piece\'s stretch on R or one record\'s own bp (must be 0)')
for key, spans in untiled[:args.examples]:
    print('   untiled', key, spans[:12])
for u in unreachable[:args.examples]:
    print('   unreachable', u)
for k, v in sorted(bad.items()):
    print(f'{v}\t{k}')
for e in bad_examples:
    print('   example', e)

if args.truth:
    # name start kind seqa:ca seqb:cb rs re order L own_bp own hapStart inva invb multi
    print("# against dep.rs's enumeration from the GFA, ends on nodes passed once only")
    by_hap = collections.defaultdict(list)
    for path, S, d, needs in computed:
        by_hap[(path, d['hap_start'])].append((d, needs))
    t = collections.Counter()
    for line in open(args.truth):
        c = line.rstrip('\n').split('\t')
        if not in_shard(c[0]):
            continue
        if c[14] == '1':
            t['multi-pass end, not compared'] += 1
            continue
        rs, re_, own_bp, own, hap, inva, invb = int(c[5]), int(c[6]), int(c[9]), int(c[10]), int(c[11]), c[12] == '1', c[13] == '1'
        found = by_hap.get((c[0], hap), [])
        if not found:
            t[f'{c[2]}: no departure decoded at its hapStart'] += 1
            continue
        d, needs = found[0]
        diffs = []
        if d['own_bp'] != own_bp:
            diffs.append('own bp')
        if (d['leave'][1] == '-') != inva:
            diffs.append('leave strand')
        if (d['rejoin'][1] == '-') != invb:
            diffs.append('rejoin strand')
        lo, hi = sorted((d['leave'][0], d['rejoin'][0]))
        if (lo, hi) != (rs, re_):
            diffs.append('stretch, an end against S' if inva or invb else 'stretch, both ends along S')
            if not (inva or invb) and t['example along'] < 3:
                t['example along'] += 1
                print('   along S, stretch differs:', c, d)
        t[f'{c[2]}: {"match" if not diffs else "differs in " + " and ".join(diffs)}'] += 1
        if not needs:
            t[f'{c[2]}: no record, the reader computes it inside one piece'] += 1
    for k, v in sorted(t.items()):
        print(f'{v}\t{k}')

print('# the reader promise: record stretch bases off the path\'s pieces under no block of the record')
blocks_of = collections.defaultdict(list)
for seq, a, b, k, _ in dep_rows:
    blocks_of[k].append((a, b))


def subtract(lo, hi, cut):
    # [lo, hi) less the sorted, disjoint intervals `cut`
    out, at = [], lo
    p = max(bisect.bisect_right(cut, (lo, lo)) - 1, 0)
    for a, b in cut[p:]:
        if a >= hi:
            break
        if b <= at:
            continue
        if a > at:
            out.append((at, a))
        at = max(at, b)
    if at < hi:
        out.append((at, hi))
    return out


def merged(v):
    v = sorted(v)
    out = []
    for a, b in v:
        if out and a <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out


uncovered_bases = uncovered_records = 0
outside_extent = 0
for k, d in enumerate(parsed):
    if not in_shard(d['path']):
        continue
    seq = rec_seq[k]
    lo, hi = sorted((d['leave'][0], d['rejoin'][0]))
    a, b = rec_extent[k]
    if lo < a or hi > b:
        outside_extent += 1
    if hi == lo:
        continue
    free = subtract(lo, hi, coverage.get((d['path'], seq), []))
    cover = merged(blocks_of[k])
    miss = sum(y - x for f, g in free for x, y in subtract(f, g, cover))
    if miss:
        uncovered_records += 1
        uncovered_bases += miss
print(f'{uncovered_bases}\tbases uncovered, over {uncovered_records} records (must be 0)')
print(f'{outside_extent}\trecords whose breakpoints lie outside their line\'s extent (must be 0)')


# Window costs, as format 7 reads a window: the tile and departure units
# whose extents overlap it, fetched in requests of touching byte ranges; the
# departure lines kept are those whose extent overlaps it
def load_units(path):
    out = collections.defaultdict(list)
    with open(path, 'rb') as f:
        for line in open(path + '.idx').read().splitlines()[1:]:
            c = line.split('\t')
            if c[0] == '#header' or (args.seq is not None and c[0] != args.seq):
                continue
            f.seek(int(c[1]))
            for e in gzip.decompress(f.read(int(c[2]))).decode().splitlines()[1:]:
                _, seq, lo, hi, kind, _, at, n = e.split('\t')
                if kind in ('tile', 'departures') and int(n) > 0:
                    out[seq].append((int(lo), int(hi), int(at), int(n), kind))
    return out


units_by_seq = load_units(args.file)
q = lambda v, p: sorted(v)[min(len(v) - 1, int(p * len(v)))] if v else 0
lines_by_seq = collections.defaultdict(list)
for k, (a, b) in rec_extent.items():
    lines_by_seq[rec_seq[k]].append((a, b, k))
for seq, units in (units_by_seq.items() if SHARD == 0 else []):
    units.sort()
    recs = sorted(lines_by_seq.get(seq, []))
    length = max(seq_len[seq], max((u[1] for u in units), default=0))
    print(f'# {seq}: {len(units)} tile and departure units, {len(recs)} departure records')
    for label, size, step in (('64 kb', args.window, args.window), ('1 bp', 1, args.point)):
        res = []
        add_u = add_r = 0
        live_u, live_r = [], []
        for w in range(0, length, step):
            while add_u < len(units) and units[add_u][0] < w + size:
                live_u.append(units[add_u])
                add_u += 1
            while add_r < len(recs) and recs[add_r][0] < w + size:
                live_r.append(recs[add_r])
                add_r += 1
            live_u = [u for u in live_u if u[1] > w]
            live_r = [x for x in live_r if x[1] > w]
            ranges = sorted((u[2], u[2] + u[3]) for u in live_u)
            requests = 0
            end = -1
            for a, b in ranges:
                requests += a != end
                end = b
            tiles = [u for u in live_u if u[4] == 'tile']
            dep_bytes = sum(u[3] for u in live_u if u[4] == 'departures')
            res.append((w, len(live_r), requests, sum(u[3] for u in live_u), dep_bytes, len(tiles)))
        print(f'{label} windows: {len(res)}')
        for i, name in ((1, 'departure records kept'), (5, 'tiles read'), (2, 'requests'), (3, 'bytes read'),
                        (4, 'departure block bytes read')):
            v = [x[i] for x in res]
            print(f'  {name}: median {q(v, .5)} p95 {q(v, .95)} max {max(v)}')
        if label == '64 kb':
            for w, nrec, requests, nbytes, dep_bytes, ntiles in sorted(res, key=lambda x: -x[3])[:args.top]:
                print(f'  costliest window {seq}:{w}-{w + size}: {nbytes} bytes in {requests} requests, '
                      f'{ntiles} tiles, {dep_bytes} departure block bytes, {nrec} departure records')
