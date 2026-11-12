"""Bytes of each candidate column on the abridged rows of a format 8 file,
simulated from its blocks rows and re-compressed as BGZF blocks at level 6:
bp (the piece's bp on its contig), end (hapOffset + bp), and trail (the bp
off R after its last block, with lead before its first). Read-only.
Usage: alt-bytes.py F.walks.gz"""
import re
import sys
import zlib

path = sys.argv[1]
data = open(path, 'rb')


def gunzip(raw):
    out = []
    while raw:
        d = zlib.decompressobj(31)
        out.append(d.decompress(raw))
        raw = d.unused_data
    return b''.join(out)


def size(text):
    total = 0
    for k in range(0, len(text), 0xFF00):
        c = zlib.compressobj(6, zlib.DEFLATED, 31)
        total += len(c.compress(text[k:k + 0xFF00])) + len(c.flush())
    return total


def unit(offset, length):
    data.seek(offset)
    return gunzip(data.read(length))


def parse(items):
    items = items.split(',')
    n = [int(re.split(r'[+-]', i)[-1]) for i in items]
    run = [i.isdigit() for i in items]
    return sum(n), n[0] if run[0] else 0, n[-1] if len(n) > 1 and run[-1] else 0


idx = open(path + '.idx').read().splitlines()
tot = dict(tiles=0, rows=0, now=0, bp=0, end=0, trail=0, allTiles=0)
worst = dict(bp=(0, ''), end=(0, ''), trail=(0, ''))
for line in idx[2:]:
    if line.startswith('#'):
        continue
    seq, toff, tlen = line.rsplit('\t', 2)
    entries = [l.split('\t') for l in unit(int(toff), int(tlen)).decode().splitlines()[1:]]
    tiles = {e[5]: e for e in entries if e[4] == 'tile'}
    tot['allTiles'] += sum(int(e[7]) for e in tiles.values())
    for e in entries:
        if e[4] == 'blocks':
            t = tiles[e[5]]
            text = unit(int(t[6]), int(t[7])).decode()
            by = {}
            for r in unit(int(e[6]), int(e[7])).decode().splitlines()[1:]:
                c = r.split('\t')
                by[(c[4], c[5], c[6])] = parse(c[7])
            out = dict(bp=[], end=[], trail=[])
            for l in text.split('\n'):
                c = l.split('\t')
                if len(c) > 3 and c[3] == 'abridged':
                    bp, lead, trail = by[(c[4], c[5], c[7])]
                    tot['rows'] += 1
                    out['bp'].append('\t'.join(c[:9] + [str(bp)] + c[9:]))
                    out['end'].append('\t'.join(c[:7] + [str(int(c[6]) + bp)] + c[7:]))
                    out['trail'].append('\t'.join(c[:9] + [str(lead), str(trail)] + c[9:]))
                else:
                    for v in out.values():
                        v.append(l)
            now = size(text.encode())
            tot['tiles'] += 1
            tot['now'] += now
            for k, v in out.items():
                s = size('\n'.join(v).encode())
                tot[k] += s
                worst[k] = max(worst[k], (s - now, f'{seq}:{e[5]} {now}->{s}'))
print(path.split('/')[-1], tot)
for k in ('bp', 'end', 'trail'):
    d = tot[k] - tot['now']
    print(f'{k}\t+{d} B\t+{100 * d / tot["now"]:.2f}% of abridged tiles\t+{100 * d / tot["allTiles"]:.4f}% of all tiles\t{d / tot["rows"]:.2f} B/row\tworst {worst[k]}')
