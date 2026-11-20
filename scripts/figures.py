#!/usr/bin/env python3
"""figures.py <gfa-to-tabix binary> [--check]

Runs the tool on docs/figures/*.gfa and redraws docs/figures/*.svg from the
lines it writes. The script draws the overview figure itself, the walks
detail figure by filling the marked regions of its .dot file for Graphviz,
the walks leave figure
from the tool's lines and the drawing scripts/bandage-figure.mjs left beside
them, and the walks tile, bytes and example figures from the tool's lines
alone.
With --check, exits 1 if a figure differs from what the tool writes now.
Either way, exits 1 if docs/walks-format-in-brief.md quotes a W line, a
walk file line or a directory line that the example's files lack.
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
VIOLET = ("#ede4f5", "#c9b3e0", "#8a5fb0")
GREEN = ("#e3f1e6", "#a8d1b0", "#3f8a55")
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
    """The graph on the reference's coordinates and, under it, each line of
    the file as a bar at the interval it is indexed under beside its text;
    the window crosses the bars of the lines its query returns."""
    seq, qstart, qend = QUERY
    q = run_query([r[:3] + r[4:] for r in node_lines], [r[:3] + r[4:] for r in link_lines])
    kept = [q["hits"][i] for i in sorted(q["kept"])]
    nodes = {r[4]: r for r in node_lines}
    ref = sorted((n for n in nodes if nodes[n][5] == "0"), key=lambda n: int(nodes[n][1]))
    alt = next(n for n in nodes if nodes[n][5] != "0")
    edges = [(r[4][:-1], r[5][:-1]) for r in link_lines]
    lo, hi = int(nodes[ref[0]][1]), int(nodes[ref[-1]][2])
    node_pale, node_ink = "#dafbe1", "#1a7f37"
    link_pale, link_ink = "#f3e8ff", "#8250df"
    region = f"{seq}:{qstart + 1}-{qend}"
    c, shade = Canvas(), Canvas()
    width, left, ax0, ax1, text_x, size = 800, 24, 64, 304, 336, 13
    x_of = lambda bp: ax0 + (ax1 - ax0) * (bp - lo) / (hi - lo)
    box_h, alt_y, ref_y, axis = 30, 40, 92, 136

    c.out.append(f'<defs><marker id="head" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">'
                 f'<path d="M0,0 L7,3.5 L0,7 z" fill="{link_ink}"/></marker></defs>')
    c.say(text_x, ref_y + box_h / 2 + 5, f"tabix {PREFIX}.graph.bed.gz {region}", 13, weight="bold")

    box = {n: (x_of(int(nodes[n][1])) + 8, x_of(int(nodes[n][2])) - 8, ref_y) for n in ref}
    into, out_ = next(a for a, b in edges if b == alt), next(b for a, b in edges if a == alt)
    middle = (box[into][1] + box[out_][0]) / 2
    box[alt] = (middle - 24, middle + 24, alt_y)
    for a, b in edges:
        (a0, a1, ay), (b0, b1, by) = box[a], box[b]
        start, end = ((a1, ay + box_h / 2), (b0, by + box_h / 2)) if ay == by else (
            ((a0 + a1) / 2, ay), (b0, by + box_h / 2)) if ay > by else ((a1, ay + box_h / 2), ((b0 + b1) / 2, by))
        c.out.append(f'<line x1="{start[0]:.1f}" y1="{start[1]:.1f}" x2="{end[0]:.1f}" y2="{end[1]:.1f}" '
                     f'stroke="{link_ink}" stroke-width="2" marker-end="url(#head)"/>')
    for n, (x0, x1, y) in box.items():
        c.rect(x0, y, x1 - x0, box_h, node_pale, 6, node_ink, 1.2)
        c.say((x0 + x1) / 2, y + box_h / 2 + 5, n, 13, INK, "bold", SANS, "middle")
    c.say(middle, alt_y - 7, nodes[alt][6], 11, MUTED, font=SANS, anchor="middle")
    c.line(x_of(lo), axis, x_of(hi), axis, width=1.2)
    c.say(x_of(lo) - 10, axis + 18, seq, 11, MUTED, "bold", SANS, "end")
    for bp in range(lo, hi + 1, 10):
        c.line(x_of(bp), axis, x_of(bp), axis + 5)
        c.say(x_of(bp), axis + 18, str(bp), 11, MUTED, anchor="middle")

    def table(y, rows, returned, labels, greyed, pale, dark):
        """Each line's bar and text under the labels of its columns; returns
        the y of the last line."""
        cw = 0.602 * size
        widths = [max(len(r[i]) for r in rows) for i in range(len(rows[0]))]
        xs = [text_x + (sum(widths[:i]) + 1.6 * i) * cw for i in range(len(widths))]
        for i, label in labels.items():
            c.say(xs[i], y, label, 11, MUTED, font=SANS)
        for k, r in enumerate(rows):
            y += 22
            hit = returned(r)
            a, b = x_of(int(r[1])), x_of(int(r[2]))
            c.rect(a + 1, y - 10, b - a - 2, 10, pale if hit else "white", 2, dark if hit else GREY)
            if hit:
                c.rect(text_x - 6, y - 15, xs[-1] + widths[-1] * cw - text_x + 12, 21, pale, 3)
            for i, (x, cell) in enumerate(zip(xs, r)):
                c.say(x, y, cell, size, GREY if not hit or i in greyed else INK, "bold" if hit and i not in greyed else "normal")
        return y

    y = table(180, node_lines, lambda r: r[4] in q["returned"],
              {0: "indexed under", 4: "node", 6: "its own position"}, {5}, node_pale, node_ink)
    y = table(y + 38, link_lines, lambda r: r[:3] + r[4:] in kept,
              {4: "link", 6: "from", 10: "to"}, {9, 13}, link_pale, link_ink)
    shade.rect(x_of(qstart), 10, x_of(qend) - x_of(qstart), y - 4, HIGHLIGHT)
    c.out.insert(0, "\n".join(shade.out))
    return c.svg(width, y + 22)


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
BANDAGE_FIGURES = ["walks-leave"]


class Canvas:
    def __init__(self):
        self.out = []

    def say(self, x, y, s, size=12, fill=INK, weight="normal", font=MONO, anchor="start"):
        anchored = "" if anchor == "start" else f' text-anchor="{anchor}"'
        self.out.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" font-weight="{weight}" '
                        f'font-family="{font}"{anchored} xml:space="preserve">{s}</text>')

    def rect(self, x, y, w, h, fill, rx=0, stroke=None, width=1):
        stroked = f' stroke="{stroke}" stroke-width="{width}"' if stroke else ""
        self.out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}"{stroked}/>')

    def line(self, x1, y1, x2, y2, stroke=MUTED, width=1):
        self.out.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" '
                        f'stroke-width="{width}" stroke-linecap="round"/>')

    def path(self, d, stroke, width=3):
        self.out.append(f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="{width}" '
                        f'stroke-linecap="round" stroke-linejoin="round"/>')

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


SCHEMATIC = "walks-schematic"
SCHEMATIC_OPTIONS = ["--walks", "--refs", REF, "--tile", "30"]
WINDOW = (30, 60)
GREY, LINE = "#9aa3ad", "#d0d7de"
REF_STROKE, REF_FILL = "#575757", "#eceff2"


def node_spans(reference, lengths):
    spans, bp = {}, 0
    for n in reference:
        spans[n] = (bp, bp + lengths[n])
        bp += lengths[n]
    return spans


def detours(spans, path):
    """Where a path leaves the reference's nodes, for nodes of its own or
    for a reference node further on: (leave bp, rejoin bp, own nodes)."""
    out, own, leave = [], [], 0
    for n in path:
        if n in spans:
            if own or spans[n][0] != leave:
                out.append((leave, spans[n][0], own))
                own = []
            leave = spans[n][1]
        else:
            own.append(n)
    return out


def schematic_parts(lines, directory, gfa):
    """What both schematics draw: the GFA's W lines, the reference's nodes,
    each haplotype's detours, the walk file's units and the two units a
    read of the window fetches, adjacent in the file."""
    lengths, _, paths, contigs = read_gfa(gfa)
    ref = next(name for name in paths if name.startswith(f"{REF}#"))
    reference = [str(n) for n in paths[ref]]
    spans = node_spans(reference, lengths)
    units = units_of(lines)
    table = next(rows for unit, rows in units if unit[4] == "table")
    tile, departures = (next((unit, rows) for unit, rows in units if unit[4] == kind and int(unit[2]) == WINDOW[0])
                        for kind in ("tile", "departures"))
    entries = sorted((e for e in table if e[4] in ("tile", "departures") and e[2:4] == tile[0][2:4]),
                     key=lambda e: int(e[6]))
    first, last = int(entries[0][6]), int(entries[-1][6]) + int(entries[-1][7])
    if sum(int(e[7]) for e in entries) != last - first:
        sys.exit("figures.py: the schematic expects the window's tile and departure block adjacent in the file")
    return {
        "contig": contigs[ref][0],
        "tile": next(int(f.split(":")[-1]) for f in lines[0] if f.startswith("tile:")),
        "length": sum(lengths[n] for n in reference),
        "spans": spans,
        "lengths": lengths,
        "haplotypes": [(name, detours(spans, [str(n) for n in paths[name]])) for name in paths if name != ref],
        "directory": directory,
        "table": table,
        "tile_unit": tile,
        "departures_unit": departures,
        "entries": entries,
        "request": (first, last - first),
    }


def mono_row(c, x, y, fields, size=11.5, bold=(), grey=(), glosses=(), gloss_size=10):
    """Draws a row's fields two spaces apart, each at its own x, and the
    glosses (field, text, line) in small sans under their fields; returns
    the row's right edge and the y below its lowest gloss."""
    cw = 0.602 * size
    xs = [x + sum(len(f) + 2 for f in fields[:i]) * cw for i in range(len(fields))]
    for i, (fx, f) in enumerate(zip(xs, fields)):
        c.say(fx, y, html.escape(f), size, GREY if i in grey else INK, "bold" if i in bold else "normal")
    bottom = y
    for i, text, line in glosses:
        c.say(xs[i], y + 13 + (gloss_size + 1) * line, html.escape(text), gloss_size, MUTED, font=SANS)
        bottom = max(bottom, y + 13 + (gloss_size + 1) * line)
    return xs[-1] + len(fields[-1]) * cw, bottom


