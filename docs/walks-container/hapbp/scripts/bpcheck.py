"""Checks the proposed `bp` column and the own-step invariant against the GFA.

Truth comes from the GFA alone: each W or P line's steps and their offsets on
their contig. From the walk file it takes only columns format 8 already has
(path, fragStart, hapOffset, nsteps of walk, ref and abridged rows; a
record's path, hapStart, ownBp, ownTiles), the blocks rows, and the `bp`
column where the file has one (--bp).

- every piece row starts on a step boundary of its line and its nsteps steps
  give its true stretch on the contig
- an abridged piece's blocks items sum to that stretch (the simulated column),
  and the `bp` column, where present, equals it
- for every departure record: the steps strictly between the step ending at
  hapStart and the one starting at hapStart+ownBp are its own steps; in each
  piece of its path filed on S, the own steps are exactly the steps inside
  [hapStart, hapStart+ownBp) ∩ [hapOffset, hapOffset+bp); the tiles of the
  pieces holding any are the record's ownTiles; and in an abridged piece they
  are its trailing or leading run off R
- how the reader-only rules do: the record alone, and the pick by hapOffset

Usage: bpcheck.py G.gfa F.walks.gz [--bp]
Exit 1 on any failure.
"""
import bisect
import collections
import re
import sys
sys.path.insert(0, __file__.rsplit('/', 1)[0])
import wf

gfa, walks = sys.argv[1], sys.argv[2]
has_bp = '--bp' in sys.argv[3:]
fail = collections.Counter()
seen = collections.Counter()


def bad(what, detail):
    fail[what] += 1
    if fail[what] <= 3:
        print(f'FAIL {what}: {detail}')


lengths = {}
lines = collections.defaultdict(dict)


def p_name(name):
    m = re.fullmatch(r'(.*)\[(\d+)(-\d+)?\]', name)
    if m:
        return m.group(1), int(m.group(2))
    m = re.fullmatch(r'(.*):(\d+)-(\d+)', name)
    if m:
        return m.group(1), int(m.group(2))
    if name.count('#') == 3:
        head, start = name.rsplit('#', 1)
        if start.isdigit():
            return head, int(start)
    return name, 0


raw = [l.rstrip('\n').split('\t') for l in open(gfa)]
for c in raw:
    if c[0] == 'S':
        ln = [t for t in c[3:] if t.startswith('LN:i:')]
        lengths[c[1]] = int(ln[0][5:]) if c[2] == '*' and ln else len(c[2]) if c[2] != '*' else 0
for c in raw:
    steps = None
    if c[0] == 'W':
        name, start = f'{c[1]}#{c[2]}#{c[3]}', int(c[4])
        steps = re.findall(r'[<>]([^<>]+)', c[6])
    elif c[0] == 'P':
        name, start = p_name(c[1])
        steps = [s[:-1] for s in c[2].split(',')] if c[2] not in ('', '*') else []
    if steps is not None:
        steps = [s for s in steps if lengths[s] > 0]
        if steps:
            offs = [start]
            for s in steps:
                offs.append(offs[-1] + lengths[s])
            lines[name][start] = offs

# every step of a contig, in order: (start, end, fragStart, index)
contig = {}
for name, frags in lines.items():
    contig[name] = sorted((offs[i], offs[i + 1], frag, i) for frag, offs in frags.items() for i in range(len(offs) - 1))


def parse_list(items):
    kinds = []
    for item in items.split(','):
        m = re.fullmatch(r'-?\d+[+-](\d+)', item)
        kinds.append(('b', int(m.group(1))) if m else ('r', int(item)))
    before = kinds[0][1] if kinds[0][0] == 'r' else 0
    after = kinds[-1][1] if len(kinds) > 1 and kinds[-1][0] == 'r' else 0
    return sum(n for _, n in kinds), before, after


