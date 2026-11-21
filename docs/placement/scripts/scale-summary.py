#!/usr/bin/env python3
"""The numbers docs/placement/scale-past-464.md quotes, from the study's files.

scale-summary.py DIR GENOME_BYTES

DIR holds scale-build.txt, scale-files.tsv, scale-windows.tsv,
scale-query.tsv and scale-distinct.tsv (docs/placement/). GENOME_BYTES is
the genome-wide 464-haplotype walk file's size, for the extrapolation.
Graphs other than 464, 2000 and 5000 (the 5,000 haplotype graph written with
other abridge budgets) appear where the files give them; their query rows
are the untimed pass's.
"""

import csv
import gzip
import math
import os
import re
import statistics
import sys
from collections import defaultdict

DIR, GENOME = sys.argv[1], int(sys.argv[2])
SCALES = ["464", "2000", "5000"]


def rows(name):
    with open(f"{DIR}/{name}") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def mb(b):
    return f"{b / 1e6:.2f} MB"


def spread(xs):
    return f"{statistics.median(xs):.1f} (range {min(xs):.1f}-{max(xs):.1f})"


with gzip.open(f"{DIR}/scale-switches.tsv.gz", "rt") as f:
    switched = {line.split("\t")[0].split("#")[0] for line in list(f)[1:]}
with open(f"{DIR}/scale-synth.txt") as f:
    synthetic = int(next(line for line in f if line.startswith("synthetic haplotypes")).split("\t")[1])
print(f"# Synthetic haplotypes with no switch: {synthetic - len(switched)} of {synthetic}\n")

print("# Builds: median wall s (range), median peak GB")
builds = defaultdict(list)
with open(f"{DIR}/scale-build.txt") if os.path.exists(f"{DIR}/scale-build.txt") else open(os.devnull) as f:
    for line in f:
        m = re.match(r"(\d+) round \d: ([\d.]+) s wall, ([\d.]+) s user, ([\d.]+) s system, (\d+) KB peak", line)
        if m:
            builds[m[1]].append((float(m[2]), int(m[5]) / 1e6))
for n in [s for s in SCALES if builds[s]]:
    walls = [w for w, _ in builds[n]]
    peaks = [p for _, p in builds[n]]
    print(f"{n}: {spread(walls)} s, peak {statistics.median(peaks):.2f} GB ({min(peaks):.2f}-{max(peaks):.2f})")

print("\n# Files")
files = rows("scale-files.tsv") + rows("scale-alt-files.tsv")
size = {}
GRAPHS = list(dict.fromkeys(r["graph"] for r in files))
for n in GRAPHS:
    mine = [r for r in files if r["graph"] == n]
    size[n] = int(mine[0]["data_bytes"])
    kinds = ", ".join(f"{r['kind']} {r['units']} units {mb(int(r['bytes']))}" for r in mine)
    print(f"{n}: walk file {mb(size[n])}, .idx {mine[0]['idx_bytes']} B, header unit {mine[0]['header_bytes']} B,"
          f" table {mb(int(mine[0]['table_bytes']))}; {kinds}")
    mapped = sum(int(r["units"]) for r in mine if r["kind"] in ("detail", "blocks"))
    print(f"  detail and blocks units, which a cut maps by name: {mapped}")
    for r in mine:
        if r["kind"] in ("tile", "blocks"):
            print(f"  a {r['kind']} unit's compressed bytes: p50 {mb(int(r['p50']))}, p90 {mb(int(r['p90']))}, p99 {mb(int(r['p99']))}, max {mb(int(r['max']))}")
for n in [g for g in GRAPHS if g != "464"]:
    base = "464-off" if n.endswith("-off") else "464"
    if n in ("464-off",) or base not in size:
        continue
    haps = int(n.split("-")[0])
    b = math.log(size[n] / size[base]) / math.log(haps / 464)
    print(f"{base} -> {n}: x{size[n] / size[base]:.2f} for x{haps / 464:.2f} haplotypes, exponent {b:.2f};"
          f" the genome-wide 464 file ({GENOME / 1e9:.2f} GB) grown by it to 10,000: {GENOME * (10000 / 464) ** b / 1e9:.1f} GB")

print("\n# Window bytes over the windows with tiles of over 1 kB: median of tiles, blocks, departures; bytesFor (all of them and attach fetches) median, max; tiles gunzipped")
windows = rows("scale-windows.tsv") + rows("scale-alt-windows.tsv")
for size_bp in ["10000", "100000", "1000000"]:
    for n in GRAPHS:
        mine = [r for r in windows if r["graph"] == n and r["size"] == size_bp and int(r["tile_bytes"]) > 1000]
        total = [int(r["bytes_for"]) for r in mine]
        text = [int(r["tile_text_bytes"]) for r in mine]
        gz = [int(r["tile_bytes"]) for r in mine]
        ratio = statistics.median(t / g for t, g in zip(text, gz))
        parts = ", ".join(f"{k} {mb(statistics.median(int(r[k + '_bytes']) for r in mine))}" for k in ("tile", "blocks", "departure"))
        print(f"{size_bp} bp, {n}: {parts}; bytesFor median {mb(statistics.median(total))}, max {mb(max(total))};"
              f" tiles gunzipped median {mb(statistics.median(text))}, {ratio:.1f}x their compressed bytes ({len(mine)} windows)")

