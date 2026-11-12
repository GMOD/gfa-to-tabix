"""Read-only measurement on a format 8 walk file.

- prints a few real lines
- checks the blocks/abridged invariants a small independent reader can check
- costs two candidate columns: piece bp on the abridged row, hapOffset on the blocks row
- tests whether a departure record's own steps in an abridged piece are exact from
  [hapOffset, hapOffset + bp) and [hapStart, hapStart + ownBp), and how often
  the record alone ([hapStart, hapStart + ownBp)) states them
"""
import re
import sys
import zlib
from collections import Counter

ATTACH = int(sys.argv[3]) if len(sys.argv) > 3 else 100000

path = sys.argv[1]
show = len(sys.argv) > 2 and sys.argv[2] == 'show'
data = open(path, 'rb')


def gunzip(raw):
    out = []
    while raw:
        d = zlib.decompressobj(31)
        out.append(d.decompress(raw))
        raw = d.unused_data
    return b''.join(out)


def bgzf_size(text):
    total = 0
    for k in range(0, len(text), 0xFF00):
        c = zlib.compressobj(6, zlib.DEFLATED, 31)
        total += len(c.compress(text[k:k + 0xFF00])) + len(c.flush())
    return total


def unit(offset, length):
    data.seek(offset)
    return gunzip(data.read(length))


idx = open(path + '.idx').read().splitlines()
seqs = [line.split('\t') for line in idx[2:] if not line.startswith('#')]
BLOCK = re.compile(r'^(-?\d+)([+-])(\d+)$')
RUN = re.compile(r'^\d+$')


def parse(items):
    pos = 0
    lo = None
    hi = None
    bp = 0
    bad = 0
    kinds = []
    for item in items.split(','):
        m = BLOCK.match(item)
        if m:
            begin = pos + int(m.group(1))
            n = int(m.group(3))
            a, b = (begin, begin + n) if m.group(2) == '+' else (begin - n, begin)
            pos = b if m.group(2) == '+' else a
            lo = a if lo is None else min(lo, a)
            hi = b if hi is None else max(hi, b)
            bp += n
            kinds.append('b')
        elif RUN.match(item):
            bp += int(item)
            kinds.append(int(item))
        else:
            bad += 1
    before = kinds[0] if kinds and kinds[0] != 'b' else 0
    after = kinds[-1] if len(kinds) > 1 and kinds[-1] != 'b' else 0
    return lo, hi, bp, before, after, bad


tot = Counter()
worst = {'tile': (0, ''), 'blocks': (0, '')}
dep = Counter()
shown = 0
if show:
    print('\n'.join(idx[:4]))
    data.seek(0)
    head = data.read(18)
    print('first bytes', head.hex())
    print(unit(0, int(idx[1].split('\t')[2])).decode()[:400])

