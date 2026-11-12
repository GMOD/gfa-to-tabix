"""Read-only. What a reader can decide about a departure record's own steps in
an abridged piece from the tile's rows and the record alone, against the
blocks rows as truth.

  rule.py <walks.gz> rules [cost]
  rule.py <walks.gz> windows <seq:start-end>...
"""
import re
import sys
import zlib
from collections import Counter, defaultdict

ATTACH = 65536
CONTEXT = 1000
path = sys.argv[1]
mode = sys.argv[2]
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


def unit(e):
    data.seek(int(e[6]))
    return gunzip(data.read(int(e[7]))).decode()


idx = open(path + '.idx').read().splitlines()
seqs = [line.split('\t') for line in idx[2:] if not line.startswith('#')]
BLOCK = re.compile(r'^(-?\d+)([+-])(\d+)$')


def parse(items):
    kinds = []
    bp = 0
    for item in items.split(','):
        m = BLOCK.match(item)
        if m:
            bp += int(m.group(3))
            kinds.append('b')
        else:
            bp += int(item)
            kinds.append(int(item))
    before = kinds[0] if kinds[0] != 'b' else 0
    after = kinds[-1] if len(kinds) > 1 and kinds[-1] != 'b' else 0
    return bp, before, after


def table(seq):
    data.seek(int(seq[1]))
    text = gunzip(data.read(int(seq[2]))).decode()
    return [line.split('\t') for line in text.splitlines()[1:]]


class Piece:
    __slots__ = ('path', 'frag', 'hap', 'n', 'kind', 'span', 'bp', 'before', 'after', 'detail', 'tile')

    def __init__(self, c):
        self.path = c[4]
        self.frag = int(c[5])
        self.hap = int(c[6])
        self.n = int(c[7])
        self.kind = c[3]
        self.span = (int(c[1]), int(c[2]))
        self.bp = None
        self.before = 0
        self.after = 0
        self.detail = c[9].split('\t')[0] if c[3] == 'abridged' else None
        self.tile = None


def tile_pieces(text):
    out = []
    for line in text.split('\n'):
        c = line.split('\t', 9)
        if len(c) > 8 and c[3] in ('walk', 'abridged'):
            out.append(Piece(c))
    return out


def add_blocks(pieces, btext):
    by = {(p.path, p.frag, p.n): p for p in pieces if p.kind == 'abridged'}
    missing = 0
    for line in btext.splitlines()[1:]:
        r = line.split('\t')
        p = by.get((r[4], int(r[5]), int(r[6])))
        if p is None:
            missing += 1
        else:
            p.bp, p.before, p.after = parse(r[7])
    return missing


def records(lines, names=None):
    out = []
    for line in set(lines):
        c = line.split('\t')
        if len(c) > 14 and c[3] == 'departure' and (names is None or names(c[4])):
            out.append(c)
    return out


def classify(own, T, rjc):
    if len(own) == 2 and own[0] != own[1]:
        return 'T is first of two ownTiles' if own[0] == T else 'T is second of two ownTiles'
    if len(own) == 1:
        return 'one ownTile, a rejoin candidate there' if rjc else 'one ownTile, no rejoin candidate there'
    return 'other ownTiles shape'


def leave_candidate(mine, h0):
    lower = [p for p in mine if p.hap < h0]
    return max(lower, key=lambda p: p.hap) if lower else None


