#!/usr/bin/env python3
"""figures.py <gfa-to-tabix binary> [--check]

Runs the tool on docs/figures/*.gfa and redraws docs/figures/*.svg from the
lines it writes. The script draws the overview figures itself, and the walks
figures by filling the marked regions of their .dot files for Graphviz.
With --check, exits 1 if a figure differs from what the tool writes now.
"""

import difflib
import gzip
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

FIGURES = Path(__file__).resolve().parent.parent / "docs" / "figures"
PREFIX = "graph"
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


def overview_svg(segs, links):
    """The two Tabix queries a browser runs for a window, the lines they
    return, and the graph it draws from them, coloured by the file each
    part came from."""
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

    def table(top, command, about, rows, labels, returned, pale, dark):
        """Each line with a bar at the interval Tabix searches; the window
        crosses the bars of the lines the query returns."""
        say(track, top, command, 13, font=mono, weight="bold")
        say(track, top + 19, about, 12, muted)
        top += 50
        char = 7.2
        widths = [max(len(r[i]) for r in rows) for i in range(len(rows[0]))]
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
            for x, cell in zip(xs, r):
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

    say(24, 28, f"1. To show {region}, a browser queries both files gfa-to-tabix writes", 14, weight="bold")
    labels = {0: "interval Tabix searches", 3: "node", 4: f"rank (0 = {seq})", 5: "the node's own position"}
    alt_row = next(r for r in segs if r[3] == alt)
    bottom = table(62, f"tabix {PREFIX}.segs.bed.gz {region}",
                   f"One line per node. {alt} is an {nodes[alt]['seq']} allele, so its line spans "
                   f"{coordinate(*alt_row[0:3])}, from {into} to {out_}.",
                   [r[:8] for r in segs], labels, lambda r: r[3] in q["returned"], node_pale, node_ink)
    labels = {0: "interval Tabix searches", 3: "link", 5: "source: position, rank", 9: "target: position, rank"}
    bottom = table(bottom + 50, f"tabix {PREFIX}.links.bed.gz {region}",
                   "One line per link, with the positions of both its nodes.",
                   links, labels, lambda r: r in kept, link_pale, link_ink)

    top = bottom + 54
    say(24, top, "2. It draws the graph from the returned lines", 14, weight="bold")
    rect(24, top + 12, 22, 14, node_pale, node_ink, 3)
    say(54, top + 23, f"from {PREFIX}.segs.bed.gz: {listing(q['returned'])}", 12, muted)
    rect(330, top + 12, 22, 14, link_pale, link_ink, 3)
    say(360, top + 23, f"from {PREFIX}.links.bed.gz: every edge, and {listing(q['far'])}", 12, muted)
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
        f"{grey}for each {chunk_size(header) // 1024} kb stretch of {contig}: {REF}'s path, each route off it, and the routes each haplotype takes</FONT>"
        f'<BR ALIGN="LEFT"/>>'
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
    return {
        "overview": overview_svg(segs, links),
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