for seq, toff, tlen in seqs:
    entries = [line.split('\t') for line in unit(int(toff), int(tlen)).decode().splitlines()[1:]]
    tiles = {e[5]: e for e in entries if e[4] == 'tile'}
    bins = [e for e in entries if e[4] == 'departures']
    tot['tileBytesAll'] += sum(int(e[7]) for e in tiles.values())
    tot['blocksBytesAll'] += sum(int(e[7]) for e in entries if e[4] == 'blocks')
    tot['departureBytesAll'] += sum(int(e[7]) for e in bins)
    tot['detailBytesAll'] += sum(int(e[7]) for e in entries if e[4] == 'detail')
    cache = {}
    for e in entries:
        if e[4] == 'blocks':
            t = tiles[e[5]]
            ttext = unit(int(t[6]), int(t[7]))
            btext = unit(int(e[6]), int(e[7]))
            trows = ttext.decode().split('\n')
            brows = [r.split('\t') for r in btext.decode().splitlines()[1:]]
            byKey = {}
            order = []
            for r in brows:
                lo, hi, bp, before, after, bad = parse(r[7])
                tot['blocksRows'] += 1
                tot['badItem'] += bad
                tot['spanMismatch'] += (lo, hi) != (int(r[1]), int(r[2]))
                byKey[(r[4], r[5], r[6])] = (bp, before, after, int(r[1]), int(r[2]))
                order.append((r[4], r[5], r[6]))
            newt = []
            abr = []
            for line in trows:
                c = line.split('\t')
                if len(c) > 3 and c[3] == 'abridged':
                    k = (c[4], c[5], c[7])
                    tot['abridgedRows'] += 1
                    got = byKey.get(k)
                    if got is None:
                        tot['abridgedWithoutBlocks'] += 1
                        newt.append(line)
                    else:
                        tot['abridgedSpanMismatch'] += (got[3], got[4]) != (int(c[1]), int(c[2]))
                        abr.append((c[4], int(c[5]), int(c[6]), got[0], got[1], got[2]))
                        tot['leading run on a piece other than a line\'s first'] += got[1] > 0 and (c[7] != '0' or c[5] != c[6])
                        tot['after>0'] += got[2] > 0
                        tot['before>0'] += got[1] > 0
                        newt.append('\t'.join(c[:9] + [str(got[0])] + c[9:]))
                else:
                    newt.append(line)
            keysInTile = [(c[4], c[5], c[7]) for c in (l.split('\t') for l in trows) if len(c) > 3 and c[3] == 'abridged']
            tot['unitsOutOfTileOrder'] += keysInTile != order
            hapOf = {(c[4], c[5], c[7]): c[6] for c in (l.split('\t') for l in trows) if len(c) > 3 and c[3] == 'abridged'}
            newb = [btext.decode().split('\n')[0]] + ['\t'.join(r[:6] + [hapOf.get((r[4], r[5], r[6]), '?')] + r[6:]) for r in brows]
            t0 = bgzf_size(ttext)
            t1 = bgzf_size('\n'.join(newt).encode())
            b0 = bgzf_size(btext)
            b1 = bgzf_size(('\n'.join(newb) + '\n').encode())
            tot['abridgedTiles'] += 1
            tot['tileDisk'] += int(t[7])
            tot['tileRe'] += t0
            tot['tileWithBp'] += t1
            tot['blocksDisk'] += int(e[7])
            tot['blocksRe'] += b0
            tot['blocksWithHap'] += b1
            worst['tile'] = max(worst['tile'], (t1 - t0, f'{seq}:{e[5]} {t0}->{t1}'))
            worst['blocks'] = max(worst['blocks'], (b1 - b0, f'{seq}:{e[5]} {b0}->{b1}'))
            if show and shown < 2 and len(brows) > 3:
                shown += 1
                print(f'--- tile {seq} {e[5]}: {int(t[7])} bytes; blocks unit {int(e[7])} bytes, {len(brows)} rows')
                kinds = Counter(l.split('\t')[3] for l in trows if l and not l.startswith('#'))
                print('tile row kinds', dict(kinds))
                seen = Counter()
                for l in trows:
                    c = l.split('\t')
                    k = c[3] if len(c) > 3 else '#'
                    if seen[k] < 2:
                        seen[k] += 1
                        print('  ' + (l[:260] + f' …[{len(l)} chars]' if len(l) > 260 else l))
                for r in btext.decode().splitlines()[:4]:
                    print('  ' + (r[:260] + f' …[{len(r)} chars]' if len(r) > 260 else r))
            # departure records whose ownTiles name this tile
            byPath = {}
            for a in abr:
                byPath.setdefault(a[0], []).append(a)
            T = e[5]
            ts, te = int(t[2]), int(t[3])
            seenRec = set()
            for b in bins:
                if int(b[2]) < te and int(b[3]) > ts:
                    key = b[6]
                    if key not in cache:
                        cache[key] = unit(int(b[6]), int(b[7])).decode().splitlines()[1:]
                    for line in cache[key]:
                        c = line.split('\t')
                        own = c[14].split(',') if c[14] != '.' else []
                        if T in own and line not in seenRec and c[4] in byPath:
                            seenRec.add(line)
                            if show and dep['shownRec'] < 3:
                                dep['shownRec'] += 1
                                print('  ' + line[:260])
                            h0 = int(c[5])
                            h1 = h0 + int(c[6])
                            dep['records naming an abridged tile, path abridged there'] += 1
                            hits = []
                            for (p, frag, hap, bp, before, after) in byPath[c[4]]:
                                s = max(h0, hap)
                                en = min(h1, hap + bp)
                                if en > s:
                                    hits.append((hap, bp, before, after, en - s))
                            if not hits:
                                dep['no abridged piece of the path holds own steps (walk row or none)'] += 1
                            for (hap, bp, before, after, ov) in hits:
                                lead = hap >= h0
                                expect = before if lead else after
                                dep['pieces holding own steps'] += 1
                                dep['  leading run' if lead else '  trailing run'] += 1
                                dep['  overlap == the run (invariant holds)'] += ov == expect
                                dep['  overlap != the run (INVARIANT BROKEN)'] += ov != expect
                                dep['  run == ownBp (record alone is exact)'] += expect == int(c[6])
                                small = int(c[6]) <= ATTACH
                                dep['  of records within ATTACH_BP'] += small
                                dep['  of those, run == ownBp'] += small and expect == int(c[6])
                                dep['  of those, run == ownBp - missingBp and one ownTile'] += small and len(own) == 1 and expect == int(c[6]) - int(c[7])
                                dep['  of those, neither'] += small and expect != int(c[6]) and not (len(own) == 1 and expect == int(c[6]) - int(c[7]))
                                if expect != int(c[6]):
                                    why = ('missingBp>0' if int(c[7]) > 0 else '') + (' twoOwnTiles' if len(own) > 1 else '')
                                    dep['  run != ownBp:' + (why or ' other (steps on another sequence, or in another piece)')] += 1
                            if len(hits) > 1:
                                dep['records with own steps in 2+ abridged pieces of this tile'] += 1
                            lower = [a for a in byPath[c[4]] if a[2] < h0]
                            if lower:
                                pick = max(lower, key=lambda a: a[2])
                                right = any(h[0] == pick[2] and h[0] < h0 for h in hits)
                                dep['by-hapOffset pick holds own steps' if right else 'by-hapOffset pick holds NO own steps (a wasted detail read)'] += 1

print('== totals', path.split('/')[-1])
for k, v in tot.items():
    print(f'{k}\t{v}')
print('worst tile growth', worst['tile'])
print('worst blocks growth', worst['blocks'])
print('== departure records against abridged pieces')
for k, v in dep.items():
    print(f'{v}\t{k}')
