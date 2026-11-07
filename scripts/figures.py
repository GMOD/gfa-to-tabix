#!/usr/bin/env python3
"""figures.py <gfa-to-tabix binary> [--check]

Runs the tool on docs/figures/*.gfa and redraws docs/figures/*.svg from the
lines it writes. The script draws the overview figure itself, the walks
detail figure by filling the marked regions of its .dot file for Graphviz,
the outputs figure from its .dot file as written, and the walks figures from
the tool's lines and the drawings scripts/bandage-figure.mjs left beside them.
With --check, exits 1 if a figure differs from what the tool writes now.
"""

import difflib
import gzip
import html
import json
import re
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

FIGURES = Path(__file__).resolve().parent.parent / "docs" / "figures"
PREFIX = "hprc"
REF = "GRCh38"
QUERY = ("chr1", 12, 18)

BLUE = ("#e8eef7", "#a9bfe2", "#4a6fa5")
ORANGE = ("#fde6cf", "#f3c08f", "#c77a2b")
PURPLE = ("#ede4f5", "#8a5fb0")
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


def overlaps(row):
    seq, qstart, qend = QUERY
    return row[0] == seq and int(row[1]) < qend and int(row[2]) > qstart


def run_query(segs, links):
    returned = {r[3] for r in segs if overlaps(r)}
    hits = [r for r in links if overlaps(r)]
    ends = [(r[3][:-1], r[4][:-1]) for r in hits]
    kept = {i for i, (a, b) in enumerate(ends) if a in returned or b in returned}
    far = {n for i in kept for n in ends[i]} - returned
    kept |= {i for i, (a, b) in enumerate(ends) if a in far and b in far}
    return {"returned": returned, "hits": hits, "ends": ends, "kept": kept, "far": far}


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


def listing(names):
    names = sorted(names)
    return " and ".join(names) if len(names) < 3 else ", ".join(names[:-1]) + " and " + names[-1]


