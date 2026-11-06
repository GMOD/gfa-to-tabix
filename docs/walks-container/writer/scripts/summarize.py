#!/usr/bin/env python3
# Classes local-compare.sh's lines by input set (test GFAs, fuzz graphs, fuzz
# graphs with no 0 bp node): identical; differing only in detail units' names
# (the units the same up to names, and nothing else differing but the table's
# entries and the unit order that follow from the names); or differing
# elsewhere, by the kinds of unit that differ. usage: summarize.py local.tsv
import collections
import json
import re
import sys

by = collections.defaultdict(collections.Counter)
for line in open(sys.argv[1]):
    name, tile, opts, summary, names = line.rstrip('\n').split('\t')
    group = 'nozero' if name.startswith('nozero') else 'fuzz' if name.startswith('fuzz') else 'test GFAs'
    diffs = json.loads(summary)['differences']
    if not diffs:
        by[group]['identical'] += 1
        continue
    kinds = {re.sub(r' unit .*', '', k) for k in diffs} - {'unit order'}
    if kinds <= {'detail', 'table'} and json.loads(names)['same up to names']:
        by[group]['only detail unit names'] += 1
    else:
        by[group]['differ in ' + ', '.join(sorted(kinds - {'table'}))] += 1
for group, counts in by.items():
    print(f'{group}: {sum(counts.values())} builds; ' + '; '.join(f'{k} {v}' for k, v in sorted(counts.items())))
