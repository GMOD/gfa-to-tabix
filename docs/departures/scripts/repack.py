#!/usr/bin/env python3
# Re-packs a walk format 8 file with one later addition, or one departure
# from walks-format.md, per output directory, so a reader or checker can be
# run on each: it gunzips the units, edits their text, deflates each unit
# again as its own BGZF members, and rewrites every table's offsets and
# lengths and the directory. Each variant is one of:
# - legal: an addition "Later additions are tags, header lines, unit kinds
#   or files" allows, which every reader and checker reads as the file
#   without it; `identity` re-packs with no edit
# - forbidden: a file the page refuses or calls another format
# - unstated: the page doesn't say
# - control: a legal file of another graph, for the variant after it
# check-walks.sh runs every checker on each legal variant of a writer's
# file, and broken.sh on the forbidden ones that broken/ holds.
#
# Usage: repack.py in.walks.gz outdir [variant ...]   one dir per variant
#        repack.py --list                              each variant, its class and why
#        repack.py --legal                             the legal variants' names
# Each outdir/<variant>/ holds f.walks.gz and f.walks.gz.idx; a variant
# that finds nothing to edit in this file (no abridged row, no #hole...)
# writes nothing and is reported as n/a.
import copy
import gzip
import os
import struct
import sys
import zlib

TAG = 'XX:Z:later'
EOF = bytes.fromhex('1f8b08040000000000ff0600424302001b0003000000000000000000')


def encoded(text):
    return text.encode('utf-8', 'surrogateescape')


def decoded(data):
    return data.decode('utf-8', 'surrogateescape')


def bgzf(text):
    out = b''
    for at in range(0, len(text), 0xff00):
        chunk = text[at:at + 0xff00]
        deflater = zlib.compressobj(6, zlib.DEFLATED, -15)
        body = deflater.compress(chunk) + deflater.flush()
        out += (b'\x1f\x8b\x08\x04\0\0\0\0\0\xff\x06\0BC\x02\0'
                + struct.pack('<H', len(body) + 25) + body
                + struct.pack('<II', zlib.crc32(chunk), len(chunk)))
    return out


def plain_gzip(text):
    return gzip.compress(text, 6, mtime=0)


def members(data):
    at = 0
    while at < len(data):
        if data[at:at + 4] != b'\x1f\x8b\x08\x04':
            sys.exit(f'no BGZF member at {at}')
        n = struct.unpack_from('<H', data, at + 16)[0] + 1
        yield at, n, zlib.decompress(data[at + 18:at + n - 8], -15)
        at += n


class Unit:
    def __init__(self, head, lines):
        self.head = head          # the #unit line's columns
        self.lines = lines        # its rows, each a list of columns
        self.entry = None         # the table entry's seq..name, head[1:6] when None
        self.entry_tags = []      # columns after the entry's length
        self.directory = None     # for a unit in no table: its directory line's first word

    @property
    def kind(self):
        return self.head[4]

    def text(self):
        return encoded(''.join('\t'.join(l) + '\n' for l in [self.head] + self.lines))


class Seq:
    def __init__(self, name):
        self.name = name
        self.units = []
        self.table_head = None
        self.dir_tags = []