def overview_svg(node_lines, link_lines):
    """The Tabix query a browser runs for a window, the node and link lines
    it returns, and the graph it draws from them, coloured by the kind of
    line each part came from."""
    # the lines without their kind column, N or L
    segs = [r[:3] + r[4:] for r in node_lines]
    links = [r[:3] + r[4:] for r in link_lines]
    seq, qstart, qend = QUERY
    ink, muted, line, grey = "#1f2328", "#57606a", "#8c959f", "#9aa3ad"
    node_pale, node_ink = "#dafbe1", "#1a7f37"
    link_pale, link_ink = "#f3e8ff", "#8250df"
    mono = "Menlo, Consolas, DejaVu Sans Mono, monospace"
    q = run_query(segs, links)
    kept = [q["hits"][i] for i in sorted(q["kept"])]
    nodes = {r[3]: {"seq": r[5], "start": r[6], "end": r[7], "alt": r[4] != "0"} for r in segs}
    ref = sorted((n for n in nodes if not nodes[n]["alt"]), key=lambda n: int(nodes[n]["start"]))
    edges = [(r[3][:-1], r[4][:-1]) for r in kept]
    alt = next(n for n in nodes if nodes[n]["alt"])
    into = next(a for a, b in edges if b == alt)
    out_ = next(b for a, b in edges if a == alt)
    lo, hi = int(nodes[ref[0]]["start"]), int(nodes[ref[-1]]["end"])
    region = f"{seq}:{qstart + 1}-{qend}"
    out = []

    def say(x, y, s, size=13, fill=ink, anchor="start", weight="normal", font=None):
        family = f' font-family="{font}"' if font else ""
        out.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" text-anchor="{anchor}" '
                   f'font-weight="{weight}"{family}>{s}</text>')

    def rect(x, y, w, h, fill, stroke="none", rx=0):
        out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}" '
                   f'stroke="{stroke}"/>')

    track, track_w, x0 = 48, 120, 196

    def t_of(bp):
        return track + track_w * (bp - lo) / (hi - lo)

    def table(top, command, about, rows, shown, labels, returned, pale, dark):
        """Each line with a bar at the interval Tabix searches; the window
        crosses the bars of the lines the query returns."""
        say(track, top, command, 13, font=mono, weight="bold")
        say(track, top + 19, about, 12, muted)
        top += 50
        char = 7.2
        widths = [max(len(r[i]) for r in shown) for i in range(len(shown[0]))]
        xs = [x0]
        for i, w in enumerate(widths[:-1], 1):
            start = max(k for k in labels if k < i)
            xs.append(max(xs[-1] + (w + 1.5) * char, xs[start] + 5.6 * len(labels[start]) + 14 if i in labels else 0))
        end = xs[-1] + widths[-1] * char
        for i in labels:
            say(xs[i], top, labels[i], 11, muted)
        first, last = top + 24, top + 24 + (len(rows) - 1) * 20
        for i, r in enumerate(rows):
            if returned(r):
                rect(x0 - 6, first + i * 20 - 14, end - x0 + 12, 19, pale)
        rect(t_of(qstart), top - 10, t_of(qend) - t_of(qstart), last - top + 16, HIGHLIGHT)
        for bp in range(lo, hi + 1, 10):
            out.append(f'<line x1="{t_of(bp):.1f}" y1="{top - 3}" x2="{t_of(bp):.1f}" y2="{top + 1}" stroke="{muted}"/>')
            say(t_of(bp), top - 6, bp, 9, muted, "middle")
        for i, r in enumerate(rows):
            y = first + i * 20
            hit = returned(r)
            a, b = t_of(int(r[1])), t_of(int(r[2]))
            rect(a + 1, y - 10, b - a - 2, 10, pale if hit else "white", dark if hit else grey, 2)
            for x, cell in zip(xs, shown[i]):
                say(x, y, cell, 12, ink if hit else grey, font=mono, weight="bold" if hit else "normal")
        return last

    def graph(top):
        left, step, box_w, box_h = 96, 150, 120, 38
        at = {n: (left + (i + 0.5) * step, top + 70) for i, n in enumerate(ref)}
        at[alt] = ((at[into][0] + at[out_][0]) / 2, top)

        def x_of(bp):
            return left + step * (bp - lo) / 10

        axis = top + 70 + box_h / 2 + 22
        rect(x_of(qstart), top + 70 - box_h / 2 - 8, x_of(qend) - x_of(qstart), axis - top - 70 + box_h / 2 + 8, HIGHLIGHT)
        for a, b in edges:
            (ax, ay), (bx, by) = at[a], at[b]
            if ay == by:
                ax, bx = ax + box_w / 2, bx - box_w / 2
            elif ay > by:
                ax, ay, bx = ax + box_w / 4, ay - box_h / 2, bx - box_w / 2
            else:
                ax, bx, by = ax + box_w / 2, bx - box_w / 4, by - box_h / 2
            out.append(f'<line x1="{ax:.1f}" y1="{ay:.1f}" x2="{bx:.1f}" y2="{by:.1f}" stroke="{link_ink}" '
                       f'stroke-width="2" marker-end="url(#head)"/>')
        for n in sorted(q["returned"] | q["far"]):
            x, y = at[n]
            fill, stroke = (node_pale, node_ink) if n in q["returned"] else (link_pale, link_ink)
            rect(x - box_w / 2, y - box_h / 2, box_w, box_h, fill, stroke, 8)
            v = nodes[n]
            say(x, y - 3, n, 13, ink, "middle", "bold")
            say(x, y + 11, coordinate(v["seq"], v["start"], v["end"]), 10, ink, "middle")
        out.append(f'<line x1="{x_of(lo):.1f}" y1="{axis}" x2="{x_of(hi) + 10:.1f}" y2="{axis}" stroke="{muted}" '
                   f'stroke-width="1.5" marker-end="url(#axis)"/>')
        say(x_of(lo) - 8, axis + 4, f"{seq} path", 12, muted, "end", "bold")
        for bp in range(lo, hi + 1, 10):
            out.append(f'<line x1="{x_of(bp):.1f}" y1="{axis - 4}" x2="{x_of(bp):.1f}" y2="{axis + 4}" stroke="{muted}"/>')
            say(x_of(bp), axis + 16, bp, 10, muted, "middle")
        say((x_of(qstart) + x_of(qend)) / 2, axis + 30, f"window {region}", 11, ink, "middle", "bold")
        return axis + 30

    out.append(f'<defs><marker id="head" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">'
               f'<path d="M0,0 L8,4 L0,8 z" fill="{link_ink}"/></marker>'
               f'<marker id="axis" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">'
               f'<path d="M0,0 L8,4 L0,8 z" fill="{muted}"/></marker></defs>')

    say(24, 28, f"1. To show {region}, a browser queries the file gfa-to-tabix writes", 14, weight="bold")
    labels = {0: "interval Tabix searches", 3: "kind", 4: "node", 5: "rank (0 = reference)", 6: "the node's own position"}
    alt_row = next(r for r in segs if r[3] == alt)
    bottom = table(62, f"tabix {PREFIX}.graph.bed.gz {region}",
                   f"N lines, one per node. {alt} is an {nodes[alt]['seq']} allele, so its line spans "
                   f"{coordinate(*alt_row[0:3])}, from {into} to {out_}.",
                   segs, [r[:9] for r in node_lines], labels, lambda r: r[3] in q["returned"], node_pale, node_ink)
    labels = {0: "interval Tabix searches", 3: "kind", 4: "link", 6: "source: position, rank", 10: "target: position, rank"}
    bottom = table(bottom + 24, "",
                   "L lines from the same query, one per link, with the positions of both its nodes.",
                   links, link_lines, labels, lambda r: r in kept, link_pale, link_ink)

    top = bottom + 54
    say(24, top, "2. It draws the graph from the returned lines", 14, weight="bold")
    rect(24, top + 12, 22, 14, node_pale, node_ink, 3)
    say(54, top + 23, f"from N lines: {listing(q['returned'])}", 12, muted)
    rect(330, top + 12, 22, 14, link_pale, link_ink, 3)
    say(360, top + 23, f"from L lines: every edge, and {listing(q['far'])}", 12, muted)
    end = graph(top + 80)

    width, height = 820, int(end + 20)
    head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
            f'font-family="Helvetica, Arial, sans-serif"><rect width="{width}" height="{height}" fill="white"/>')
    return head + "\n" + "\n".join(out) + "\n</svg>\n"


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