def step(h):
    return f"{'<' if h[1] else '>'}{h[0]}"


def glossed(row, routes, spans):
    """A row's first-look columns, its bold and grey ones and what the
    bold ones encode, for mono_row."""
    kind = row[3]
    if kind == "ref":
        steps = " ".join(step(h) for h in deltas(row[9])[0])
        lengths = sorted(set(row[10].split(",")))
        bp = f"{lengths[0]} bp each" if len(lengths) == 1 else f"{row[10]} bp"
        spec = dict(bold=(1, 2, 3, 9, 10), grey=(0, 4, 5, 7, 11), glosses=[(9, steps, 0), (10, bp, 0)])
    elif kind == "route":
        entry, interior, exit_ = routes[tuple(row)]
        parts = [[entry], interior, [exit_]]
        spec = dict(bold=(3, 4, 5, 6), grey=(0,),
                    glosses=[(4 + i, " ".join(step(h) for h in hs if h), 0) for i, hs in enumerate(parts)])
    elif kind == "walk":
        start = int(row[9])
        taken = ", ".join(f"route {r}" for r, _ in deltas(row[10])[0])
        text = f"{row[8]} steps from {step((start >> 1, start & 1))}, " + (f"taking {taken}" if taken else "no routes")
        spec = dict(bold=(1, 2, 3, 4, 8, 9, 10), grey=(0, 5, 7), glosses=[(8, text, 0)])
    else:
        leave = next(n for n, (_, end) in spans.items() if end == int(row[8]))
        rejoin = next(n for n, (start, _) in spans.items() if start == int(row[11]))
        spec = dict(bold=(1, 2, 3, 4, 6, 8, 9, 11, 12, 14), grey=(0, 7, 10, 13),
                    glosses=[(1, f">{leave} to >{rejoin}", 0), (6, f"{row[6]} bp of its own", 1),
                             (8, f"leaves {row[8]}", 0), (11, f"rejoins {row[11]}", 0), (14, "own steps' tile", 1)])
    return spec