class Walks:
    def __init__(self, path):
        data = open(path, 'rb').read()
        directory = [l.split('\t') for l in decoded(open(path + '.idx', 'rb').read()).rstrip('\n').split('\n')]
        header_end = int(directory[1][2])
        self.header = []          # header lines, each a list of columns
        self.seqs = []
        self.loose = []           # units after the last table, in no table
        self.bytes_at = None      # where bytes:i: goes in directory line 1; the end when None
        self.dir_header_tags = []
        self.dir_lines = []       # lines added after the sequences'
        self.plain_gzip = False   # each unit as one gzip member without BGZF's extra field
        self.beside = {}          # other files to write, by suffix
        header = b''
        seq = None
        unit = None
        texts = []
        for at, n, text in members(data):
            if at < header_end:
                header += text
            elif n == 28 and not text:
                pass
            elif text.startswith(b'#unit\t'):
                texts.append(text)
            else:
                texts[-1] += text
        self.header = [l.split('\t') for l in decoded(header).rstrip('\n').split('\n')]
        for text in texts:
            lines = [l.split('\t') for l in decoded(text).rstrip('\n').split('\n')]
            unit = Unit(lines[0], lines[1:])
            if seq is None or seq.name != unit.head[1]:
                seq = Seq(unit.head[1])
                self.seqs.append(seq)
            if unit.kind == 'table':
                listed = [l[1:6] for l in unit.lines]
                if listed != [u.head[1:6] for u in seq.units]:
                    sys.exit(f'the table of {seq.name} does not list its units')
                seq.table_head = unit.head
                seq = None
            else:
                seq.units.append(unit)
        if [s.name for s in self.seqs] != [c[0] for c in directory[2:] if not c[0].startswith('#')]:
            sys.exit('the directory does not list the sequences in file order')

    def units(self, kind=None):
        return [u for s in self.seqs for u in s.units if kind is None or u.kind == kind]

    def rows(self, kind):
        return [l for u in self.units() for l in u.lines if len(l) > 3 and l[3] == kind]

    def write(self, path):
        bgzf = plain_gzip if self.plain_gzip else globals()['bgzf']
        out = bgzf(encoded(''.join('\t'.join(l) + '\n' for l in self.header)))
        header_length = len(out)
        tables = []
        for seq in self.seqs:
            entries = []
            for unit in seq.units:
                packed = bgzf(unit.text())
                entries.append(['#entry'] + (unit.entry or unit.head[1:6])
                               + [str(len(out)), str(len(packed))] + unit.entry_tags)
                out += packed
            packed = bgzf(Unit(seq.table_head, entries).text())
            tables.append([seq.name, str(len(out)), str(len(packed))] + seq.dir_tags)
            out += packed
        loose = []
        for unit in self.loose:
            packed = bgzf(unit.text())
            loose.append([unit.directory, str(len(out)), str(len(packed))])
            out += packed
        out += EOF
        first = list(self.header[0])
        first.insert(len(first) if self.bytes_at is None else self.bytes_at, f'bytes:i:{len(out)}')
        directory = ([first, ['#header', '0', str(header_length)] + self.dir_header_tags]
                     + tables + loose + self.dir_lines)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, 'wb').write(out)
        open(path + '.idx', 'wb').write(encoded(''.join('\t'.join(l) + '\n' for l in directory)))
        for suffix, text in self.beside.items():
            open(path + suffix, 'w').write(text)


VARIANTS = {}


def variant(name, kind, why):
    def register(edit):
        VARIANTS[name] = (kind, why, edit)
        return edit
    return register


def tag_rows(kind, tag=TAG, at=None):
    def edit(w):
        rows = w.rows(kind)
        for row in rows:
            row.insert(len(row) if at is None else at, tag)
        return len(rows)
    return edit


def tag_header(key):
    def edit(w):
        lines = [l for l in w.header if l[0] == key]
        for line in lines:
            line.append(TAG)
        return len(lines)
    return edit


variant('identity', 'legal', 'the same lines, deflated again')(lambda w: 1)

for _kind in ('ref', 'nodes', 'route', 'walk', 'abridged', 'blocks', 'departure'):
    variant(f'tag-row-{_kind}', 'legal', f'a tag on every {_kind} row')(tag_rows(_kind))


@variant('tag-row-ref-before-SQ', 'legal', 'a tag before SQ:Z:, as tags come in any order')
def _(w):
    rows = [r for r in w.rows('ref') if len(r) > 12 and r[12].startswith('SQ:Z:')]
    for row in rows:
        row.insert(12, TAG)
    return len(rows)


variant('tag-row-walk-lowercase', 'legal', 'a tag named in lower case, letters and digits')(
    tag_rows('walk', 'note:Z:later'))
variant('tag-row-walk-underscore', 'forbidden', 'a tag name with an underscore, not letters and digits')(
    tag_rows('walk', 'my_note:Z:later'))
variant('tag-row-walk-float', 'legal', 'a tag of type f')(
    tag_rows('walk', 'XX:f:0.5'))
variant('col-row-walk-untagged', 'forbidden', 'a column after a walk row\'s fixed ones that is no tag')(
    tag_rows('walk', 'later'))


@variant('tag-walks', 'legal', 'a tag last on the #walks line, which the directory repeats')
def _(w):
    w.header[0].append(TAG)
    return 1


@variant('tag-walks-first', 'legal', 'a tag before format:i:, as the #walks line is tags in any order')
def _(w):
    w.header[0].insert(1, TAG)
    return 1


@variant('tag-walks-bytes-not-last', 'legal', 'bytes:i: before the directory\'s last tag, as the line is tags in any order')
def _(w):
    w.header[0].append(TAG)
    w.bytes_at = len(w.header[0]) - 1
    return 1


for _key in ('#reference', '#haplotype', '#hole'):
    variant(f'tag-{_key[1:]}', 'legal', f'a tag after the stated fields of each {_key} line')(
        tag_header(_key))


@variant('header-new-line', 'legal', 'a header line of an unknown first word, last')
def _(w):
    w.header.append(['#provenance', 'gfa-to-tabix 9.9', 'graph.gfa', 'sha256:00'])
    return 1


@variant('header-new-line-second', 'legal', 'a header line of an unknown first word, before #reference')
def _(w):
    w.header.insert(1, ['#provenance', 'gfa-to-tabix 9.9', 'graph.gfa', 'sha256:00'])
    return 1


