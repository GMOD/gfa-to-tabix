#!/usr/bin/env python3
# The release checks of a walk format 7 file and its directory, read as a
# stream: one gzip member at a time, holding one unit and one sequence's
# departure records, so a file of any size checks in bounded memory. It
# checks what arbiter A's verify7.mjs does, which reads files whole and so
# none past 2 GiB, and more:
# - the directory's line 1 is the header's `#walks` line with the data
#   file's length; `#header 0 <length>` is the header unit; then one line
#   per sequence naming its table, in file order
# - the header, the units, the tables and the EOF block partition the file;
#   every unit starts on a gzip member with its `#unit` line
# - each table lists exactly the units of its sequence since the last
#   table, in file order, as they are, at their offsets and lengths, each
#   above 0 bytes, and its `#unit` line runs from 0 to `|S|`, where the
#   sequence's last `ref` row ends
# - no two units of a kind and sequence share a name other than `.`
# - every line starts with its unit's sequence; a tile's or detail unit's
#   lines lie in its extent, which runs from the first base its ref rows'
#   stretches and its pieces' spans cover to the last, or where they cover
#   no base is the base after their point `p`, the base before it where `p`
#   is `|S|`, or `[0, 0)` where `|S|` is 0; its other rows state the extent
# - a departure block is named `.` and aligned, each of its lines overlaps
#   it, or lies at its start where the line is a point, and each record is
#   in every block of its cover and no other
# Usage: verify7.py walks.gz [tile]; prints a JSON summary, exits 1 on the
# first failure.
import hashlib
import json
import os
import struct
import sys
import zlib

path = sys.argv[1]
size = os.path.getsize(path)


def fail(msg):
    sys.exit(f'verify7.py: {path}: {msg}')


directory = [l.split('\t') for l in open(path + '.idx').read().rstrip('\n').split('\n')]
walks = directory[0]
if walks[:2] != ['#walks', 'format:i:7'] or not walks[-1].startswith('bytes:i:'):
    fail('directory line 1 is not a format 7 #walks line ending in bytes:i:')
if int(walks[-1][8:]) != size:
    fail(f'bytes:i: is {walks[-1][8:]}, the file {size}')
if directory[1][:2] != ['#header', '0']:
    fail('directory line 2 is not #header 0')
header_end = int(directory[1][2])
tables = [(c[0], int(c[1]), int(c[2])) for c in directory[2:]]
tile = int(sys.argv[2]) if len(sys.argv) > 2 else int(next(t for t in walks if t.startswith('tile:i:'))[7:])
sizes = [tile * n for n in (512, 64, 8, 1)]