def splice(R, routes, first, nsteps, choices):
    pos = R.index(first)
    steps, cells = [R[pos]], [td(R[pos][0], BLUE[0])]
    pending = list(choices)
    while len(steps) < nsteps:
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
                line = route_colors(routes[route_id])[-1]
                bridge = f'<TABLE BORDER="0" CELLSPACING="0" CELLPADDING="0"><TR><TD FIXEDSIZE="TRUE" HEIGHT="3" WIDTH="68" BGCOLOR="{line}"></TD></TR></TABLE>'
                cells += [td(bridge, border=0, cellpadding=0) for _ in range(skipped)]
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

    table = []
    rebuilt = [rebuilt_row(reference, [td(h[0], BLUE[0], width=60) for h in R])]
    route_id = 0
    for row in rows:
        kind, rest = row[3], row[4:]
        meaning, bg = "", None
        if kind == "ref":
            meaning, bg = f"R, the reference path: {' '.join(handle(h) for h in R)}", BLUE[0]
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
            route_id += 1
        elif kind == "walk":
            start = int(rest[5])
            first = (start >> 1, start & 1)
            choices, _ = deltas(rest[6])
            taken = " and ".join(f"route {c}" for c, _ in choices)
            steps, cells = splice(R, routes, first, int(rest[4]), choices)
            meaning = f"follows R from {handle(first)} to {handle(steps[-1])}" + (f" by {taken}" if choices else ", no routes")
            path = rest[0].rsplit("#", 1)[0]
            if [h[0] for h in steps] != w_lines[path]:
                sys.exit(f"figures.py: {path} decodes to {steps}, but its W line visits {w_lines[path]}")
            label = " and ".join(
                f'<FONT POINT-SIZE="11" COLOR="{route_colors(routes[c])[-1]}">route {c}</FONT>' for c, _ in choices
            )
            rebuilt.append(rebuilt_row(path, cells, label))
        columns = " ".join(rest)
        table.append(tr([
            td(kind, bg),
            td(f'<FONT FACE="Courier" POINT-SIZE="11">{columns}</FONT>', align="LEFT"),
            td(meaning, align="LEFT"),
        ]))
    return table, rebuilt