print("\n# Queries: median cut ms (range) over the timed runs, compressed bytes read, browser preset")
query = rows("scale-query.tsv") if os.path.exists(f"{DIR}/scale-query.tsv") else []
groups = defaultdict(list)
for r in query:
    groups[(r["center"], r["size"], r["set"], r["graph"])].append(r)
for key in sorted(groups, key=lambda k: (int(k[0]), int(k[1]), k[2], int(k[3]))):
    timed = [r for r in groups[key] if r["run"] != "0"] or groups[key]
    if timed:
        ms = [float(r["cut_ms"]) for r in timed]
        tables = [float(r["tables_ms"]) for r in timed]
        loads = [float(r["load1"]) for r in timed]
        print(f"{key[0]} {key[1]} bp {key[2]} {key[3]}: cut {spread(ms)} ms, tables {statistics.median(tables):.1f} ms,"
              f" {mb(int(timed[0]['bytes']))}, {timed[0]['steps']} steps, {timed[0]['nodes']} nodes, {timed[0]['placeholders']} placeholders,"
              f" load {min(loads):.2f}-{max(loads):.2f}; browser: {timed[0]['browser'][:90]}")

print("\n# Compact: per size, set and graph, the lowest and highest of the three windows' median cut ms, and the widest run spread (max-min over median)")
compact = defaultdict(list)
for key, rs in groups.items():
    timed = [r for r in rs if r["run"] != "0"]
    if timed:
        ms = [float(r["cut_ms"]) for r in timed]
        compact[(key[1], key[2], key[3])].append((statistics.median(ms), (max(ms) - min(ms)) / statistics.median(ms), len(ms)))
for (size_bp, set_name, graph), xs in sorted(compact.items(), key=lambda kv: (int(kv[0][0]), kv[0][1], int(kv[0][2]))):
    meds = [m for m, _, _ in xs]
    print(f"{size_bp} bp {set_name} {graph}: {min(meds):.0f}-{max(meds):.0f} ms, widest spread {max(sp for _, sp, _ in xs) * 100:.0f}%, runs {min(n for _, _, n in xs)}")

print("\n# Untimed pass (scale-query-untimed.tsv and scale-query-alt-untimed.tsv, one cut each, the machine loaded): compressed bytes read, ms, browser preset")
for r in rows("scale-query-untimed.tsv") + rows("scale-query-alt-untimed.tsv"):
    print(f"{r['center']} {r['size']} bp {r['set']} {r['graph']}: {mb(int(r['bytes']))}, cut {float(r['cut_ms']):.0f} ms,"
          f" {r['steps']} steps, {r['placeholders']} placeholders; browser: {r['browser'][:60]}")

print("\n# Distinct walk rows per tile (median over the tiles with rows) / rows")
distinct = rows("scale-distinct.tsv")
by = defaultdict(list)
for r in distinct:
    if int(r["rows"]) > 0:
        by[(r["graph"], r["subset"])].append((int(r["distinct"]), int(r["rows"])))
for (graph, subset), xs in sorted(by.items(), key=lambda kv: (int(kv[0][0]), kv[0][1])):
    d = statistics.median(x for x, _ in xs)
    n = statistics.median(y for _, y in xs)
    print(f"{graph} {subset}: {d:.0f} distinct of {n:.0f} rows ({len(xs)} tiles)")

print("\n# Tiles split by row kind and into 50 groups (scale-rowsplit.tsv), medians over the tiles of over 1 kB, bytes deflated")
split = rows("scale-rowsplit.tsv")
for graph in dict.fromkeys(r["graph"] for r in split):
    mine = [r for r in split if r["graph"] == graph and int(r["tile_bytes"]) > 1000]

    def med(k):
        return statistics.median(int(r[k]) for r in mine)

    four = statistics.median(int(r["shared_bytes"]) + 4 * int(r["grouped_walk_bytes"]) / 50 for r in mine)
    print(f"{graph}: tile {med('tile_bytes') / 1e3:.1f} kB, shared rows {med('shared_bytes') / 1e3:.1f} kB,"
          f" walk and abridged rows {med('walk_bytes') / 1e3:.1f} kB, as 50 groups {med('grouped_walk_bytes') / 1e3:.1f} kB;"
          f" shared rows and 4 average groups {four / 1e3:.1f} kB; the 4 kept haplotypes' groups ({med('kept_groups'):.0f}) {med('kept_bytes') / 1e3:.1f} kB;"
          f" {med('rows'):.0f} walk and abridged rows, {med('abridged_rows'):.0f} abridged")