def decoded_routes(unit, rows):
    """A tile's route rows, by row, as entry, interior and exit handles."""
    return dict(zip((tuple(r) for r in rows if r[3] == "route"), decode_walks(rows)[1])) if unit[4] == "tile" else {}


def unit_rows(c, x, y, unit, rows, spans, kinds=None):
    """A unit's #unit line and its rows, the first-look columns bold and
    glossed; returns the y below them."""
    mono_row(c, x, y, unit, bold=(4, 5), grey=(1,))
    y += 22
    routes = decoded_routes(unit, rows)
    for r in rows:
        if not kinds or r[3] in kinds:
            y = mono_row(c, x, y, r, **glossed(r, routes, spans))[1] + 20
    return y


def ruler(c, x_of, y, parts):
    """The contig's coordinates with its tiles bracketed above."""
    tile, length = parts["tile"], parts["length"]
    for start in range(0, length, tile):
        x0, x1 = x_of(start), x_of(start + tile)
        c.rect(x0 + 1, y - 26, x1 - x0 - 2, 18, "none", 3, LINE)
        c.say((x0 + x1) / 2, y - 13, f"tile {start}", 11, MUTED, "bold", anchor="middle")
    c.line(x_of(0), y, x_of(length), y, width=1.2)
    c.say(x_of(0) - 8, y + 18, parts["contig"], 10, MUTED, "bold", SANS, "end")
    for bp in range(0, length + 1, 10):
        tall = bp % tile == 0
        c.line(x_of(bp), y, x_of(bp), y + (6 if tall else 3))
        if tall:
            c.say(x_of(bp), y + 18, str(bp), 10, MUTED, anchor="middle")