def walks_caption(header, rows):
    tiles = [h for h in header if h[0] == "#unit" and h[4] == "tile"]
    if len(tiles) != 1:
        sys.exit("figures.py: the walks figure expects one tile")
    _, seq, start, end, _, _ = tiles[0]
    text = (
        f"Every row starts with its sequence and the stretch it is about: a walk row its piece's span, the "
        f"tile's ref, nodes and route rows the tile's extent, {seq} {start} {end}. The file holds each distinct "
        "route once, and a walk row lists only the routes its path takes."
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
        arrow(("rows", "cluster_file"), ("rebuilt", "cluster_rebuilt"), f"a read on {contig}\nfetches this tile"),
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


MONO = "Menlo, Consolas, DejaVu Sans Mono, monospace"
SANS = "Helvetica, Arial, sans-serif"
INK, MUTED = "#1f2328", "#57606a"
BANDAGE_FIGURES = ["walks-simple", "walks-leave"]


class Canvas:
    def __init__(self):
        self.out = []

    def say(self, x, y, s, size=12, fill=INK, weight="normal", font=MONO):
        self.out.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" font-weight="{weight}" '
                        f'font-family="{font}" xml:space="preserve">{s}</text>')

    def rect(self, x, y, w, h, fill, rx=0):
        self.out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}"/>')

    def down(self, x, y, h):
        self.out.append(f'<path d="M{x:.1f},{y:.1f} v{h - 8:.1f}" stroke="{MUTED}" stroke-width="2"/>'
                        f'<path d="M{x - 6:.1f},{y + h - 9:.1f} l6,9 l6,-9 z" fill="{MUTED}"/>')

    def svg(self, width, height):
        size = f'width="{width:.0f}" height="{height:.0f}"'
        return (f'<svg xmlns="http://www.w3.org/2000/svg" {size} viewBox="0 0 {width:.0f} {height:.0f}" '
                f'font-family="{SANS}"><rect {size} fill="white"/>\n' + "\n".join(self.out) + "\n</svg>\n")


def mono_line(c, x, y, fields, size=12, bold=(), tint=None):
    """Draws a line's fields two spaces apart; returns its width."""
    text = "  ".join(fields)
    width = 0.602 * size * len(text)
    if tint:
        c.rect(x - 4, y - size * 0.9, width + 8, size * 1.35, tint, 3)
    c.say(x, y, "  ".join(f'<tspan font-weight="bold">{f}</tspan>' if i in bold else f for i, f in enumerate(fields)), size)
    return width


def units_of(lines):
    units = []
    for f in lines:
        if f[0] == "#unit":
            units.append((f, []))
        elif units:
            units[-1][1].append(f)
    return units


def decode_tile(rows):
    """One tile's ref rows as the reference's node ids, and each walk row's
    node ids by its path and piece."""
    reference = [h[0] for r in sorted((r for r in rows if r[3] == "ref"), key=lambda r: int(r[6])) for h in deltas(r[9])[0]]
    routes, prev = [], 0
    for r in rows:
        if r[3] == "route":
            entry, prev = deltas(r[4], prev)
            interior, prev = deltas(r[5], prev)
            exit_, prev = deltas(r[6], prev)
            routes.append((entry[0] if entry else None, interior, exit_[0] if exit_ else None))
    on_ref = [h for r in sorted((r for r in rows if r[3] == "ref"), key=lambda r: int(r[6])) for h in deltas(r[9])[0]]
    walks = {}
    for r in rows:
        if r[3] == "walk":
            if ":" in r[10] or "@" in r[10] or "@" in r[9]:
                sys.exit("figures.py: the Bandage figures expect no repeated reference nodes")
            taken = [flipped(routes[i]) if flip else routes[i] for i, flip in deltas(r[10])[0]]
            pos = on_ref.index((int(r[9]) >> 1, int(r[9]) & 1))
            steps = list(taken[0][1]) if taken and taken[0][0] is None else []
            steps.append(on_ref[pos])
            ended = False
            for entry, interior, exit_ in (t for t in taken if t[0] is not None):
                while on_ref[pos] != entry:
                    pos += 1
                    steps.append(on_ref[pos])
                steps += interior
                ended = exit_ is None
                if not ended:
                    pos = on_ref.index(exit_)
                    steps.append(on_ref[pos])
            while not ended and len(steps) < int(r[8]):
                pos += 1
                steps.append(on_ref[pos])
            walks[r[4], int(r[7])] = [h[0] for h in steps]
    return reference, walks


