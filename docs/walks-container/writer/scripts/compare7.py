#!/usr/bin/env python3
# Compares two walk format 7 files unit by unit: the header, every unit's
# `#unit` line and lines (a departures unit's as a set), each table's entries
# without offsets and lengths, the directory's sequences, and the unit order.
# Units are keyed by sequence, kind and name, or for a departure block its
# start and end. Holds a hash per unit, then reads back the units that differ to
# show up to --show of each kind of difference. Prints a JSON summary last.
# usage: compare7.py writer.walks.gz converter.walks.gz [--show 5]
import argparse
import collections
import gzip
import hashlib
import json

ap = argparse.ArgumentParser()
ap.add_argument('a')
ap.add_argument('b')
ap.add_argument('--show', type=int, default=5)
args = ap.parse_args()


def scan(path, wanted=None):
    # unit key -> (extent, line count, hash), or the lines of the wanted keys
    header, out, order = [], {}, []
    state = {'key': None, 'extent': None, 'lines': []}

    def close():
        key, lines = state['key'], state['lines']
        if key is None:
            return
        body = sorted(lines) if key[1] == 'departures' else lines
        if key[1] == 'table':
            body = ['\t'.join(l.split('\t')[:6]) for l in body]
        k = key
        while k in out:
            k = k + ('again',)
        if wanted is None:
            out[k] = (state['extent'], len(body), hashlib.sha1('\n'.join(body).encode()).hexdigest())
            order.append(k)
        elif k in wanted:
            out[k] = (state['extent'], body)

    with gzip.open(path, 'rt') as f:
        for line in f:
            line = line.rstrip('\n')
            if line.startswith('#unit\t'):
                close()
                c = line.split('\t')
                state.update(key=(c[1], c[4], f'{c[2]}-{c[3]}' if c[4] == 'departures' else c[5]), extent=(c[2], c[3]), lines=[])
            elif state['key'] is None:
                header.append(line)
            else:
                state['lines'].append(line)
    close()
    return header, out, order


def directory(path):
    lines = open(path + '.idx').read().rstrip('\n').split('\n')
    first = '\t'.join(t for t in lines[0].split('\t') if not t.startswith('bytes:i:'))
    return first, [l.split('\t')[0] for l in lines[1:] if not l.startswith('#header')]


ha, ua, oa = scan(args.a)
hb, ub, ob = scan(args.b)
diffs = collections.Counter()
examples = collections.defaultdict(list)
if ha != hb:
    diffs['header'] += 1
    examples['header'].append((ha, hb))
da, db = directory(args.a), directory(args.b)
if da[0] != db[0]:
    diffs['directory line 1'] += 1
    examples['directory line 1'].append((da[0], db[0]))
extra = [s for s in da[1] if s not in db[1]]
if [s for s in da[1] if s in db[1]] != db[1]:
    diffs['directory sequences'] += 1
if extra:
    diffs["sequences only in the writer's directory"] = len(extra)
    examples["sequences only in the writer's directory"] = extra[:args.show]
differing = set()
for k in ua.keys() | ub.keys():
    if k not in ub:
        empty = k[1] == 'table' and ua[k][1] == 0
        kind = "empty table only in the writer's" if empty else f"{k[1]} unit only in the writer's"
        diffs[kind] += 1
        examples[kind].append((k, ua[k][:2]))
        continue
    if k not in ua:
        diffs[f"{k[1]} unit only in the converter's"] += 1
        examples[f"{k[1]} unit only in the converter's"].append((k, ub[k][:2]))
        continue
    (ea, na, xa), (eb, nb, xb) = ua[k], ub[k]
    if ea != eb:
        diffs[f'{k[1]} unit extent'] += 1
        examples[f'{k[1]} unit extent'].append((k, ea, eb))
    if xa != xb:
        diffs[f'{k[1]} unit lines'] += 1
        differing.add(k)
order_a = [k for k in oa if k in ub]
order_b = [k for k in ob if k in ua]
if order_a != order_b:
    diffs['unit order'] += 1
if differing:
    shown = set(sorted(differing)[: 20 * args.show])
    _, la, _ = scan(args.a, shown)
    _, lb, _ = scan(args.b, shown)
    for k in sorted(shown):
        sa, sb = set(la[k][1]), set(lb[k][1])
        examples[f'{k[1]} unit lines'].append({'unit': k, "writer's only": sorted(sa - sb)[:3],
                                               "converter's only": sorted(sb - sa)[:3], 'order only': sa == sb})
for kind, ex in examples.items():
    for e in ex[: args.show]:
        print(kind, json.dumps(e)[:1500])
print(json.dumps({'units': [len(ua), len(ub)], 'lines': [sum(u[1] for u in ua.values()), sum(u[1] for u in ub.values())],
                  'differences': dict(diffs)}))