def window_label(parts):
    return f"{parts['contig']}:{WINDOW[0] + 1}-{WINDOW[1]}"


def window_shade(c, x_of, top, bottom, label=None):
    s, e = WINDOW
    c.rect(x_of(s), top, x_of(e) - x_of(s), bottom - top, HIGHLIGHT)
    if label:
        c.say((x_of(s) + x_of(e)) / 2, top + 13, label, 11.5, INK, "bold", SANS, "middle")


def node_box(c, x0, x1, y, h, label, fill, stroke):
    c.rect(x0 + 1.5, y, x1 - x0 - 3, h, fill, 4, stroke, 1.2)
    c.say((x0 + x1) / 2, y + h / 2 + 4, label, 11, INK, "bold", SANS, "middle")


def reference_boxes(c, x_of, y, parts):
    for n, (start, end) in parts["spans"].items():
        node_box(c, x_of(start), x_of(end), y, 22, n, REF_FILL, REF_STROKE)


def hug(c, x_of, y, colours, dips, depth, parts):
    """A haplotype's line along the reference, dipping to a box of its own
    nodes wherever it walks away from it."""
    fill, _, stroke = colours
    d, boxes = f"M{x_of(0):.1f},{y:.1f}", []
    for leave, rejoin, own in dips:
        xl, xr = x_of(leave), x_of(rejoin)
        ramp = min(18, (xr - xl) / 4)
        w = min(x_of(sum(parts["lengths"][n] for n in own)) - x_of(0), xr - xl - 2 * ramp - 8)
        b0, b1 = (xl + xr - w) / 2, (xl + xr + w) / 2
        d += (f" L{xl:.1f},{y:.1f} C{xl + ramp / 2:.1f},{y:.1f} {xl + ramp / 2:.1f},{y + depth:.1f} {xl + ramp:.1f},{y + depth:.1f}"
              f" L{xr - ramp:.1f},{y + depth:.1f} C{xr - ramp / 2:.1f},{y + depth:.1f} {xr - ramp / 2:.1f},{y:.1f} {xr:.1f},{y:.1f}")
        boxes += [(b0, b1, " ".join(own))] if own else []
    c.path(f"{d} L{x_of(parts['length']):.1f},{y:.1f}", stroke)
    for b0, b1, label in boxes:
        node_box(c, b0, b1, y + depth - 9, 18, label, fill, stroke)


