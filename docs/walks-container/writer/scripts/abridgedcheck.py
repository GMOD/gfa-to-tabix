#!/usr/bin/env python3
# Whether each abridged row's detail unit, `cs:d` by its tile and detail
# number, holds walk rows of the row's path (and fragStart), in a format 7
# file. usage: abridgedcheck.py f.walks.gz
import collections, gzip, json, sys

want = collections.defaultdict(set)
held = collections.defaultdict(set)
unit = None
with gzip.open(sys.argv[1], 'rt') as f:
    for line in f:
        if line.startswith('#unit\t'):
            c = line.rstrip('\n').split('\t')
            unit = (c[1], c[4], c[5])
            continue
        if line[0] == '#' or unit is None:
            continue
        c = line.rstrip('\n').split('\t')
        if unit[1] == 'tile' and c[3] == 'abridged':
            want[(unit[0], f'{unit[2]}:{c[12]}')].add((c[4], c[5]))
        elif unit[1] == 'detail' and c[3] == 'walk':
            held[(unit[0], unit[2])].add((c[4], c[5]))
wrong = [k for k, paths in want.items() if paths != held.get(k)]
print(json.dumps({'file': sys.argv[1], 'detail numbers named by abridged rows': len(want),
                  'whose unit holds other paths or none': len(wrong), 'examples': wrong[:3]}))