pieces = collections.defaultdict(list)   # (seq, path) -> pieces
blocks = {}
records = collections.OrderedDict()
tile_of = {}
for seq, start, end, kind, name, rows in wf.units(walks):
    for row in rows[1:]:
        c = row.split('\t')
        if kind == 'tile' and c[3] in ('walk', 'abridged'):
            off = lines.get(c[4], {}).get(int(c[5]))
            if off is None:
                bad('piece of no GFA line', row)
                continue
            at = bisect.bisect_left(off, int(c[6]))
            n = int(c[8])
            if at >= len(off) or off[at] != int(c[6]) or at + n >= len(off):
                bad('piece not on a step boundary of its line', row)
                continue
            p = dict(seq=c[0], tile=name, path=c[4], frag=int(c[5]), hap=int(c[6]), piece=int(c[7]),
                     first=at, n=n, bp=off[at + n] - off[at], kind=c[3],
                     col=int(c[9]) if has_bp and c[3] == 'abridged' else None)
            seen[c[3] + ' rows'] += 1
            if p['col'] is not None and p['col'] != p['bp']:
                bad('bp column is not the piece\'s bp on its contig', f'{row} (true {p["bp"]})')
            pieces[(c[0], c[4])].append(p)
        elif kind == 'blocks':
            blocks[(c[0], name, c[4], int(c[5]), int(c[6]))] = parse_list(c[7])
        elif kind == 'departures':
            records[row] = c

for ps in pieces.values():
    for p in ps:
        if p['kind'] == 'abridged':
            b = blocks.get((p['seq'], p['tile'], p['path'], p['frag'], p['piece']))
            if b is None:
                bad('abridged row with no blocks row', str(p))
            else:
                p['before'], p['after'] = b[1], b[2]
                if b[0] != p['bp']:
                    bad('blocks items do not sum to the piece\'s bp', f'{p} sum {b[0]}')

for row, c in records.items():
    seq, path, hs, own, missing = c[0], c[4], int(c[5]), int(c[6]), int(c[7])
    own_tiles = [] if c[14] == '.' else c[14].split(',')
    seen['records'] += 1
    steps = contig.get(path)
    if steps is None:
        bad('record of no GFA contig', row)
        continue
    starts = [s[0] for s in steps]
    ends = [s[1] for s in steps]
    leave = bisect.bisect_left(ends, hs)
    rejoin = bisect.bisect_left(starts, hs + own)
    if leave >= len(steps) or ends[leave] != hs or rejoin >= len(steps) or starts[rejoin] != hs + own:
        bad('record ends are not step boundaries', row)
        continue
    truth = {(s[2], s[3]) for s in steps[leave + 1:rejoin]}
    if own - missing != sum(s[1] - s[0] for s in steps[leave + 1:rejoin]):
        bad('ownBp - missingBp is not the own steps\' bp', row)
    holders = []
    for p in pieces.get((seq, path), []):
        mine = [(p['frag'], i) for i in range(p['first'], p['first'] + p['n']) if (p['frag'], i) in truth]
        true_bp = sum(lines[path][f][i + 1] - lines[path][f][i] for f, i in mine)
        lo, hi = max(hs, p['hap']), min(hs + own, p['hap'] + p['bp'])
        rule = max(0, hi - lo)
        if rule != true_bp:
            bad('overlap is not the piece\'s own steps', f'{row} piece {p} rule {rule} truth {true_bp}')
        if true_bp:
            holders.append(p)
            seen['pieces holding own steps'] += 1
            seen['  ' + p['kind']] += 1
            if p['kind'] == 'abridged' and 'before' in p:
                lead = p['hap'] >= hs
                seen['  abridged, leading run' if lead else '  abridged, trailing run'] += 1
                if rule != (p['before'] if lead else p['after']):
                    bad('own steps are not the piece\'s whole run off R at that end', f'{row} {p}')
                seen['    record alone exact (run == ownBp)'] += rule == own
                seen['    run == ownBp - missingBp'] += rule == own - missing
                seen['    neither'] += rule != own and rule != own - missing
    if sorted({p['tile'] for p in holders}) != sorted(own_tiles):
        bad('tiles of the pieces holding own steps are not ownTiles', f'{row} holders {[ (p["tile"], p["hap"]) for p in holders]}')
    if len(holders) > 1:
        seen['records with own steps in two pieces'] += 1
    # the reader-only pick: in each own tile, the abridged piece of the path with the highest hapOffset below hapStart
    for t in own_tiles:
        here = [p for p in pieces.get((seq, path), []) if p['tile'] == t and p['kind'] == 'abridged' and p['hap'] < hs]
        if here:
            pick = max(here, key=lambda p: p['hap'])
            seen['by-hapOffset pick: holds own steps' if pick in holders else 'by-hapOffset pick: holds NO own steps'] += 1

for k, v in seen.items():
    print(f'{v}\t{k}')
print('FAILED ' + ', '.join(f'{k} x{v}' for k, v in fail.items()) if fail else 'ok')
sys.exit(1 if fail else 0)
