# What a format 7 reader gets for one window: bytes read, the walk and
# abridged rows whose span overlaps D (window +- 1 kb) and their
# haplotypes, and the departure records overlapping D: how many, how many
# with 0 own bp, how many span all of D, and their haplotypes.
# usage: inspect_window.py <file.walks.gz> <seq> <start> <end>
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from r2sim import table, read_unit

path, seq, s, e = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
d0, d1 = max(0, s - 1000), e + 1000
hit = [x for x in table(path) if x['seq'] == seq and x['kind'] in ('tile', 'departures') and x['lo'] < d1 and x['hi'] > d0]
hap = lambda p: '#'.join(p.split('#')[:2])
walk_haps, abr_haps, dep_haps, span_haps = set(), set(), set(), set()
walk_rows = abr_rows = 0
deps = set()
for u in hit:
    for l in read_unit(path, u['off'], u['len']).split('\n'):
        c = l.split('\t')
        if len(c) < 5 or l.startswith('#') or not (int(c[1]) < d1 and int(c[2]) > d0):
            continue
        if c[3] == 'walk':
            walk_rows += 1
            walk_haps.add(hap(c[4]))
        elif c[3] == 'abridged':
            abr_rows += 1
            abr_haps.add(hap(c[4]))
        elif c[3] == 'departure':
            deps.add(l)
own0 = spanning = 0
own_spanning = []
for l in deps:
    c = l.split('\t')
    dep_haps.add(hap(c[4]))
    own0 += c[6] == '0'
    if int(c[1]) <= d0 and int(c[2]) >= d1:
        spanning += 1
        span_haps.add(hap(c[4]))
        own_spanning.append(int(c[6]))
own_spanning.sort()
print(json.dumps({
    'file': path, 'window': f'{seq}:{s}-{e}',
    'bytes': {'tile': sum(u['len'] for u in hit if u['kind'] == 'tile'), 'departures': sum(u['len'] for u in hit if u['kind'] == 'departures')},
    'walk_rows': walk_rows, 'walk_haplotypes': len(walk_haps), 'abridged_rows': abr_rows, 'abridged_haplotypes': len(abr_haps),
    'departure_records': len(deps), 'own0': own0, 'departure_haplotypes': len(dep_haps),
    'records_spanning_D': spanning, 'haplotypes_spanning_D': len(span_haps),
    'haplotypes_shown': len(walk_haps | abr_haps | dep_haps),
    'haplotypes_only_by_record': len(dep_haps - walk_haps - abr_haps),
    'spanning_ownBp_median': own_spanning[len(own_spanning) // 2] if own_spanning else None,
}))
