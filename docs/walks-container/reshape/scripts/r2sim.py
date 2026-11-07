# R2, departures as neighbour fields, simulated over a format 7 file.
# Every walk and abridged row gains two columns, prev and next: "." or
# pos:strand:ownBp:missingBp[:ownTiles, where not the leave piece's tile] of the departure record whose rejoin (prev) or
# leave (next) step it holds. A departure record stays in the pyramid, now
# a "gap" unit, only when its extent is not covered by the extents of the
# tiles holding its leave and rejoin pieces, the only case where a window
# can overlap the departure and read neither row. Each rewritten unit's new
# length is its real length plus the difference of the old and new text
# deflated as BGZF (raw deflate level 7, 65,280-byte blocks, 26 bytes per
# member), so the writer's compressor cancels out.
# usage: r2sim.py <dataset> <file.walks.gz> <out-prefix>
import bisect, collections, gzip, json, sys, zlib
from multiprocessing import Pool
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from winbytes import DATASETS, measure, summary

BLOCK = 65280


def bgzf_size(text):
    data = text.encode()
    n = 0
    for k in range(0, max(1, len(data)), BLOCK):
        c = zlib.compressobj(7, zlib.DEFLATED, -15)
        n += len(c.compress(data[k:k + BLOCK]) + c.flush()) + 26
    return n


def read_unit(path, off, length):
    with open(path, 'rb') as f:
        f.seek(off)
        return gzip.decompress(f.read(length)).decode()


def table(path):
    directory = [l.split('\t') for l in open(path + '.idx').read().strip().split('\n')]
    out = []
    for c in directory[2:]:
        for l in read_unit(path, int(c[1]), int(c[2])).split('\n'):
            if l.startswith('#entry\t'):
                e = l.split('\t')[1:]
                out.append({'seq': e[0], 'lo': int(e[1]), 'hi': int(e[2]), 'kind': e[3], 'name': e[4], 'off': int(e[5]), 'len': int(e[6])})
    return out


def scan_tile(args):
    path, e = args
    rows = []
    for l in read_unit(path, e['off'], e['len']).split('\n'):
        c = l.split('\t')
        if len(c) > 8 and c[3] in ('walk', 'abridged'):
            rows.append((c[4], int(c[6]), c[5], c[7]))
    return e['seq'], e['name'], rows


def scan_deps(args):
    path, e = args
    return [l for l in read_unit(path, e['off'], e['len']).split('\n') if l and not l.startswith('#')]


def covered(s, e, a, b):
    (a0, a1), (b0, b1) = sorted([a, b])
    return a0 <= s and e <= max(a1, b1) if b0 <= a1 else (a0 <= s and e <= a1) or (b0 <= s and e <= b1)


def field(pos, strand, own, missing, tiles):
    return f'{pos}:{strand}:{own}:{missing}' + (f':{tiles}' if tiles else '')


def rewrite_tile(args):
    path, e, prevs, nexts = args
    old = read_unit(path, e['off'], e['len'])
    out = []
    for l in old.split('\n'):
        c = l.split('\t')
        if len(c) > 8 and c[3] in ('walk', 'abridged'):
            key = (c[4], c[5], c[6], c[7])
            l = l + '\t' + prevs.get(key, '.') + '\t' + nexts.get(key, '.')
        out.append(l)
    new = '\n'.join(out)
    return e['seq'], e['name'], bgzf_size(new) - bgzf_size(old), len(new) - len(old)


def rewrite_deps(args):
    path, e, keep = args
    old = read_unit(path, e['off'], e['len'])
    lines = old.split('\n')
    kept = [l for l in lines if not l or l.startswith('#') or l in keep]
    has = any(l and not l.startswith('#') for l in kept)
    return e['seq'], e['lo'], e['hi'], (bgzf_size('\n'.join(kept)) - bgzf_size(old)) if has else None