def check_cut(lines, cut):
    """Exits unless the cut graph-walks drew holds each path as the walk
    file's rows decode it, its pieces joined in order."""
    decoded, reference = {}, []
    for unit, rows in units_of(lines):
        if unit[4] == "tile":
            ref, walks = decode_tile(rows)
            reference += ref
            decoded |= walks
    paths = {next(r for _, rs in units_of(lines) for r in rs if r[3] == "ref")[4]: reference}
    for (path, piece) in sorted(decoded, key=lambda k: k[1]):
        paths.setdefault(path, []).extend(decoded[path, piece])
    drawn = {f"{f[1]}#{f[2]}#{f[3]}": [int(n) for n in f[6].replace("<", ">").split(">") if n]
             for f in (line.split("\t") for line in cut.splitlines()) if f[0] == "W"}
    if drawn != paths:
        sys.exit(f"figures.py: the drawn cut's walks {drawn} differ from the walk file's {paths}; "
                 "run scripts/bandage-figure.mjs to redraw them")


def bandage_drawing(svg):
    """bandage-core's figure, less any key above its first panel's title, as
    an element and its height."""
    head = re.match(r'<svg [^>]*width="(\d+)" height="(\d+)"[^>]*>', svg)
    width, height = int(head[1]), int(head[2])
    first = re.search(r'<g transform="translate\(6 (\d+)\)"[^>]*><rect[^>]*url\(#key0\)', svg)
    top = int(first[1]) - 2 if first else 0
    inner = svg[head.end() : svg.rindex("</svg>")]
    return width, height - top, (f'viewBox="0 {top} {width} {height - top}" width="{width}" height="{height - top}">'
                                 f"{inner}</svg>")


def bandage_spec(name):
    """The options and region scripts/bandage-figure.mjs drew `name` with,
    from the metadata of its drawing."""
    svg = (FIGURES / f"{name}-bandage.svg").read_text()
    return json.loads(html.unescape(re.search(r"<metadata>(.*?)</metadata>", svg)[1]))["spec"]


def overlaps_region(fields, start, end):
    a, b = int(fields[2]), int(fields[3])
    return a < end and max(b, a + 1) > start


def byte_range(offset, length):
    return f"bytes {offset}-{offset + length - 1}"


