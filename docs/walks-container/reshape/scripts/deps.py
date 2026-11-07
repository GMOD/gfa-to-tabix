# Departure records of a format 7 file, each once: how many, how many with
# 0 own bp, with an end on a node the reference passes more than once, and
# by size of own bp; walk rows with @k or :k; ref rows with a pass list.
# usage: deps.py <file.walks.gz>
import collections, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from r2sim import table, read_unit

path = sys.argv[1]
recs = set()
c = collections.Counter()
for e in table(path):
    if e['kind'] == 'departures':
        recs.update(l for l in read_unit(path, e['off'], e['len']).split('\n') if l and not l.startswith('#'))
    elif e['kind'] in ('tile', 'detail'):
        for l in read_unit(path, e['off'], e['len']).split('\n'):
            f = l.split('\t')
            if len(f) > 4 and f[3] == 'walk':
                c['walk_rows'] += 1
                c['walk_rows_with_copies'] += '@' in f[9] or ':' in f[10]
            elif len(f) > 4 and f[3] == 'abridged':
                c['abridged_rows'] += 1
            elif len(f) > 11 and f[3] == 'ref':
                c['ref_rows'] += 1
                c['ref_rows_with_passes'] += f[11] != '.'
            elif len(f) > 4 and f[3] == 'route':
                c['route_rows'] += 1
for l in recs:
    f = l.split('\t')
    own = int(f[6])
    c['records'] += 1
    c['own0'] += own == 0
    c['revisited_end'] += f[10] != '1' or f[13] != '1'
    c['own_le_1kb'] += own <= 1000
    c['own_gt_64kb'] += own > 65536
print(json.dumps({'file': path, **c}))
