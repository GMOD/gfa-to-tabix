#!/usr/bin/env python3
# Writes a broken walk file for broken.sh: the data file read as text, each
# OLD replaced by NEW (each OLD must occur once, or with --all at least
# once, every one replaced), repacked as a walk file whose units, tables
# and directory are right, so only the rows differ. A table unit is rebuilt
# from the repacked units, and the directory from the tables; a corruption
# of those is asked for by name:
# - --table OLD NEW: in the one rebuilt table that holds OLD
# - --idx OLD NEW: in the directory
# - --header N: the directory states `#header 0 N`
# - --append UNIT: a unit's text after the last table, in no table
# - --tag TAG: TAG as a last column on every row and on the #walks line
# - --drop-entry PREFIX: the one rebuilt table line starting with PREFIX left out, its unit kept
# - --prepend-header LINE: LINE before the header's #walks line, which the directory's line 1 still repeats
# - --empty-table SEQ: a table of SEQ with no entry after the last table, which the directory lists
# With no edit, a text is packed as it is.
# Usage: corrupt.py in.walks.gz out.walks.gz [[--all|--table|--idx] OLD NEW | --header N | --append UNIT | --tag TAG | --drop-entry PREFIX | --prepend-header LINE | --empty-table SEQ]...
import gzip
import struct
import sys
import zlib

src, dst, *args = sys.argv[1:]
edits = dict(once=[], all=[], table=[], idx=[])
appended, tags, dropped, prepended, emptied, header_stated = [], [], [], [], [], None
while args:
    kind = args.pop(0)[2:] if args[0] in ('--all', '--table', '--idx', '--header', '--append', '--tag', '--drop-entry',
                                         '--prepend-header', '--empty-table') else 'once'
    if kind == 'append':
        appended.append(args.pop(0))
    elif kind == 'drop-entry':
        dropped.append(args.pop(0))
    elif kind == 'empty-table':
        emptied.append(args.pop(0))
    elif kind == 'prepend-header':
        prepended.append(args.pop(0) + '\n')
    elif kind == 'tag':
        tags.append(args.pop(0))
    elif kind == 'header':
        header_stated = int(args.pop(0))
    else:
        edits[kind].append((args.pop(0), args.pop(0)))


def replaced(text, pairs, every=False):
    for old, new in pairs:
        if text.count(old) != 1 and not (every and text.count(old) > 1):
            sys.exit(f'corrupt.py: {old!r} occurs {text.count(old)} times, not once')
        text = text.replace(old, new)
    return text


text = replaced(replaced(gzip.open(src, 'rt', errors='surrogateescape').read(), edits['once']), edits['all'], True)
for tag in tags:
    text = ''.join(line + '\t' + tag + '\n' if line[0] != '#' or line.startswith('#walks\t') else line + '\n'
                   for line in text.splitlines())
EOF = bytes.fromhex('1f8b08040000000000ff0600424302001b0003000000000000000000')


def bgzf(data):
    out = b''
    for at in range(0, len(data), 65280):
        chunk = data[at:at + 65280]
        body = zlib.compress(chunk, 6)[2:-4]
        block = b'\x1f\x8b\x08\x04\x00\x00\x00\x00\x00\xff\x06\x00BC\x02\x00' + struct.pack('<H', len(body) + 25)
        out += block + body + struct.pack('<II', zlib.crc32(chunk), len(chunk))
    return out


units = []
for line in text.splitlines(keepends=True):
    if line.startswith('#unit\t') or not units:
        units.append(line)
    else:
        units[-1] += line
header, units = units[0], [u for u in units[1:] if u.split('\t')[4] != 'table']
walks = header.split('\n')[0]
data, tables, entries, at = bgzf((''.join(prepended) + header).encode(errors='surrogateescape')), [], [], 0
header_length = len(data)
table_edits = {pair: 0 for pair in edits['table']}
drops = {prefix: 0 for prefix in dropped}
for n, unit in enumerate(units):
    seq, lo, hi, kind, name = unit.split('\n')[0].split('\t')[1:6]
    packed = bgzf(unit.encode(errors='surrogateescape'))
    entries.append(f'#entry\t{seq}\t{lo}\t{hi}\t{kind}\t{name}\t{len(data)}\t{len(packed)}\n')
    data += packed
    last = n + 1 == len(units) or units[n + 1].split('\t')[1] != seq
    if last:
        length = max(int(u.split('\n')[0].split('\t')[3]) for u in units[:n + 1]
                     if u.split('\t')[1] == seq and u.split('\t')[4] == 'tile')
        listing = f'#unit\t{seq}\t0\t{length}\ttable\t.\n' + ''.join(entries)
        for old, new in [pair for pair in table_edits if pair[0] in listing]:
            table_edits[(old, new)] += listing.count(old)
            listing = listing.replace(old, new)
        for prefix in drops:
            kept = [l for l in listing.splitlines(keepends=True) if not l.startswith(prefix)]
            drops[prefix] += listing.count('\n') - ''.join(kept).count('\n')
            listing = ''.join(kept)
        table = bgzf(listing.encode(errors='surrogateescape'))
        tables.append(f'{seq}\t{len(data)}\t{len(table)}\n')
        data += table
        entries = []
for (old, new), n in table_edits.items():
    if n != 1:
        sys.exit(f'corrupt.py: {old!r} occurs {n} times in the tables, not once')
for prefix, n in drops.items():
    if n != 1:
        sys.exit(f'corrupt.py: {prefix!r} starts {n} table lines, not one')
for seq in emptied:
    table = bgzf(f'#unit\t{seq}\t0\t0\ttable\t.\n'.encode(errors='surrogateescape'))
    tables.append(f'{seq}\t{len(data)}\t{len(table)}\n')
    data += table
for unit in appended:
    data += bgzf(unit.encode(errors='surrogateescape'))
data += EOF
stated = header_length if header_stated is None else header_stated
directory = replaced(f'{walks}\tbytes:i:{len(data)}\n#header\t0\t{stated}\n' + ''.join(tables), edits['idx'])
open(dst, 'wb').write(data)
open(dst + '.idx', 'w', errors='surrogateescape').write(directory)