def cover(lo, hi):
    out, at = [], lo // tile * tile
    end = max(-(-hi // tile) * tile, at + tile)
    while at < end:
        s = next(s for s in sizes if at % s == 0 and at + s <= end)
        out.append((at, s))
        at += s
    return out


def members(f):
    at = 0
    while at < size:
        head = f.read(18)
        if head[:2] != b'\x1f\x8b':
            fail(f'no gzip member at {at}')
        n = struct.unpack_from('<H', head, 16)[0] + 1
        body = head + f.read(n - 18)
        yield at, n, zlib.decompress(body[18:-8], -15)
        at += n


stats = dict(units=0, tables=0, lines=0, departure_lines=0)
state = dict(units=[], names=set(), records={}, table=0, ref_end=0, points=[])


def check_unit(at, length, text):
    lines = text.decode().split('\n')
    if lines[-1] != '':
        fail(f'the unit at {at} does not end in a newline')
    head = lines[0].split('\t')
    seq, lo, hi, kind, name = head[1], int(head[2]), int(head[3]), head[4], head[5]
    if kind == 'table':
        check_table(at, length, seq, lo, hi, lines[1:-1])
        return
    stats['units'] += 1
    state['units'].append('\t'.join([seq, head[2], head[3], kind, name, str(at), str(length)]))
    if name != '.' and (kind, name) in state['names']:
        fail(f'two {kind} units of {seq} named {name}')
    state['names'].add((kind, name))
    union = None
    for line in lines[1:-1]:
        c = line.split('\t')
        stats['lines'] += 1
        if c[0] != seq:
            fail(f'a line of another sequence in the unit at {at}: {line[:80]}')
        a, b = int(c[1]), int(c[2])
        if kind == 'departures':
            stats['departure_lines'] += 1
            if name != '.':
                fail(f'departure block {lo} {hi} named {name}, not .')
            if lo % (hi - lo):
                fail(f'departure block {lo} {hi} is not aligned')
            if not (a < hi and (lo < b or a == b)):
                fail(f'a departure line not overlapping its block {lo} {hi}: {line[:80]}')
            key = hashlib.blake2b(line.encode(), digest_size=12).digest()
            state['records'].setdefault(key, [a, b, []])[2].append((lo, hi - lo))
            continue
        if not (lo <= a <= b <= hi):
            fail(f'a line outside its unit\'s extent {lo} {hi}: {line[:80]}')
        stretch = None
        if c[3] == 'ref':
            start = int(c[6])
            stretch = (start, start + sum(int(x) for x in c[10].split(',')))
            state['ref_end'] = max(state['ref_end'], stretch[1])
        elif c[3] in ('walk', 'abridged'):
            stretch = (a, b)
        if c[3] in ('ref', 'nodes', 'route') and (a, b) != (lo, hi):
            fail(f'a {c[3]} row not stating its unit\'s extent: {line[:80]}')
        if stretch:
            union = stretch if union is None else (min(union[0], stretch[0]), max(union[1], stretch[1]))
    if kind != 'departures':
        if union is None:
            fail(f'the {kind} unit at {at} has no ref row and no piece')
        if union[0] < union[1]:
            if union != (lo, hi):
                fail(f'the {kind} unit at {at} has extent {lo} {hi}, its lines {union}')
        else:
            state['points'].append((at, kind, union[0], lo, hi))


def check_table(at, length, seq, head_lo, head_hi, lines):
    if state['table'] >= len(tables) or tables[state['table']] != (seq, at, length):
        fail(f'the table of {seq} at {at} is not the directory\'s next')
    state['table'] += 1
    stats['tables'] += 1
    listed = ['\t'.join(l.split('\t')[1:]) for l in lines]
    if any(not l.startswith('#entry\t') for l in lines) or listed != state['units']:
        fail(f'the table of {seq} does not list its units as they are, in file order')
    if any(int(l.split('\t')[7]) <= 0 for l in lines):
        fail(f'the table of {seq} lists a unit of 0 bytes')
    length = state['ref_end']
    if (head_lo, head_hi) != (0, length):
        fail(f'the table of {seq} states {head_lo} {head_hi}, not 0 and |S| {length}')
    for unit_at, kind, p, lo, hi in state['points']:
        beside = (0, 0) if length == 0 else (p - 1, p) if p == length else (p, p + 1)
        if (lo, hi) != beside:
            fail(f'the {kind} unit at {unit_at} covers no base at {p}, and its extent {lo} {hi} is not {beside}')
    for a, b, blocks in state['records'].values():
        if sorted(blocks) != cover(a, b):
            fail(f'a departure record of {seq} over {a} {b} is in blocks {sorted(blocks)}, not its cover')
    state.update(units=[], names=set(), records={}, ref_end=0, points=[])


with open(path, 'rb') as f:
    header = b''
    unit = None
    eof = None
    for at, n, text in members(f):
        if eof is not None:
            fail(f'a member after the EOF block at {eof}')
        if at < header_end:
            header += text
            continue
        if at == header_end:
            lines = header.decode().split('\n')
            if lines[0] != '\t'.join(walks[:-1]):
                fail('the directory\'s line 1 differs from the header\'s #walks line')
            if any(l and (not l.startswith('#') or l.startswith('#unit')) for l in lines):
                fail('a header line that is not a header line')
        if n == 28 and not text:
            if unit:
                check_unit(*unit)
            unit = None
            eof = at
        elif text.startswith(b'#unit\t'):
            if unit:
                check_unit(*unit)
            unit = [at, n, text]
        elif unit:
            unit[1] += n
            unit[2] += text
        else:
            fail(f'the member at {at} belongs to no unit')
    if eof is None or eof + 28 != size:
        fail('no EOF block at the end')
    if state['table'] != len(tables):
        fail('the directory names tables the file does not hold')
    if state['units']:
        fail('units after the last table')
print(json.dumps(dict(file=path, ok=True, **stats)))
