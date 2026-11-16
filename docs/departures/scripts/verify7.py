#!/usr/bin/env python3
# The release checks of a walk format 8 file and its directory, read as a
# stream: one gzip member at a time, holding one unit, one sequence's
# departure records and a byte for each node id up to the largest a ref row
# steps, so a file of any size checks in memory its node ids bound, at most
# 2 GiB. It checks what arbiter A's verify7.mjs does, which reads files
# whole and so none past 2 GiB, and more:
# - the directory's line 1 is the header's `#walks` line with the data
#   file's length as a `bytes:i:` tag, its tags in any order;
#   `#header 0 <length>` is the header unit, which ends where a gzip member
#   starts; then one line per sequence naming its table, in file order. A
#   line that starts with `#` past line 2 is a later addition, skipped; the
#   `#header` and sequence lines, `#unit` lines and `#entry` lines hold no
#   tag
# - the `#walks` line states `graph:Z:` as 16 lowercase hex digits and
#   `leftout:i:` as a decimal integer, each at most once; a file without
#   them is checked as one with them
# - every unit is BGZF members, and every row of a tile, departure block,
#   detail unit or blocks unit is of a kind that unit holds
# - the header, the units, the tables and the EOF block partition the file;
#   every unit starts on a gzip member with its `#unit` line: a member that
#   begins `#unit<TAB>` after one whose text ended in a newline, as a member
#   cut inside a line of a sequence named `...#unit` begins so too
# - a unit of a kind this script doesn't know is listed by its own
#   sequence's table like any other, and its rows are not read
# - each table lists exactly the units of its sequence since the last
#   table, in file order, as they are, at their offsets and lengths, each
#   above 0 bytes, and its `#unit` line runs from 0 to `|S|`, where the
#   sequence's last `ref` row ends
# - no two units of a kind and sequence share a name other than `.`
# - every line starts with its unit's sequence; a tile's, detail unit's or
#   blocks unit's lines lie in its extent, which runs, for a tile, from the
#   first base its ref rows' stretches cover to the last, for a detail unit
#   from the first base its pieces' spans cover to the last, and for a blocks
#   unit from the first base its rows' spans cover to the last, or where they
#   cover no base is the base after their point `p`, the base before it where
#   `p` is `|S|`, or `[0, 0)` where `|S|` is 0; its other rows state the extent
# - a departure block is named `.` and aligned, each of its lines overlaps
#   it, or lies at its start where the line is a point, and each record is
#   in every block of its cover and no other: blocks of `tile × 8^L` bp,
#   each at a multiple of its size, that tile the record's stretch widened
#   to whole tiles, and to at least the tile holding its start, with no
#   larger block aligned at a block's start that would fit
# - over the whole file, whatever tile or sequence a row is in: no route
#   interior, of a tile or a detail unit, holds a node the file's ref rows
#   step once, and each ref row's `passes` states for each step how many
#   steps the file's ref rows make on its node. The script counts every ref
#   row's steps as it streams, then reads the tile and detail units a second
#   time against the counts, and names every failure of the two at once
# Usage: verify7.py walks.gz [tile]; prints a JSON summary, exits 1 on the
# first failure.
import collections
import hashlib
import itertools
import json
import os
import re
import struct
import sys
import zlib

path = sys.argv[1]
size = os.path.getsize(path)


def fail(msg):
    sys.exit(f'verify7.py: {path}: {msg}')


def decoded(raw):
    return raw.decode('utf-8', 'surrogateescape')


directory = [l.split('\t') for l in decoded(open(path + '.idx', 'rb').read()).rstrip('\n').split('\n')]
first = directory[0]
stated = [t for t in first if t.startswith('bytes:i:')]
walks = [t for t in first if not t.startswith('bytes:i:')]
if walks[0] != '#walks' or [t for t in walks if t.startswith('format:i:')] != ['format:i:8'] or len(stated) != 1:
    fail('directory line 1 is not a format 8 #walks line with one bytes:i:')
