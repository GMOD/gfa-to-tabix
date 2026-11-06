# KB of graph-walks 6's first read and of the read with attach fetches,
# median/p90/p99 as arbiter A's summarize2.py takes them (sorted[int(p * n)]),
# median and most requests, and the most round trips, per dataset and size.
# usage: python3 summarize7.py <measure7 out.jsonl>...
import json, sys
from statistics import median

def q(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(p * len(xs)))]

for path in sys.argv[1:]:
    rows = [json.loads(l) for l in open(path)]
    print(path, rows[0])
    for size in sorted({r['size'] for r in rows[1:]}):
        rs = [r for r in rows[1:] if r['size'] == size]
        ok = [r for r in rs if 'total' in r]
        read = [r['read']['bytes'] / 1000 for r in rs]
        total = [r['total']['bytes'] / 1000 for r in ok]
        req = [r['total']['requests'] for r in ok]
        print(f"  {size:>8} n={len(rs)} errors={len(rs) - len(ok)}"
              f" read KB {q(read, .5):.0f}/{q(read, .9):.0f}/{q(read, .99):.0f}"
              f" with attach KB {q(total, .5):.0f}/{q(total, .9):.0f}/{q(total, .99):.0f}"
              f" requests first read {q([r['read']['requests'] for r in rs], .5)}"
              f" with attach {q(req, .5)}/{max(req)}"
              f" trips max {max(r['total']['trips'] for r in ok)}")
