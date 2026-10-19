#!/usr/bin/env python3
"""figures.py <gfa-to-tabix binary> [--check]

Runs the tool on docs/figures/*.gfa, writes the rows it outputs into the
marked regions of docs/figures/*.dot and redraws the SVGs with Graphviz.
With --check, exits 1 if a .dot file or a drawn panel differs from what the
tool writes now.
"""

import difflib
import gzip
import math
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

FIGURES = Path(__file__).resolve().parent.parent / "docs" / "figures"
PREFIX = "graph"
REF = "GRCh38"
QUERY = ("chr1", 25, 30)
BP_PER_CELL = 2.5
TICK_BP = 10

BLUE = ("#e8eef7", "#a9bfe2", "#4a6fa5")
ORANGE = ("#fde6cf", "#f3c08f", "#c77a2b")
PURPLE = ("#ede4f5", "#8a5fb0")
GREY = "#e4e4e4"
KEPT = "#c4c4c4"
HIGHLIGHT = "#fff3b0"


def read_rows(path):
    with gzip.open(path, "rt") as f:
        return [line.rstrip("\n").split("\t") for line in f if not line.startswith("#")]


def read_header(path):
    with gzip.open(path, "rt") as f:
        return [line.rstrip("\n").split("\t") for line in f if line.startswith("#")]


def td(text="", bg=None, bold=False, **attrs):
    attrs = "".join(f' {k.upper()}="{v}"' for k, v in attrs.items())
    if bg:
        attrs += f' BGCOLOR="{bg}"'
    return f"<TD{attrs}>{f'<B>{text}</B>' if bold and text else text}</TD>"


def tr(cells, bg=None):
    attr = f' BGCOLOR="{bg}"' if bg else ""
    return f"<TR{attr}>{''.join(cells)}</TR>"


def caption(cols, text, width, color="#555555"):
    lines = "<BR/>".join(line for para in text.split("\n") for line in textwrap.wrap(para, width))
    return tr([td(f'<FONT POINT-SIZE="12" COLOR="{color}">{lines}</FONT>', border=0, cellpadding=8, colspan=cols, align="LEFT", balign="LEFT")])


def link_ends(row):
    return tuple(
        {"name": row[i][:-1], "seq": row[j], "start": row[j + 1], "end": row[j + 2], "rank": row[j + 3]}
        for i, j in ((3, 5), (4, 9))
    )


def segs_caption(segs, links):
    off = next(r for r in segs if r[4] != "0")
    name, seq, start, end = off[3], off[0], off[1], off[2]
    attached = []
    for end_a, end_b in (link_ends(row) for row in links):
        for this, other in ((end_a, end_b), (end_b, end_a)):
            if this["name"] == name and other["rank"] == "0":
                attached.append((int(other["start"]), other["name"]))
    attached.sort()
    first, last = attached[0][1], attached[-1][1]
    text = f"{name} lies off {seq}, so the tool files it under the reference span it hangs from: {first} to {last}, {coordinate(seq, start, end)}."
    return [caption(4, text, 64, "#a15f1c")]


def simple_caption(segs):
    off = next(r for r in segs if r[4] != "0")
    span = coordinate(*off[0:3])
    text = (
        f"{off[3]} lies off {off[0]}, so the tool files it under the span it hangs from, {span}.\n"
        f"The tool files each link in {PREFIX}.links.bed.gz under the span its two nodes cover."
    )
    return [caption(20, text, 84, "#555555")]


def segs_table(segs):
    rows = []
    for row in segs:
        off = row[4] != "0"
        cells = [td(coordinate(*row[0:3]), bold=off), td(row[3]), td(row[4]), td(coordinate(*row[5:8]))]
        rows.append(tr(cells, ORANGE[0] if off else BLUE[0]))
    return rows


def links_table(links):
    rows = []
    for row in links:
        ends = [td(coordinate(*row[i:i + 3]), ORANGE[0] if row[i + 3] != "0" else None) for i in (5, 9)]
        rows.append(tr([td(coordinate(*row[0:3])), td(f"{row[3]} → {row[4]}"), *ends], "#f2f2f2"))
    return rows


