"""Read-only referee measurement on a format 8 walk file.

For every tile with a blocks unit and every departure record naming it:
- truth: which abridged pieces hold own steps, and how many bp, from the blocks rows
- rule BP: the same from a simulated piece bp on the abridged row
- rule W: which piece to load, from walk and abridged rows' hapOffset alone
- rule U: the own run's bp from tile rows and the record alone, sound
- rule H: rule U plus "missingBp 0 and one ownTile means the run is ownBp"
- bytes: the tile with a bp column, and with a hapEnd column
"""
import re
import sys
import zlib
from collections import Counter

path = sys.argv[1]
ATTACH = int(sys.argv[2]) if len(sys.argv) > 2 else 65536
data = open(path, 'rb')


def gunzip(raw):
    out = []
    while raw:
        d = zlib.decompressobj(31)
        out.append(d.decompress(raw))
        raw = d.unused_data
    return b''.join(out)


def packed(text):
    total = 0
    for k in range(0, len(text), 0xFF00):
        c = zlib.compressobj(9, zlib.DEFLATED, 31)
        total += len(c.compress(text[k:k + 0xFF00])) + len(c.flush())
    return total


def unit(offset, length):
    data.seek(offset)
    return gunzip(data.read(length)).decode()


ITEM = re.compile(r'^(?:(-?\d+)([+-])(\d+)|(\d+))$')


def shape(items):
    parts = [ITEM.match(i) for i in items.split(',')]
    sizes = [int(m.group(3) or m.group(4)) for m in parts]
    runs = [m.group(4) is not None for m in parts]
    return sum(sizes), sizes[0] if runs[0] else 0, sizes[-1] if runs[-1] and len(parts) > 1 else 0


idx = open(path + '.idx').read().splitlines()
fileBytes = int(re.search(r'\tbytes:i:(\d+)', idx[0]).group(1))
seqs = [line.split('\t') for line in idx[2:] if not line.startswith('#')]
n = Counter()
by = {'all': Counter(), 'attach': Counter()}
worst = {'bp': (0, ''), 'end': (0, '')}
tileSets = {k: {} for k in ('named', 'U', 'H', 'V')}
perTile = {}