for name, form in (('graph:Z:', '[0-9a-f]{16}'), ('leftout:i:', '0|[1-9][0-9]*')):
    values = [t[len(name):] for t in walks if t.startswith(name)]
    if len(values) > 1 or not all(re.fullmatch(form, v) for v in values):
        fail(f'the #walks line states {" ".join(name + v for v in values)}, not one {name} of {form}')
if int(stated[0][8:]) != size:
    fail(f'bytes:i: is {stated[0][8:]}, the file {size}')
if len(directory) < 2 or directory[1][:2] != ['#header', '0'] or len(directory[1]) != 3:
    fail('directory line 2 is not #header 0 <length>, with no tag')
header_end = int(directory[1][2])
listed = [c for c in directory[2:] if not c[0].startswith('#')]
if any(len(c) != 3 for c in listed):
    fail('a directory line of a sequence is not its name, offset and length alone')
tables = [(c[0], int(c[1]), int(c[2])) for c in listed]
tile = int(sys.argv[2]) if len(sys.argv) > 2 else int(next(t for t in walks if t.startswith('tile:i:'))[7:])
sizes = [tile * n for n in (512, 64, 8, 1)]


def not_cover(lo, hi, blocks):
    start = lo // tile * tile
    end = max(-(-hi // tile) * tile, start + tile)
    at = start
    for a, s in blocks:
        if s not in sizes or a % s:
            return f'block {a} of {s} bp is no aligned pyramid block'
        if a != at:
            return f'blocks leave {at} uncovered or overlap there'
        if any(t > s and a % t == 0 and a + t <= end for t in sizes):
            return f'block {a} of {s} bp where a larger one fits'
        at = a + s
    return None if at == end else f'blocks end at {at}, not {end}'


def members(f, at, end):
    while at < end:
        head = f.read(18)
        if head[:4] != b'\x1f\x8b\x08\x04' or head[10:16] != b'\x06\x00BC\x02\x00':
            fail(f'no BGZF member at {at}')
        n = struct.unpack_from('<H', head, 16)[0] + 1
        body = head + f.read(n - 18)
        yield at, n, zlib.decompress(body[18:-8], -15)
        at += n


stats = dict(units=0, tables=0, lines=0, departure_lines=0, members_cut_before_unit_text=0, ref_steps=0,
             route_interior_steps=0, once_passed_nodes=0, once_passed_nodes_in_a_route_interior=0,
             ref_rows_stating_fewer_passes=0, ref_rows_stating_more_passes=0)
ROWS = dict(tile=('ref', 'nodes', 'route', 'walk', 'abridged'), departures=('departure',),
            detail=('nodes', 'route', 'walk'), blocks=('blocks',))
COVERED_BY = dict(tile='ref rows', blocks='blocks rows')
state = dict(units=[], names=set(), records={}, table=0, ref_end=0, points=[])
held = bytearray()
beyond = collections.Counter()
routed = []


def node_ids(field, before=0):
    return list(itertools.accumulate((int(t) >> 1 for t in field.split(',') if t != '.'), initial=before))[1:]


def hold(nodes, line):
    top = max(nodes)
    if min(nodes) < 0 or top >> 31:
        fail(f'a ref row steps a node id outside 0 to 2^31: {line[:80]}')
    held.extend(bytes(max(top + 1 - len(held), 0)))
    for node in nodes:
        if held[node] < 255:
            held[node] += 1
        else:
            beyond[node] += 1


def passes_held(nodes):
    return [held[n] if held[n] < 255 else 255 + beyond[n] for n in nodes]


def check_unit(at, length, text):
    lines = decoded(text).split('\n')
    if lines[-1] != '':
        fail(f'the unit at {at} does not end in a newline')
    head = lines[0].split('\t')
    if len(head) != 6:
        fail(f'the #unit line at {at} is not its sequence, start, end, kind and name alone: {lines[0][:80]}')
    seq, lo, hi, kind, name = head[1], int(head[2]), int(head[3]), head[4], head[5]
    if kind == 'table':
        check_table(at, length, seq, lo, hi, lines[1:-1])
        return
    stats['units'] += 1
    if kind in ('tile', 'detail'):
        routed.append((at, length, seq, kind, name))
    state['units'].append('\t'.join([seq, head[2], head[3], kind, name, str(at), str(length)]))
    if name != '.' and (kind, name) in state['names']:
        fail(f'two {kind} units of {seq} named {name}')
    state['names'].add((kind, name))
    union = None
    for line in lines[1:-1] if kind in ROWS else []:
        c = line.split('\t')
        stats['lines'] += 1
        if c[0] != seq:
            fail(f'a line of another sequence in the unit at {at}: {line[:80]}')
        if len(c) < 4 or c[3] not in ROWS[kind]:
            fail(f'a row of a kind a {kind} unit doesn\'t hold, at {at}: {line[:80]}')
        a, b = int(c[1]), int(c[2])
        if kind == 'departures':
            stats['departure_lines'] += 1
            if name != '.':
                fail(f'departure block {lo} {hi} named {name}, not .')
            if lo % (hi - lo):
                fail(f'departure block {lo} {hi} is not aligned')
            if not (lo < b and a < hi if a < b else a == lo):
                fail(f'a departure line not overlapping its block {lo} {hi}: {line[:80]}')
            key = hashlib.blake2b(line.encode('utf-8', 'surrogateescape'), digest_size=12).digest()
            state['records'].setdefault(key, [a, b, []])[2].append((lo, hi - lo))
            continue
        if not (lo <= a <= b <= hi):
            fail(f'a line outside its unit\'s extent {lo} {hi}: {line[:80]}')
        stretch = None
        if c[3] == 'ref':
            start = int(c[6])
            stretch = (start, start + sum(int(x) for x in c[10].split(',')))
            state['ref_end'] = max(state['ref_end'], stretch[1])
            hold(node_ids(c[9]), line)
        elif (c[3] in ('walk', 'abridged') and kind == 'detail') or (c[3] == 'blocks' and kind == 'blocks'):
            stretch = (a, b)
        if c[3] in ('ref', 'nodes', 'route') and (a, b) != (lo, hi):
            fail(f'a {c[3]} row not stating its unit\'s extent: {line[:80]}')
        if stretch:
            union = stretch if union is None else (min(union[0], stretch[0]), max(union[1], stretch[1]))
    if kind in ROWS and kind != 'departures':
        if union is None:
            fail(f'the {kind} unit at {at} has no ref row, piece or blocks row')
        if union[0] < union[1]:
            if union != (lo, hi):
                fail(f'the {kind} unit at {at} has extent {lo} {hi}, where its '
                     f'{COVERED_BY.get(kind, "pieces")} cover {union}')
        else:
            state['points'].append((at, kind, union[0], lo, hi))


def check_table(at, length, seq, head_lo, head_hi, lines):
    if state['table'] >= len(tables) or tables[state['table']] != (seq, at, length):
        fail(f'the table of {seq} at {at} is not the directory\'s next')
    state['table'] += 1
    stats['tables'] += 1
    listed = ['\t'.join(l.split('\t')[1:]) for l in lines]
    if any(not l.startswith('#entry\t') or l.count('\t') != 7 for l in lines) or listed != state['units']:
        fail(f'the table of {seq} does not list its units as they are, in file order')
    if any(int(l.split('\t')[7]) <= 0 for l in lines):
        fail(f'the table of {seq} lists a unit of 0 bytes')
    if any(l.split('\t')[1] != seq for l in lines):
        fail(f'the table of {seq} lists a unit of another sequence')
    length = state['ref_end']
    if (head_lo, head_hi) != (0, length):
        fail(f'the table of {seq} states {head_lo} {head_hi}, not 0 and |S| {length}')
    for unit_at, kind, p, lo, hi in state['points']:
        beside = (0, 0) if length == 0 else (p - 1, p) if p == length else (p, p + 1)
        if (lo, hi) != beside:
            fail(f'the {kind} unit at {unit_at} covers no base at {p}, and its extent {lo} {hi} is not {beside}')
    for a, b, blocks in state['records'].values():
        wrong = not_cover(a, b, sorted(blocks))
        if wrong:
            fail(f'a departure record of {seq} over {a} {b} is in blocks {sorted(blocks)}, not its cover: {wrong}')
    state.update(units=[], names=set(), records={}, ref_end=0, points=[])


def check_passes(f):
    examples = collections.defaultdict(list)
    inside = set()

    def found(what, example):
        stats[what] += 1
        if stats[what] <= 3:
            examples[what].append(example)

    for at, length, seq, kind, name in routed:
        f.seek(at)
        lines = decoded(b''.join(text for _, _, text in members(f, at, at + length))).split('\n')
        last = 0
        for line in lines[1:-1]:
            c = line.split('\t')
            if c[3] == 'ref':
                nodes = node_ids(c[9])
                stated = [1] * len(nodes) if c[11] == '.' else [int(p) for p in c[11].split(',')]
                counted = passes_held(nodes)
                stats['ref_steps'] += len(nodes)
                if len(stated) != len(nodes):
                    fail(f'a ref row whose passes are not one per step: {line[:80]}')
                if stated != counted:
                    steps = list(zip(nodes, stated, counted))
                    for what, off in (('ref_rows_stating_fewer_passes', [s for s in steps if s[1] < s[2]]),
                                      ('ref_rows_stating_more_passes', [s for s in steps if s[1] > s[2]])):
                        if off:
                            node, p, n = off[0]
                            found(what, f'{p} for node {node}, which they step {n} times, in {seq} {kind} {name}: '
                                        f'{line[:80]}')
            elif c[3] == 'route':
                ids = node_ids(','.join(c[4:7]), last)
                last = ids[-1] if ids else last
                interior = ids[c[4] != '.':len(ids) - (c[6] != '.')]
                stats['route_interior_steps'] += len(interior)
                for node in interior:
                    if 0 <= node < len(held) and held[node] == 1 and node not in inside:
                        inside.add(node)
                        found('once_passed_nodes_in_a_route_interior',
                              f'node {node} in {seq} {kind} {name}: {line[:80]}')
    stats['once_passed_nodes'] = held.count(1)
    failed = [f'{stats[what]} {text}, as {"; ".join(examples[what])}' for what, text in (
        ('once_passed_nodes_in_a_route_interior', 'nodes the file\'s ref rows step once are in a route interior'),
        ('ref_rows_stating_fewer_passes', 'ref rows state fewer passes than the file\'s ref rows step the node'),
        ('ref_rows_stating_more_passes', 'ref rows state more passes than the file\'s ref rows step the node'),
    ) if stats[what]]
    if failed:
        fail('; '.join(failed))


with open(path, 'rb') as f:
    header = b''
    unit = None
    eof = None
    header_read = False
    for at, n, text in members(f, 0, size):
        if eof is not None:
            fail(f'a member after the EOF block at {eof}')
        if at < header_end:
            header += text
            continue
        if not header_read:
            if at != header_end:
                fail(f'#header 0 {header_end} ends inside the member at {at}')
            header_read = True
            lines = decoded(header).split('\n')
            if lines[0] != '\t'.join(walks):
                fail('the directory\'s line 1 differs from the header\'s #walks line')
            if any(l and (not l.startswith('#') or l.startswith('#unit')) for l in lines):
                fail('a header line that is not a header line')
        if n == 28 and not text:
            if unit:
                check_unit(*unit)
            unit = None
            eof = at
        elif text.startswith(b'#unit\t') and (unit is None or unit[2].endswith(b'\n')):
            if unit:
                check_unit(*unit)
            unit = [at, n, text]
        elif unit:
            stats['members_cut_before_unit_text'] += text.startswith(b'#unit\t')
            unit[1] += n
            unit[2] += text
        else:
            fail(f'the member at {at} belongs to no unit')
    if not header_read:
        fail(f'#header 0 {header_end} runs past the units')
    if eof is None or eof + 28 != size:
        fail('no EOF block at the end')
    if state['table'] != len(tables):
        fail('the directory names tables the file does not hold')
    if state['units']:
        fail('units after the last table')
    check_passes(f)
print(json.dumps(dict(file=path, ok=True, **stats)))
