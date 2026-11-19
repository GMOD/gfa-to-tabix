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
# - the `#walks` line states `tile:i:`, from 1 to 2^40, and each tag name
#   the page gives at most once, with its type letter: `format`, `tile`,
#   `revisited`, `stay`, `abridge`, `abridgebytes`, `leftout` and the
#   directory's `bytes` as `i` and a number, `graph` as `Z` and 16 lowercase
#   hex digits; a file without any of them but `format` and `tile` is
#   checked as one with them, and the data file's line states no `bytes`
# - every line of the directory and of the data file ends in a newline and
#   none is empty or holds an empty field; one `#reference` line; no line
#   of a unit after its first begins `#unit`, whatever the unit's kind
# - every number of a `#unit`, `#entry`, `#hole` or directory line and of a
#   row's fixed columns is decimal digits with no sign, no leading zero and
#   no space, `0` for zero, a delta token and a choice token alone
#   beginning `-` and neither of them `-0` (claims7.py's K7 and K8 hold a
#   blocks row's list to its grammar); every length a ref or nodes row
#   states is at least 1; and no coordinate is above
#   2^53: a line's `start end`, a `fragStart`, a `hapOffset`, the end of a
#   ref row's stretch, `hapOffset + hapBp`, `hapStart + ownBp` and a
#   record's breakpoints (claims7.py holds a walk row's piece to it, whose
#   end on its contig takes decoding)
# - a tile, departure block, detail unit or blocks unit holds a row, and a
#   table an entry
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
#   step once, each ref row's `passes` states for each step how many
#   steps the file's ref rows make on its node, and the `#walks` line's
#   `revisited:i:`, where it states one, is how many nodes they step more
#   than once. The script counts every ref row's steps as it streams, then
#   reads the tile and detail units a second time against the counts, and
#   names every failure of the three at once. The page promises the first
#   of a file that states `revisited:i:0`, and this writer keeps it on
#   every file it writes, which is what the script holds a file to: on a
#   file with revisited nodes from another writer it fails what the format
#   leaves open, and spec8.py holds a file to the page alone
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


NUMBER = '(?:0|[1-9][0-9]*)'
NAME = '[!"$-~][!-~]*'
MAX = 1 << 53


def not_plain(raw):
    return (not raw.endswith(b'\n') or raw.startswith((b'\n', b'\t')) or b'\n\n' in raw or b'\t\t' in raw
            or b'\n\t' in raw or b'\t\n' in raw)


def numbers(*fields):
    return all(re.fullmatch(NUMBER, x) for x in fields)


def names(*fields):
    return all(re.fullmatch(NAME, x) for x in fields)


raw_directory = open(path + '.idx', 'rb').read()
if not_plain(raw_directory):
    fail('the directory holds an empty line or field, or does not end in a newline')
directory = [l.split('\t') for l in decoded(raw_directory)[:-1].split('\n')]
first = directory[0]
stated = [t for t in first if t.startswith('bytes:i:')]
walks = [t for t in first if not t.startswith('bytes:i:')]
if walks[0] != '#walks' or [t for t in walks if t.startswith('format:i:')] != ['format:i:8'] or len(stated) != 1:
    fail('directory line 1 is not a format 8 #walks line with one bytes:i:')
for name, form in [(f'{n}:i:', NUMBER) for n in ('format', 'tile', 'revisited', 'stay', 'abridge', 'abridgebytes',
                                                 'leftout', 'bytes')] + [('graph:Z:', '[0-9a-f]{16}')]:
    values = [t for t in first if t.startswith(name[:-2])]
    if len(values) > 1 or not all(t.startswith(name) and re.fullmatch(form, t[len(name):]) for t in values):
        fail(f'the #walks line states {" ".join(values)}, not one {name} of {form}')
if not any(t.startswith('tile:i:') for t in walks):
    fail('the #walks line states no tile:i:')
if int(stated[0][8:]) != size:
    fail(f'bytes:i: is {stated[0][8:]}, the file {size}')
if len(directory) < 2 or directory[1][:2] != ['#header', '0'] or len(directory[1]) != 3:
    fail('directory line 2 is not #header 0 <length>, with no tag')
