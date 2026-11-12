#!/usr/bin/env python3
# Counts what a walk format 8 file holds, unit by unit from its tables:
# units by kind with their bytes; the repeat-only mechanisms (`@k` and `:k`
# on walk rows, `passes` on ref rows, departure ends passed more than once);
# abridged rows per tile, blocks and detail units against their tiles;
# pieces per line; departure bins by lines and bytes; and the extremes, so
# windows can be cut over them. With --pieces OUT, writes each piece's
# path, fragStart, piece, tile and nsteps, for comparing two builds.
# Usage: stats8.py FILE.walks.gz [--pieces OUT.tsv] > stats.json
import collections
import hashlib
import json
import sys
import zlib

path = sys.argv[1]
pieces_out = sys.argv[sys.argv.index('--pieces') + 1] if '--pieces' in sys.argv else None


def gunzip(data):
    out = []
    while data:
        d = zlib.decompressobj(31)
        out.append(d.decompress(data))
        data = d.unused_data
    return b''.join(out).decode()


def pct(xs, ps=(50, 90, 99, 100)):
    xs = sorted(xs)
    if not xs:
        return {}
    return {f'p{p}': xs[min(len(xs) - 1, (len(xs) * p) // 100)] for p in ps} | {'n': len(xs), 'sum': sum(xs)}


def top(items, k=8):
    return sorted(items, key=lambda x: -x[0])[:k]


idx = open(path + '.idx').read().splitlines()
seqs = [line.split('\t') for line in idx[2:] if not line.startswith('#')]
f = open(path, 'rb')

kinds = collections.Counter()
kind_bytes = collections.Counter()
kind_raw = collections.Counter()
walk_rows = {'tile': 0, 'detail': 0}
walk_start_at = {'tile': 0, 'detail': 0}
walk_choice_rows = {'tile': 0, 'detail': 0}
choice_tokens = {'tile': 0, 'detail': 0}
choice_colon = {'tile': 0, 'detail': 0}
choice_at = {'tile': 0, 'detail': 0}
max_k = 0
ref_steps = 0
ref_steps_revisited = 0
ref_rows_with_passes = 0
max_passes = 0
abridged_per_tile = []
tile_info = {}
detail_info = []
blocks_info = []
bins = []
records = {}
pieces_per_line = collections.Counter()
line_tiles = collections.defaultdict(set)
block_items = collections.Counter()
pieces_rows = []

for seq, off, length in seqs:
    f.seek(int(off))
    table = gunzip(f.read(int(length))).splitlines()
    units = [e.split('\t') for e in table[1:]]
    for e in units:
        _, s, start, end, kind, name, uoff, ulen = e
        start, end, uoff, ulen = int(start), int(end), int(uoff), int(ulen)
        kinds[kind] += 1
        kind_bytes[kind] += ulen
        f.seek(uoff)
        text = gunzip(f.read(ulen))
        kind_raw[kind] += len(text)
        rows = [r.split('\t') for r in text.splitlines()[1:]]
        if kind == 'tile':
            nwalk = nabr = steps = 0
            for r in rows:
                k = r[3]
                if k == 'ref':
                    ref_steps += int(r[8])
                    if r[11] != '.':
                        ref_rows_with_passes += 1
                        ps = [int(x) for x in r[11].split(',')]
                        ref_steps_revisited += sum(1 for p in ps if p > 1)
                        max_passes = max(max_passes, max(ps))
                elif k in ('walk', 'abridged'):
                    pieces_per_line[(r[4], r[5])] = max(pieces_per_line[(r[4], r[5])], int(r[7]) + 1)
                    line_tiles[(r[4], r[5])].add(name)
                    steps += int(r[8])
                    if pieces_out:
                        pieces_rows.append((r[4], r[5], int(r[7]), name, int(r[8]), k))
                    if k == 'abridged':
                        nabr += 1
                    else:
                        nwalk += 1
            tile_info[(seq, name)] = dict(seq=seq, name=name, start=start, end=end, bytes=ulen, raw=len(text),
                                          walk=nwalk, abridged=nabr, steps=steps)
            if nabr:
                abridged_per_tile.append(nabr)
        if kind in ('tile', 'detail'):
            where = 'tile' if kind == 'tile' else 'detail'
            for r in rows:
                if r[3] != 'walk':
                    continue
                walk_rows[where] += 1
                if '@' in r[9]:
                    walk_start_at[where] += 1
                    max_k = max(max_k, int(r[9].split('@')[1]))
                if r[10] != '.':
                    toks = r[10].split(',')
                    choice_tokens[where] += len(toks)
                    named = False
                    for t in toks:
                        if ':' in t:
                            choice_colon[where] += 1
                            named = True
                            max_k = max(max_k, int(t.split(':')[1].split('@')[0]))
                        if '@' in t:
                            choice_at[where] += 1
                            named = True
                            max_k = max(max_k, int(t.split('@')[1]))
                    walk_choice_rows[where] += named
        if kind == 'detail':
            cs = name.split(':')[0]
            detail_info.append(dict(seq=seq, name=name, tile=cs, bytes=ulen, raw=len(text), start=start, end=end,
                                    walk=sum(1 for r in rows if r[3] == 'walk'),
                                    steps=sum(int(r[8]) for r in rows if r[3] == 'walk')))
        if kind == 'blocks':
            nb = nr = neg = minus = 0
            for r in rows:
                for item in r[7].split(','):
                    if item.isdigit():
                        nr += 1
                    else:
                        nb += 1
                        cut = next(i for i in range(1, len(item)) if item[i] in '+-')
                        d = int(item[:cut])
                        neg += d < 0
                        minus += item[cut] == '-'
            block_items['blocks'] += nb
            block_items['runs'] += nr
            block_items['negative d'] += neg
            block_items['against R'] += minus
            blocks_info.append(dict(seq=seq, name=name, start=start, end=end, bytes=ulen, raw=len(text), rows=len(rows),
                                    blocks=nb, runs=nr))
        if kind == 'departures':
            level = 0
            size = end - start
            bins.append(dict(seq=seq, start=start, end=end, size=size, bytes=ulen, raw=len(text), lines=len(rows)))
            for r in rows:
                key = hashlib.blake2b('\t'.join(r).encode(), digest_size=8).digest()
                if key not in records:
                    records[key] = (int(r[10]) > 1, int(r[13]) > 1)

for d in detail_info:
    t = tile_info[(d['seq'], d['tile'])]
    d['tileBytes'] = t['bytes']
    d['ratio'] = round(d['bytes'] / t['bytes'], 3)
for b in blocks_info:
    t = tile_info[(b['seq'], b['name'])]
    b['tileBytes'] = t['bytes']
    b['detailBytes'] = sum(d['bytes'] for d in detail_info if d['seq'] == b['seq'] and d['tile'] == b['name'])
    b['ratioTile'] = round(b['bytes'] / t['bytes'], 3)
    b['ratioDetail'] = round(b['bytes'] / b['detailBytes'], 4)

rec_leave = sum(1 for a, b in records.values() if a)
rec_rejoin = sum(1 for a, b in records.values() if b)
rec_either = sum(1 for a, b in records.values() if a or b)
tiles = list(tile_info.values())
out = dict(
    file=path,
    units=dict(kinds), unitBytes=dict(kind_bytes), unitRawBytes=dict(kind_raw),
    walkRows=walk_rows, walkRowsStartAt=walk_start_at, walkRowsWithChoiceK=walk_choice_rows,
    choiceTokens=choice_tokens, choiceColonK=choice_colon, choiceAtK=choice_at, maxK=max_k,
    refSteps=ref_steps, refStepsRevisited=ref_steps_revisited, refRowsWithPasses=ref_rows_with_passes, maxPasses=max_passes,
    departureRecords=len(records), recordsLeavePassedTwice=rec_leave, recordsRejoinPassedTwice=rec_rejoin,
    recordsEitherEndPassedTwice=rec_either,
    piecesPerLine=pct(list(pieces_per_line.values())),
    tilesPerLine=pct([len(v) for v in line_tiles.values()]),
    abridgedPerTile=pct(abridged_per_tile),
    blockItems=dict(block_items),
    blocksUnitBytes=pct([b['bytes'] for b in blocks_info]),
    blocksOverTile=pct([b['ratioTile'] for b in blocks_info]),
    blocksOverDetail=pct([b['ratioDetail'] for b in blocks_info]),
    detailUnitBytes=pct([d['bytes'] for d in detail_info]),
    detailOverTile=pct([d['ratio'] for d in detail_info]),
    tileBytes=pct([t['bytes'] for t in tiles]),
    tileRawBytes=pct([t['raw'] for t in tiles]),
    binLines=pct([b['lines'] for b in bins]),
    binBytes=pct([b['bytes'] for b in bins]),
    topTilesByBytes=[t for _, t in top([(t['bytes'], t) for t in tiles])],
    topTilesByAbridged=[t for _, t in top([(t['abridged'], t) for t in tiles])],
    topBlocks=[b for _, b in top([(b['bytes'], b) for b in blocks_info])],
    topDetails=[d for _, d in top([(d['bytes'], d) for d in detail_info])],
    topBinsByLines=[b for _, b in top([(b['lines'], b) for b in bins])],
    topBinsByBytesL0=[b for _, b in top([(b['bytes'], b) for b in bins if b['size'] == int(idx[0].split('tile:i:')[1].split('\t')[0])])],
    topLinesByPieces=[(n, k) for n, k in top([(n, '#'.join(k)) for k, n in pieces_per_line.items()])],
)
json.dump(out, sys.stdout, indent=1)
if pieces_out:
    with open(pieces_out, 'w') as w:
        for row in pieces_rows:
            w.write('\t'.join(map(str, row)) + '\n')
