"""Price format 6's cross-row encodings against plain rows, per chunk.

For a sample of chunks of the main sequence, re-emit the window-read rows
(ref, nodes, route, walk) under each variant and compress each chunk alone
with zlib level 6 (what BGZF does, minus block edges):

  f6        the rows as written
  abs       route rows with absolute GAF handles (`>12 <13`), no chain
            across rows; walk rows with absolute route ids; ref steps absolute
  absdelta  route rows absolute as above, walk choices still deltas
  inline    no route dictionary: each walk row lists its departures inline
            as `entry>interior<exit` GAF strings, absolute
  gaf       no dictionary, no R reference: each walk row is the piece's full
            step list as a GAF path (`>1>2<5>7`)

usage: bgzip -dc f6.bed.gz | python3 -I encode_variants.py SEQ NCHUNKS SEED
"""
import random
import sys
import zlib
from collections import defaultdict

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from decode6 import Chunk, decode_walk, expand, parse_routes, tokens

seq, nchunks, seed = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])

rows = defaultdict(list)
for raw in sys.stdin:
    if raw[0] == "#":
        continue
    cols = raw.rstrip("\n").split("\t")
    if cols[0] != seq:
        continue
    rows[int(cols[1])].append(cols)

chunks = sorted(rows)
rng = random.Random(seed)
picked = sorted(rng.sample(chunks, min(nchunks, len(chunks))))


def gaf(handles):
    return "".join(("<" if h & 1 else ">") + str(h >> 1) for h in handles) or "."


def gz(lines):
    return len(zlib.compress("\n".join(lines).encode() + b"\n", 6))


totals = defaultdict(int)
raw_totals = defaultdict(int)
counts = defaultdict(int)
for cs in picked:
    cols_list = rows[cs]
    c = Chunk(seq, cs)
    walks = []
    for cols in cols_list:
        kind = cols[3]
        if kind == "ref":
            c.ref.append(cols)
        elif kind == "nodes":
            from decode6 import parse_nodes
            parse_nodes(cols, c.nodes)
        elif kind == "route":
            c.routes.append(cols)
        elif kind == "walk":
            walks.append(cols)
    c.finish()
    routes = parse_routes(c.routes)
    f6 = ["\t".join(cols) for cols in cols_list if cols[3] in ("ref", "nodes", "route", "walk")]
    head = f"{seq}\t{cs}\t{cs + 65536}"
    ref_abs = []
    for r in c.ref:
        from decode6 import handles
        hs, _ = handles(r[9])
        ref_abs.append("\t".join([head, "ref"] + r[4:9] + [gaf(hs)] + r[10:]))
    nodes_rows = ["\t".join([head] + cols[3:]) for cols in cols_list if cols[3] == "nodes"]
    route_abs = []
    for entry, interior, exit in routes:
        route_abs.append(
            "\t".join([head, "route", gaf([entry]) if entry is not None else ".", gaf(interior), gaf([exit]) if exit is not None else "."])
        )
    route_rowdelta = []
    for entry, interior, exit in routes:
        prev = 0
        def dtok(h):
            global prev
            t = 2 * ((h >> 1) - prev) + (h & 1)
            prev = h >> 1
            return str(t)
        cols_r = []
        cols_r.append(dtok(entry) if entry is not None else ".")
        cols_r.append(",".join(dtok(h) for h in interior) or ".")
        cols_r.append(dtok(exit) if exit is not None else ".")
        route_rowdelta.append("\t".join([head, "route"] + cols_r))
    walk_abs = []
    walk_absdelta = []
    walk_inline = []
    walk_gaf = []
    for cols in walks:
        choice_ids = []
        prev = 0
        toks = [] if cols[10] == "." else cols[10].split(",")
        for tok in toks:
            text = tok.split("@")[0].split(":")[0]
            t = int(text)
            prev += t >> 1
            choice_ids.append((prev, t & 1, tok[len(text):]))
        absolute = ",".join(f"{rid * 2 + f}{suffix}" for rid, f, suffix in choice_ids) or "."
        walk_abs.append("\t".join([head, "walk"] + cols[4:9] + [gaf([int(cols[9].split('@')[0])]) + ("@" + cols[9].split("@")[1] if "@" in cols[9] else ""), absolute]))
        walk_absdelta.append("\t".join([head, "walk"] + cols[4:10] + [cols[10]]))
        inline = []
        for rid, f, suffix in choice_ids:
            entry, interior, exit = routes[rid]
            if f:
                entry, interior, exit = (None if exit is None else exit ^ 1), [h ^ 1 for h in reversed(interior)], (None if entry is None else entry ^ 1)
            inline.append((gaf([entry]) if entry is not None else "") + "[" + gaf(interior).replace(".", "") + "]" + (gaf([exit]) if exit is not None else "") + suffix)
        walk_inline.append("\t".join([head, "walk"] + cols[4:9] + [gaf([int(cols[9].split('@')[0])]), ",".join(inline) or "."]))
        p = decode_walk(c, cols, routes)
        steps = [h for h, _ in expand(c, p)]
        walk_gaf.append("\t".join([head, "walk"] + cols[4:9] + [gaf(steps)]))
    variants = {
        "f6": f6,
        "abs": ref_abs + nodes_rows + route_abs + walk_abs,
        "absdelta": ref_abs + nodes_rows + route_abs + walk_absdelta,
        "rowdelta": [l for l in f6 if "\troute\t" not in l] + route_rowdelta,
        "inline": ref_abs + nodes_rows + walk_inline,
        "gaf": ref_abs + nodes_rows + walk_gaf,
    }
    assert len(route_rowdelta) == len(routes)
    for name, lines in variants.items():
        totals[name] += gz(lines)
        raw_totals[name] += sum(len(l) + 1 for l in lines)
    counts["chunks"] += 1
    counts["walks"] += len(walks)
    counts["routes"] += len(routes)

print(f"chunks {counts['chunks']} walk rows {counts['walks']} routes {counts['routes']}")
base = totals["f6"]
for name in ("f6", "rowdelta", "abs", "absdelta", "inline", "gaf"):
    print(f"{name:9} gz {totals[name] / 1e6:8.2f} MB  ratio {totals[name] / base:5.2f}   raw {raw_totals[name] / 1e6:8.1f} MB")
