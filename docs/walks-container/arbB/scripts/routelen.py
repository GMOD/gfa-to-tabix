"""Price dropping the `nodes` row: each route row carries its interior
nodes' lengths instead (`route entry interior exit lengths`), so a chunk or
detail record has one row kind fewer and no node table to join. Compressed
(zlib 6) bytes of the chunk's walk-read rows and of every detail record,
both ways.

usage: bgzip -dc f6.bed.gz | python3 -I routelen.py SEQ NCHUNKS SEED
"""
import random
import sys
import zlib
from collections import defaultdict

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from decode6 import handles, parse_nodes, parse_routes

seq, nchunks, seed = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
rows = defaultdict(list)
records = defaultdict(list)
for raw in sys.stdin:
    if raw[0] == "#":
        continue
    cols = raw.rstrip("\n").split("\t")
    if cols[0] == seq:
        rows[int(cols[1])].append(cols)
    elif cols[0].startswith(seq + "~") and not cols[0].endswith("~departure"):
        records[(cols[0], int(cols[1]) // 16384)].append(cols)


def gz(lines):
    return len(zlib.compress("".join(l + "\n" for l in lines).encode(), 6))


def with_lengths(group):
    """Rows of one chunk or record, nodes row dropped, lengths on routes."""
    node_len = {}
    for cols in group:
        if cols[3] == "nodes":
            parse_nodes(cols, node_len)
        elif cols[3] == "ref":
            hs, _ = handles(cols[9])
            for h, ln in zip(hs, cols[10].split(",")):
                node_len[h >> 1] = int(ln)
    out = []
    routes = parse_routes([c for c in group if c[3] == "route"])
    k = 0
    for cols in group:
        if cols[3] == "nodes":
            continue
        if cols[3] == "route":
            interior = routes[k][1]
            k += 1
            lens = ",".join(str(node_len[h >> 1]) for h in interior) or "."
            out.append("\t".join(cols + [lens]))
        else:
            out.append("\t".join(cols))
    return out


rng = random.Random(seed)
picked = sorted(rng.sample(sorted(rows), min(nchunks, len(rows))))
a = b = 0
for cs in picked:
    group = [c for c in rows[cs] if c[3] in ("ref", "nodes", "route", "walk")]
    a += gz(["\t".join(c) for c in group])
    b += gz(with_lengths(group))
print(f"chunks {len(picked)}: nodes row {a / 1e6:.2f} MB, lengths on routes {b / 1e6:.2f} MB, ratio {b / a:.3f}")

# detail records decode against their chunk's ref rows, so the chunk's R gives
# lengths for nodes on R; a record's nodes row gives the rest
a = b = n = 0
for (name, rec), group in records.items():
    cs = int(name.rsplit("~", 1)[1])
    ref = [c for c in rows[cs] if c[3] == "ref"]
    a += gz(["\t".join(c) for c in group])
    b += gz([l for l in with_lengths(ref + group) if "\tref\t" not in l])
    n += 1
print(f"detail records {n}: nodes row {a / 1e6:.2f} MB, lengths on routes {b / 1e6:.2f} MB, ratio {b / a:.3f}")