@variant('tag-unit-tile', 'forbidden', 'a tag on every tile\'s #unit line')
def _(w):
    units = w.units('tile')
    for unit in units:
        unit.entry = unit.head[1:6]
        unit.head = unit.head + [TAG]
    return len(units)


@variant('tag-unit-table', 'forbidden', 'a tag on every table\'s #unit line')
def _(w):
    for seq in w.seqs:
        seq.table_head = seq.table_head + [TAG]
    return 1


@variant('tag-entry', 'forbidden', 'a tag on every #entry line')
def _(w):
    for unit in w.units():
        unit.entry_tags = [TAG]
    return 1


@variant('dir-new-line', 'legal', 'a directory line starting with # and an unknown word')
def _(w):
    w.dir_lines.append(['#checksum', 'sha256', '00'])
    return 1


@variant('dir-tag-seq-line', 'forbidden', 'a tag on every sequence\'s directory line')
def _(w):
    for seq in w.seqs:
        seq.dir_tags = [TAG]
    return 1


@variant('dir-tag-header-line', 'forbidden', 'a tag on the directory\'s #header line')
def _(w):
    w.dir_header_tags = [TAG]
    return 1


def notes_unit(seq, name='.'):
    end = seq.table_head[3]
    return Unit(['#unit', seq.name, '0', end, 'notes', name],
                [[seq.name, '0', end, 'note', 'a later addition']])


@variant('unit-new-kind-last', 'legal', 'a unit of an unknown kind before each table, listed in it')
def _(w):
    for seq in w.seqs:
        seq.units.append(notes_unit(seq))
    return 1


@variant('unit-new-kind-first', 'legal', 'a unit of an unknown kind first of its sequence\'s')
def _(w):
    for seq in w.seqs:
        seq.units.insert(0, notes_unit(seq))
    return 1


@variant('unit-new-kind-between', 'legal', 'a unit of an unknown kind between a tile and the departure block after it')
def _(w):
    for seq in w.seqs:
        seq.units.insert(1, notes_unit(seq))
    return 1


@variant('unit-new-kind-two-named', 'legal', 'two units of an unknown kind with names of their own')
def _(w):
    for seq in w.seqs:
        seq.units += [notes_unit(seq, 'a'), notes_unit(seq, 'b')]
    return 1


@variant('unit-new-kind-free-rows', 'legal', 'a unit of an unknown kind whose rows are no rows of this format')
def _(w):
    for seq in w.seqs:
        unit = notes_unit(seq)
        unit.lines = [['{"free": "text"}']]
        seq.units.append(unit)
    return 1


@variant('unit-new-kind-no-seq', 'forbidden', 'a unit in no table, after the last one, named by a # line of the '
         'directory: the header, units, tables and EOF block partition the file (C93)')
def _(w):
    unit = Unit(['#unit', '.', '0', '0', 'meta', '.'], [['.', '0', '0', 'meta', 'a later addition']])
    unit.directory = '#meta'
    w.loose.append(unit)
    return 1


def new_row(kind):
    def edit(w):
        units = w.units(kind)
        for unit in units:
            unit.lines.append(unit.head[1:4] + ['note', 'a later addition'])
        return len(units)
    return edit


for _kind in ('tile', 'departures', 'detail', 'blocks'):
    variant(f'row-new-kind-in-{_kind}', 'forbidden', f'a row of an unknown kind in every {_kind} unit (C49, C155)')(
        new_row(_kind))


@variant('format-9', 'forbidden', 'format:i:9: a reader refuses any other format (C49)')
def _(w):
    w.header[0] = [c.replace('format:i:8', 'format:i:9') for c in w.header[0]]
    return 1


@variant('bound-one-departure-block', 'forbidden', 'each sequence\'s records in one block over 0 to |S|, no pyramid (C43, C88)')
def _(w):
    edited = 0
    for seq in w.seqs:
        blocks = [u for u in seq.units if u.kind == 'departures']
        if blocks:
            lines = sorted({tuple(l) for u in blocks for l in u.lines},
                           key=lambda l: (int(l[1]), int(l[2]), l))
            at = seq.units.index(blocks[0])
            seq.units = [u for u in seq.units if u.kind != 'departures']
            seq.units.insert(at, Unit(['#unit', seq.name, '0', seq.table_head[3], 'departures', '.'],
                                      [list(l) for l in lines]))
            edited += 1
    return edited


@variant('bound-unit-order', 'forbidden', 'each sequence\'s units in reverse file order (C32, C33)')
def _(w):
    for seq in w.seqs:
        seq.units.reverse()
    return 1


@variant('bound-sequence-order', 'forbidden', 'the sequences in reverse byte order (C31)')
def _(w):
    w.seqs.reverse()
    return len(w.seqs) > 1


