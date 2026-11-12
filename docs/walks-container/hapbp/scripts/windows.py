"""Read-only: what an every-haplotype 1 kb cut's attach fetches must read of blocks units.

Windows sit mid-tile in the tile before, at and after each of the N tiles with
the largest blocks units. For each attached record and attach tile:
- today: the tile's blocks unit, where the record's path is abridged there
- sound reader rule: none where the piece's end is the hapOffset of the line's
  next piece in a tile this cut read, or the piece starts in the own stretch
- with bp on the abridged row: none
"""
import sys
import zlib
from collections import Counter

path = sys.argv[1]
N = int(sys.argv[2]) if len(sys.argv) > 2 else 30
ATTACH = 65536
CONTEXT = int(sys.argv[5]) if len(sys.argv) > 5 else 1000
WIDTH = int(sys.argv[4]) if len(sys.argv) > 4 else 1000
TILE = int(sys.argv[3]) if len(sys.argv) > 3 else 65536
data = open(path, 'rb')


def unit(offset, length):
    data.seek(offset)
    raw = data.read(length)
    out = []
    while raw:
        d = zlib.decompressobj(31)
        out.append(d.decompress(raw))
        raw = d.unused_data
    return b''.join(out).decode()


idx = open(path + '.idx').read().splitlines()
tables = {}
for seq, toff, tlen in (line.split('\t') for line in idx[2:] if not line.startswith('#')):
    tables[seq] = [line.split('\t') for line in unit(int(toff), int(tlen)).splitlines()[1:]]
biggest = sorted(((int(e[7]), seq, int(e[5])) for seq, es in tables.items() for e in es if e[4] == 'blocks'), reverse=True)[:N]
tileCache = {}


def tileRows(seq, e):
    key = (seq, e[5])
    if key not in tileCache:
        rows = {}
        for line in unit(int(e[6]), int(e[7])).split('\n'):
            c = line.split('\t')
            if len(c) > 7 and c[3] in ('walk', 'abridged'):
                rows.setdefault(c[4], {})[(int(c[5]), int(c[7]))] = (int(c[6]), c[3] == 'abridged')
        tileCache[key] = rows
    return tileCache[key]


tot = Counter()
worst = {'today': (0, ''), 'sound': (0, '')}
print('window\twindow tiles\tattached records\tattach tiles\tattach tile bytes\tblocks bytes today\tblocks bytes sound rule\trecords the sound rule leaves\tblocks bytes with bp')
for size, seq, T in biggest:
    es = tables[seq]
    tiles = {int(e[5]): e for e in es if e[4] == 'tile'}
    blocks = {int(e[5]): int(e[7]) for e in es if e[4] == 'blocks'}
    for s in (at + off for at in (T - TILE, T, T + TILE) for off in (0, TILE // 2)):
        d0, d1 = max(0, s - CONTEXT), s + WIDTH + CONTEXT
        win = {int(e[5]): e for e in es if e[4] == 'tile' and int(e[2]) < d1 and int(e[3]) > d0}
        if not win:
            continue
        held = {}
        for name, e in win.items():
            for p, pieces in tileRows(seq, e).items():
                held.setdefault(p, {}).update(pieces)
        recs = set()
        for e in es:
            if e[4] == 'departures' and int(e[2]) < d1 and int(e[3]) > d0:
                for line in unit(int(e[6]), int(e[7])).splitlines()[1:]:
                    c = line.split('\t')
                    if int(c[1]) < d1 and int(c[2]) > d0 and 0 < int(c[6]) <= ATTACH and c[14] != '.':
                        recs.add(line)
        attached = []
        attachTiles = set()
        for line in recs:
            c = line.split('\t')
            own = [int(x) for x in c[14].split(',')]
            away = [x for x in own if x not in win and x in tiles]
            if away:
                attached.append((c[4], int(c[5]), int(c[6]), away))
                attachTiles.update(away)
        for x in attachTiles:
            for p, pieces in tileRows(seq, tiles[x]).items():
                if any(a[0] == p for a in attached):
                    held.setdefault(p, {}).update(pieces)
        today = set()
        sound = set()
        left = 0
        for p, h0, ownBp, away in attached:
            h1 = h0 + ownBp
            for x in away:
                pieces = tileRows(seq, tiles[x]).get(p, {})
                if any(v[1] for v in pieces.values()):
                    today.add(x)
                below = [(v[0], k) for k, v in pieces.items() if v[0] < h0]
                if below:
                    C = max(below)[1]
                    if pieces[C][1] and (C[0], C[1] + 1) not in held.get(p, {}):
                        sound.add(x)
                        left += 1
        tb = sum(int(tiles[x][7]) for x in attachTiles)
        b0 = sum(blocks.get(x, 0) for x in today)
        b1 = sum(blocks.get(x, 0) for x in sound)
        label = f'{seq}:{s}-{s + WIDTH}'
        print(f'{label}\t{len(win)}\t{len(attached)}\t{len(attachTiles)}\t{tb}\t{b0}\t{b1}\t{left}\t0')
        tot['windows'] += 1
        tot['windows whose attach fetches read a blocks unit today'] += b0 > 0
        tot['windows whose attach fetches read one under the sound rule'] += b1 > 0
        tot['attach tile bytes'] += tb
        tot['attach blocks bytes today'] += b0
        tot['attach blocks bytes under the sound rule'] += b1
        tot['attached records'] += len(attached)
        tot['records the sound rule leaves to a blocks unit'] += left
        worst['today'] = max(worst['today'], (b0, label))
        worst['sound'] = max(worst['sound'], (b1, label))
print('==', path.split('/')[-1])
for k, v in tot.items():
    print(f'{v}\t{k}')
print('worst window today', worst['today'])
print('worst window under the sound rule', worst['sound'])
