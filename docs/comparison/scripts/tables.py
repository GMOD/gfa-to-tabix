#!/usr/bin/env python3
"""tables.py [--check]

Writes the measured tables of docs/comparison.md from docs/comparison/results,
each between `<!-- generated:NAME -->` and `<!-- /generated -->`. With
--check it writes nothing and exits 1 when the doc's tables differ from the
results.
"""
import csv
import json
import re
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
RESULTS = HERE / "results"
DOC = HERE.parent / "comparison.md"
GRAPHS = {"mc22": "MC chr22", "pggbY": "pggb chrY"}


def rows(name):
    with open(RESULTS / name) as f:
        return list(csv.DictReader(f, delimiter="\t"))


def size(n):
    n = float(n)
    return (f"{n / 1e9:.2f} GB" if n >= 1e9 else f"{n / 1e6:.0f} MB" if n >= 1e7 else f"{n / 1e6:.1f} MB" if n >= 1e6
            else f"{n / 1e3:.0f} KB" if n >= 1e3 else f"{n:.0f} bytes" if n else "0")


def count(n):
    n = float(n)
    return f"{n / 1e9:.2f} billion" if n >= 1e9 else f"{n / 1e6:.1f} M" if n >= 1e6 else f"{n:,.0f}"


def seconds(s):
    s = float(s)
    return f"{s / 60:.0f} min" if s >= 600 else f"{s:.0f} s"


def memory(kb):
    return f"{float(kb) / 1048576:.1f} GiB"


def table(header, body):
    return "\n".join(["| " + " | ".join(header) + " |", "|" + "|".join(" --- " for _ in header) + "|"]
                     + ["| " + " | ".join(r) + " |" for r in body])


def versions():
    return "\n".join("- " + line for line in (RESULTS / "versions.txt").read_text().splitlines())


def graphs():
    body = []
    for key, label in GRAPHS.items():
        g = json.loads((RESULTS / f"{key}.gfaidx.params.json").read_text())["graph"]
        body.append([label, count(g["segments"]), count(g["links"]), count(g["total_sequence_bp"]),
                     count(g["paths"] + g["walks"]), count(g["path_steps"])])
    return table(["graph", "segments", "links", "bp in segments", "P and W lines", "steps"], body)


def build():
    done = {(r["graph"], r["tool"], r["step"]): r for r in rows("build.tsv")}
    steps = [("gfaidx", "index_gfa", "gfaidx `index_gfa --threads 8`"),
             ("gfaidx", "index_coordinates", "gfaidx `index_coordinates`"),
             ("gfa-to-tabix", "walks", "gfa-to-tabix `--walks`"),
             ("gfa-to-tabix", "walks-sequences", "gfa-to-tabix `--walks --sequences`"),
             ("gfa-to-tabix", "index", "gfa-to-tabix, the node and link index")]

    def cell(r):
        return f"{seconds(r['seconds'])}, {memory(r['peak_kb'])}" if r["status"] == "0" else f"failed ({r['status']})"

    return table(["time and peak memory"] + list(GRAPHS.values()),
                 [[label] + [cell(done[(g, tool, step)]) for g in GRAPHS] for tool, step, label in steps])


def sizes():
    files = {r["file"]: int(r["bytes"]) for r in rows("sizes.tsv")}

    def of(graph, *suffixes):
        return size(sum(files[graph + s] for s in suffixes))

    groups = [("gfaidx: segments and links, with bases (`.gfa.gz`, `.idx`)", (".gfaidx.gfa.gz", ".gfaidx.gfa.gz.idx")),
              ("gfaidx: paths (`.pdx`, `.pcx`)", (".gfaidx.gfa.gz.pdx", ".gfaidx.gfa.gz.pcx")),
              ("gfaidx: node names, lengths and coordinates (`.ndx`, `.lnx`, `.cdx`)",
               (".gfaidx.gfa.gz.ndx", ".gfaidx.gfa.gz.lnx", ".gfaidx.gfa.gz.cdx")),
              ("gfaidx: all of them", (".gfaidx.gfa.gz", ".gfaidx.gfa.gz.idx", ".gfaidx.gfa.gz.pdx", ".gfaidx.gfa.gz.pcx",
                                       ".gfaidx.gfa.gz.ndx", ".gfaidx.gfa.gz.lnx", ".gfaidx.gfa.gz.cdx")),
              ("gfa-to-tabix: walk file", (".GRCh38.walks.gz", ".GRCh38.walks.gz.idx")),
              ("gfa-to-tabix: walk file with bases", (".seq.GRCh38.walks.gz", ".seq.GRCh38.walks.gz.idx")),
              ("gfa-to-tabix: node and link index", (".graph.bed.gz", ".graph.bed.gz.tbi"))]
    return table(["files"] + list(GRAPHS.values()), [[label] + [of(g, *s) for g in GRAPHS] for label, s in groups])


