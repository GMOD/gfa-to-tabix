# The reference nodes over a stretch of a format 7 file's sequence, each
# with its length, how many times the reference passes it, and every pass's
# offset on any sequence.
# usage: nodeat.py <file.walks.gz> <seq> <start> <end>
import collections, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from r2sim import table, read_unit
from refscan import tokens

path, seq, s, e = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
here, offsets, info = [], collections.defaultdict(list), {}
for u in table(path):
    if u['kind'] != 'tile':
        continue
    for l in read_unit(path, u['off'], u['len']).split('\n'):
        c = l.split('\t')
        if len(c) > 11 and c[3] == 'ref':
            at = int(c[6])
            lens = [int(x) for x in c[10].split(',')]
            ps = [1] * len(lens) if c[11] == '.' else [int(x) for x in c[11].split(',')]
            for (node, _), n, p in zip(tokens(c[9]), lens, ps):
                offsets[node].append((c[0], at))
                info[node] = (n, p)
                if c[0] == seq and at < e and at + n > s:
                    here.append((at, node))
                at += n
for at, node in sorted(set(here)):
    n, p = info[node]
    o = sorted(offsets[node])
    print(f"{node}\tat {at}\t{n} bp\tpasses {p}\t" + ','.join(f'{x[1]}' for x in o[:10]) + (' ...' if len(o) > 10 else ''))
