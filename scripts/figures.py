#!/usr/bin/env python3
"""figures.py <gfa-to-tabix binary> [--check]

Runs the tool on docs/figures/*.gfa, writes the rows it outputs into the
marked regions of docs/figures/*.dot and redraws the SVGs with Graphviz.
With --check, exits 1 if a .dot file differs from what the tool writes now.
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
QUERY = ("chr1", 25, 30)
BP_PER_CELL = 2.5
TICK_BP = 10

BLUE = ("#e8eef7", "#a9bfe2", "#4a6fa5")
ORANGE = ("#fde6cf", "#f3c08f", "#c77a2b")
PURPLE = ("#ede4f5", "#8a5fb0")
GREY = ("#e4e4e4", "#e4e4e4")
KEPT = ("#cfcfcf", "#666666")
DROPPED = ("#ececec", "#bdbdbd")
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
    lines = "<BR/>".join(textwrap.wrap(text, width))
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
    text = f"{name} lies off {seq}, so the tool files it under the reference span it hangs from: {first} to {last}, {seq}:{start}-{end}."
    return [caption(8, text, 64, "#a15f1c")]


def segs_table(segs):
    rows = []
    for row in segs:
        off = row[4] != "0"
        cells = [td(v, bold=off and i in (1, 2)) for i, v in enumerate(row)]
        rows.append(tr(cells, ORANGE[0] if off else BLUE[0]))
    return rows


def links_table(links):
    rows = []
    for row in links:
        off = set()
        if row[8] != "0":
            off |= {3, 5, 6, 7, 8}
        if row[12] != "0":
            off |= {4, 9, 10, 11, 12}
        rows.append(tr([td(v, ORANGE[0] if i in off else None) for i, v in enumerate(row)], "#f2f2f2"))
    return rows


def cell(bp):
    return int(int(bp) / BP_PER_CELL)


def lanes(segs, links):
    seq, qstart, qend = QUERY
    cells = cell(max(int(r[2]) for r in segs + links))
    query = range(cell(qstart), cell(qend))

    def bars(start, end, light, dark):
        fills = []
        for i in range(cells):
            inside = cell(start) <= i < cell(end)
            fills.append(dark if inside and i in query else light if inside else HIGHLIGHT if i in query else None)
        runs, i = [], 0
        while i < cells:
            j = i
            while j < cells and fills[j] == fills[i]:
                j += 1
            runs.append(td(bg=fills[i], **({"colspan": j - i} if j > i + 1 else {})))
            i = j
        return "".join(runs)

    def lane(label, start, end, colors, note, shown):
        text = f"<B>{label}</B>" if shown else f'<FONT COLOR="#999999">{label}</FONT>'
        note = f'<FONT POINT-SIZE="12" COLOR="#777777">  {note}</FONT>' if note else ""
        gap = "".join(td(bg=HIGHLIGHT if i in query else None) for i in range(cells))
        return [
            f'<TR><TD HEIGHT="5"></TD><TD></TD>{gap}<TD></TD><TD></TD></TR>',
            f'<TR><TD ALIGN="RIGHT" HEIGHT="18">{text}  </TD><TD></TD>{bars(start, end, *colors)}<TD></TD><TD ALIGN="LEFT">{note}</TD></TR>',
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
    rows += lane(f"{seq}:{qstart}-{qend}", qstart, qend, ("#555555", "#555555"), "query", True)

    q = run_query(segs, links)
    rows.append(heading(f"{PREFIX}.segs.bed.gz"))
    for row in segs:
        hit = row[3] in q["returned"]
        colors = (ORANGE if row[4] != "0" else BLUE)[1:] if hit else GREY
        rows += lane(row[3], row[1], row[2], colors, "returned" if hit else "", hit)

    hits = q["hits"]
    count = "all" if len(hits) == len(links) else f"{len(hits)} of"
    rows.append(heading(f"{PREFIX}.links.bed.gz: {count} {len(links)} rows return"))
    for i, row in enumerate(hits):
        keep = i in q["kept"]
        rows += lane(link_label(row), row[1], row[2], KEPT if keep else DROPPED, "kept" if keep else "dropped", keep)
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


def bubble(prefix, ref, labels, edges, far=()):
    alts = [n for n in labels if n not in ref]
    centre = prefix + ref[len(ref) // 2]
    lines = []
    for name in ref + alts:
        attrs = [f'label=<<B>{name}</B><BR/><FONT POINT-SIZE="10">{labels[name]}</FONT>>']
        if name in far:
            attrs += ['style="dashed,rounded,filled"', 'fillcolor="#f4f7fb"']
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
    return lines, prefix + alts[0] if alts else centre, bottom


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


def overview_graphs(segs, links):
    nodes = {r[3]: {"seq": r[5], "start": r[6], "end": r[7], "rank": r[4]} for r in segs}
    graph, _, graph_bottom = bubble("", ref_order(nodes), coordinates(nodes), [(r[3][:-1], r[4][:-1]) for r in links])

    q = run_query(segs, links)
    drawn = {n: nodes[n] for n in nodes if n in q["returned"]}
    for i in sorted(q["kept"]):
        for end in link_ends(q["hits"][i]):
            drawn.setdefault(end["name"], end)
    edges = [q["ends"][i] for i in sorted(q["kept"])]
    far = set(drawn) - q["returned"]
    drawn_lines, drawn_top, _ = bubble("d_", ref_order(drawn), coordinates(drawn), edges, far)

    seq, qstart, qend = QUERY
    arrows = [
        arrow((graph_bottom, "cluster_graph"), ("rows", "cluster_files"), f"gfa-to-tabix {PREFIX}.gfa"),
        arrow(("rows", "cluster_files"), ("hits", "cluster_query"), f"a browser queries\n{coordinate(seq, qstart, qend)}"),
        arrow(("hits", "cluster_query"), (drawn_top, "cluster_drawn"), "kept rows"),
    ]
    return graph, drawn_lines, arrows


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
        columns = " ".join(rest)
        table.append(tr([
            td(kind, bg),
            td(f'<FONT FACE="Courier" POINT-SIZE="11">{columns}</FONT>', align="LEFT"),
            td(meaning, align="LEFT"),
        ]))
    return table, rebuilt


def walks_caption(header, rows):
    chunk = int(next(f for f in header[0] if f.startswith("chunk:i:")).split(":")[2])
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
    lengths, links, paths = {}, [], {}
    with open(path) as f:
        for line in f:
            fields = line.rstrip("\n").split("\t")
            if fields[0] == "S":
                lengths[fields[1]] = len(fields[2])
            elif fields[0] == "L":
                links.append((fields[1], fields[3]))
            elif fields[0] == "W":
                paths[f"{fields[1]}#{fields[2]}"] = [int(x) for x in fields[6].replace("<", ">").split(">") if x]
    return lengths, links, paths


def walks_graph(lengths, links, paths):
    ref = [str(n) for n in next(path for name, path in paths.items() if name.startswith(f"{REF}#"))]
    graph, _, bottom = bubble("n", ref, {n: f"{length} bp" for n, length in lengths.items()}, links)
    arrows = [
        arrow((bottom, "cluster_graph"), ("rows", "cluster_file"), f"gfa-to-tabix --walks\n--refs {REF}"),
        arrow(("rows", "cluster_file"), ("rebuilt", "cluster_rebuilt"), "a region query\nreturns the chunk"),
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
    lengths, gfa_links, paths = read_gfa(FIGURES / "walks.gfa")
    table, rebuilt = walks(walk_rows, paths)
    walks_nodes, walks_arrows = walks_graph(lengths, gfa_links, paths)
    graph, drawn, arrows = overview_graphs(segs, links)
    return {
        "overview": {
            "graph": graph,
            "segs": segs_table(segs),
            "segs-caption": segs_caption(segs, links),
            "links": links_table(links),
            "lanes": lanes(segs, links),
            "keep-caption": keep_caption(segs, links),
            "drawn": drawn,
            "arrows": arrows,
        },
        "walks": {
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
        dot = FIGURES / f"{figure}.dot"
        old = dot.read_text()
        new = splice_regions(old, regions, dot.name)
        if check:
            if new != old:
                stale = True
                sys.stdout.writelines(difflib.unified_diff(
                    old.splitlines(True), new.splitlines(True), str(dot), "from the tool"))
            continue
        dot.write_text(new)
        subprocess.run(["dot", "-Tsvg", dot, "-o", dot.with_suffix(".svg")], check=True)
    if stale:
        sys.exit("figures.py: docs/figures is stale; run scripts/figures.py <binary> to redraw it")


if __name__ == "__main__":
    main()