def main():
    dataset, path, prefix = sys.argv[1:4]
    es = table(path)
    tiles = [e for e in es if e['kind'] == 'tile']
    deps = [e for e in es if e['kind'] == 'departures']
    ext = {(e['seq'], e['name']): (e['lo'], e['hi']) for e in tiles}
    with Pool(8) as pool:
        pieces = collections.defaultdict(list)
        for seq, name, rows in pool.imap_unordered(scan_tile, [(path, e) for e in tiles], chunksize=4):
            for p, hap, frag, piece in rows:
                pieces[(seq, p)].append((hap, name, frag, piece))
        for v in pieces.values():
            v.sort()
        records = set()
        for lines in pool.imap_unordered(scan_deps, [(path, e) for e in deps], chunksize=4):
            records.update(lines)
        stats = collections.Counter()
        prevs, nexts, keep = collections.defaultdict(dict), collections.defaultdict(dict), set()
        for l in records:
            c = l.split('\t')
            seq, start, end = c[0], int(c[1]), int(c[2])
            p, hap, own, missing = c[4], int(c[5]), int(c[6]), c[7]
            lpos, lstr, rpos, rstr = c[8], c[9], c[11], c[12]
            v = pieces.get((seq, p), [])
            i = bisect.bisect_left(v, (hap,)) - 1
            j = bisect.bisect_right(v, (hap + own, '￿')) - 1
            stats['records'] += 1
            stats['own0'] += own == 0
            if i < 0 or j < 0:
                stats['unmatched'] += 1
                keep.add(l)
                continue
            leave, rejoin = v[i], v[j]
            stats["rejoin_starts_piece"] += rejoin[0] == hap + own
            stats["same_piece"] += i == j
            own_tiles = c[14] if c[14] not in (".", leave[1]) else ""
            stats["own_tiles_stated"] += own_tiles != ""
            nexts[(seq, leave[1])][(p, leave[2], str(leave[0]), leave[3])] = field(rpos, rstr, own, missing, own_tiles)
            prevs[(seq, rejoin[1])][(p, rejoin[2], str(rejoin[0]), rejoin[3])] = field(lpos, lstr, own, missing, own_tiles)
            if not covered(start, end, ext[(seq, leave[1])], ext[(seq, rejoin[1])]):
                keep.add(l)
                stats['gap'] += 1
        tile_delta = {}
        text_delta = 0
        for seq, name, d, t in pool.imap_unordered(rewrite_tile, [(path, e, prevs[(e['seq'], e['name'])], nexts[(e['seq'], e['name'])]) for e in tiles], chunksize=4):
            tile_delta[(seq, name)] = d
            text_delta += t
        dep_new = {}
        for seq, lo, hi, d in pool.imap_unordered(rewrite_deps, [(path, e, keep) for e in deps], chunksize=4):
            dep_new[(seq, lo, hi)] = d
    new = []
    for e in es:
        e = dict(e)
        if e['kind'] == 'tile':
            e['len'] += tile_delta[(e['seq'], e['name'])]
        elif e['kind'] == 'departures':
            d = dep_new[(e['seq'], e['lo'], e['hi'])]
            if d is None:
                continue
            e['len'] += d
        new.append(e)
    import os
    size = os.path.getsize(path)
    old_parts = {k: sum(e['len'] for e in es if e['kind'] == k) for k in ('tile', 'departures', 'detail')}
    new_parts = {k: sum(e['len'] for e in new if e['kind'] == k) for k in ('tile', 'departures', 'detail')}
    seq = DATASETS[dataset][0]
    rows = measure(dataset, [e for e in new if e['seq'] == seq and e['kind'] in ('tile', 'departures')], [1000, 65536, 1000000])
    with open(prefix + '.jsonl', 'w') as f:
        for r in rows:
            f.write(json.dumps(r) + '\n')
    result = {'file': path, 'bytes_old': size, 'bytes_new': size + sum(new_parts.values()) - sum(old_parts.values()),
              'parts_old': old_parts, 'parts_new': new_parts, 'gap_units': sum(1 for e in new if e['kind'] == 'departures'),
              'dep_units_old': len(deps), 'tile_text_added': text_delta, 'stats': stats, 'summary': summary(rows)}
    json.dump(result, open(prefix + '.json', 'w'), indent=1)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