@variant('bound-walk-row-order', 'forbidden', 'each tile\'s walk rows in reverse order (C125)')
def _(w):
    edited = 0
    for unit in w.units('tile') + w.units('detail'):
        at = [i for i, l in enumerate(unit.lines) if l[3] == 'walk']
        rows = [unit.lines[i] for i in at]
        for i, row in zip(at, reversed(rows)):
            unit.lines[i] = row
        edited += len(rows) > 1
    return edited


@variant('bound-row-kind-order', 'forbidden', 'a tile\'s abridged rows, then walk, route, nodes and ref rows (C59)')
def _(w):
    for unit in w.units('tile'):
        order = ['abridged', 'walk', 'route', 'nodes', 'ref']
        unit.lines.sort(key=lambda l: order.index(l[3]))
    return 1


@variant('bound-passes-spelled-out', 'forbidden', 'passes as 1,1,... where every one is 1, not "." (C62)')
def _(w):
    rows = [r for r in w.rows('ref') if r[11] == '.']
    for row in rows:
        row[11] = ','.join('1' for _ in row[9].split(','))
    return len(rows)


@variant('bound-tile-tag-doubled', 'forbidden', 'tile:i: twice the tile size the units were cut at (C12, C43)')
def _(w):
    w.header[0] = [f'tile:i:{2 * int(c[7:])}' if c.startswith('tile:i:') else c for c in w.header[0]]
    return 1


@variant('bound-no-writer-tags', 'unstated', '#walks without revisited, stay, abridge and abridgebytes, which a reader ignores')
def _(w):
    w.header[0] = [c for c in w.header[0]
                   if not c.startswith(('revisited:', 'stay:', 'abridge:', 'abridgebytes:'))]
    return 1


@variant('bound-tile-names-shifted', 'forbidden', 'every tile named 3 more than its start, with the names that point at it (C12, C127)')
def _(w):
    shift = lambda name: str(int(name) + 3)
    for unit in w.units():
        if unit.kind in ('tile', 'blocks'):
            unit.head[5] = shift(unit.head[5])
        elif unit.kind == 'detail':
            cs, d = unit.head[5].split(':')
            unit.head[5] = f'{shift(cs)}:{d}'
        elif unit.kind == 'departures':
            for row in unit.lines:
                if row[14] != '.':
                    row[14] = ','.join(shift(t) for t in row[14].split(','))
    return 1


@variant('bound-no-haplotype-lines', 'forbidden', 'no #haplotype line (C51)')
def _(w):
    kept = [l for l in w.header if l[0] != '#haplotype']
    edited = len(w.header) - len(kept)
    w.header = kept
    return edited


def shift_ids(by):
    def first(field, by):
        tokens = field.split(',')
        tokens[0] = str(int(tokens[0]) + by)
        return ','.join(tokens)

    def edit(w):
        for unit in w.units():
            chained = False
            for row in unit.lines:
                if row[3] == 'ref':
                    row[9] = first(row[9], 2 * by)
                elif row[3] == 'nodes':
                    row[4] = first(row[4], by)
                elif row[3] == 'route' and not chained:
                    at = next(k for k in (4, 5, 6) if row[k] != '.')
                    row[at] = first(row[at], 2 * by)
                    chained = True
                elif row[3] == 'walk':
                    handle, _, k = row[9].partition('@')
                    row[9] = str(int(handle) + 2 * by) + ('@' + k if k else '')
        return 1
    return edit


variant('limit-ids-plus-1000', 'control', 'every node id 1000 higher, another graph\'s file')(shift_ids(1000))
variant('limit-ids-plus-2^31', 'forbidden', 'every node id 2^31 higher (C126)')(shift_ids(2 ** 31))


@variant('gzip-not-bgzf', 'forbidden', 'each unit one plain gzip member, not BGZF members (C29)')
def _(w):
    w.plain_gzip = True
    return 1


@variant('new-file', 'legal', 'a file f.walks.gz.meta beside the two')
def _(w):
    w.beside = {'.meta': 'a later addition\n'}
    return 1


if __name__ == '__main__':
    if sys.argv[1:] == ['--list']:
        print('\n'.join(f'{name}\t{kind}\t{why}' for name, (kind, why, _) in VARIANTS.items()))
        sys.exit(0)
    if sys.argv[1:] == ['--legal']:
        print('\n'.join(name for name, (kind, _, _) in VARIANTS.items() if kind == 'legal'))
        sys.exit(0)
    source, outdir = sys.argv[1], sys.argv[2]
    base = Walks(source)
    for name in sys.argv[3:] or VARIANTS:
        walks = copy.deepcopy(base)
        edited = VARIANTS[name][2](walks)
        if edited:
            walks.write(os.path.join(outdir, name, 'f.walks.gz'))
        print(f'{name}\t{"written" if edited else "n/a"}')
