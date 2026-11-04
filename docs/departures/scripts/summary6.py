#!/usr/bin/env python3
# Tables from the rebuild's build logs and audits: one row per graph and
# filing. Usage: summary6.py out/   (reads NAME.VARIANT.build.log and .audit.txt)
import glob
import os
import re
import sys

out = sys.argv[1]


def grab(text, pattern, default='-'):
    m = re.search(pattern, text)
    return m.group(1) if m else default


rows = []
for log in sorted(glob.glob(os.path.join(out, '*.build.log'))):
    name, variant = os.path.basename(log).split('.')[:2]
    b = open(log).read()
    audit = log.replace('.build.log', '.audit.txt')
    a = open(audit).read() if os.path.exists(audit) else ''
    f = os.path.join(out, f'{name}.{variant}.GRCh38.walks.bed.gz')
    size = os.path.getsize(f) if os.path.exists(f) else 0
    win = a.split('64 kb windows')[1].split('1 bp windows')[0] if '64 kb windows' in a else ''
    pt = a.split('1 bp windows')[1] if '1 bp windows' in a else ''
    rows.append(dict(
        graph=name, filing=variant, mb=f'{size / 1e6:.1f}',
        dep_bytes=grab(a, r'(\d+)\tdeparture \('), dep_pct=grab(a, r'\tdeparture \(([\d.]+%)\)'),
        records=grab(b, r'departures: (\d+) records'),
        rows=grab(a, r'(\d+)\tdeparture rows'), crowd_rows=grab(a, r'(\d+)\tcrowd rows', '0'),
        win_p95=grab(win, r'rows median \d+ p95 (\d+)'), win_max=grab(win, r'rows median \d+ p95 \d+ max (\d+)'),
        pt_max=grab(pt, r'rows median \d+ p95 \d+ max (\d+)'),
        req_max=grab(win, r'departure read requests: median \d+ p95 \d+ max (\d+)'),
        bytes_p95=grab(win, r'departure read bytes: median \d+ p95 (\d+)'),
        bytes_max=grab(win, r'departure read bytes: median \d+ p95 \d+ max (\d+)'),
        uncovered=grab(a, r'(\d+)\tbases uncovered'),
        missing=sum(int(x) for x in re.findall(r'(\d+)\t[^\n]*MISSING RECORD', a)),
        mismatched=sum(int(x) for x in re.findall(r'(\d+)\t[^\n]*: field mismatch', a)),
        time=grab(b, r': ([\d.]+) s, \d+ KB peak'), peak_gb=f"{int(grab(b, r'(\d+) KB peak', '0')) / 1e6:.1f}",
    ))
cols = list(rows[0]) if rows else []
print('\t'.join(cols))
for r in rows:
    print('\t'.join(str(r[c]) for c in cols))

print()
print('graph\tpositions and copies (k8 build)')
for log in sorted(glob.glob(os.path.join(out, '*.k8.build.log'))):
    b = open(log).read()
    print(os.path.basename(log).split('.')[0])
    for key in ('positions:', 'stay:', 'filing:', 'departures:', 'pages:', 'holes'):
        for line in b.splitlines():
            if key in line:
                print('  ' + line.strip())