listed = [c for c in directory[2:] if not c[0].startswith('#')]
if any(len(c) != 3 for c in listed):
    fail('a directory line of a sequence is not its name, offset and length alone')
if not numbers(directory[1][2], *(x for c in listed for x in c[1:])):
    fail('a directory line states an offset or length that is not a number as the page writes one')
if not names(*(c[0] for c in listed)):
    fail('a directory line names a sequence in bytes outside 0x21 to 0x7E')
header_end = int(directory[1][2])
tables = [(c[0], int(c[1]), int(c[2])) for c in listed]
stated_tile = int(next(t for t in walks if t.startswith('tile:i:'))[7:])
if not 1 <= stated_tile <= 1 << 40:
    fail(f'tile:i: is {stated_tile}, not 1 to 2^40')
tile = int(sys.argv[2]) if len(sys.argv) > 2 else stated_tile
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
             route_interior_steps=0, once_passed_nodes=0, revisited_nodes=0, once_passed_nodes_in_a_route_interior=0,
             ref_rows_stating_fewer_passes=0, ref_rows_stating_more_passes=0)
ROWS = dict(tile=('ref', 'nodes', 'route', 'walk', 'abridged'), departures=('departure',),
            detail=('nodes', 'route', 'walk'), blocks=('blocks',))
# a row's columns after its start and end: the forms of the short ones, then its lists, each with whether it can be `.`
FIXED = dict(
    ref=([NAME] + [NUMBER] * 4, [('tokens', False), ('lengths', False), ('numbers', True)]),
    nodes=([], [('numbers', False), ('lengths', False)]),
    route=([], [('tokens', True)] * 3),
    walk=([NAME] + [NUMBER] * 4 + [f'{NUMBER}(?:@{NUMBER})?'], [('choices', True)]),
    abridged=([NAME] + [NUMBER] * 6, []),
    blocks=([NAME] + [NUMBER] * 2 + ['[^\t]+'], []),
    departure=([NAME] + [NUMBER] * 4 + ['[+-]', NUMBER, NUMBER, '[+-]', NUMBER], [('numbers', True)]),
)
ROW = {row: re.compile('\t'.join([NUMBER, NUMBER, row] + short)) for row, (short, _) in FIXED.items()}
# a list's characters, and what no list of its kind holds: an empty item, a leading zero, `-0`, a `-` inside an
# item, a length of 0, and in a choice a `:k` or `@k` that is empty, twice or out of order. Each is a search over
# single characters, so a list of any length is checked in the memory its text takes
LISTS = dict(
    numbers=('[0-9,]+', '(?:^|,)(?:0[0-9]|,|$)'),
    lengths=('[0-9,]+', '(?:^|,)(?:0|,|$)'),
    tokens=('[0-9,-]+', '(?:^|,)-?(?:0[0-9]|,|$)|(?:^|,)-0|[0-9-]-'),
    choices=('[0-9,:@-]+', '(?:^|,)-?(?:0[0-9]|[,:@]|$)|(?:^|,)-0|[0-9:@-]-|[:@](?:0[0-9]|[,:@]|$)'
                           '|@[0-9]*:|:[0-9]*:|@[0-9]*@'),
)
LISTS = {kind: (re.compile(held), re.compile(wrong)) for kind, (held, wrong) in LISTS.items()}


def written(row, c):
    short, lists = FIXED[row]
    at = 4 + len(short)
    return (len(c) >= at + len(lists) and ROW[row].fullmatch('\t'.join(c[1:at])) is not None
            and all((none and field == '.') or (LISTS[kind][0].fullmatch(field) and not LISTS[kind][1].search(field))
                    for field, (kind, none) in zip(c[at:], lists)))