def cell(bp):
    return int(int(bp) / BP_PER_CELL)


def lanes(segs, links, with_links=True):
    seq, qstart, qend = QUERY
    cells = cell(max(int(r[2]) for r in segs + links))
    query = range(cell(qstart), cell(qend))

    def bars(start, end, color):
        fills = []
        for i in range(cells):
            fills.append(color if cell(start) <= i < cell(end) else HIGHLIGHT if i in query else None)
        runs, i = [], 0
        while i < cells:
            j = i
            while j < cells and fills[j] == fills[i]:
                j += 1
            runs.append(td(bg=fills[i], **({"colspan": j - i} if j > i + 1 else {})))
            i = j
        return "".join(runs)

    def lane(label, start, end, color, note, shown):
        text = f"<B>{label}</B>" if shown else f'<FONT COLOR="#999999">{label}</FONT>'
        note = f'<FONT POINT-SIZE="12" COLOR="#777777">  {note}</FONT>' if note else ""
        gap = "".join(td(bg=HIGHLIGHT if i in query else None) for i in range(cells))
        return [
            f'<TR><TD HEIGHT="5"></TD><TD></TD>{gap}<TD></TD><TD></TD></TR>',
            f'<TR><TD ALIGN="RIGHT" HEIGHT="18">{text}  </TD><TD></TD>{bars(start, end, color)}<TD></TD><TD ALIGN="LEFT">{note}</TD></TR>',
        ]

    def heading(text):
        return f'<TR><TD COLSPAN="{cells + 4}" ALIGN="LEFT" HEIGHT="26" VALIGN="BOTTOM"><I>{text}</I></TD></TR>'

    tick_cells = cell(TICK_BP)
    ticks = [
        f'<TD COLSPAN="2"><FONT POINT-SIZE="10" COLOR="#777777">{bp}</FONT></TD>'
        for bp in range(0, int(cells * BP_PER_CELL) + 1, TICK_BP)
    ]
    rows = [
        tr([td(), td(width=16), *[td(width=16) for _ in range(cells)], td(width=16), td()]),
        tr([td(), td(colspan=tick_cells - 2).join(ticks), td()]),
        tr([td(height=1), td(), td(bg="#999999", colspan=cells), td(), td()]),
    ]
    rows += lane(coordinate(seq, qstart, qend), qstart, qend, "#555555", "query", True)

    q = run_query(segs, links)
    rows.append(heading(f"{PREFIX}.segs.bed.gz"))
    for row in segs:
        hit = row[3] in q["returned"]
        color = (ORANGE if row[4] != "0" else BLUE)[1] if hit else GREY
        rows += lane(row[3], row[1], row[2], color, "returned" if hit else "", hit)

    if not with_links:
        return rows
    hits = q["hits"]
    count = "all" if len(hits) == len(links) else f"{len(hits)} of"
    rows.append(heading(f"{PREFIX}.links.bed.gz: {count} {len(links)} rows return"))
    for i, row in enumerate(hits):
        keep = i in q["kept"]
        rows += lane(link_label(row), row[1], row[2], KEPT if keep else GREY, "kept" if keep else "dropped", keep)
    return rows


def overlaps(row):
    seq, qstart, qend = QUERY
    return row[0] == seq and int(row[1]) < qend and int(row[2]) > qstart


def link_label(row):
    return f"{row[3][:-1]}→{row[4][:-1]}"


def run_query(segs, links):
    returned = {r[3] for r in segs if overlaps(r)}
    hits = [r for r in links if overlaps(r)]
    ends = [(r[3][:-1], r[4][:-1]) for r in hits]
    kept = {i for i, (a, b) in enumerate(ends) if a in returned or b in returned}
    far = {n for i in kept for n in ends[i]} - returned
    kept |= {i for i, (a, b) in enumerate(ends) if a in far and b in far}
    return {"returned": returned, "hits": hits, "ends": ends, "kept": kept, "far": far}


def keep_caption(segs, links):
    q = run_query(segs, links)
    text = "The reader keeps a link when the node file returned one of its nodes, or when both its nodes are far ends of links it kept."
    for i, row in enumerate(q["hits"]):
        if i not in q["kept"]:
            loose = next(n for n in q["ends"][i] if n not in q["returned"] | q["far"])
            text += f" {link_label(row)} fails both tests, since no kept link ends at {loose}."
    return [caption(20, text, 92)]