HAPLOTYPE_COLOURS = [BLUE, ORANGE, VIOLET, GREEN]


def graph_over_tiles(c, x_of, left, top, parts):
    """The tiles, the contig's ruler and the reference's nodes, then each
    haplotype as a lane, those that stay on the reference first and the
    widest detour last, so a narrow detour nests inside a wide one; returns
    the y below the lowest node."""
    ruler(c, x_of, top + 52, parts)
    y_ref = top + 82
    reference_boxes(c, x_of, y_ref, parts)
    c.say(left, y_ref + 15, f"{REF}#0", 11.5, REF_STROKE, "bold")
    widest = lambda dips: max((rejoin - leave for leave, rejoin, _ in dips), default=0)
    lanes = sorted(enumerate(parts["haplotypes"]), key=lambda h: widest(h[1][1]))
    bottom, dipping = y_ref + 34, 0
    for lane, (i, (name, dips)) in enumerate(lanes):
        y, depth = y_ref + 34 + 14 * lane, 36 + 24 * dipping
        hug(c, x_of, y, HAPLOTYPE_COLOURS[i], dips, depth, parts)
        c.say(left, y + 4, name, 11.5, HAPLOTYPE_COLOURS[i][2], "bold")
        dipping += bool(dips)
        bottom = max(bottom, y + (depth + 9 if dips else 0))
    return bottom + 3


EXAMPLE = "walks-example"
BRIEF = FIGURES.parent / "walks-format-in-brief.md"


QUOTED = ("W", "#reference", "#haplotype", "#unit", "#entry", "#header")


def misquoted(lines, directory):
    """The brief's fenced W lines, header, #unit, #entry and directory
    lines and rows that are not a line of the example's GFA, of its walk
    file or of its directory."""
    gfa = (FIGURES / f"{EXAMPLE}.gfa").read_text().splitlines()
    written = {tuple(f) for f in lines + directory} | {tuple(line.split()) for line in gfa}
    fenced, quoted = False, []
    for line in BRIEF.read_text().splitlines():
        fenced = fenced != line.startswith("```")
        fields = tuple(line.split())
        if fenced and fields and (fields[0] in QUOTED or fields[0].startswith(f"{REF}#")):
            quoted.append(fields)
    return [" ".join(fields) for fields in quoted if fields not in written]


def example_svg(parts):
    """The graph over the walk file as a bar of its units, each tile and
    its departures under their stretch of the reference; the window's two
    units are shaded with the graph above them."""
    c, shade = Canvas(), Canvas()
    width, left, x0 = 900, 24, 160
    x_of = lambda bp: x0 + (width - 110 - x0) * bp / parts["length"]
    bottom = graph_over_tiles(c, x_of, left, 10, parts)
    name_y = bottom + 38
    c.say(left, name_y, f"{PREFIX}.{REF}.walks.gz", 12, weight="bold")
    bar, bar_h = name_y + 12, 34
    blocks = [(left, x_of(0), "header", "", False)]
    stretches = sorted({(int(e[2]), int(e[3])) for e in parts["table"]})
    for start, end in stretches:
        units = [e for e in parts["table"] if (int(e[2]), int(e[3])) == (start, end)]
        share = (x_of(end) - x_of(start)) / len(units)
        blocks += [(x_of(start) + share * k, x_of(start) + share * (k + 1),
                    *((f"tile {e[5]}", "") if e[4] == "tile" else (e[4], f"{start}-{end}")), e in parts["entries"])
                   for k, e in enumerate(units)]
    blocks.append((x_of(parts["length"]), width - left, "table", "", False))
    for a, b, kind, name, lit in blocks:
        c.rect(a + 1, bar, b - a - 2, bar_h, "none", 3, LINE)
        weight = "bold" if lit else "normal"
        c.say((a + b) / 2, bar + (15 if name else 21), kind, 10, INK, weight, anchor="middle")
        c.say((a + b) / 2, bar + 27, name, 10, INK, weight, anchor="middle")
    label_y = bar + bar_h + 20
    c.say((x_of(WINDOW[0]) + x_of(WINDOW[1])) / 2, label_y, "one request", 11.5, INK, "bold", SANS, "middle")
    window_shade(shade, x_of, 10, label_y + 10, window_label(parts))
    c.out.insert(0, "\n".join(shade.out))
    return c.svg(width, label_y + 22)


