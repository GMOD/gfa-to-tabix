#!/usr/bin/env python3
"""What the hapBp column costs, from two builds of one graph: a format 8
file written before the column and one written with it.

Reads both through their tables. Every unit of the first must be in the
second with the same lines, but for the tenth column of the second's
abridged rows and the offsets and lengths of table entries. Prints the
compressed bytes of each kind of unit in both, and of the tiles with
abridged rows, with the tile that grows most.

Usage: column-bytes.py before.walks.gz after.walks.gz
"""
import collections
import sys
import zlib


def gunzip(raw):
    out = []
    while raw:
        d = zlib.decompressobj(31)
        out.append(d.decompress(raw))
        raw = d.unused_data
    return b''.join(out)


class Walks:
    def __init__(self, path):
        self.data = open(path, 'rb')
        self.bytes = self.data.seek(0, 2)
        lines = open(path + '.idx', 'rb').read().splitlines()
        self.entries = []
        for line in lines[2:]:
            if not line.startswith(b'#'):
                seq, offset, length = line.rsplit(b'\t', 2)
                self.entries.append([b'#entry', seq, b'0', b'0', b'table', b'.', offset, length])
                self.entries += [e.split(b'\t') for e in self.unit(int(offset), int(length)).splitlines()[1:]]

    def unit(self, offset, length):
        self.data.seek(offset)
        return gunzip(self.data.read(length))


before, after = Walks(sys.argv[1]), Walks(sys.argv[2])
sizes = collections.defaultdict(lambda: [0, 0])
differ = rows = 0
abridged = []
if [e[1:6] for e in before.entries] != [e[1:6] for e in after.entries]:
    sys.exit('column-bytes.py: the two files list different units')
for old, new in zip(before.entries, after.entries):
    kind = old[4].decode()
    sizes[kind][0] += int(old[7])
    sizes[kind][1] += int(new[7])
    if kind != 'table':
        was = before.unit(int(old[6]), int(old[7])).split(b'\n')
        now = [line.split(b'\t') for line in after.unit(int(new[6]), int(new[7])).split(b'\n')]
        held = sum(len(c) > 3 and c[3] == b'abridged' for c in now)
        differ += was != [b'\t'.join(c[:9] + c[10:] if len(c) > 3 and c[3] == b'abridged' else c) for c in now]
        rows += held
        if kind == 'tile' and held:
            abridged.append((int(new[7]) - int(old[7]), int(old[7]), int(new[7]), f'{old[1].decode()}:{old[5].decode()}', held))
print(f'{sys.argv[1]}: {before.bytes} bytes; {sys.argv[2]}: {after.bytes} bytes, {after.bytes - before.bytes:+d}, '
      f'{100 * (after.bytes - before.bytes) / before.bytes:+.4f}%')
for kind, (was, now) in sorted(sizes.items()):
    print(f'{kind} units: {was} -> {now} bytes, {now - was:+d}')
was, now = sum(a[1] for a in abridged), sum(a[2] for a in abridged)
print(f'tiles with abridged rows: {len(abridged)}, holding {rows} abridged rows: {was} -> {now} bytes, {now - was:+d}, '
      f'{100 * (now - was) / max(was, 1):+.3f}%, {(now - was) / max(rows, 1):.2f} bytes a row')
if abridged:
    grew, was, now, name, held = max(abridged)
    print(f'the tile that grows most: {name}, {held} abridged rows, {was} -> {now} bytes, {grew:+d}')
print(f'units whose lines differ beyond the column: {differ}')
sys.exit(1 if differ else 0)