def bubble(prefix, ref, labels, edges):
    alts = [n for n in labels if n not in ref]
    centre = prefix + ref[len(ref) // 2]
    lines = []
    for name in ref + alts:
        attrs = [f'label=<<B>{name}</B><BR/><FONT POINT-SIZE="10">{labels[name]}</FONT>>']
        if name in alts:
            attrs += [f'fillcolor="{ORANGE[0]}"', f'color="{ORANGE[2]}"']
        lines.append(f"{prefix}{name} [{', '.join(attrs)}]")
    lines.append(f"{{rank=same; {'; '.join(prefix + n for n in ref)}}}")
    skips = [(a, b) for a, b in edges if a in ref and b in ref and abs(ref.index(a) - ref.index(b)) > 1]
    for a, b in edges:
        if (a, b) in skips:
            lines.append(f'{prefix}{a}:s -> {prefix}{b}:s [color="{PURPLE[1]}", constraint=false]')
        elif a in ref and b in ref:
            lines.append(f"{prefix}{a} -> {prefix}{b} [weight=20]")
        else:
            lines.append(f'{prefix}{a} -> {prefix}{b} [color="{ORANGE[2]}", constraint=false]')
    for name in alts:
        linked = [ref.index(e) for edge in edges if name in edge for e in edge if e in ref]
        middle = ref[(min(linked) + max(linked)) // 2]
        lines.append(f"{prefix}{name} -> {prefix}{middle} [style=invis, weight=20]")
    bottom = centre
    if skips:
        bottom = f"{prefix}below"
        lines += [f'{bottom} [style=invis, label="", width=0, height=0]', f"{centre} -> {bottom} [style=invis]"]
    return lines, bottom


def arrow(tail, head, label):
    (tail, tail_cluster), (head, head_cluster) = tail, head
    label = "\\n".join(f"  {line}" for line in label.split("\n"))
    return f'{tail} -> {head} [ltail={tail_cluster}, lhead={head_cluster}, label="{label}", penwidth=2]'


def coordinate(seq, start, end):
    return f"{seq}:{start}-{end}"


def coordinates(nodes):
    return {n: coordinate(v["seq"], v["start"], v["end"]) for n, v in nodes.items()}


def ref_order(nodes):
    return sorted((n for n in nodes if nodes[n]["rank"] == "0"), key=lambda n: int(nodes[n]["start"]))


def force_layout(lengths, seeds, edges, px_per_bp=8, bp_per_point=5, steps=800):
    """Lays out each node as a chain of points, as Bandage does. Springs hold
    chains and links together, and points of different nodes repel."""
    pts, chains, springs, owner = [], {}, [], []
    for name, bp in lengths.items():
        n = max(2, round(bp / bp_per_point))
        step = bp * px_per_bp / n
        x, y = seeds[name]
        chains[name] = list(range(len(pts), len(pts) + n + 1))
        pts += [[x + k * step, y] for k in range(n + 1)]
        owner += [name] * (n + 1)
        springs += [(a, b, step, 1.0) for a, b in zip(chains[name], chains[name][1:])]
        springs += [(a, b, 2 * step, 1.0) for a, b in zip(chains[name], chains[name][2:])]
    springs += [(chains[a][-1], chains[b][0], 10, 1.0) for a, b in edges]

    def push(disp, i, j, f, dx, dy, d):
        disp[i][0] += f * dx / d
        disp[i][1] += f * dy / d
        disp[j][0] -= f * dx / d
        disp[j][1] -= f * dy / d

    for it in range(steps):
        disp = [[0.0, 0.0] for _ in pts]
        for i in range(len(pts)):
            for j in range(i + 1, len(pts)):
                if owner[i] == owner[j]:
                    continue
                dx, dy = pts[i][0] - pts[j][0], pts[i][1] - pts[j][1]
                d2 = max(dx * dx + dy * dy, 1.0)
                push(disp, i, j, 1600 / d2, dx, dy, math.sqrt(d2))
        for a, b, rest, k in springs:
            dx, dy = pts[a][0] - pts[b][0], pts[a][1] - pts[b][1]
            d = max(math.hypot(dx, dy), 0.01)
            push(disp, a, b, -k * (d - rest), dx, dy, d)
        cap = 6 * (1 - it / steps) + 0.1
        for p, (dx, dy) in zip(pts, disp):
            scale = min(0.3, cap / max(math.hypot(dx, dy), 1e-9))
            p[0] += dx * scale
            p[1] += dy * scale
    return {name: [tuple(pts[i]) for i in chain] for name, chain in chains.items()}


def catmull_rom(points, per=8):
    p = [points[0], *points, points[-1]]
    out = [points[0]]
    for a, b, c, d in zip(p, p[1:], p[2:], p[3:]):
        for k in range(1, per + 1):
            t = k / per
            out.append(tuple(
                0.5 * (2 * b[i] + (c[i] - a[i]) * t + (2 * a[i] - 5 * b[i] + 4 * c[i] - d[i]) * t * t
                       + (3 * b[i] - a[i] - 3 * c[i] + d[i]) * t * t * t)
                for i in (0, 1)
            ))
    return out


def polyline(points):
    return "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in points)


def portion(points, f0, f1):
    cuts = [0.0]
    for a, b in zip(points, points[1:]):
        cuts.append(cuts[-1] + math.dist(a, b))

    def at(f):
        s = f * cuts[-1]
        i = next(i for i in range(len(points) - 1) if s <= cuts[i + 1])
        t = (s - cuts[i]) / (cuts[i + 1] - cuts[i])
        (ax, ay), (bx, by) = points[i], points[i + 1]
        return i, (ax + t * (bx - ax), ay + t * (by - ay))

    (i0, p0), (i1, p1) = at(f0), at(f1)
    return [p0, *points[i0 + 1 : i1 + 1], p1]


def text(x, y, label, size, bold=False):
    weight = ' font-weight="bold"' if bold else ""
    return f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="middle" font-family="Helvetica,sans-Serif" font-size="{size}"{weight}>{label}</text>'


def bandage(nodes, edges, pad=36, width=14):
    """Draws nodes as tubes as long as their sequence, as Bandage and the
    JBrowse graph view do."""
    paths = force_layout({n: v["bp"] for n, v in nodes.items()}, {n: v["seed"] for n, v in nodes.items()}, edges)
    xs = [x for p in paths.values() for x, _ in p]
    ys = [y for p in paths.values() for _, y in p]
    left, top = min(xs) - pad - 20, min(ys) - pad
    paths = {n: catmull_rom([(x - left, y - top) for x, y in p]) for n, p in paths.items()}
    cx, cy = (max(xs) + min(xs)) / 2 - left, (max(ys) + min(ys)) / 2 - top
    body = []
    for a, b in edges:
        (ax, ay), (x0, y0) = paths[a][-2:]
        (x1, y1), (bx, by) = paths[b][:2]
        reach = math.dist((x0, y0), (x1, y1)) / 4
        u0, u1 = reach / math.dist((ax, ay), (x0, y0)), reach / math.dist((bx, by), (x1, y1))
        c0 = (x0 + (x0 - ax) * u0, y0 + (y0 - ay) * u0)
        c1 = (x1 + (x1 - bx) * u1, y1 + (y1 - by) * u1)
        color = ORANGE[2] if nodes[a]["alt"] or nodes[b]["alt"] else "#555555"
        body.append(
            f'<path d="M{x0:.1f},{y0:.1f} C{c0[0]:.1f},{c0[1]:.1f} {c1[0]:.1f},{c1[1]:.1f} {x1:.1f},{y1:.1f}" '
            f'fill="none" stroke="{color}" stroke-width="1.5"/>'
        )
    halo = width + 12
    for name, v in nodes.items():
        if v["query"]:
            body.insert(0, f'<path d="{polyline(portion(paths[name], *v["query"]))}" fill="none" stroke="{HIGHLIGHT}" stroke-width="{halo}"/>')
    for name, v in nodes.items():
        d = polyline(paths[name])
        dash = ' stroke-dasharray="5,2"' if v["far"] else ""
        body.append(f'<path d="{d}" fill="none" stroke="{v["line"]}" stroke-width="{width}"{dash}/>')
        body.append(f'<path d="{d}" fill="none" stroke="{v["fill"]}" stroke-width="{width - 3}"/>')
        mid = len(paths[name]) // 2
        (ax, ay), (mx, my), (bx, by) = paths[name][mid - 1 : mid + 2]
        nx, ny = ay - by, bx - ax
        if nx * (mx - cx) + ny * (my - cy) < 0:
            nx, ny = -nx, -ny
        d = math.hypot(nx, ny)
        x, y = mx + nx / d * (halo / 2 + 4), my + ny / d * (halo / 2 + 4)
        if ny > 0:
            body += [text(x, y + 11, name, 12, bold=True), text(x, y + 23, v["label"], 10)]
        else:
            body += [text(x, y - 14, name, 12, bold=True), text(x, y - 2, v["label"], 10)]
    w, h = max(xs) - left + pad + 20, max(ys) - top + pad
    return w, h, "\n".join(body)


def overview_graphs(segs, links):
    nodes = {r[3]: {"seq": r[5], "start": r[6], "end": r[7], "rank": r[4]} for r in segs}
    graph, graph_bottom = bubble("", ref_order(nodes), coordinates(nodes), [(r[3][:-1], r[4][:-1]) for r in links])

    q = run_query(segs, links)
    drawn = {n: nodes[n] for n in nodes if n in q["returned"]}
    for i in sorted(q["kept"]):
        for end in link_ends(q["hits"][i]):
            drawn.setdefault(end["name"], end)
    edges = [q["ends"][i] for i in sorted(q["kept"])]
    far = set(drawn) - q["returned"]

    seq, qstart, qend = QUERY
    ref = ref_order(drawn)
    seeds = {n: (80 * i, 0) for i, n in enumerate(ref)}
    for n in drawn:
        if n not in ref:
            linked = [seeds[e][0] for edge in edges if n in edge for e in edge if e in ref]
            seeds[n] = (sum(linked) / len(linked), -40)
    tubes = {}
    for n, v in drawn.items():
        start, end = int(v["start"]), int(v["end"])
        lo, hi = max(start, qstart), min(end, qend)
        alt = v["rank"] != "0"
        tubes[n] = {
            "bp": end - start,
            "seed": seeds[n],
            "label": coordinate(v["seq"], start, end),
            "alt": alt,
            "far": n in far,
            "line": (ORANGE if alt else BLUE)[2],
            "fill": BLUE[0] if n in far else (ORANGE if alt else BLUE)[1],
            "query": ((lo - start) / (end - start), (hi - start) / (end - start)) if v["seq"] == seq and lo < hi else None,
        }
    w, h, panel = bandage(tubes, edges)
    drawn = [f'drawn [shape=box, style="", color=transparent, label="", fixedsize=true, width={w / 72:.2f}, height={h / 72:.2f}]']

    detail = [
        arrow((graph_bottom, "cluster_graph"), ("rows", "cluster_files"), f"gfa-to-tabix {PREFIX}.gfa"),
        arrow(("rows", "cluster_files"), ("hits", "cluster_query"), f"a browser queries\n{coordinate(seq, qstart, qend)}"),
        arrow(("hits", "cluster_query"), ("drawn", "cluster_drawn"), "kept rows"),
    ]
    simple = [
        arrow((graph_bottom, "cluster_graph"), ("hits", "cluster_query"), f"gfa-to-tabix {PREFIX}.gfa"),
        arrow(("hits", "cluster_query"), ("drawn", "cluster_drawn"), f"the rows returned, plus\ntheir links from {PREFIX}.links.bed.gz"),
    ]
    return graph, drawn, detail, simple, panel


def tokens(column):
    return [] if column == "." else [int(t) for t in column.split(",")]


def deltas(column, prev=0):
    """Decodes 2 × (value − previous) + bit tokens into (value, bit) pairs."""
    out = []
    for t in tokens(column):
        bit = t & 1
        prev += (t - bit) // 2
        out.append((prev, bit))
    return out, prev


def handle(h):
    return f"{h[0]}{'-' if h[1] else '+'}"


def flipped(route):
    entry, interior, exit_ = route
    rev = lambda h: h and (h[0], 1 - h[1])
    return rev(exit_), [rev(h) for h in reversed(interior)], rev(entry)


def route_colors(route):
    return ORANGE if route[1] else PURPLE


def decode_walks(rows):
    refs = [r for r in rows if r[3] == "ref"]
    if len(refs) != 1:
        sys.exit("figures.py: the walks figure expects one ref row")
    R, _ = deltas(refs[0][9])
    routes, prev = [], 0
    for row in rows:
        if row[3] == "route":
            entry, prev = deltas(row[4], prev)
            interior, prev = deltas(row[5], prev)
            exit_, prev = deltas(row[6], prev)
            routes.append((entry[0] if entry else None, interior, exit_[0] if exit_ else None))
    return R, routes


def splice(R, routes, first, last, choices):
    pos = R.index(first)
    steps, cells = [R[pos]], [td(R[pos][0], BLUE[0])]
    pending = list(choices)
    while R[pos] != last or pending:
        route = None
        if pending:
            route_id, flip = pending[0]
            route = flipped(routes[route_id]) if flip else routes[route_id]
        if route and route[0] == R[pos]:
            _, interior, exit_ = route
            bg = route_colors(routes[pending.pop(0)[0]])[0]
            skipped = R.index(exit_) - pos - 1
            steps += interior
            if len(interior) == skipped:
                cells += [td(h[0], bg) for h in interior]
            elif not interior:
                cells += [td(border=0) for _ in range(skipped)]
            else:
                cells.append(td(" ".join(str(h[0]) for h in interior), bg, colspan=max(skipped, 1)))
            pos = R.index(exit_)
        else:
            pos += 1
        steps.append(R[pos])
        cells.append(td(R[pos][0], BLUE[0]))
    return steps, cells


def walks(rows, w_lines):
    R, routes = decode_walks(rows)
    reference = next(r for r in rows if r[3] == "ref")[4].rsplit("#", 1)[0]

    def rebuilt_row(path, cells, label=""):
        return tr([td(path, border=0, align="RIGHT"), *cells, td(label, border=0, align="LEFT")])

    def node(h):
        return f"{h[0]}{'-' if h[1] else ''}"

    table, simple = [], []
    rebuilt = [rebuilt_row(reference, [td(h[0], BLUE[0], width=60) for h in R])]
    route_id = 0
    for row in rows:
        kind, rest = row[3], row[4:]
        meaning, bg = "", None
        if kind == "ref":
            meaning, bg = f"R, the reference path: {' '.join(handle(h) for h in R)}", BLUE[0]
            simple.append(tr([td(reference, bg), td(" → ".join(node(h) for h in R), align="LEFT")]))
        elif kind == "nodes":
            ids, total = [], 0
            for d in rest[0].split(","):
                total += int(d)
                ids.append(total)
            listed = ", ".join(f"{i}, {n} bp" for i, n in zip(ids, rest[1].split(",")))
            meaning = f"node {listed}, the one node a route visits" if len(ids) == 1 else f"nodes routes visit: {listed}"
        elif kind == "route":
            entry, interior, exit_ = routes[route_id]
            via = f"through {' '.join(handle(h) for h in interior)} to" if interior else "straight to"
            meaning = f"route {route_id}: from {handle(entry)} {via} {handle(exit_)}"
            bg = route_colors(routes[route_id])[0]
            nodes = [entry, *interior, exit_]
            simple.append(tr([td(f"route {route_id}", bg), td(" → ".join(node(h) for h in nodes if h), align="LEFT")]))
            route_id += 1
        elif kind == "walk":
            start, end = int(rest[5]), int(rest[5]) + int(rest[6])
            first, last = (start >> 1, start & 1), (end >> 1, end & 1)
            choices, _ = deltas(rest[7])
            taken = " and ".join(f"route {c}" for c, _ in choices)
            meaning = f"follows R from {handle(first)} to {handle(last)}" + (f" by {taken}" if choices else ", no routes")
            steps, cells = splice(R, routes, first, last, choices)
            path = rest[0].rsplit("#", 1)[0]
            if [h[0] for h in steps] != w_lines[path]:
                sys.exit(f"figures.py: {path} decodes to {steps}, but its W line visits {w_lines[path]}")
            label = " and ".join(
                f'<FONT POINT-SIZE="11" COLOR="{route_colors(routes[c])[-1]}">route {c}</FONT>' for c, _ in choices
            )
            rebuilt.append(rebuilt_row(path, cells, label))
            simple.append(tr([td(path), td(taken or f"{REF}'s path", align="LEFT")]))
        columns = " ".join(rest)
        table.append(tr([
            td(kind, bg),
            td(f'<FONT FACE="Courier" POINT-SIZE="11">{columns}</FONT>', align="LEFT"),
            td(meaning, align="LEFT"),
        ]))
    return table, simple, rebuilt


def chunk_size(header):
    return int(next(f for f in header[0] if f.startswith("chunk:i:")).split(":")[2])


def walks_label(header, rows):
    contig = rows[0][0].rsplit("#", 1)[1]
    grey = '<FONT POINT-SIZE="12" COLOR="#555555">'
    return [
        f'label=<<B>2. {PREFIX}.{REF}.walks.bed.gz</B><BR ALIGN="LEFT"/>'
        f"{grey}per {chunk_size(header) // 1024} kb stretch of {contig}: {REF}'s path and each route off it, once each,</FONT>"
        f'<BR ALIGN="LEFT"/>{grey}and the routes each haplotype takes</FONT><BR ALIGN="LEFT"/>>'
    ]


def walks_caption(header, rows):
    chunk = chunk_size(header)
    starts = {(r[0], r[1]) for r in rows}
    if len(starts) != 1:
        sys.exit("figures.py: the walks figure expects one chunk")
    seq, start = starts.pop()
    text = (
        f"Every row starts {seq} {start} {int(start) + 1}, the chunk's first base, so a query returns whole "
        f"{chunk // 1024} kb chunks. The file holds each distinct route once, and a walk row lists only the routes "
        "its path takes."
    )
    return [caption(3, text, 100)]


def read_gfa(path):
    lengths, links, paths, contigs = {}, [], {}, {}
    with open(path) as f:
        for line in f:
            fields = line.rstrip("\n").split("\t")
            if fields[0] == "S":
                lengths[fields[1]] = len(fields[2])
            elif fields[0] == "L":
                links.append((fields[1], fields[3]))
            elif fields[0] == "W":
                name = f"{fields[1]}#{fields[2]}"
                paths[name] = [int(x) for x in fields[6].replace("<", ">").split(">") if x]
                contigs[name] = (fields[3], int(fields[4]))
    return lengths, links, paths, contigs


def walks_graph(lengths, links, paths, contigs):
    name = next(name for name in paths if name.startswith(f"{REF}#"))
    ref = [str(n) for n in paths[name]]
    labels = {n: f"{length} bp" for n, length in lengths.items()}
    contig, start = contigs[name]
    for n in ref:
        labels[n] = coordinate(contig, start, start + lengths[n])
        start += lengths[n]
    graph, bottom = bubble("n", ref, labels, links)
    arrows = [
        arrow((bottom, "cluster_graph"), ("rows", "cluster_file"), f"gfa-to-tabix --walks\n--refs {REF}"),
        arrow(("rows", "cluster_file"), ("rebuilt", "cluster_rebuilt"), f"a query on {contig}\nreturns these rows"),
    ]
    return graph, arrows


def splice_regions(text, regions, name):
    lines = text.split("\n")
    for region, rows in regions.items():
        begin = [i for i, line in enumerate(lines) if line.strip().endswith(f"begin {region}") or f"begin {region} -->" in line]
        end = [i for i, line in enumerate(lines) if line.strip().endswith(f"end {region}") or f"end {region} -->" in line]
        if len(begin) != 1 or len(end) != 1 or end[0] < begin[0]:
            sys.exit(f"figures.py: {name} needs one begin and one end marker for {region}")
        indent = lines[begin[0]][: len(lines[begin[0]]) - len(lines[begin[0]].lstrip())]
        lines[begin[0] + 1 : end[0]] = [f"{indent}{row}" for row in rows]
    return "\n".join(lines)


def inject(svg, body):
    node = svg.index("<title>drawn</title>")
    points = svg[svg.index('points="', node) + 8 :].split('"', 1)[0]
    xs, ys = zip(*(map(float, p.split(",")) for p in points.split()))
    close = svg.index("</g>", node) + len("</g>")
    group = f'\n<!-- begin bandage -->\n<g transform="translate({min(xs)},{min(ys)})">\n{body}\n</g>\n<!-- end bandage -->'
    return svg[:close] + group + svg[close:]


def drawn_panel(svg):
    begin, end = svg.find("<!-- begin bandage -->"), svg.find("<!-- end bandage -->")
    return "\n".join(svg[begin:end].split("\n")[2:-2]) if begin >= 0 else None


def generate(binary):
    with tempfile.TemporaryDirectory() as tmp:
        out = f"{tmp}/{PREFIX}"
        quiet = dict(check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run([binary, FIGURES / "overview.gfa", "-o", out], **quiet)
        segs, links = read_rows(f"{out}.segs.bed.gz"), read_rows(f"{out}.links.bed.gz")
        subprocess.run([binary, FIGURES / "walks.gfa", "--walks", "--refs", REF, "-o", out], **quiet)
        walk_file = f"{out}.{REF}.walks.bed.gz"
        walk_rows, header = read_rows(walk_file), read_header(walk_file)
    lengths, gfa_links, paths, contigs = read_gfa(FIGURES / "walks.gfa")
    table, simple, rebuilt = walks(walk_rows, paths)
    walks_nodes, walks_arrows = walks_graph(lengths, gfa_links, paths, contigs)
    graph, drawn, arrows, simple_arrows, panel = overview_graphs(segs, links)
    return {
        "overview": {
            "graph": graph,
            "lanes": lanes(segs, links, with_links=False),
            "caption": simple_caption(segs),
            "drawn": drawn,
            "arrows": simple_arrows,
            "svg": panel,
        },
        "overview-detail": {
            "graph": graph,
            "segs": segs_table(segs),
            "segs-caption": segs_caption(segs, links),
            "links": links_table(links),
            "lanes": lanes(segs, links),
            "keep-caption": keep_caption(segs, links),
            "drawn": drawn,
            "arrows": arrows,
            "svg": panel,
        },
        "walks": {
            "graph": walks_nodes,
            "label": walks_label(header, walk_rows),
            "rows": simple,
            "rebuilt": rebuilt,
            "arrows": walks_arrows,
        },
        "walks-detail": {
            "graph": walks_nodes,
            "rows": table,
            "caption": walks_caption(header, walk_rows),
            "rebuilt": rebuilt,
            "arrows": walks_arrows,
        },
    }


def main():
    args = [a for a in sys.argv[1:] if a != "--check"]
    if len(args) != 1:
        sys.exit(__doc__.strip())
    check = "--check" in sys.argv[1:]
    stale = False
    for figure, regions in generate(Path(args[0]).resolve()).items():
        dot, svg = FIGURES / f"{figure}.dot", FIGURES / f"{figure}.svg"
        panel = regions.pop("svg", None)
        old = dot.read_text()
        new = splice_regions(old, regions, dot.name)
        if check:
            if panel is not None and drawn_panel(svg.read_text()) != panel:
                stale = True
                print(f"{svg}: the drawn panel differs from the tool's output")
            if new != old:
                stale = True
                sys.stdout.writelines(difflib.unified_diff(
                    old.splitlines(True), new.splitlines(True), str(dot), "from the tool"))
            continue
        dot.write_text(new)
        drawing = subprocess.run(["dot", "-Tsvg", dot], check=True, capture_output=True, text=True).stdout
        svg.write_text(inject(drawing, panel) if panel is not None else drawing)
    if stale:
        sys.exit("figures.py: docs/figures is stale; run scripts/figures.py <binary> to redraw it")


if __name__ == "__main__":
    main()
