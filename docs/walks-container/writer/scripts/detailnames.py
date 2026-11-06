#!/usr/bin/env python3
# Whether two format 7 files hold the same detail units up to their names:
# per sequence and tile, the multiset of (extent, lines) of its detail units.
# Prints how many detail units each holds, how many names differ, and the
# names the second file gives twice. usage: detailnames.py a.walks.gz b.walks.gz
import collections, gzip, hashlib, json, sys


def details(path):
    out, cur = collections.defaultdict(collections.Counter), None
    names = collections.Counter()
    by_name = {}
    def close():
        if cur:
            h = hashlib.sha1('\n'.join(cur[3]).encode()).hexdigest()
            out[cur[0]][(cur[1], h)] += 1
            names[(cur[0], cur[2])] += 1
            by_name[(cur[0], cur[2])] = (cur[1], h)
    with gzip.open(path, 'rt') as f:
        for line in f:
            if line.startswith('#unit\t'):
                close()
                c = line.rstrip('\n').split('\t')
                cur = ((c[1], c[5].split(':')[0]), (c[2], c[3]), c[5], []) if c[4] == 'detail' else None
            elif cur:
                cur[3].append(line.rstrip('\n'))
    close()
    return out, names, by_name


a, na, ba = details(sys.argv[1])
b, nb, bb = details(sys.argv[2])
same = a == b
renamed = sum(1 for k in ba if bb.get(k) != ba[k])
twice = sorted(k for k, n in nb.items() if n > 1)
print(json.dumps({'same up to names': same, 'detail units': [sum(na.values()), sum(nb.values())],
                  'names whose unit differs': renamed, "names the second file gives more than once": len(twice),
                  'examples': twice[:5]}))
