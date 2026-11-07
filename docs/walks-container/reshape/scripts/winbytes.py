# Bytes a format 7 reader reads per window: the tile and departures units
# overlapping D = window +- 1 kb, as arbA's s7Cand (measure.mjs) selects
# them, over arbA's seeded windows (mulberry32(seed * 1000 + size), 300 per
# size). KB = 1000 bytes, quantile = sorted[int(p * n)], as summarize2.py.
# usage: winbytes.py <dataset> <file.walks.gz> [sizes] [--extra extra.tsv]
import gzip, json, sys, zlib

DATASETS = {
    'mc22': ('GRCh38#0#chr22', (10_510_000, 50_790_000), 22),
    'pggbY': ('GRCh38#0#chrY', (2_781_480, 26_673_214), 24),
    'pggbYall': ('GRCh38#0#chrY', (2_800_000, 56_800_000), 25),
}
CONTEXT = 1000
M32 = 0xFFFFFFFF


def imul(a, b):
    return (a * b) & M32


def mulberry32(a):
    state = [a & M32]

    def rnd():
        state[0] = (state[0] + 0x6D2B79F5) & M32
        a = state[0]
        t = imul(a ^ (a >> 15), 1 | a)
        t = ((t + imul(t ^ (t >> 7), 61 | t)) & M32) ^ t
        return ((t ^ (t >> 14)) & M32) / 4294967296

    return rnd


def windows(dataset, sizes, per=300):
    seq, (lo, hi), seed = DATASETS[dataset]
    out = []
    for size in sizes:
        rnd = mulberry32(seed * 1000 + size)
        for i in range(per):
            s = int(lo + rnd() * (hi - lo - size))
            out.append((size, i, s, s + size))
    return out


def entries(path, seq):
    directory = [l.split('\t') for l in open(path + '.idx').read().strip().split('\n')]
    line = next(c for c in directory if c[0] == seq)
    with open(path, 'rb') as f:
        f.seek(int(line[1]))
        text = gzip.decompress(f.read(int(line[2]))).decode()
    out = []
    for l in text.split('\n'):
        if l.startswith('#entry\t'):
            c = l.split('\t')[1:]
            if c[3] in ('tile', 'departures') and int(c[6]) > 0:
                out.append({'kind': c[3], 'lo': int(c[1]), 'hi': int(c[2]), 'name': c[4], 'off': int(c[5]), 'len': int(c[6])})
    return out


def q(v, p):
    v = sorted(v)
    return v[min(len(v) - 1, int(p * len(v)))] if v else 0


def measure(dataset, es, sizes):
    rows = []
    for size, i, s, e in windows(dataset, sizes):
        d0, d1 = max(0, s - CONTEXT), e + CONTEXT
        hit = [x for x in es if x['lo'] < d1 and x['hi'] > d0]
        rows.append({'size': size, 'i': i, 'start': s,
                     'tile': sum(x['len'] for x in hit if x['kind'] == 'tile'),
                     'departures': sum(x['len'] for x in hit if x['kind'] == 'departures'),
                     'units': len(hit)})
    return rows


def summary(rows):
    out = {}
    for size in sorted({r['size'] for r in rows}):
        b = [(r['tile'] + r['departures']) / 1000 for r in rows if r['size'] == size]
        d = [r['departures'] / 1000 for r in rows if r['size'] == size]
        out[size] = {'med': q(b, .5), 'p90': q(b, .9), 'p99': q(b, .99), 'dep_med': q(d, .5), 'dep_p90': q(d, .9)}
    return out


if __name__ == '__main__':
    dataset, path = sys.argv[1], sys.argv[2]
    sizes = [int(x) for x in (sys.argv[3] if len(sys.argv) > 3 else '1000,65536,1000000').split(',')]
    es = entries(path, DATASETS[dataset][0])
    rows = measure(dataset, es, sizes)
    for r in rows:
        print(json.dumps(r))
    print(json.dumps({'summary': summary(rows), 'file': path}), file=sys.stderr)