TILE = "walks-tile"


def tile_parts(lines, gfa):
    """What the tile figure draws: the reference's nodes, each haplotype's
    detours, and the file's units in order with the window's byte range."""
    lengths, _, paths, contigs = read_gfa(gfa)
    ref = next(name for name in paths if name.startswith(f"{REF}#"))
    reference = [str(n) for n in paths[ref]]
    spans = node_spans(reference, lengths)
    units = [u[4] for u, _ in units_of(lines)]
    if units != ["tile"] * (len(units) - 1) + ["table"]:
        sys.exit(f"figures.py: the tile figure expects tiles and a table, got {units}")
    entries = [f for f in lines if f[0] == "#entry"]
    window = next(f for f in entries if int(f[2]) == WINDOW[0])
    return {
        "contig": contigs[ref][0],
        "tile": next(int(f.split(":")[-1]) for f in lines[0] if f.startswith("tile:")),
        "length": sum(lengths[n] for n in reference),
        "spans": spans,
        "lengths": lengths,
        "haplotypes": [(name, detours(spans, [str(n) for n in paths[name]])) for name in paths if name != ref],
        "tiles": [(int(f[2]), int(f[3])) for f in entries],
        "bytes": byte_range(int(window[6]), int(window[7])),
    }


def tile_svg(parts):
    """The graph along the reference with each haplotype as a lane, over
    the file as a bar of its units, each tile under its stretch of the
    reference; the window's tile is shaded down to its byte range."""
    c, shade = Canvas(), Canvas()
    width, left, x0 = 800, 24, 130
    x_of = lambda bp: x0 + (width - 110 - x0) * bp / parts["length"]
    spans, tile = parts["spans"], parts["tile"]
    axis = 40
    c.say(left, axis + 4, parts["contig"], 12, MUTED, "bold")
    c.line(x_of(0), axis, x_of(parts["length"]), axis, LINE)
    for bp in range(0, parts["length"] + 1, tile):
        c.line(x_of(bp), axis - 5, x_of(bp), axis, MUTED)
        c.say(x_of(bp), axis - 10, str(bp), 11, MUTED, anchor="middle")
    y, box_h, own_h = axis + 14, 64, 22
    for start, end in spans.values():
        c.rect(x_of(start) + 2, y, x_of(end) - x_of(start) - 4, box_h, REF_FILL, 5, REF_STROKE, 1.2)
    lane = lambda k: y + 18 + 14 * k
    c.path(f"M{x_of(0) + 8:.1f},{lane(0)} L{x_of(parts['length']) - 8:.1f},{lane(0)}", REF_STROKE)
    c.say(left, lane(0) + 4, f"{REF}#0", 12, REF_STROKE, "bold")
    lanes = sorted(enumerate(parts["haplotypes"]), key=lambda h: bool(h[1][1]))
    own_y = y + box_h + 8
    for k, (i, (name, dips)) in enumerate(lanes, 1):
        fill, _, stroke = HAPLOTYPE_COLOURS[i]
        ly = lane(k)
        d = f"M{x_of(0) + 8:.1f},{ly}"
        for leave, rejoin, nodes in dips:
            xl, xr, low = x_of(leave), x_of(rejoin), own_y + own_h / 2
            w = min(x_of(sum(parts["lengths"][n] for n in nodes)) - x_of(0), xr - xl - 22)
            c.rect((xl + xr - w) / 2, own_y, w, own_h, fill, 5, stroke, 1.2)
            d += (f" L{xl - 8:.1f},{ly} C{xl:.1f},{ly} {xl:.1f},{low:.1f} {xl + 8:.1f},{low:.1f}"
                  f" L{xr - 8:.1f},{low:.1f} C{xr:.1f},{low:.1f} {xr:.1f},{ly} {xr + 8:.1f},{ly}")
        c.path(f"{d} L{x_of(parts['length']) - 8:.1f},{ly}", stroke)
        c.say(left, ly + 4, name, 12, stroke, "bold")
    top = own_y + own_h + 34
    c.say(left, top, f"{PREFIX}.{REF}.walks.gz", 12.5, INK, "bold")
    bar, bar_h = top + 12, 30
    blocks = [(left, x_of(0), "header", False)]
    blocks += [(x_of(a), x_of(b), f"tile {a}-{b}", a == WINDOW[0]) for a, b in parts["tiles"]]
    blocks += [(x_of(parts["length"]), width - left, "table", False)]
    for a, b, label, lit in blocks:
        c.rect(a + 2, bar, b - a - 4, bar_h, "#ffe066" if lit else "white", 5, "#d4a72c" if lit else LINE, 1.2)
        c.say((a + b) / 2, bar + 20, label, 12, INK if lit else MUTED, "bold" if lit else "normal", anchor="middle")
    label_y = bar + bar_h + 22
    mid = (x_of(WINDOW[0]) + x_of(WINDOW[1])) / 2
    c.say(mid, label_y, parts["bytes"], 12, INK, "bold", anchor="middle")
    table_x = (x_of(parts["length"]) + width - left) / 2
    tip = mid + 4.2 * len(parts["bytes"]) + 10
    c.out.append(f'<path d="M{table_x:.1f},{bar + bar_h + 2} V{label_y - 10} Q{table_x:.1f},{label_y - 4} {table_x - 8:.1f},{label_y - 4} '
                 f'H{tip + 8:.1f}" fill="none" stroke="{MUTED}" stroke-width="1.4"/>'
                 f'<path d="M{tip + 9:.1f},{label_y - 9} l-9,5 l9,5 z" fill="{MUTED}"/>')
    bottom = label_y + 12
    shade.rect(x_of(WINDOW[0]), axis - 26, x_of(WINDOW[1]) - x_of(WINDOW[0]), bottom - axis + 26, HIGHLIGHT, 4)
    c.out.insert(0, "\n".join(shade.out))
    return c.svg(width, bottom + 12)