def bandage_figure(name, lines, directory, tint):
    """The GFA's W lines, the command, the walk file's directory line, table
    entries and units a read of the region fetches, and bandage-core's
    drawing of graph-walks' cut there."""
    cut = (FIGURES / f"{name}-cut.gfa").read_text()
    check_cut(lines, cut)
    width, height, drawing = bandage_drawing((FIGURES / f"{name}-bandage.svg").read_text())
    spec = bandage_spec(name)
    contig, start, end = spec["region"]["refName"], spec["region"]["start"], spec["region"]["end"]
    sequence = next(f for f in directory if not f[0].startswith("#") and f[0].endswith(f"#{contig}"))
    units = units_of(lines)
    table = next(rows for unit, rows in units if unit[4] == "table" and unit[1] == sequence[0])
    entries = [e for e in table if overlaps_region(e, start, end)]
    fetched = [(unit, rows) for unit, rows in units
               if unit[4] not in ("table", "header") and any(e[4:6] == unit[4:6] for e in entries)]
    c = Canvas()
    left, y, widest = 24, 28, width

    def heading(text):
        nonlocal y
        c.say(left, y, text, 13, weight="bold")

    def show(fields, bold, size=11.5, tinted=None):
        nonlocal y, widest
        y += 20
        widest = max(widest, mono_line(c, left + 12, y, fields, size, bold, tinted))

    def arrow(label):
        nonlocal y
        c.down(left + 18, y + 12, 34)
        c.say(left + 40, y + 34, label, 12, weight="bold")
        y += 78

    heading(f"{name}.gfa")
    for w in (line.split("\t") for line in (FIGURES / f"{name}.gfa").read_text().splitlines()):
        if w[0] == "W":
            show(w, {4, 5}, 12)
    arrow(" ".join(["gfa-to-tabix", f"{name}.gfa", *spec["options"], "-o", PREFIX]))
    heading(f"{PREFIX}.{REF}.walks.gz.idx")
    show(sequence, {1, 2})
    arrow(byte_range(int(sequence[1]), int(sequence[2])))
    heading(f"{PREFIX}.{REF}.walks.gz")
    for e in table:
        show(e, {2, 3, 6, 7} if e in entries else set())
    spans = []
    for e in sorted(entries, key=lambda e: int(e[6])):
        offset, length = int(e[6]), int(e[7])
        spans = (spans[:-1] + [(spans[-1][0], offset + length - spans[-1][0])]
                 if spans and sum(spans[-1]) == offset else spans + [(offset, length)])
    ranges = ", ".join(byte_range(offset, length) for offset, length in spans)
    arrow(f"{contig}:{start + 1}-{end}: {ranges}")
    heading(f"{PREFIX}.{REF}.walks.gz")
    for unit, rows in fetched:
        show(unit, {4, 5})
        for f in rows:
            show(f, {1, 2}, tinted=tint(f))
    arrow("graph-walks, bandage-core")
    y -= 18
    c.out.append(f'<svg x="{left}" y="{y}" {drawing}')
    return c.svg(left + widest + 36, y + height + 12)


def generate(binary):
    with tempfile.TemporaryDirectory() as tmp:
        out = f"{tmp}/{PREFIX}"
        quiet = dict(check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run([binary, FIGURES / "overview.gfa", "-o", out], **quiet)
        rows = read_rows(f"{out}.graph.bed.gz")
        segs, links = [r for r in rows if r[3] == "N"], [r for r in rows if r[3] == "L"]
        subprocess.run([binary, FIGURES / "walks.gfa", "--walks", "--refs", REF, "-o", out], **quiet)
        walk_file = f"{out}.{REF}.walks.gz"
        walk_rows, header = read_rows(walk_file), read_header(walk_file)
        built, directories = {}, {}
        for name in BANDAGE_FIGURES:
            subprocess.run([binary, FIGURES / f"{name}.gfa", *bandage_spec(name)["options"], "-o", out], **quiet)
            with gzip.open(walk_file, "rt") as f:
                built[name] = [line.rstrip("\n").split("\t") for line in f]
            directories[name] = [line.split("\t") for line in Path(f"{walk_file}.idx").read_text().splitlines()]
    lengths, gfa_links, paths, contigs = read_gfa(FIGURES / "walks.gfa")
    table, rebuilt = walks(walk_rows, paths)
    walks_nodes, walks_arrows = walks_graph(lengths, gfa_links, paths, contigs)
    return {
        "walks-simple-figure": bandage_figure("walks-simple", built["walks-simple"], directories["walks-simple"],
                                              lambda f: None),
        "walks-leave-figure": bandage_figure("walks-leave", built["walks-leave"], directories["walks-leave"],
                                             lambda f: HIGHLIGHT if f[3] == "departure" else None),
        "outputs": {},
        "overview": overview_svg(segs, links),
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
        if isinstance(regions, str):
            if not check:
                svg.write_text(regions)
            elif svg.read_text() != regions:
                stale = True
                print(f"{svg}: differs from the tool's output")
            continue
        old = dot.read_text()
        new = splice_regions(old, regions, dot.name)
        if check:
            if new != old:
                stale = True
                sys.stdout.writelines(difflib.unified_diff(
                    old.splitlines(True), new.splitlines(True), str(dot), "from the tool"))
            continue
        dot.write_text(new)
        drawing = subprocess.run(["dot", "-Tsvg", dot], check=True, capture_output=True, text=True).stdout
        svg.write_text(drawing)
    if stale:
        sys.exit("figures.py: docs/figures is stale; run scripts/figures.py <binary> to redraw it")


if __name__ == "__main__":
    main()