for seq, toff, tlen in seqs:
    entries = [line.split('\t') for line in unit(int(toff), int(tlen)).splitlines()[1:]]
    tiles = {e[5]: e for e in entries if e[4] == 'tile'}
    bins = [e for e in entries if e[4] == 'departures']
    cache = {}
    for e in entries:
        if e[4] != 'blocks':
            continue
        T = e[5]
        t = tiles[T]
        ttext = unit(int(t[6]), int(t[7]))
        shapes = {}
        for r in unit(int(e[6]), int(e[7])).splitlines()[1:]:
            c = r.split('\t')
            shapes[(c[4], c[5], c[6])] = shape(c[7])
        rows = {}
        withBp = []
        withEnd = []
        for line in ttext.split('\n'):
            c = line.split('\t')
            kind = c[3] if len(c) > 3 else ''
            if kind == 'abridged':
                bp, before, after = shapes[(c[4], c[5], c[7])]
                rows.setdefault(c[4], {})[(int(c[5]), int(c[7]))] = (int(c[6]), bp, before, after, True)
                withBp.append('\t'.join(c[:7] + [str(bp)] + c[7:]))
                withEnd.append('\t'.join(c[:7] + [str(int(c[6]) + bp)] + c[7:]))
                n['abridged rows'] += 1
            else:
                if kind == 'walk':
                    rows.setdefault(c[4], {})[(int(c[5]), int(c[7]))] = (int(c[6]), None, None, None, False)
                withBp.append(line)
                withEnd.append(line)
        base = packed(ttext.encode())
        b1 = packed('\n'.join(withBp).encode())
        b2 = packed('\n'.join(withEnd).encode())
        n['abridged tiles'] += 1
        n['tile bytes on disk'] += int(t[7])
        n['tile bytes repacked'] += base
        n['tile bytes with bp'] += b1
        n['tile bytes with hapEnd'] += b2
        n['blocks bytes on disk'] += int(e[7])
        worst['bp'] = max(worst['bp'], (b1 - base, f'{seq}:{T} {base}->{b1}'))
        worst['end'] = max(worst['end'], (b2 - base, f'{seq}:{T} {base}->{b2}'))
        for p, pieces in rows.items():
            for (frag, k), (hap, bp, before, after, abr) in pieces.items():
                nxt = pieces.get((frag, k + 1))
                if abr and nxt:
                    n['abridged piece with the next piece of its line in its tile'] += 1
                    n['  hapOffset + bp != next hapOffset (BROKEN)'] += hap + bp != nxt[0]
        ts, te = int(t[2]), int(t[3])
        seen = set()
        for b in bins:
            if int(b[2]) >= te or int(b[3]) <= ts:
                continue
            if b[6] not in cache:
                cache[b[6]] = unit(int(b[6]), int(b[7])).splitlines()[1:]
            for line in cache[b[6]]:
                c = line.split('\t')
                own = c[14].split(',') if c[14] != '.' else []
                if T not in own or line in seen or c[4] not in rows:
                    continue
                seen.add(line)
                h0 = int(c[5])
                ownBp = int(c[6])
                missing = int(c[7])
                h1 = h0 + ownBp
                pieces = rows[c[4]]
                if not any(v[4] for v in pieces.values()):
                    continue
                groups = [by['all']] + ([by['attach']] if 0 < ownBp <= ATTACH else [])
                truth = {}
                for key, (hap, bp, before, after, abr) in pieces.items():
                    if abr:
                        ov = min(h1, hap + bp) - max(h0, hap)
                        if ov > 0:
                            truth[key] = ov
                            run = before if hap >= h0 else after
                            for g in groups:
                                g['BP: pieces whose stretch meets the own stretch'] += 1
                                g['BP:   overlap == its one leading or trailing run'] += ov == run
                                g['BP:   overlap != that run (BROKEN)'] += ov != run
                        elif (after > 0 and hap + bp - after == h0) or (before > 0 and hap + before == h1 and hap >= h0):
                            for g in groups:
                                g['BP: a run at the record\'s end the overlap misses (BROKEN)'] += 1
                lead = {key for key, v in pieces.items() if v[4] and h0 <= v[0] < h1}
                below = [(v[0], key) for key, v in pieces.items() if v[0] < h0]
                C = max(below)[1] if below else None
                Cabr = C is not None and pieces[C][4]
                nxt = pieces.get((C[0], C[1] + 1)) if C else None
                picks = set(lead)
                if Cabr and not (nxt and nxt[0] <= h0):
                    picks.add(C)
                und = 0
                wrongH = 0
                undH = 0
                undV = 0
                for g in groups:
                    g['records naming an abridged tile, path abridged there'] += 1
                    g['W: pieces holding own steps the rule does not load (WRONG)'] += len(set(truth) - picks)
                    g['W: pieces loaded that hold no own steps (wasted detail read)'] += len(picks - set(truth))
                    g['W: pieces loaded that hold own steps'] += len(picks & set(truth))
                for key in lead:
                    hap, bp, before, after, _ = pieces[key]
                    for g in groups:
                        g['U: leading piece, run = hapStart + ownBp - hapOffset'] += 1
                        g['U:   wrong (BROKEN)'] += min(h1 - hap, bp) != truth.get(key, 0) or truth.get(key) != before
                if Cabr:
                    hap, bp, before, after, _ = pieces[C]
                    real = truth.get(C, 0)
                    if nxt:
                        for g in groups:
                            g['U: trailing candidate, end known from the next piece in the tile'] += 1
                            g['U:   wrong (BROKEN)'] += max(0, min(nxt[0], h1) - h0) != real
                    else:
                        und = 1
                        easy = missing == 0 and own == [T] and not lead
                        for g in groups:
                            g['U: trailing candidate, end not in the tile (blocks unit needed)'] += 1
                            g['U:   of those, the candidate holds own steps'] += real > 0
                            g['U:   of those, it holds none'] += real == 0
                            g['H: missingBp 0, one ownTile, no leading piece: say ownBp'] += easy
                            g['H:   right'] += easy and real == ownBp
                            g['H:   WRONG (a false size stated)'] += easy and real != ownBp
                            g['H: still needs the blocks unit'] += not easy
                            g['V: the run is ownBp, so the rejoin piece is the line\'s next: sound if the reader holds that row'] += real == ownBp
                            g['V: otherwise the blocks unit is needed'] += real != ownBp
                        undH = 0 if easy else 1
                        undV = 0 if real == ownBp else 1
                        wrongH = 1 if easy and real != ownBp else 0
                if 0 < ownBp <= ATTACH:
                    key = (seq, T)
                    tileSets['named'][key] = int(e[7])
                    if und:
                        tileSets['U'][key] = int(e[7])
                    if undH:
                        tileSets['H'][key] = int(e[7])
                    if undV:
                        tileSets['V'][key] = int(e[7])
                    stat = perTile.setdefault(key, [int(e[7]), 0, 0, 0])
                    stat[1] += 1
                    stat[2] += und
                    stat[3] += undV

print('==', path.split('/')[-1], 'ATTACH', ATTACH, 'file bytes', fileBytes)
for k, v in n.items():
    print(f'{v}\t{k}')
base = n['tile bytes repacked'] or 1
for name, key in (('bp', 'tile bytes with bp'), ('hapEnd', 'tile bytes with hapEnd')):
    d = n[key] - base
    print(f'{name}: +{d} bytes, {100 * d / base:.3f}% of abridged tiles, {100 * d / fileBytes:.5f}% of the file, worst tile {worst["bp" if name == "bp" else "end"]}')
for label, g in by.items():
    print('-- records:', 'every ownBp' if label == 'all' else f'0 < ownBp <= {ATTACH}')
    for k in sorted(g):
        print(f'{g[k]}\t{k}')
print('-- abridged tiles an attach fetch can name (a record within ATTACH whose path is abridged there)')
for label, name in (('named', 'all such tiles'), ('U', 'needing the blocks unit under rule U (tile rows alone)'), ('H', 'needing it under rule U + H'), ('V', 'needing it under rule U + V (the reader also holds the rejoin piece\'s row)')):
    v = tileSets[label]
    print(f'{len(v)}\t{sum(v.values())} blocks bytes, largest {max(v.values()) if v else 0}\t{name}')
print('0\t0 blocks bytes\tneeding it with bp on the abridged row')
print('-- the ten such tiles with the largest blocks units: blocks bytes, attachable records, undetermined under U, under U + V')
for key, stat in sorted(perTile.items(), key=lambda kv: -kv[1][0])[:10]:
    print(f'{key[0]}:{key[1]}\t{stat[0]}\t{stat[1]}\t{stat[2]}\t{stat[3]}')
