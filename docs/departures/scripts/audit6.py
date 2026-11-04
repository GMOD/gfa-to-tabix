#!/usr/bin/env python3
# Audits a walk format 6 file as a reader sees it. Decodes every walk row,
# detail ones included, to positions on its sequence by the decoding rules
# (`@k` copies, step counts), recomputes every departure from those
# positions, and checks them against the departure records: each departure
# that needs a record has one with the same fields, and no record lacks a
# departure. Then checks the reader promise (every base of a record's
# stretch where its path has no piece lies under a block of the record or a
# crowd row of the path), and costs each window the way @gmod/tabix reads
# it: rows by class, text bytes, and requests and bytes from the .tbi with
# its chunk merging (gaps under 65,000 bytes, merged spans under 5 MB).
#
# Usage: audit6.py walks.bed.gz [--window 65536] [--point 1024] [--top 1]
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
ap.add_argument('--shard', default='0/1', help='I/N: check only the paths whose name hashes to I of N; '
                'shard 0 also costs the windows')
args = ap.parse_args()
SHARD, SHARDS = map(int, args.shard.split('/'))


def in_shard(path):
    return zlib.crc32(path.encode()) % SHARDS == SHARD

SPACING = 16384


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
    start, sk = with_k(cols[9])
    start = int(start)
    end_tok = cols[10]
    counted = ':' in end_tok
    if counted:
        d, tail = end_tok.split(':')
        tail = int(tail)
    else:
        d, tail = end_tok, 0
    end = start + int(d)
    choices = []
    prev = 0
    if cols[11] != '.':
        for tok in cols[11].split(','):
            tok, k = with_k(tok)
            n = None
            if ':' in tok:
                tok, n = tok.split(':')
                n = int(n)
            v = int(tok)
            flip = v & 1
            prev += (v - flip) // 2
            choices.append((prev, flip, n, k))
    segs = []

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
            q = 1
    h = start
    i = r.copy(h, sk) if sk is not None else r.copy(h, 0)
    if i is None:
        raise Bad('start not on R')
    run = [i, i, h != r.h[i]]

    def follow(h, i, target, count):
        if counted:
            if count == 0:
                return h, i
            if r.h[i] == h:
                j = i + count
                if j >= len(r.h):
                    raise Bad('count past R')
                return r.h[j], j
            j = i - count
            if j < 0:
                raise Bad('count before R')
            return r.h[j] ^ 1, j
        if h == target:
            return h, i
        if r.h[i] == h:
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

    for rank, flip, n, k in choices[q:]:
        e, inter, x = oriented(rank, flip)
        if e is None:
            raise Bad('entry-less route inside a row')
        h, j = follow(h, i, e, n)
        if h != e:
            raise Bad('entry mismatch')
        run[1] = j
        i = j
        segs.append(('R', run[0], run[1], run[2]))
        segs.append(('I', inter))
        if x is None:
            return segs
        h = x
        i = r.copy(h, k) if k is not None else r.nearest(h, i)
        if i is None:
            raise Bad('exit not on R')
        run = [i, i, h != r.h[i]]
    h, j = follow(h, i, end, tail)
    if h != end:
        raise Bad('end mismatch')
    run[1] = j
    segs.append(('R', run[0], run[1], run[2]))
    return segs


passes = collections.Counter()   # (seq, node) -> passes, from mp
ref_nodes = set()
pieces = collections.defaultdict(list)   # path -> [(frag, offset, piece, steps)]
records = []
crowds = collections.defaultdict(list)    # (seq, path) -> [(a, b)]
dep_rows = []   # (seq, a, b, kind, body index or crowd path)
header = {}
holes = collections.defaultdict(list)
longs = collections.defaultdict(list)
kinds = collections.Counter()
text_bytes = collections.Counter()
seq_len = collections.Counter()
bad = collections.Counter()
bad_examples = []
crowd_detail = 0
abridged = {}   # (seq, cs) -> [(detail, pages)]
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
            out.append(('I', len(s[1]), bp))
        else:
            _, i0, i1, against = s
            lo, hi = min(i0, i1), max(i0, i1)
            first = (r.h[i0] >> 1, r.off[i0], r.len[i0])
            last = (r.h[i1] >> 1, r.off[i1], r.len[i1])
            out.append(('R', r.seq, r.start, first, last, against, hi - lo + 1,
                        r.off[hi] + r.len[hi] - r.off[lo], r.off[lo], r.off[hi] + r.len[hi]))
    return out