def spread(values, fmt):
    v = sorted(float(x) for x in values)
    return f"{fmt(statistics.median(v))} ({fmt(v[-1])})"


def window(graph):
    w = [r for r in rows(f"{graph}.windows.tsv")]
    good = [r for r in w if r["gfaidx_status"] == "0"]
    opened = {r["reader"]: r for r in rows(f"{graph}.open.tsv")}
    plain = lambda n: f"{n:,.0f}"
    ms = lambda n: f"{n:.0f} ms" if n < 1000 else f"{n / 1000:.1f} s"

    def col(name, rs=w):
        return [r[name] for r in rs]

    body = [
        ["read at open", size(opened["walks"]["bytes"]), size(opened["walks_bases"]["bytes"]), size(opened["gfaidx"]["bytes"])],
        ["bytes read", spread(col("walks_bytes"), size), spread(col("walks_bases_bytes"), size), spread(col("gfaidx_bytes", good), size)],
        ["byte ranges", spread(col("walks_ranges"), plain), spread(col("walks_bases_ranges"), plain),
         spread(col("gfaidx_ranges", good), plain)],
        ["the tile's blocks unit, read to draw abridged pieces", spread(col("walks_blocks_bytes"), size),
         spread(col("walks_bases_blocks_bytes"), size), ""],
        ["byte ranges, gaps of up to 64 KB joined", "", "", spread(col("gfaidx_ranges_gaps_joined", good), plain)],
        ["bytes read, gaps of up to 64 KB joined", "", "", spread(col("gfaidx_bytes_gaps_joined", good), size)],
        ["files read", "1", "1", spread(col("gfaidx_files", good), plain)],
        ["time on local disk", "", "", spread(col("gfaidx_ms_median", good), ms)],
        ["GFA written", "", "", spread(col("gfaidx_gfa_bytes", good), size)],
    ]
    failed = len(w) - len(good)
    note = f"\n\n{failed} of the {len(w)} windows failed in gfaidx and are left out of its column." if failed else ""
    return table([f"{GRAPHS[graph]}, {len(w)} windows: median (largest)", "walk file", "walk file with bases", "gfaidx"], body) + note


def files(graph):
    body = [[f"`{r['file'].split('.gfa.gz')[1] or '.gfa.gz'}`", size(r["size"]), "memory-mapped" if r["memory_mapped"] == "yes" else "read",
             size(r["open_bytes"]), f"{size(r['window_bytes_median'])} ({size(r['window_bytes_max'])})",
             f"{int(r['window_ranges_median']):,} ({int(r['window_ranges_max']):,})"] for r in rows(f"{graph}.files.tsv")]
    return table([f"{GRAPHS[graph]}: gfaidx file", "size", "how", "every window reads", "bytes per window: median (largest)",
                  "byte ranges per window"], body)


BLOCKS = {"versions": versions, "graphs": graphs, "build": build, "sizes": sizes,
          "window-mc22": lambda: window("mc22"), "window-pggbY": lambda: window("pggbY"),
          "files-mc22": lambda: files("mc22"), "files-pggbY": lambda: files("pggbY")}


def main():
    text = DOC.read_text()
    new = re.sub(r"(<!-- generated:([\w-]+) -->\n)(?:(?!<!-- /generated -->).*\n)*(<!-- /generated -->)",
                 lambda m: m.group(1) + BLOCKS[m.group(2)]() + "\n" + m.group(3), text)
    if "--check" in sys.argv:
        if new != text:
            sys.exit("docs/comparison.md's tables differ from docs/comparison/results; run docs/comparison/scripts/tables.py")
    else:
        DOC.write_text(new)


if __name__ == "__main__":
    main()
