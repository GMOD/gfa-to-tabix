#!/usr/bin/env python3
"""placement-crux.py: can a path graph's walk files stand in for its node and
link index? docs/placement/scripts compares what graph-walks draws from each,
which ADR 0008 rests on; `windows` here compares node sets, a weaker test.

  placement-crux.py edges GRAPH.gfa|-
      Counts the L lines no P or W line traverses, which a viewer that reads
      only walk files never draws, and path steps with no L line.
      zstd -dc graph.gfa.zst | placement-crux.py edges -

  placement-crux.py windows PREFIX WALKS SEQ FROM TO COUNT [WIDTH]
      For COUNT windows of WIDTH bp (default 10000) spread over FROM-TO on
      SEQ, compares the nodes and edges an index query keeps
      (PREFIX.graph.bed.gz, format 2, anchored) with those the walk file's
      chunks hold: their ref, nodes and route rows, read back as far as a
      reader reads, and the chunks' detail records listed apart.
      Needs tabix on PATH. Node ids must match, as they do when both files
      come from one base-level GFA.

A window's index-only nodes are ones the walk file files elsewhere, in a
detail record, or nowhere (`absent`). Only absent nodes are lost to a
walk-file view: the index also keeps a collapsed repeat's nodes megabases
from where the walk files place them. Walk-only nodes are steps the walk
file files nearer the window than the index does.
"""

import gzip
import re
import statistics
import subprocess
import sys
from collections import defaultdict


def flip(h):
    return h ^ 1


def edge(a, b):
    return min((a, b), (flip(b), flip(a)))


def handle(name, strand):
    return int(name) * 2 + (strand == "-")


def lines(path):
    if path == "-":
        return sys.stdin
    opener = gzip.open if path.endswith(".gz") else open
    return opener(path, "rt")


WALK_STEP = re.compile(r"([<>])([^<>]+)")


def edges(path):
    links, traversed = set(), set()
    for line in lines(path):
        kind = line[:2]
        if kind == "L\t":
            f = line.split("\t")
            links.add(edge(handle(f[1], f[2]), handle(f[3], f[4])))
            continue
        if kind == "P\t":
            hs = [handle(s[:-1], s[-1]) for s in line.split("\t")[2].split(",")]
        elif kind == "W\t":
            walk = line.rstrip("\n").split("\t")[6]
            hs = [handle(n, "-" if d == "<" else "+") for d, n in WALK_STEP.findall(walk)]
        else:
            continue
        traversed.update(edge(a, b) for a, b in zip(hs, hs[1:]))
    untraversed = len(links - traversed)
    print(f"{len(links)} links; {untraversed} traversed by no path "
          f"({100 * untraversed / max(len(links), 1):.3f}%)")
    print(f"{len(traversed - links)} distinct path steps between nodes no L line joins")


def pairs(es):
    """Edges as node pairs: the index turns a node the reference reads
    reversed to read forward, and the walk files keep the GFA's strands."""
    return {tuple(sorted((a >> 1, b >> 1))) for a, b in es}


def tabix(path, region):
    out = subprocess.run(["tabix", path, region], capture_output=True, text=True, check=True).stdout
    return [line.split("\t") for line in out.splitlines()]


def deltas(column, previous=0):
    out = []
    if column == ".":
        return out, previous
    for token in column.split(","):
        t = int(token.split(":")[0])
        previous += t >> 1
        out.append(previous * 2 + (t & 1))
    return out, previous


def index_cut(prefix, seq, start, end):
    rows = tabix(f"{prefix}.graph.bed.gz", f"{seq}:{start + 1}-{end}")
    nodes = {int(r[4]) for r in rows if r[3] == "N"}
    links = [(handle(r[4][:-1], r[4][-1]), handle(r[5][:-1], r[5][-1])) for r in rows if r[3] == "L"]
    kept = {e for e in links if e[0] >> 1 in nodes or e[1] >> 1 in nodes}
    far = {h >> 1 for e in kept for h in e} - nodes
    kept |= {e for e in links if e[0] >> 1 in far and e[1] >> 1 in far}
    return nodes | far, {edge(*e) for e in kept}


def flipped(route):
    entry, interior, exit_ = route
    return [flip(h) for h in exit_], [flip(h) for h in reversed(interior)], [flip(h) for h in entry]


def chunk_graph(rows):
    """A chunk's nodes and edges, and each piece's (path, piece, first
    handle, last handle), which a reader joins across chunks."""
    nodes, edges_, ends = set(), set(), []
    previous, routes = 0, []
    for r in rows:
        kind = r[3]
        if kind == "ref":
            steps, _ = deltas(r[9])
            nodes.update(h >> 1 for h in steps)
            edges_.update(edge(a, b) for a, b in zip(steps, steps[1:]))
            ends.append(((r[4], r[5]), int(r[7]), steps[0], steps[-1]))
        elif kind == "nodes":
            ids, total = [], 0
            for d in r[4].split(","):
                total += int(d)
                ids.append(total)
            nodes.update(ids)
        elif kind == "route":
            parts = []
            for column in r[4:7]:
                hs, previous = deltas(column, previous)
                parts.append(hs)
            routes.append(tuple(parts))
            route = parts[0] + parts[1] + parts[2]
            nodes.update(h >> 1 for h in route)
            edges_.update(edge(a, b) for a, b in zip(route, route[1:]))
        elif kind == "walk":
            start = int(r[9].split(":")[0])
            last_on_r = start + int(r[10].split(":")[0])
            taken, route_id = [], 0
            if r[11] != ".":
                for token in r[11].split(","):
                    t = int(token.split(":")[0])
                    route_id += t >> 1
                    route = routes[route_id]
                    taken.append(flipped(route) if t & 1 else route)
            first = start
            if taken and not taken[0][0]:
                first = (taken[0][1] + taken[0][2])[0]
            last = last_on_r
            if taken and not taken[-1][2]:
                last = (taken[-1][0] + taken[-1][1])[-1]
            ends.append(((r[4], r[5]), int(r[7]), first, last))
    return nodes, edges_, ends