def take_walk(r, routes, nodes, cols):
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
    pieces[cols[4]].append((int(cols[5]), int(cols[6]), int(cols[7]), steps))


chunk = None
r = None
routes = []
route_prev = 0
nodes = {}
detail = None   # (seq, cs, record start) of the detail record being read
with gzip.open(args.file, 'rt') as f:
    for line in f:
        if line[0] == '#':
            c = line.rstrip('\n').split('\t')
            if c[0] == '#walks':
                for t in c[1:]:
                    k, _, v = t.split(':', 2)
                    header[k] = v
            elif c[0] == '#long':
                longs[c[1]].append((int(c[2]), int(c[3])))
            elif c[0] == '#hole':
                holes[c[1]].append((int(c[2]), int(c[3])))
            continue
        c = line.rstrip('\n').split('\t')
        seq, a, b = c[0], int(c[1]), int(c[2])
        kind = c[3]
        text_bytes[kind if not seq.endswith(('~departure', '~crowd')) else seq.rsplit('~', 1)[1]] += len(line)
        if seq.endswith('~departure'):
            base = seq[:-len('~departure')]
            kinds[f'{kind} rows'] += 1
            if kind == 'departure':
                body = '\t'.join(c[3:])
                k = record_index.get(body)
                if k is None:
                    k = record_index[body] = len(records)
                    records.append(c[3:])
                dep_rows.append((base, a, b, 'd', k, len(line)))
            else:
                crowds[(base, c[4])].append((a, b))
                dep_rows.append((base, a, b, 'c', c[4], len(line)))
                seq_len[base] = max(seq_len[base], b)
            continue
        if seq.endswith('~crowd'):
            kinds['crowd detail rows'] += 1
            continue
        if '~' in seq:
            base, cs = seq.rsplit('~', 1)
            cs = int(cs)
            kinds[f'detail {kind} rows'] += 1
            starts = abridged.get((base, cs), [])
            p = bisect.bisect_right(starts, a // SPACING) - 1
            key = (base, cs, starts[p] if p >= 0 else None)
            if key != detail:
                detail = key
                r = keep_r[(base, cs)]
                routes, route_prev, nodes = [], 0, {}
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
            continue
        kinds[f'{kind} rows'] += 1
        if (seq, a) != chunk:
            chunk = (seq, a)
            r = R(seq, a)
            routes, route_prev, nodes = [], 0, {}
            indexed = False
            detail = None
        if kind == 'ref':
            hs, _ = handles(c[9], 0)
            lengths = ints(c[10])
            r.add(int(c[6]), hs, lengths)
            seq_len[seq] = max(seq_len[seq], r.off[-1] + r.len[-1])
            for h in hs:
                ref_nodes.add((seq, h >> 1))
            for t in c[11:]:
                if t.startswith('mp:Z:'):
                    start = len(r.h) - len(hs)
                    for run in t[5:].split(';'):
                        i, n, count = map(int, run.split(','))
                        for j in range(i, i + n):
                            passes[r.h[start + j] >> 1] = count
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
            # abridged path frag offset pieces steps bp start end detail pages
            keep_r[(seq, a)] = r
            abridged.setdefault((seq, a), []).append(int(c[12]))
for v in abridged.values():
    v.sort()

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
tbi = args.file + '.tbi' if os.path.exists(args.file + '.tbi') else args.file + '.csi'
print(f'{size}\tfile bytes; {os.path.getsize(tbi)} index bytes ({os.path.basename(tbi)})')
print(f'{sum(len(v) for v in holes.values())}\t#hole lines')

chunk_size = int(header['chunk'])
unreachable = []


def squeeze(seq, bp):
    return bp - sum(b - a for a, b in holes.get(seq, []) if b <= bp)


# Departures recomputed from the decoded rows, per path and sequence
def end_of(step, against, leave, chunk):
    node, off, length = step
    on_start = against == leave
    bp = off if on_start else off + length
    return (bp, node, '-' if against else '+', passes.get(node, 1), chunk)


def parse_record(rec):
    # departure path fragStart hapStart ownBp ownSteps missingBp L(5) R(5) [tags]
    def end(cols):
        return None if cols[0] == '.' else (int(cols[0]), int(cols[1]), cols[2], int(cols[3]), int(cols[4]))
    tags = {t.split(':')[0]: t.split(':', 2)[2] for t in rec[17:]}
    return dict(path=rec[1], frag=int(rec[2]), hap_start=int(rec[3]), own_bp=int(rec[4]), own_steps=int(rec[5]),
                missing=int(rec[6]), leave=end(rec[7:12]), rejoin=end(rec[12:17]), xb=int(tags.get('xb', 0)))


parsed = [parse_record(rec) for rec in records]
rec_seq = {}
for seq, a, b, kind, k, _ in dep_rows:
    if kind == 'd':
        rec_seq[k] = seq
by_key = collections.defaultdict(list)
for k, d in enumerate(parsed):
    lp = d['leave'][0] if d['leave'] else None
    rp = d['rejoin'][0] if d['rejoin'] else None
    by_key[(d['path'], d['hap_start'], lp, rp)].append(k)

truth_keys = set()
if args.truth:
    for line in open(args.truth):
        c_ = line.split('\t', 12)
        truth_keys.add((c_[0], int(c_[11])))
quiet = collections.Counter()


def emit(path, S, d, needs):
    # keeps a departure only where a record or a truth row may match it
    key = (path, d['hap_start'], d['leave'][0] if d['leave'] else None, d['rejoin'][0] if d['rejoin'] else None)
    if needs or key in by_key or (path, d['hap_start']) in truth_keys or d['leave'] is None or d['rejoin'] is None:
        computed.append((path, S, d, needs))
    else:
        kind = 'one-ended' if d['leave'] is None or d['rejoin'] is None else (
            'across a record gap' if d['gap'] else 'within a record')
        quiet[f'{kind}: computed by the reader, no record'] += 1


def reachable(seq, cs, lo, hi):
    # whether a reader of any window over [lo, hi) reads chunk `cs`: it reads
    # the window's chunks and the one before, and for a #long pass it
    # overlaps, the pass's first chunk and the one before
    reach = [(cs, cs + 2 * chunk_size)] + [(a, b) for a, b in longs.get(seq, [])
                                           if a // chunk_size * chunk_size in (cs, cs + chunk_size)]
    reach.sort()
    at = lo
    for a, b in reach:
        if a <= at < b:
            at = b
    return at >= max(hi, lo + 1)


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
                stream.append(('I', frag, at, s[1], s[2]))
                at += s[2]
            else:
                _, seq, cs, first, last, against, n, bp, lo, hi = s
                stream.append(('R', frag, at, seq, cs, first, last, against, n, bp, (frag, offset, piece)))
                coverage[(path, seq)].append((lo, hi))
                at += bp
    seqs = {s[3] for s in stream if s[0] == 'R'}
    first_frag = ps[0][0]
    for S in seqs:
        leave = None   # (end tuple, hap after, frag, piece key)
        own_bp = own_steps = xb = missing = 0
        hap = None
        lead = None
        for s in stream:
            if s[0] == 'I':
                if hap is not None and s[2] != hap:
                    own_bp += s[2] - hap
                    missing += s[2] - hap
                own_steps += s[3]
                own_bp += s[4]
                hap = s[2] + s[4]
                continue
            _, frag, at, seq, cs, first, last, against, n, bp, key = s
            if hap is not None and at != hap:
                own_bp += at - hap
                missing += at - hap
            if seq != S:
                own_steps += n
                own_bp += bp
                xb += bp
                hap = at + bp
                continue
            rejoin = end_of(first, against, False, cs)
            if leave is None:
                lead = dict(hap_start=first_frag, own_bp=at - first_frag, own_steps=own_steps, xb=xb,
                            frag=frag, rejoin=rejoin, missing=missing)
            else:
                lend, after, lfrag, lkey = leave
                adjacent = own_steps == 0 and own_bp == 0 and lend[2] == rejoin[2] and squeeze(S, lend[0]) == squeeze(S, rejoin[0])
                if not adjacent:
                    lo, hi = min(lend[0], rejoin[0]), max(lend[0], rejoin[0], min(lend[0], rejoin[0]) + 1)
                    needs = lkey != key
                    empty = lend[0] == rejoin[0]
                    ok = (reachable(S, lend[4], lo - 1, lo) or reachable(S, lend[4], lo, lo + 1)) if empty else reachable(S, lend[4], lo, hi)
                    if not needs and not ok:
                        unreachable.append((path, lend, rejoin))
                    emit(path, S, dict(frag=lfrag, hap_start=after, own_bp=own_bp, own_steps=own_steps,
                                                   leave=lend, rejoin=rejoin, xb=xb, missing=missing, gap=lfrag != frag),
                                     needs or lfrag != frag)
            leave = (end_of(last, against, True, cs), at + bp, frag, key)
            own_bp = own_steps = xb = missing = 0
            hap = at + bp
        if lead is not None and lead['own_bp'] > 0:
            emit(path, S, dict(frag=lead['frag'], hap_start=lead['hap_start'], own_bp=lead['own_bp'],
                                           own_steps=lead['own_steps'], leave=None, rejoin=lead['rejoin'],
                                           xb=lead['xb'], missing=lead['missing'], gap=False), True)
        # the tail: own bp after the last step on S to the contig's last decoded step
        if leave is not None and hap is not None and hap > leave[1]:
            tail_bp = hap - leave[1]
            emit(path, S, dict(frag=leave[2], hap_start=leave[1], own_bp=tail_bp, own_steps=own_steps,
                                           leave=leave[0], rejoin=None, xb=xb, missing=missing, gap=False),
                             True)
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
    diffs = [f for f in ('frag', 'own_bp', 'own_steps', 'xb', 'missing') if rec[f] != d[f]]
    for side in ('leave', 'rejoin'):
        if (rec[side] is None) != (d[side] is None):
            diffs.append(side)
        elif rec[side] is not None:
            names = ['Pos', 'Node', 'Strand', 'Passes', 'Chunk']
            diffs += [side + names[i] for i in range(5) if rec[side][i] != d[side][i] and (i != 3 or passes)]
    return diffs


def key_of(d):
    return (d['path'] if 'path' in d else None, d['hap_start'], d['leave'][0] if d['leave'] else None,
            d['rejoin'][0] if d['rejoin'] else None)


by_path_end = collections.defaultdict(list)
for k, d in enumerate(parsed):
    if d['leave'] is None or d['rejoin'] is None:
        side = 'rejoin' if d['leave'] is None else 'leave'
        by_path_end[(d['path'], side, d[side][0])].append(k)
exact = set()
for path, S, d, needs in computed:
    for k in by_key.get((path,) + key_of(d)[1:], []):
        if not differences(parsed[k], d):
            exact.add(k)
for path, S, d, needs in computed:
    lp = d['leave'][0] if d['leave'] else None
    rp = d['rejoin'][0] if d['rejoin'] else None
    ks = by_key.get((path, d['hap_start'], lp, rp), [])
    kind = 'one-ended' if lp is None or rp is None else ('across a record gap' if d['gap'] else 'within a record')
    if not ks and kind == 'one-ended':
        side = 'rejoin' if lp is None else 'leave'
        alike = [k for k in by_path_end.get((path, side, (d[side] or (None,))[0]), []) if k not in matched]
        if alike and parsed[alike[0]]['own_bp'] > d['own_bp']:
            matched.add(alike[0])
            tally[f'{kind}: over a W line the file holds no row of (steps unseen)'] += 1
            continue
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
    if diffs and set(diffs) <= {'own_steps', 'missing'} and rec['missing'] < d['missing']:
        tally[f'{kind}: over a W line the file holds no row of (steps unseen)'] += 1
    elif diffs and kind == 'one-ended' and set(diffs) <= {'own_bp', 'own_steps', 'missing', 'xb'} and rec['missing'] > d['missing']:
        tally[f'{kind}: to a W line the file holds no row of (steps unseen)'] += 1
    elif diffs:
        tally[f'{kind}: field mismatch'] += 1
        for x in diffs:
            tally[f'   mismatch in {x}'] += 1
        if len(bad_examples) < 3 * args.examples:
            bad_examples.append(('fields', diffs, d, rec))
    else:
        tally[f'{kind}: match'] += 1
extent = {}
for path, ps in pieces.items():
    first = ps[0]
    extent[path] = first[0]
unmatched = []
for k, d in enumerate(parsed):
    if k in matched or not in_shard(d['path']):
        continue
    if d['leave'] is None and d['hap_start'] < extent.get(d['path'], 0):
        tally['one-ended: from a W line the file holds no row of (steps unseen)'] += 1
    elif d['rejoin'] is None and d['missing'] > 0:
        tally['one-ended: to a W line the file holds no row of (steps unseen)'] += 1
    else:
        unmatched.append(k)
tally['records with no recomputed departure'] = len(unmatched)
for k in unmatched[:args.examples]:
    bad_examples.append(('unmatched record', parsed[k]))
for k, v in sorted(tally.items()):
    print(f'{v}\t{k}')
print(f'{len(unreachable)}\tdepartures inside a piece reaching past the chunk after its own (must be 0)')
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
        found = [x for x in by_hap.get((c[0], hap), []) if x[0]['leave'] and x[0]['rejoin']]
        if not found:
            t[f'{c[2]}: no departure decoded at its hapStart'] += 1
            continue
        d, needs = found[0]
        diffs = []
        if d['own_bp'] != own_bp:
            diffs.append('own bp')
        if d['own_steps'] != own:
            diffs.append('own steps')
        if (d['leave'][2] == '-') != inva:
            diffs.append('leave strand')
        if (d['rejoin'][2] == '-') != invb:
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

print('# the reader promise: record stretch bases off the path\'s pieces under no block or crowd')
blocks_of = collections.defaultdict(list)
for seq, a, b, kind, k, _ in dep_rows:
    if kind == 'd':
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


crowd_cover = {k: merged(v) for k, v in crowds.items()}
uncovered_bases = uncovered_records = 0
whole_bases = whole_records = 0
for k, d in enumerate(parsed):
    if d['leave'] is None or d['rejoin'] is None or not in_shard(d['path']):
        continue
    seq = rec_seq[k]
    lo, hi = sorted((d['leave'][0], d['rejoin'][0]))
    if hi == lo:
        continue
    free = subtract(lo, hi, coverage.get((d['path'], seq), []))
    cover = merged(blocks_of[k] + crowd_cover.get((seq, d['path']), []))
    miss = sum(b - a for x, y in free for a, b in subtract(x, y, cover))
    if miss:
        uncovered_records += 1
        uncovered_bases += miss
    whole_miss = sum(b - a for a, b in subtract(lo, hi, cover))
    if whole_miss:
        whole_records += 1
        whole_bases += whole_miss
print(f'{uncovered_bases}\tbases uncovered, over {uncovered_records} records (must be 0)')
print(f'{whole_bases}\tstretch bases under no block of their record or crowd, over {whole_records} records '
      '(0 where every record is filed over its whole stretch)')

# Window costs
refs = None


def load_index(path):
    raw = gzip.open(path).read()
    o = 4
    n_ref, fmt, cs, cb, ce, meta, skip, l_nm = struct.unpack_from('<8i', raw, o)
    o += 32
    names = raw[o:o + l_nm].split(b'\0')[:-1]
    o += l_nm
    out = {}
    for k in range(n_ref):
        (n_bin,) = struct.unpack_from('<i', raw, o)
        o += 4
        bins = {}
        for _ in range(n_bin):
            bn, nc = struct.unpack_from('<Ii', raw, o)
            o += 8
            bins[bn] = [struct.unpack_from('<QQ', raw, o + 16 * j) for j in range(nc)]
            o += 16 * nc
        (n_intv,) = struct.unpack_from('<i', raw, o)
        o += 4
        lin = list(struct.unpack_from(f'<{n_intv}Q', raw, o))
        o += 8 * n_intv
        out[names[k].decode()] = (bins, lin)
    return out


def reg2bins(beg, end):
    end -= 1
    out = [0]
    for shift, off in [(26, 1), (23, 9), (20, 73), (17, 585), (14, 4681)]:
        out += range(off + (beg >> shift), off + (end >> shift) + 1)
    return out


def gmod_query(ref, beg, end):
    # requests and bytes as @gmod/tabix's optimizeChunks merges them
    bins, lin = ref
    i = beg >> 14
    lowest = lin[i] if i < len(lin) else (lin[-1] if lin else 0)
    chunks = sorted(c for bn in reg2bins(beg, end) for c in bins.get(bn, []) if c[1] > lowest)
    if not chunks:
        return 0, 0
    merged_ = [list(chunks[0])]
    for a, b in chunks[1:]:
        last = merged_[-1]
        if (a >> 16) - (last[1] >> 16) < 65000 and (b >> 16) - (last[0] >> 16) < 5000000:
            if b > last[1]:
                last[1] = b
        else:
            merged_.append([a, b])
    return len(merged_), sum((b >> 16) - (a >> 16) + 65536 for a, b in merged_)


if tbi.endswith('.tbi'):
    refs = load_index(tbi)


def classify(seq, a, b, kind, k):
    if kind == 'c':
        return 'crowd'
    d = parsed[k]
    for e in (d['leave'], d['rejoin']):
        # a row holding a base beside an end's breakpoint
        if e is not None and a <= e[0] and e[0] <= b and (a < e[0] or b > e[0]) and (e[0] - 1 >= a or e[0] + 1 <= b):
            return 'end'
    if d['leave'] is None or d['rejoin'] is None:
        return 'end'
    whole_type = d['leave'][3] == 1 and d['rejoin'][3] == 1 and (
        d['leave'][2] != d['rejoin'][2] or ((d['rejoin'][0] < d['leave'][0]) if d['leave'][2] == '+' else (d['rejoin'][0] > d['leave'][0])))
    return 'whole' if whole_type else 'interior'


q = lambda v, p: sorted(v)[min(len(v) - 1, int(p * len(v)))] if v else 0
by_seq = collections.defaultdict(list)
for row in dep_rows:
    by_seq[row[0]].append(row)
CLASSES = ('end', 'interior', 'whole', 'crowd')
for seq, rows in (by_seq.items() if SHARD == 0 else []):
    rows.sort(key=lambda x: (x[1], x[2]))
    cls = [classify(seq, a, b, kind, k) for _, a, b, kind, k, _ in rows]
    print(f'# {seq}~departure: rows by class: ' + ', '.join(f'{c} {cls.count(c)}' for c in CLASSES))
    length = seq_len[seq]
    path_of = [parsed[k]['path'] if kind == 'd' else k for _, _, _, kind, k, _ in rows]
    chunk_of = [parsed[k]['leave'][4] if kind == 'd' and parsed[k]['leave'] else None for _, _, _, kind, k, _ in rows]
    by_end = sorted(range(len(rows)), key=lambda j: rows[j][2])
    for label, size, step in (('64 kb', args.window, args.window), ('1 bp', 1, args.point)):
        # a sweep: rows join as their start passes the window's end and
        # leave as their end passes its start
        res = []
        add = drop = 0
        n_active = 0
        counts = collections.Counter()
        nbytes = 0
        paths = collections.Counter()
        chunks = collections.Counter()
        alive = bytearray(len(rows))
        for w in range(0, length, step):
            while add < len(rows) and rows[add][1] < w + size:
                j = add
                add += 1
                if rows[j][2] <= w:
                    continue
                alive[j] = 1
                n_active += 1
                counts[cls[j]] += 1
                nbytes += rows[j][5]
                paths[path_of[j]] += 1
                if chunk_of[j] is not None:
                    chunks[chunk_of[j]] += 1
            while drop < len(by_end) and rows[by_end[drop]][2] <= w:
                j = by_end[drop]
                drop += 1
                if not alive[j]:
                    continue
                alive[j] = 0
                n_active -= 1
                counts[cls[j]] -= 1
                nbytes -= rows[j][5]
                paths[path_of[j]] -= 1
                if paths[path_of[j]] == 0:
                    del paths[path_of[j]]
                if chunk_of[j] is not None:
                    chunks[chunk_of[j]] -= 1
                    if chunks[chunk_of[j]] == 0:
                        del chunks[chunk_of[j]]
            outside = sum(1 for c in chunks if not (w - chunk_size <= c < w + size))
            reqd, byd = gmod_query(refs[seq + '~departure'], w, w + size) if refs and seq + '~departure' in refs else (0, 0)
            reqw, byw = gmod_query(refs[seq], max(0, w - chunk_size), w + size) if refs and seq in refs else (0, 0)
            res.append((w, n_active, dict(counts), nbytes, len(paths), outside, reqd, byd, reqw, byw))
        n = [x[1] for x in res]
        print(f'{label} windows: {len(res)}')
        print(f'  rows median {q(n, .5)} p95 {q(n, .95)} max {max(n)}')
        for c in CLASSES:
            v = [x[2].get(c, 0) for x in res]
            print(f'    {c}: median {q(v, .5)} p95 {q(v, .95)} max {max(v)}')
        for i, name in ((3, 'text bytes'), (4, 'paths with a row'), (5, 'distinct leaveChunks outside the walk read'),
                        (6, 'departure read requests'), (7, 'departure read bytes'), (8, 'walk read requests'),
                        (9, 'walk read bytes')):
            v = [x[i] for x in res]
            print(f'  {name}: median {q(v, .5)} p95 {q(v, .95)} max {max(v)}')
        if label == '64 kb':
            for w, nsel, counts, nbytes, npaths, _, reqd, byd, reqw, byw in sorted(res, key=lambda x: -x[1])[:args.top]:
                sel = [j for j in range(len(rows)) if rows[j][1] < w + size and rows[j][2] > w]
                counts = collections.Counter(cls[j] for j in sel)
                print(f'  densest window {seq}:{w}-{w + size}: {nsel} rows, {nbytes} text bytes, {npaths} paths, '
                      f'departure read {reqd} requests {byd} bytes; walk read {reqw} requests {byw} bytes')
                print('    by class: ' + ', '.join(f'{c} {counts[c]}' for c in CLASSES))
                per_path = collections.Counter((parsed[rows[j][4]]['path'] if rows[j][3] == 'd' else rows[j][4]) for j in sel)
                print('    most rows by path: ' + ', '.join(f'{p} {v}' for p, v in per_path.most_common(5)))
                recs = {rows[j][4] for j in sel if rows[j][3] == 'd'}
                kinds_ = collections.Counter()
                for k in recs:
                    d = parsed[k]
                    if d['leave'] is None or d['rejoin'] is None:
                        kinds_['one-ended'] += 1
                        continue
                    multi = d['leave'][3] > 1 or d['rejoin'][3] > 1
                    kinds_['an end on a node passed more than once' if multi else 'both ends on nodes passed once'] += 1
                    kinds_['0 own bp' if d['own_bp'] == 0 else 'own bp'] += 1
                    span = abs(d['rejoin'][0] - d['leave'][0])
                    kinds_['stretch under 1 kb' if span < 1000 else ('stretch under 64 kb' if span < 65536 else 'stretch 64 kb or more')] += 1
                print(f'    {len(recs)} records: ' + ', '.join(f'{k} {v}' for k, v in sorted(kinds_.items())))
