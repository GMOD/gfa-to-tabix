#!/usr/bin/env python3
# Writes results.jsonl and README.md beside it from what run.sh left in this
# directory: identity.tsv, each file's verify7 summary and time, and spec8's
# report and time where it ran. Exits 1 where a local file is not the hosted
# one, a check failed, or verify7 and spec8 count other nodes.
# Usage: table.py
import csv
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def text(name):
    path = os.path.join(HERE, name)
    return open(path).read() if os.path.exists(path) else None


def timed(name):
    seconds, kb, status = text(name).split('\n')[-2].split('\t')
    return dict(seconds=float(seconds), peak_kb=int(kb), exit=int(status))


def spec8(label):
    report = text(f'spec8.{label}.txt')
    counts = {k.strip(): int(n) for n, k in re.findall(r'^ +(\d+)  (.+)$', report.split('== agreed ==')[0], re.M)}
    disagreed = report.split('== disagreed ==')[1].strip().split('\n')[0].strip()
    promised = next((n for k, n in counts.items() if k.startswith('once-passed nodes in a route interior')), None)
    return dict(timed(f'spec8.{label}.time'), disagreed=disagreed, once_passed_nodes=counts['nodes the ref rows step once'],
                nodes_in_a_route_interior=counts['nodes in a route interior'],
                once_passed_nodes_in_a_route_interior_unpromised=promised)


rows = []
for line in csv.DictReader(open(os.path.join(HERE, 'identity.tsv')), delimiter='\t'):
    label = line['file']
    hosted = line['hosted'] != 'not hosted'
    row = dict(file=label, hosted=line['hosted'], bytes=int(line['local bytes']), sha256=line['local sha256'],
               same_length=hosted and line['local bytes'] == line['hosted Content-Length'],
               same_etag=hosted and line['local ETag, 8 MiB parts'] == line['hosted ETag'],
               etag=line['hosted ETag'], same_idx=hosted and line['local .idx sha256'] == line['hosted .idx sha256'],
               idx_sha256=line['local .idx sha256'],
               verify7=dict(timed(f'verify7.{label}.time'), **json.loads(text(f'verify7.{label}.json') or '{"ok": false}')),
               spec8=spec8(label) if text(f'spec8.{label}.txt') else None)
    rows.append(row)
with open(os.path.join(HERE, 'results.jsonl'), 'w') as f:
    f.write(''.join(json.dumps(r) + '\n' for r in rows))


checkers = ', '.join(f'`{name}` {blob[:12]}' for name, blob in (l.split('\t') for l in text('checkers.tsv').split('\n') if l))


def n(x):
    return f'{x:,}'


def yes(x):
    return 'equal' if x else '**differs**'


out = ['# The whole-file checks on the hosted bytes', '',
       f'Written by [table.py](table.py) from [results.jsonl](results.jsonl), which it writes from what [run.sh](run.sh) '
       f'left here on {text("date.txt").strip()}. Not edited by hand. The scripts that ran, by git blob '
       f'([checkers.tsv](checkers.tsv)): {checkers}.', '',
       '## The local files are the hosted ones', '',
       'Each local file against its hosted copy ([identity.tsv](identity.tsv)): the length against `Content-Length`, the '
       'S3 multipart ETag of the local bytes over 8 MiB parts against the hosted ETag, and the sha256 of the `.idx`.', '',
       '| File | Hosted as | Bytes | Length | ETag | `.idx` | sha256 of the local data |', '|---|---|---|---|---|---|---|']
for r in rows:
    name = f'`{r["hosted"].rsplit("/", 1)[1]}`' if r['hosted'] != 'not hosted' else 'not hosted'
    same = [yes(r[k]) if name != 'not hosted' else 'n/a' for k in ('same_length', 'same_etag', 'same_idx')]
    out.append(f'| {r["file"]} | {name} | {n(r["bytes"])} | {same[0]} | {same[1]} | {same[2]} | `{r["sha256"][:16]}…` |')
out += ['', '## verify7.py over each whole file', '',
        'Nodes the file\'s `ref` rows step once, those among them in a route interior of a tile or a detail unit on any '
        'sequence, and `ref` rows whose `passes` states another count than the file\'s `ref` rows step.', '',
        '| File | `revisited` nodes | `ref` steps | Nodes stepped once | Route interior steps read | Stepped once and in an '
        'interior | `ref` rows stating fewer | stating more | Exit | Time | Peak |', '|---|---|---|---|---|---|---|---|---|---|---|']
for r in rows:
    v = r['verify7']
    out.append(f'| {r["file"]} | {n(v.get("revisited_nodes", -1))} | {n(v.get("ref_steps", -1))} | {n(v.get("once_passed_nodes", -1))} | '
               f'{n(v.get("route_interior_steps", -1))} | {n(v.get("once_passed_nodes_in_a_route_interior", -1))} | '
               f'{n(v.get("ref_rows_stating_fewer_passes", -1))} | {n(v.get("ref_rows_stating_more_passes", -1))} | {v["exit"]} | '
               f'{v["seconds"]:.0f} s | {v["peak_kb"] / 1e6:.2f} GB |')
out += ['', 'Each summary is `verify7.<file>.json`, and its time, peak memory and exit status `verify7.<file>.time`.', '',
        '## spec8.py, written from the page alone', '',
        'spec8.py holds every piece of a file in memory, so it ran on the chromosome files and not on the genome files. '
        'It counts the nodes the `ref` rows step once as verify7.py does, with no code of it.', '',
        '| File | Disagreements with the page | Nodes stepped once | Same as verify7 | Nodes in a route interior | Stepped once '
        'and in an interior, which the page promises nothing of where `revisited` is above 0 | Time | Peak |',
        '|---|---|---|---|---|---|---|---|']
failed = False
for r in rows:
    s = r['spec8']
    if s:
        agree = s['once_passed_nodes'] == r['verify7'].get('once_passed_nodes')
        failed = failed or not agree or s['disagreed'] != 'none' or s['exit'] != 0
        unpromised = 'n/a: the file states `revisited:i:0`' if s['once_passed_nodes_in_a_route_interior_unpromised'] is None \
            else n(s['once_passed_nodes_in_a_route_interior_unpromised'])
        out.append(f'| {r["file"]} | {s["disagreed"]} | {n(s["once_passed_nodes"])} | {yes(agree)} | '
                   f'{n(s["nodes_in_a_route_interior"])} | {unpromised} | {s["seconds"]:.0f} s | {s["peak_kb"] / 1e6:.2f} GB |')
    failed = failed or r['verify7']['exit'] != 0 or not r['verify7'].get('ok') or \
        (r['hosted'] != 'not hosted' and not (r['same_length'] and r['same_etag'] and r['same_idx']))
out += ['', 'Each report is `spec8.<file>.txt`.', '',
        '## What the checks fail', '',
        '[broken-matrix.txt](broken-matrix.txt) lists, for each planted file of '
        '[cases.tsv](../../../departures/scripts/broken/cases.tsv) that breaks one of these and for the unbroken files they '
        'were made from, the checkers that fail it, as [matrix.sh](matrix.sh) printed them with the same scripts.', '']
open(os.path.join(HERE, 'README.md'), 'w').write('\n'.join(out))
sys.exit(1 if failed else 0)