def rules(cost):
    tot = Counter()
    dep = Counter()
    examples = defaultdict(list)
    for seq in seqs:
        entries = table(seq)
        tiles = {e[5]: e for e in entries if e[4] == 'tile'}
        bins = [e for e in entries if e[4] == 'departures']
        cache = {}
        for e in entries:
            if e[4] != 'blocks':
                continue
            T = e[5]
            t = tiles[T]
            ttext = unit(t)
            btext = unit(e)
            pieces = tile_pieces(ttext)
            tot['abridged rows with no blocks row'] += add_blocks(pieces, btext)
            byPath = defaultdict(list)
            byKey = {}
            for p in pieces:
                byPath[p.path].append(p)
                byKey[(p.path, p.frag, p.n)] = p
            for p in pieces:
                if p.kind == 'abridged':
                    tot['abridged pieces'] += 1
                    nxt = byKey.get((p.path, p.frag, p.n + 1))
                    if nxt is not None:
                        tot['  next piece of the line in the same tile'] += 1
                        tot['    its hapOffset != hapOffset + bp (C163 BROKEN)'] += nxt.hap != p.hap + p.bp
                    tot['  leading run on a piece that is not first of its line at fragStart'] += p.before > 0 and not (p.n == 0 and p.hap == p.frag)
            if cost:
                lines = ttext.split('\n')
                plus_bp = []
                plus_end = []
                for line in lines:
                    c = line.split('\t')
                    if len(c) > 9 and c[3] == 'abridged':
                        p = byKey[(c[4], int(c[5]), int(c[7]))]
                        plus_bp.append('\t'.join(c[:9] + [str(p.bp)] + c[9:]))
                        plus_end.append('\t'.join(c[:7] + [str(p.hap + p.bp)] + c[7:]))
                    else:
                        plus_bp.append(line)
                        plus_end.append(line)
                tot['cost: abridged tiles'] += 1
                tot['cost: tile bytes on disk'] += int(t[7])
                base = bgzf_size(ttext.encode())
                tot['cost: tile bytes recompressed'] += base
                a = bgzf_size('\n'.join(plus_bp).encode())
                b = bgzf_size('\n'.join(plus_end).encode())
                tot['cost: with bp column'] += a
                tot['cost: with end column'] += b
                tot['cost: worst tile growth, bp'] = max(tot['cost: worst tile growth, bp'], a - base)
                tot['cost: worst tile growth, end'] = max(tot['cost: worst tile growth, end'], b - base)
            ts, te = int(t[2]), int(t[3])
            lines = []
            for b in bins:
                if int(b[2]) < te and int(b[3]) > ts:
                    if b[6] not in cache:
                        cache[b[6]] = unit(b).splitlines()[1:]
                        if cost:
                            text = '\n'.join(cache[b[6]])
                            grown = '\n'.join(
                                line + ('' if line.endswith('\t.') else '\t' + line.split('\t')[6])
                                for line in cache[b[6]]
                            )
                            tot['cost: departure bins over abridged tiles'] += 1
                            tot['cost: their bytes recompressed'] += bgzf_size(text.encode())
                            tot['cost: with one more number on each record that has ownTiles'] += bgzf_size(grown.encode())
                    lines.append(cache[b[6]])
            seen = set()
            for group in lines:
                for line in group:
                    if line in seen:
                        continue
                    seen.add(line)
                    c = line.split('\t')
                    own = c[14].split(',') if c[14] != '.' else []
                    mine = byPath.get(c[4])
                    if T not in own or not mine or not any(p.kind == 'abridged' for p in mine):
                        continue
                    h0 = int(c[5])
                    ownBp = int(c[6])
                    missingBp = int(c[7])
                    h1 = h0 + ownBp
                    small = ownBp <= ATTACH
                    dep['records naming an abridged tile where their path has an abridged piece'] += 1
                    dep['  of them within ATTACH_BP'] += small
                    leaveHolders = [p for p in mine if p.kind == 'abridged' and p.after > 0 and p.hap + p.bp - p.after == h0]
                    rejoinHolders = [p for p in mine if p.kind == 'abridged' and p.before > 0 and p.hap + p.before == h1]
                    for p in mine:
                        if p.kind == 'abridged':
                            ov = max(0, min(h1, p.hap + p.bp) - max(h0, p.hap))
                            want = (p.after if p in leaveHolders else 0) + (p.before if p in rejoinHolders else 0)
                            dep['interval rule with bp: pieces checked'] += 1
                            dep['interval rule with bp: overlap != own steps there (BROKEN)'] += ov != want
                            dep['interval rule with bp: pieces holding own steps'] += want > 0
                    # the naive pick the for side measured
                    lowerA = [p for p in mine if p.kind == 'abridged' and p.hap < h0]
                    if lowerA:
                        pick = max(lowerA, key=lambda p: p.hap)
                        dep['naive pick (abridged rows only): holds own steps' if pick in leaveHolders else 'naive pick (abridged rows only): holds NONE'] += 1
                    # the rejoin side from the rows alone
                    rjc = [p for p in mine if h0 <= p.hap < h1]
                    dep['rejoin candidates (h0 <= hapOffset < h1)'] += len(rjc)
                    dep['  more than one in a tile (UNEXPECTED)'] += len(rjc) > 1
                    for p in rjc:
                        if p.kind == 'abridged':
                            dep['  abridged'] += 1
                            dep['    leading run != h1 - hapOffset (BROKEN)'] += p.before != h1 - p.hap
                    dep['abridged rejoin holders that are no candidate (MISSED)'] += sum(1 for p in rejoinHolders if p not in rjc)
                    # the leave side from the rows alone
                    cand = leave_candidate(mine, h0)
                    cls = classify(own, T, rjc)
                    dep['leave side: ' + cls] += 1
                    dep['abridged leave holders that are not the candidate (MISSED)'] += sum(1 for p in leaveHolders if p is not cand)
                    if cand is None or cand.kind == 'walk':
                        dep['leave side: ' + cls + ': candidate is a walk row or none'] += 1
                    else:
                        holds = cand in leaveHolders
                        dep['leave side: ' + cls + ': abridged candidate ' + ('holds own steps' if holds else 'holds NONE')] += 1
                        if small:
                            dep['leave side: ' + cls + ': abridged candidate ' + ('holds own steps' if holds else 'holds NONE') + ', within ATTACH_BP'] += 1
                        if cls == 'one ownTile, a rejoin candidate there':
                            lead = sum(h1 - p.hap for p in rjc)
                            rest_bp = ownBp - missingBp - lead
                            dep['ambiguous: ownBp - missingBp - leading ' + ('== 0' if rest_bp == 0 else '> 0') + ': candidate ' + ('holds own steps' if holds else 'holds NONE') + (', within ATTACH_BP' if small else ', over ATTACH_BP')] += 1
                        if not holds and len(examples[cls]) < 3:
                            examples[cls].append((seq[0], T, line[:200], cand.frag, cand.hap, cand.n, cand.bp, cand.after))
                        if holds:
                            nxt = byKey.get((cand.path, cand.frag, cand.n + 1))
                            tag = ' (within ATTACH_BP)' if small else ' (over ATTACH_BP)'
                            dep['trailing bp' + tag + ': holders'] += 1
                            if cand.after == ownBp:
                                dep['trailing bp' + tag + ': == ownBp, provable only with the rejoin piece in the read'] += 1
                            else:
                                dep['trailing bp' + tag + ': != ownBp, in no field of the tile or the record'] += 1
                                dep['trailing bp' + tag + ':   of them == ownBp - missingBp'] += cand.after == ownBp - missingBp
                                dep['trailing bp' + tag + ':   of them missingBp == 0 (rest is on other sequences or lines)'] += missingBp == 0
                                dep['trailing bp' + tag + ':   of them one ownTile and missingBp == 0'] += missingBp == 0 and len(own) == 1
                                if missingBp == 0 and len(own) == 1 and len(examples['same fields, other trailing bp']) < 4:
                                    examples['same fields, other trailing bp'].append((seq[0], T, line[:200], cand.frag, cand.hap, cand.n, cand.bp, cand.after))
                            dep['trailing bp' + tag + ': next piece of the line in this tile'] += nxt is not None
    print('== totals', path.split('/')[-1])
    for k, v in tot.items():
        print(f'{v}\t{k}')
    print('== records')
    for k in sorted(dep):
        print(f'{dep[k]}\t{k}')
    print('== examples')
    for k, v in examples.items():
        for x in v:
            print(k, x)