def joins(ends):
    by_piece = {(path, piece): (first, last) for path, piece, first, last in ends}
    return {
        edge(last, by_piece[(path, piece + 1)][0])
        for (path, piece), (_, last) in by_piece.items()
        if (path, piece + 1) in by_piece
    }


def walk_cut(walks, seq, header, start, end):
    """A reader queries from the chunk before the window's first, and from the
    chunk before each #long pass that overlaps the window."""
    chunk, longs = header
    reach = min([start] + [s for name, s, e in longs if name == seq and s < end and e > start])
    first = max(reach // chunk - 1, 0) * chunk
    rows = tabix(walks, f"{seq}:{first + 1}-{end}")
    by_chunk = defaultdict(list)
    for r in rows:
        by_chunk[int(r[1])].append(r)
    nodes, edges_, ends, detail_nodes = set(), set(), [], set()
    for cs, chunk_rows in by_chunk.items():
        n, e, chunk_ends = chunk_graph(chunk_rows)
        nodes |= n
        edges_ |= e
        ends += chunk_ends
        if any(r[3] == "abridged" for r in chunk_rows):
            records = defaultdict(list)
            for r in tabix(walks, f"{seq}~{cs}"):
                records[r[1]].append(r)
            for record in records.values():
                detail_nodes |= chunk_graph(record)[0]
    return nodes, edges_ | joins(ends), detail_nodes - nodes


def walk_header(walks):
    """The chunk size and each #long pass: (sequence, start, end)."""
    header = subprocess.run(["tabix", "-H", walks], capture_output=True, text=True, check=True).stdout
    chunk = int(re.search(r"chunk:i:(\d+)", header).group(1))
    longs = []
    for line in header.splitlines():
        f = line.split("\t")
        if f[0] == "#long":
            longs.append((f[1], int(f[2]), int(f[3])))
    return chunk, longs


def every_walk_node(walks):
    """Every node any chunk or detail record of the walk file holds."""
    nodes, group, key = set(), [], None
    with gzip.open(walks, "rt") as f:
        for line in f:
            if line.startswith("#"):
                continue
            r = line.rstrip("\n").split("\t")
            if (r[0], r[1]) != key:
                nodes |= chunk_graph(group)[0]
                group, key = [], (r[0], r[1])
            group.append(r)
    return nodes | chunk_graph(group)[0]


def windows(prefix, walks, seq, lo, hi, count, width=10000):
    header = walk_header(walks)
    anywhere = every_walk_node(walks)
    step = (hi - lo - width) // max(count - 1, 1)
    print("start\tindex_nodes\twalk_nodes\tindex_only\twalk_only\tdetail_only\tabsent\tindex_edges\twalk_edges\tindex_only_edges")
    summary = defaultdict(list)
    for i in range(count):
        start = lo + i * step
        end = start + width
        in_nodes, in_edges = index_cut(prefix, seq, start, end)
        wk_nodes, wk_edges, detail = walk_cut(walks, seq, header, start, end)
        in_edges, wk_edges = pairs(in_edges), pairs(wk_edges)
        row = {
            "index_nodes": len(in_nodes),
            "walk_nodes": len(wk_nodes),
            "index_only": len(in_nodes - wk_nodes),
            "walk_only": len(wk_nodes - in_nodes),
            "detail_only": len((in_nodes - wk_nodes) & detail),
            "absent": len(in_nodes - anywhere),
            "index_edges": len(in_edges),
            "walk_edges": len(wk_edges),
            "index_only_edges": len(in_edges - wk_edges),
        }
        for k, v in row.items():
            summary[k].append(v)
        print(start, *row.values(), sep="\t", flush=True)
    print("median", *(statistics.median(v) for v in summary.values()), sep="\t")
    clean = sum(1 for v in summary["index_only"] if v == 0)
    print(f"# {clean} of {count} windows: the walk chunks hold every node the index cut keeps")
    held = sum(1 for v in summary["absent"] if v == 0)
    print(f"# {held} of {count} windows: the walk file holds every node the index cut keeps, somewhere")
    print(f"# {len(anywhere)} nodes in the walk file")


def main(argv):
    if len(argv) >= 2 and argv[0] == "edges":
        edges(argv[1])
    elif len(argv) in (7, 8) and argv[0] == "windows":
        prefix, walks, seq = argv[1:4]
        windows(prefix, walks, seq, *map(int, argv[4:]))
    else:
        sys.exit(__doc__.strip())


if __name__ == "__main__":
    main(sys.argv[1:])
