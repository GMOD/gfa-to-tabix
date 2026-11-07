# R3, the first view at genome scale, by arithmetic over the genome-wide
# format 7 structure (~/work/s7-genome/res/structure.*.json, the files behind
# docs/walks-container/genome/report.md). Open = directory + header + the
# sequence's table; R3 = the same with the table's detail entries split into
# a second table read on first expansion ("gzipWithoutDetail"). KB = 1024.
# usage: r3.py
import json, re, statistics

PRIMARY = re.compile(r'#chr([0-9]+|X|Y)$')
for g in ('grch38', 'chm13'):
    d = json.load(open(f'/home/cdiesh/work/s7-genome/res/structure.{g}.json'))
    fixed = d['directoryBytes'] + d['headerBytes']
    rows = []
    for seq, s in d['perSeq'].items():
        if PRIMARY.search(seq):
            rows.append((seq, fixed + s['tableBytes'], fixed + s['gzipWithoutDetail'], s['entries']['tile']['gzipAlone'], s['entries']['departures']['gzipAlone'], s['entries']['detail']['gzipAlone']))
    kb = lambda x: x / 1024
    now = [r[1] for r in rows]
    r3 = [r[2] for r in rows]
    print(f"{g}: directory {d['directoryBytes']} B, header {d['headerBytes']} B, {len(rows)} primary sequences")
    print(f"  open now   median {kb(statistics.median(now)):.1f} KB, max {kb(max(now)):.1f} KB ({max(rows, key=lambda r: r[1])[0]})")
    print(f"  open R3    median {kb(statistics.median(r3)):.1f} KB, max {kb(max(r3)):.1f} KB ({max(rows, key=lambda r: r[2])[0]})")
    print(f"  all tables {d['tablesTotalBytes']} B")
    for r in sorted(rows, key=lambda r: -r[1])[:4]:
        print(f"  {r[0]}: open {kb(r[1]):.1f} -> {kb(r[2]):.1f} KB; entry kinds gzipped alone tile {r[3]} departures {r[4]} detail {r[5]}")