def merged(units):
    spans = sorted((int(u[6]), int(u[6]) + int(u[7])) for u in units)
    count = 0
    end = -1
    for a, b in spans:
        if a > end:
            count += 1
        end = max(end, b)
    return count


def size(units):
    return sum(int(u[7]) for u in units)


def windows(specs):
    header = unit(['', '', '', '', '', '', '0', idx[1].split('\t')[2]])
    haps = [line.split('\t')[1] for line in header.splitlines() if line.startswith('#haplotype')]
    sets = {
        'every': None,
        'four0': haps[:4],
        'four1': [haps[int((k + 0.5) * len(haps) / 4)] for k in range(4)],
    }
    tables = {}
    for spec in specs:
        m = re.match(r'^(.*):(\d+)-(\d+)$', spec)
        name, s, e = m.group(1), int(m.group(2)), int(m.group(3))
        if name not in tables:
            tables[name] = table(next(q for q in seqs if q[0] == name))
        entries = tables[name]
        d0, d1 = max(0, s - CONTEXT), e + CONTEXT
        tiles = {u[5]: u for u in entries if u[4] == 'tile'}
        blocks = {u[5]: u for u in entries if u[4] == 'blocks'}
        details = {u[5]: u for u in entries if u[4] == 'detail'}
        wtiles = [u for u in tiles.values() if int(u[2]) < d1 and int(u[3]) > d0]
        wbins = [u for u in entries if u[4] == 'departures' and int(u[2]) < d1 and int(u[3]) > d0]
        wnames = {u[5] for u in wtiles}
        text = {}

        def rows(T):
            if T not in text:
                pieces = tile_pieces(unit(tiles[T]))
                for p in pieces:
                    p.tile = T
                if T in blocks:
                    add_blocks(pieces, unit(blocks[T]))
                text[T] = pieces
            return text[T]

        def dunits(keys):
            return [details[k] for k in keys]

        def over(p):
            return p.span[0] < d1 and p.span[1] > d0

        lines = []
        for b in wbins:
            lines.extend(unit(b).splitlines()[1:])
        base = wtiles + wbins
        print(f'{spec}: window tiles {len(wtiles)} {size(wtiles)}; departure bins {len(wbins)} {size(wbins)}; bytesFor today {size(base) + size([blocks[T] for T in wnames if T in blocks])}')
        for label, wanted in sets.items():
            keep = (lambda p: True) if wanted is None else (lambda p, w=tuple(x + '#' for x in wanted): p.startswith(w))
            recs = [c for c in records(lines, keep) if int(c[1]) < d1 and int(c[2]) > d0]
            small = [c for c in recs if int(c[6]) <= ATTACH and c[14] != '.']
            fetch = defaultdict(list)
            for c in small:
                for T in c[14].split(','):
                    if T not in wnames and T in tiles:
                        fetch[T].append(c)
            atiles = [tiles[T] for T in fetch]
            held = {}
            for T in list(wnames) + list(fetch):
                for p in rows(T):
                    if keep(p.path):
                        held[(p.path, p.frag, p.n)] = p

            # what each design decides for record c in tile T, T in its ownTiles
            def decide(c, T, only=None):
                mine = [p for p in rows(T) if p.path == c[4]]
                h0 = int(c[5])
                ownBp = int(c[6])
                h1 = h0 + ownBp
                own = c[14].split(',')
                rjc = [p for p in mine if h0 <= p.hap < h1]
                out = {'rule': [], 'bp': [], 'noend': [], 'spec': 0}
                for p in rjc:
                    if p.kind == 'abridged':
                        out['rule'].append(p)
                        out['bp'].append(p)
                cand = leave_candidate(mine, h0)
                if cand is not None and cand.kind == 'abridged':
                    holds = cand.hap + cand.bp > h0
                    if holds:
                        out['bp'].append(cand)
                    nxt = held.get((cand.path, cand.frag, cand.n + 1))
                    cls = classify(own, T, rjc)
                    if nxt is not None:
                        if nxt.hap > h0:
                            out['rule'].append(cand)
                    elif cls == 'T is second of two ownTiles':
                        pass
                    elif cls == 'one ownTile, a rejoin candidate there':
                        if ownBp - int(c[7]) - sum(h1 - p.hap for p in rjc) > 0:
                            out['rule'].append(cand)
                            out['noend'].append(cand)
                            out['spec'] += not holds
                    else:
                        out['rule'].append(cand)
                        out['noend'].append(cand)
                return out

            # unloaded cut
            wb_all = [blocks[T] for T in wnames if T in blocks and any(p.kind == 'abridged' and keep(p.path) for p in rows(T))]
            wb_drawn = {T for T in wnames if T in blocks and any(p.kind == 'abridged' and keep(p.path) and over(p) for p in rows(T))}
            ab_today = [blocks[T] for T, wanting in fetch.items() if T in blocks and any(p.kind == 'abridged' and p.path in {c[4] for c in wanting} for p in rows(T))]
            rule_blocks = set(wb_drawn)
            noend = 0
            cands = 0
            for c in small:
                for T in c[14].split(','):
                    if T in tiles:
                        got = decide(c, T)
                        cands += len(got['rule'])
                        for p in got['noend']:
                            if p.tile not in wb_drawn:
                                noend += 1
                                rule_blocks.add(p.tile)
            today = size(base) + size(wb_all) + size(atiles) + size(ab_today)
            rule = size(base) + size(atiles) + size([blocks[T] for T in rule_blocks])
            bp = size(base) + size(atiles) + size([blocks[T] for T in wb_drawn])
            print(f'  [{label}] records over D {len(recs)}, within ATTACH_BP with ownTiles {len(small)}; attach tiles {len(atiles)} {size(atiles)}')
            print(f'    unloaded: today {today} ({merged(base)}+{merged(wb_all)}+{merged(atiles)}+{merged(ab_today)} ranges; attach blocks units {len(ab_today)} {size(ab_today)}) | rule {rule} ({noend} of {cands} pieces need a blocks unit for their end, {len(rule_blocks - wb_drawn)} more units) | bp {bp}')

            # expanded cut: every kept abridged piece over D loads
            wp = [p for T in wnames for p in rows(T) if keep(p.path)]
            drawn_details = {p.tile + ':' + p.detail for p in wp if p.kind == 'abridged' and over(p)}
            off = [p for p in wp if p.kind == 'abridged' and p.tile + ':' + p.detail not in drawn_details]
            today_blocks = {p.tile for p in off}
            ex = {'today': set(), 'rule': set(), 'bp': set()}
            spec_reads = 0
            for c in small:
                h0 = int(c[5])
                h1 = h0 + int(c[6])
                for p in off:
                    if p.path == c[4] and ((p.after > 0 and p.hap + p.bp - p.after == h0) or (p.before > 0 and p.hap + p.before == h1)):
                        ex['today'].add(p.tile + ':' + p.detail)
                for T in c[14].split(','):
                    if T in wnames:
                        got = decide(c, T)
                        spec_reads += got['spec']
                        for k in ('rule', 'bp'):
                            for p in got[k]:
                                ex[k].add(p.tile + ':' + p.detail)
            at = {'today': set(), 'rule': set(), 'bp': set()}
            for T, wanting in fetch.items():
                paths = {c[4] for c in wanting}
                for p in rows(T):
                    if p.kind == 'abridged' and p.path in paths:
                        at['today'].add(T + ':' + p.detail)
                for c in wanting:
                    got = decide(c, T)
                    spec_reads += got['spec']
                    for k in ('rule', 'bp'):
                        for p in got[k]:
                            at[k].add(T + ':' + p.detail)
            # runs of consecutive pieces in the window tiles: pieces between two drawn ones, and a last piece whose end no row gives
            lines_by = defaultdict(list)
            for p in wp:
                lines_by[(p.path, p.frag)].append(p)
            middle = set()
            tail_unknown = {'rule': set(), 'bp': set()}
            for group in lines_by.values():
                group.sort(key=lambda p: p.n)
                run = []
                for p in group + [None]:
                    if p is not None and run and p.n == run[-1].n + 1:
                        run.append(p)
                        continue
                    on = [k for k, q in enumerate(run) if over(q)]
                    if on:
                        for q in run[on[0]:on[-1] + 1]:
                            if q.kind == 'abridged':
                                middle.add(q.tile + ':' + q.detail)
                        last = run[-1]
                        if last.kind == 'abridged' and not over(last):
                            for k in ('rule', 'bp'):
                                if last.tile + ':' + last.detail not in drawn_details | middle | ex[k]:
                                    tail_unknown[k].add(last.tile)
                    run = [p] if p is not None else []
            middle -= drawn_details
            dd = size(dunits(drawn_details))
            t = size(base) + dd + size([blocks[T] for T in today_blocks]) + size(dunits(ex['today'] - drawn_details)) + size(atiles) + size(dunits(at['today']))
            r = size(base) + dd + size(dunits((ex['rule'] | middle) - drawn_details)) + size([blocks[T] for T in tail_unknown['rule']]) + size(atiles) + size(dunits(at['rule']))
            b = size(base) + dd + size(dunits((ex['bp'] | middle) - drawn_details)) + size(atiles) + size(dunits(at['bp']))
            print(f'    expanded: today {t} (drawn detail {len(drawn_details)} {dd}; blocks units {len(today_blocks)} {size([blocks[T] for T in today_blocks])}; attach detail {len(at["today"])}) | rule {r} (attach detail {len(at["rule"])}; speculative loads {spec_reads}; blocks units for a run\'s last piece end {len(tail_unknown["rule"])} {size([blocks[T] for T in tail_unknown["rule"]])}) | bp {b} (attach detail {len(at["bp"])}) | pieces between drawn pieces to load, F5: {len(middle)}')


if mode == 'rules':
    rules(len(sys.argv) > 3 and sys.argv[3] == 'cost')
elif mode == 'scan':
    seen = []
    for line in open(sys.argv[3]):
        w = line.split()
        if line.startswith('  ') and w and w[0] not in seen:
            seen.append(w[0])
    windows(seen[:int(sys.argv[4])])
else:
    windows(sys.argv[3:])
