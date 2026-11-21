#!/usr/bin/env python3
"""tables.py [--check]

Writes the measured tables of docs/comparison-details.md from docs/comparison/results,
each between `<!-- generated:NAME -->` and `<!-- /generated -->`. With
--check it writes nothing and exits 1 when the doc's tables differ from the
results.
"""
import csv
import json
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
RESULTS = HERE / "results"
DOC = HERE.parent / "comparison-details.md"
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
    version, commit, node = (RESULTS / "graph-walks.commit.txt").read_text().split()
    load = ", ".join(f"{max(float(r['load1']) for r in rows(f'{g}.times.tsv')):.2f} on {label}" for g, label in GRAPHS.items())
    return "\n".join("- " + line for line in (RESULTS / "versions.txt").read_text().splitlines()
                     + [f"@jbrowse/graph-walks {version} at commit {commit}, on Node {node}",
                        f"each timed window began at a 1-minute load average of at most {load}"])


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


def times(graph):
    runs = defaultdict(list)
    for r in rows(f"{graph}.times.tsv"):
        runs[(r["case"], r["start"])].append(r)
    out = defaultdict(dict)
    for (case, start), rs in runs.items():
        last = max(rs, key=lambda r: int(r["run"]))
        out[case][start] = {**last, **{k: statistics.median(float(r[k]) for r in rs)
                                       for k in ("open_ms", "cut_ms", "tables_ms") if last[k] != ""}}
    return out


def window(graph):
    w = rows(f"{graph}.windows.tsv")
    opened = {r["reader"]: r for r in rows(f"{graph}.open.tsv")}
    plain = lambda n: f"{n:,.0f}"
    ms = lambda n: f"{n:.0f} ms" if n < 1000 else f"{n / 1000:.1f} s"
    t = times(graph)
    cut, cut_bases, browser = (list(t[case].values()) for case in ("walks", "walks_bases", "browser"))
    browser_cut = [r for r in browser if r["status"] == "ok"]
    refused = [r for r in browser if r["status"] == "refused"]
    runs = [("gfaidx", "", "gfaidx")] + ([("gfaidx, `--haplotype_gap 10kb`", ".gap", "gfaidx_gap")]
                                         if (RESULTS / f"{graph}.gap.windows.tsv").exists() else [])

    def col(name, rs):
        return [r[name] for r in rs]

    def gfaidx(suffix, case):
        g = rows(f"{graph}{suffix}.windows.tsv")
        good = [r for r in g if r["gfaidx_status"] == "0" and t[case][r["start"]]["status"] == "ok"]
        at_open = {r["reader"]: r for r in rows(f"{graph}{suffix}.open.tsv")}["gfaidx"]["bytes"]
        cells = {
            "bytes read on opening the files": size(at_open),
            "bytes read": spread(col("gfaidx_bytes", good), size),
            "byte ranges": spread(col("gfaidx_ranges", good), plain),
            "byte ranges, gaps of up to 64 KB joined": spread(col("gfaidx_ranges_gaps_joined", good), plain),
            "bytes read, gaps of up to 64 KB joined": spread(col("gfaidx_bytes_gaps_joined", good), size),
            "files read": spread(col("gfaidx_files", good), plain),
            "time on local disk, from a new reader or process": spread([t[case][r["start"]]["open_ms"] for r in good], ms),
            "distinct nodes returned": spread(col("gfaidx_gfa_S", good), plain),
            "GFA written": spread(col("gfaidx_gfa_bytes", good), size),
        }
        return g, good, case, cells

    measured = [(label, *gfaidx(suffix, case)) for label, suffix, case in runs]
    walk_rows = [
        ["bytes read on opening the files", size(opened["walks"]["bytes"]), size(opened["walks_bases"]["bytes"]),
         size(opened["walks"]["bytes"])],
        ["bytes read", spread(col("walks_bytes", w), size), spread(col("walks_bases_bytes", w), size),
         spread(col("bytes", browser), size)],
        ["byte ranges", spread(col("walks_ranges", w), plain), spread(col("walks_bases_ranges", w), plain),
         spread(col("ranges", browser), plain)],
        ["bytes read to expand haplotypes moved out of a crowded tile", spread(col("walks_blocks_bytes", w), size),
         spread(col("walks_bases_blocks_bytes", w), size), ""],
        ["byte ranges, gaps of up to 64 KB joined", "", "", ""],
        ["bytes read, gaps of up to 64 KB joined", "", "", ""],
        ["files read", "1", "1", "1"],
        ["windows refused, and the time to refuse from a new reader", "0", "0",
         f"{len(refused)}, {spread(col('open_ms', refused), ms)}" if refused else "0"],
        ["time on local disk, reader already open", spread(col("cut_ms", cut), ms), spread(col("cut_ms", cut_bases), ms),
         spread(col("cut_ms", browser_cut), ms)],
        ["time on local disk, from a new reader or process", spread(col("open_ms", cut), ms),
         spread(col("open_ms", cut_bases), ms), spread(col("open_ms", browser_cut), ms)],
    ] + ([["time over HTTP from jbrowse.org's whole-genome file, from a new reader",
           spread(col("open_ms", t["http"].values()), ms), "", ""]] if "http" in t else []) + [
        ["time to build the tables a viewer draws from", spread(col("tables_ms", cut), ms),
         spread(col("tables_ms", cut_bases), ms), spread(col("tables_ms", browser_cut), ms)],
        ["distinct nodes returned", spread(col("nodes", cut), plain), spread(col("nodes", cut_bases), plain),
         spread(col("nodes", browser_cut), plain)],
        ["steps returned", spread(col("steps", cut), count), spread(col("steps", cut_bases), count),
         spread(col("steps", browser_cut), count)],
        ["GFA written", "", "", ""],
    ]
    body = [r + [cells.get(r[0], "") for *_, cells in measured] for r in walk_rows]
    note = ""
    for label, g, good, case, _ in measured:
        same = sum(1 for r in good if r["gfaidx_gfa_S_sha1"] == t["walks"][r["start"]]["nodes_sha1"])
        faster = sum(1 for r in good if t["walks"][r["start"]]["open_ms"] < t[case][r["start"]]["open_ms"])
        failed = len(g) - len(good)
        note += (f"\n- Against {label}: from a new reader, the walk file reader is faster in {faster} of the {len(good)} windows."
                 f" The nodes on the paths it returns match the GFA's segments id for id in {same},"
                 f" and the GFA has more nodes in the other {len(good) - same}" + (f". {failed} of the {len(g)} windows failed in gfaidx and are left out"
                                                                                  if failed else ""))
    browser_faster = " and than ".join(
        f"{label}{',' if ',' in label else ''} in {sum(1 for r in good if t['browser'][r['start']]['status'] == 'ok' and t['browser'][r['start']]['open_ms'] < t[case][r['start']]['open_ms'])}"
        for label, _, good, case, _ in measured)
    note += (f"\n- With the browser preset, the walk file reader cuts {len(browser_cut)} of the {len(browser)} windows and refuses {len(refused)}."
             f" From a new reader it is faster than {browser_faster} of them")
    header = ([f"{GRAPHS[graph]}, {len(w)} windows: median (largest)", "walk file", "walk file with bases", "walk file, browser preset"]
              + [m[0] for m in measured])
    return table(header, body) + "\n" + note


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
            sys.exit("docs/comparison-details.md's tables differ from docs/comparison/results; run docs/comparison/scripts/tables.py")
    else:
        DOC.write_text(new)


if __name__ == "__main__":
    main()
