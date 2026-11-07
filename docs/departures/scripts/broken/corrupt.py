#!/usr/bin/env python3
# Writes a broken walk file for broken.sh: the data file read as text, each
# OLD replaced by NEW (each OLD must occur once), repacked as a format 7 file
# whose units, tables and directory are right, so only the rows differ. A
# table unit is rebuilt from the repacked units, and the directory from the
# tables, so a corruption of a table or the directory is made by hand.
# Usage: corrupt.py in.walks.gz out.walks.gz OLD NEW [OLD NEW ...]
import gzip
import struct
import sys
import zlib

src, dst, *edits = sys.argv[1:]
text = gzip.open(src, 'rt').read()
for old, new in zip(edits[::2], edits[1::2]):
    if text.count(old) != 1:
        sys.exit(f'corrupt.py: {old!r} occurs {text.count(old)} times, not once')
    text = text.replace(old, new)

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
data, tables, entries, at = bgzf(header.encode()), [], [], 0
header_length = len(data)
for n, unit in enumerate(units):
    seq, lo, hi, kind, name = unit.split('\n')[0].split('\t')[1:6]
    packed = bgzf(unit.encode())
    entries.append(f'#entry\t{seq}\t{lo}\t{hi}\t{kind}\t{name}\t{len(data)}\t{len(packed)}\n')
    data += packed
    last = n + 1 == len(units) or units[n + 1].split('\t')[1] != seq
    if last:
        length = max(int(u.split('\n')[0].split('\t')[3]) for u in units[:n + 1]
                     if u.split('\t')[1] == seq and u.split('\t')[4] == 'tile')
        table = bgzf((f'#unit\t{seq}\t0\t{length}\ttable\t.\n' + ''.join(entries)).encode())
        tables.append(f'{seq}\t{len(data)}\t{len(table)}\n')
        data += table
        entries = []
data += EOF
open(dst, 'wb').write(data)
open(dst + '.idx', 'w').write(f'{walks}\tbytes:i:{len(data)}\n#header\t0\t{header_length}\n' + ''.join(tables))
