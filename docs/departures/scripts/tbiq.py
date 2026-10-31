# Requests and bytes a 64 kb window costs on one sequence of a .tbi, by the
# Tabix bin and linear index rules (blind-2's tbiread.py with named sequences)
import gzip, struct, sys
def load(path):
    d = gzip.open(path).read(); o = 4
    n_ref, fmt, cs, cb, ce, meta, skip, l_nm = struct.unpack_from('<8i', d, o); o += 32
    names = d[o:o + l_nm].split(b'\0')[:-1]; o += l_nm
    refs = {}
    for k in range(n_ref):
        (n_bin,) = struct.unpack_from('<i', d, o); o += 4
        bins = {}
        for _ in range(n_bin):
            b, nc = struct.unpack_from('<Ii', d, o); o += 8
            bins[b] = [struct.unpack_from('<QQ', d, o + 16 * j) for j in range(nc)]; o += 16 * nc
        (n_intv,) = struct.unpack_from('<i', d, o); o += 4
        lin = list(struct.unpack_from(f'<{n_intv}Q', d, o)); o += 8 * n_intv
        refs[names[k].decode()] = (bins, lin)
    return refs
def reg2bins(beg, end):
    end -= 1; out = [0]
    for shift, off in [(26, 1), (23, 9), (20, 73), (17, 585), (14, 4681)]:
        out += range(off + (beg >> shift), off + (end >> shift) + 1)
    return out
def query(ref, beg, end):
    bins, lin = ref
    i = beg >> 14
    min_off = lin[i] if i < len(lin) else (lin[-1] if lin else 0)
    chunks = sorted(c for b in reg2bins(beg, end) for c in bins.get(b, []) if c[1] > min_off)
    merged = []
    for a, b in chunks:
        if merged and (a >> 16) <= (merged[-1][1] >> 16) + 65536: merged[-1][1] = max(merged[-1][1], b)
        else: merged.append([a, b])
    return len(merged), sum((b >> 16) - (a >> 16) + 65536 for a, b in merged)
path, seq, length, win = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
refs = load(path + '.tbi')
q = lambda v, p: v[min(len(v) - 1, int(p * len(v)))]
for name in [seq, seq + '~departure']:
    if name not in refs: print(name, 'absent'); continue
    res = [query(refs[name], w, w + win) for w in range(0, length, win)]
    req = sorted(r[0] for r in res); by = sorted(r[1] for r in res)
    print(f'{name}: requests median {q(req,.5)} p95 {q(req,.95)} max {req[-1]}; bytes median {q(by,.5)} p95 {q(by,.95)} max {by[-1]} total {sum(by)}')