def bytes_svg(parts):
    """The reader's path: the window on the graph, the .idx, the data file
    as a bar of its units with offsets, the window's units shaded as the
    one request, then the rows it gets."""
    c, shade = Canvas(), Canvas()
    width, left, x0 = 900, 24, 160
    x_of = lambda bp: x0 + (width - 24 - x0) * bp / parts["length"]
    c.say(left, 26, " ".join(["gfa-to-tabix", f"{SCHEMATIC}.gfa", *SCHEMATIC_OPTIONS, "-o", PREFIX]), 13, weight="bold")
    bottom = graph_over_tiles(c, x_of, left, 40, parts)
    window_shade(shade, x_of, 40, bottom, window_label(parts))
    c.out.insert(1, "\n".join(shade.out))
    data = f"{PREFIX}.{REF}.walks.gz"
    y = bottom + 24
    c.say(left, y, f"{data}.idx", 12, weight="bold")
    header, sequence = parts["directory"][1:]
    mono_row(c, left + 8, y + 18, header, 10.5)
    mono_row(c, left + 8, y + 34, sequence, 10.5, bold=(1, 2))
    total = next(int(f.split(":")[-1]) for f in parts["directory"][0] if f.startswith("bytes:"))
    bar_y = y + 86
    bx0, bx1 = left, width - 24
    b_of = lambda b: bx0 + (bx1 - bx0) * b / total
    c.say(left, bar_y - 10, data, 12, weight="bold")
    c.say(left + 0.602 * 12 * (len(data) + 2), bar_y - 10, f"{total} bytes", 10.5, MUTED)
    segments = [(("header", ""), 0, int(header[2]))]
    for e in parts["table"]:
        label = (f"tile {e[5]}", "") if e[4] == "tile" else (e[4], f"{e[2]}-{e[3]}")
        segments.append((label, int(e[6]), int(e[6]) + int(e[7])))
    t0, t1 = int(sequence[1]), int(sequence[1]) + int(sequence[2])
    segments.append((("table", ""), t0, t1))
    offset, length = parts["request"]
    c.rect(b_of(offset), bar_y - 2, b_of(offset + length) - b_of(offset), 60, HIGHLIGHT)
    for (kind, name), lo, hi in segments:
        c.rect(b_of(lo) + 1, bar_y, b_of(hi) - b_of(lo) - 2, 34, "none", 3, LINE)
        weight = "bold" if offset <= lo < offset + length else "normal"
        c.say((b_of(lo) + b_of(hi)) / 2, bar_y + (15 if name else 21), kind, 10, INK, weight, anchor="middle")
        c.say((b_of(lo) + b_of(hi)) / 2, bar_y + 27, name, 10, INK, weight, anchor="middle")
        c.say(b_of(lo), bar_y + 46, str(lo), 9, MUTED, anchor="middle")
    c.say(b_of(total), bar_y + 46, str(total), 9, MUTED, anchor="middle")
    ex = left + 8 + 0.602 * 10.5 * (len(sequence[0]) + 3.5)
    c.path(f"M{ex:.1f},{y + 40:.1f} V{bar_y - 22:.1f} H{(b_of(t0) + b_of(t1)) / 2:.1f} V{bar_y - 4:.1f}", MUTED, 1)
    c.say((b_of(offset) + b_of(offset + length)) / 2, bar_y + 76,
          f"{window_label(parts)}: one request, {byte_range(offset, length)}", 11.5, INK, "bold", SANS, "middle")
    y = unit_rows(c, left + 8, bar_y + 108, *parts["tile_unit"], parts["spans"], kinds=("ref", "route", "walk"))
    y = unit_rows(c, left + 8, y, *parts["departures_unit"], parts["spans"])
    return c.svg(width, y - 10)


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
        subprocess.run([binary, FIGURES / f"{SCHEMATIC}.gfa", *SCHEMATIC_OPTIONS, "-o", out], **quiet)
        with gzip.open(walk_file, "rt") as f:
            schematic = [line.rstrip("\n").split("\t") for line in f]
        schematic_directory = [line.split("\t") for line in Path(f"{walk_file}.idx").read_text().splitlines()]
        subprocess.run([binary, FIGURES / f"{TILE}.gfa", *SCHEMATIC_OPTIONS, "-o", out], **quiet)
        with gzip.open(walk_file, "rt") as f:
            tile = [line.rstrip("\n").split("\t") for line in f]
        subprocess.run([binary, FIGURES / f"{EXAMPLE}.gfa", *SCHEMATIC_OPTIONS, "-o", out], **quiet)
        with gzip.open(walk_file, "rt") as f:
            example = [line.rstrip("\n").split("\t") for line in f]
        example_directory = [line.split("\t") for line in Path(f"{walk_file}.idx").read_text().splitlines()]
    lengths, gfa_links, paths, contigs = read_gfa(FIGURES / "walks.gfa")
    table, rebuilt = walks(walk_rows, paths)
    walks_nodes, walks_arrows = walks_graph(lengths, gfa_links, paths, contigs)
    parts = schematic_parts(schematic, schematic_directory, FIGURES / f"{SCHEMATIC}.gfa")
    return misquoted(example, example_directory), {
        TILE: tile_svg(tile_parts(tile, FIGURES / f"{TILE}.gfa")),
        "walks-bytes": bytes_svg(parts),
        EXAMPLE: example_svg(schematic_parts(example, example_directory, FIGURES / f"{EXAMPLE}.gfa")),
        "walks-leave-figure": bandage_figure("walks-leave", built["walks-leave"], directories["walks-leave"],
                                             lambda f: HIGHLIGHT if f[3] == "departure" else None),
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
    wrong, figures = generate(Path(args[0]).resolve())
    for line in wrong:
        print(f"{BRIEF}: not a line of {EXAMPLE}.gfa, its walk file or its directory: {line}")
    for figure, regions in figures.items():
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
    if wrong:
        sys.exit(f"figures.py: {BRIEF.name} misquotes its example")


if __name__ == "__main__":
    main()
