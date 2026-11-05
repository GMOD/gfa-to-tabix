"""How much of the detail tier repeats routes: per abridged chunk, the routes
each detail record carries that the chunk's own route rows or an earlier
record of the same chunk already hold, by count and by compressed bytes.

usage: bgzip -dc f6.bed.gz | python3 -I detail_dup.py SEQ
"""
import sys
import zlib
from collections import defaultdict

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from decode6 import parse_routes

seq = sys.argv[1]
chunk_routes = defaultdict(list)
records = defaultdict(lambda: defaultdict(list))
sizes = defaultdict(int)
kinds = defaultdict(int)
for raw in sys.stdin:
    if raw[0] == "#":
        continue
    cols = raw.rstrip("\n").split("\t")
    name = cols[0]
    if name == seq:
        if cols[3] == "route":
            chunk_routes[int(cols[1])].append(cols)
        sizes["main"] += len(raw)
    elif name.startswith(seq + "~"):
        tail = name.rsplit("~", 1)[1]
        if tail == "departure":
            sizes["departure"] += len(raw)
            continue
        cs = int(tail)
        rec = int(cols[1]) // 16384
        records[cs][rec].append(cols)
        kinds[cols[3]] += len(raw)
        sizes["detail"] += len(raw)


def key(route):
    entry, interior, exit = route
    return (entry, tuple(interior), exit)


def gz(lines):
    return len(zlib.compress("".join(l + "\n" for l in lines).encode(), 6))


tot_routes = dup_chunk = dup_prev = 0
tot_gz = dup_gz = walk_gz = nodes_gz = 0
n_rec = 0
for cs, recs in records.items():
    held = {key(r) for r in parse_routes(chunk_routes.get(cs, []))}
    seen = set()
    for rec in sorted(recs):
        rows = recs[rec]
        n_rec += 1
        route_rows = [r for r in rows if r[3] == "route"]
        routes = parse_routes(route_rows)
        dup_lines = []
        for r, cols in zip(routes, route_rows):
            k = key(r)
            tot_routes += 1
            if k in held:
                dup_chunk += 1
                dup_lines.append("\t".join(cols))
            elif k in seen:
                dup_prev += 1
                dup_lines.append("\t".join(cols))
            seen.add(k)
        tot_gz += gz(["\t".join(r) for r in rows])
        dup_gz += gz(dup_lines)
        walk_gz += gz(["\t".join(r) for r in rows if r[3] == "walk"])
        nodes_gz += gz(["\t".join(r) for r in rows if r[3] == "nodes"])

print(f"raw bytes: main {sizes['main'] / 1e6:.1f} MB, departures {sizes['departure'] / 1e6:.1f} MB, detail {sizes['detail'] / 1e6:.1f} MB")
print("detail raw by kind: " + ", ".join(f"{k} {v / 1e6:.1f} MB" for k, v in sorted(kinds.items())))
print(f"abridged chunks {len(records)}, records {n_rec}, record routes {tot_routes}")
print(f"routes also in the chunk's route rows: {dup_chunk} ({100 * dup_chunk / max(1, tot_routes):.1f}%)")
print(f"routes also in an earlier record of the chunk: {dup_prev} ({100 * dup_prev / max(1, tot_routes):.1f}%)")
print(f"records compressed alone: {tot_gz / 1e6:.1f} MB; their duplicate route rows {dup_gz / 1e6:.1f} MB; walk rows {walk_gz / 1e6:.1f} MB; nodes rows {nodes_gz / 1e6:.1f} MB")