COORDINATES = dict(ref=(5, 6), nodes=(), route=(), walk=(5, 6), abridged=(5, 6), blocks=(5,), departure=(5, 8, 11))
SUMS = dict(abridged=(6, 9), departure=(5, 6))
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
    if not text.endswith(b'\n'):
        fail(f'the unit at {at} does not end in a newline')
    if not_plain(text):
        fail(f'the unit at {at} holds an empty line or field')
    if b'\n#unit' in text:
        fail(f'a line of the unit at {at} after its first begins #unit')
    lines = decoded(text).split('\n')
    head = lines[0].split('\t')
    if len(head) != 6:
        fail(f'the #unit line at {at} is not its sequence, start, end, kind and name alone: {lines[0][:80]}')
    if not names(head[1]):
        fail(f'the #unit line at {at} names a sequence in bytes outside 0x21 to 0x7E: {lines[0][:80]}')
    if not numbers(head[2], head[3]):
        fail(f'the #unit line at {at} states a start or end that is not a number as the page writes one: '
             f'{lines[0][:80]}')
    seq, lo, hi, kind, name = head[1], int(head[2]), int(head[3]), head[4], head[5]
    if hi > MAX:
        fail(f'a coordinate above 2^53 in the #unit line at {at}: {lines[0][:80]}')
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
        if not written(c[3], c):
            fail(f'a {c[3]} row with a column short, a number not written as the page writes one, a length of 0 '
                 f'or a path in bytes outside 0x21 to 0x7E, at {at}: {line[:80]}')
        a, b = int(c[1]), int(c[2])
        stated = [a, b, sum(int(c[k]) for k in SUMS.get(c[3], ()))] + [int(c[k]) for k in COORDINATES[c[3]]]
        if max(stated) > MAX:
            fail(f'a coordinate above 2^53 at {at}: {line[:80]}')
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
            if stretch[1] > MAX:
                fail(f'a ref row whose stretch ends above 2^53 at {at}: {line[:80]}')
            state['ref_end'] = max(state['ref_end'], stretch[1])
            hold(node_ids(c[9]), line)
        elif (c[3] in ('walk', 'abridged') and kind == 'detail') or (c[3] == 'blocks' and kind == 'blocks'):
            stretch = (a, b)
        if c[3] in ('ref', 'nodes', 'route') and (a, b) != (lo, hi):
            fail(f'a {c[3]} row not stating its unit\'s extent: {line[:80]}')
        if stretch:
            union = stretch if union is None else (min(union[0], stretch[0]), max(union[1], stretch[1]))
    if kind == 'departures' and len(lines) < 3:
        fail(f'the departures unit at {at} has no record')
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
    if not lines:
        fail(f'the table of {seq} lists no unit')
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
    stats['revisited_nodes'] = len(held) - held.count(0) - held.count(1)
    failed = [f'{stats[what]} {text}, as {"; ".join(examples[what])}' for what, text in (
        ('once_passed_nodes_in_a_route_interior', 'nodes the file\'s ref rows step once are in a route interior'),
        ('ref_rows_stating_fewer_passes', 'ref rows state fewer passes than the file\'s ref rows step the node'),
        ('ref_rows_stating_more_passes', 'ref rows state more passes than the file\'s ref rows step the node'),
    ) if stats[what]] + [
        f'the #walks line states {t}, and the file\'s ref rows step {stats["revisited_nodes"]} nodes more than once'
        for t in walks if t.startswith('revisited:i:') and t != f'revisited:i:{stats["revisited_nodes"]}']
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
            if not_plain(header):
                fail('the header unit holds an empty line or field, or does not end in a newline')
            lines = decoded(header)[:-1].split('\n')
            if lines[0] != '\t'.join(walks):
                fail('the directory\'s line 1 differs from the header\'s #walks line')
            if any(not l.startswith('#') or l.startswith('#unit') for l in lines):
                fail('a header line that is not a header line')
            stated_lines = [l.split('\t') for l in lines]
            if sum(c[0] == '#reference' for c in stated_lines) != 1:
                fail('the header does not hold one #reference line')
            holes = [c for c in stated_lines if c[0] == '#hole']
            if any(len(c) < 4 or not numbers(c[2], c[3]) or int(c[3]) > MAX for c in holes):
                fail('a #hole line without a start and end written as the page writes a number, at most 2^53')
            if not all(len(c) > 1 and names(c[1]) for c in stated_lines if c[0] in ('#reference', '#haplotype', '#hole')):
                fail('a #reference, #haplotype or #hole line states a name in bytes outside 0x21 to 0x7E')
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
