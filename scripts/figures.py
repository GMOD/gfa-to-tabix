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
from pathlib import Path

FIGURES = Path(__file__).resolve().parent.parent / "docs" / "figures"
PREFIX = "graph"
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


def td(text="", bg=None, bold=False, **attrs):
    attrs = "".join(f' {k.upper()}="{v}"' for k, v in attrs.items())
    if bg:
        attrs += f' BGCOLOR="{bg}"'
    return f"<TD{attrs}>{f'<B>{text}</B>' if bold and text else text}</TD>"


def tr(cells, bg=None):
    attr = f' BGCOLOR="{bg}"' if bg else ""
    return f"<TR{attr}>{''.join(cells)}</TR>"


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

    def overlaps(row):
        return row[0] == seq and int(row[1]) < qend and int(row[2]) > qstart

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

    rows.append(heading(f"{PREFIX}.segs.bed.gz"))
    returned = set()
    for row in segs:
        hit = overlaps(row)
        colors = (ORANGE if row[4] != "0" else BLUE)[1:] if hit else GREY
        rows += lane(row[3], row[1], row[2], colors, "returned" if hit else "", hit)
        if hit:
            returned.add(row[3])

    hits = [r for r in links if overlaps(r)]
    ends = [(r[3][:-1], r[4][:-1]) for r in hits]
    kept = {i for i, (a, b) in enumerate(ends) if a in returned or b in returned}
    far = {n for i in kept for n in ends[i]} - returned
    kept |= {i for i, (a, b) in enumerate(ends) if a in far and b in far}
    count = "all" if len(hits) == len(links) else f"{len(hits)} of"
    rows.append(heading(f"{PREFIX}.links.bed.gz: {count} {len(links)} rows return"))
    for i, row in enumerate(hits):
        keep = i in kept
        label = f"{ends[i][0]}→{ends[i][1]}"
        rows += lane(label, row[1], row[2], KEPT if keep else DROPPED, "kept" if keep else "dropped", keep)
    return rows


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
        meaning, bold, bg = "", None, None
        if kind == "ref":
            meaning, bold, bg = f"R, the reference path: {' '.join(handle(h) for h in R)}", 5, BLUE[0]
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
            bold = 7
            steps, cells = splice(R, routes, first, last, choices)
            path = rest[0].rsplit("#", 1)[0]
            if [h[0] for h in steps] != w_lines[path]:
                sys.exit(f"figures.py: {path} decodes to {steps}, but its W line visits {w_lines[path]}")
            label = " and ".join(
                f'<FONT POINT-SIZE="11" COLOR="{route_colors(routes[c])[-1]}">route {c}</FONT>' for c, _ in choices
            )
            rebuilt.append(rebuilt_row(path, cells, label))
        columns = " ".join(f"<B>{v}</B>" if i == bold else v for i, v in enumerate(rest))
        table.append(tr([
            td(kind, bg),
            td(f'<FONT FACE="Courier" POINT-SIZE="11">{columns}</FONT>', align="LEFT"),
            td(meaning, align="LEFT"),
        ]))
    return table, rebuilt


def read_w_lines(gfa):
    paths = {}
    with open(gfa) as f:
        for line in f:
            fields = line.rstrip("\n").split("\t")
            if fields[0] == "W":
                paths[f"{fields[1]}#{fields[2]}"] = [int(x) for x in fields[6].replace("<", ">").split(">") if x]
    return paths


def splice_regions(text, regions, name):
    for region, rows in regions.items():
        begin, end = f"<!-- begin {region} -->", f"<!-- end {region} -->"
        head, found, rest = text.partition(begin)
        if not found or end not in rest:
            sys.exit(f"figures.py: {name} lacks the {region} markers")
        indent = head[head.rfind("\n") + 1 :]
        body = "".join(f"{indent}{row}\n" for row in rows)
        text = f"{head}{begin}\n{body}{indent}{end}{rest.partition(end)[2]}"
    return text


def generate(binary):
    with tempfile.TemporaryDirectory() as tmp:
        out = f"{tmp}/{PREFIX}"
        quiet = dict(check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run([binary, FIGURES / "overview.gfa", "-o", out], **quiet)
        segs, links = read_rows(f"{out}.segs.bed.gz"), read_rows(f"{out}.links.bed.gz")
        subprocess.run([binary, FIGURES / "walks.gfa", "--walks", "--refs", "GRCh38", "-o", out], **quiet)
        table, rebuilt = walks(read_rows(f"{out}.GRCh38.walks.bed.gz"), read_w_lines(FIGURES / "walks.gfa"))
    return {
        "overview": {"segs": segs_table(segs), "links": links_table(links), "lanes": lanes(segs, links)},
        "walks": {"rows": table, "rebuilt": rebuilt},
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
