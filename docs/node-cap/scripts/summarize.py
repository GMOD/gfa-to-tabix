#!/usr/bin/env python3
"""summarize.py RUNS.jsonl CUT.tsv OUTDIR: flattens every reader run into OUTDIR/reader-runs.tsv, writes the median
of each point's runs to OUTDIR/reader-points.tsv and the cut's to OUTDIR/cut-points.tsv, and prints the summary the
report quotes. A point is a reader, a layout and a window. Times are ms; "layout + draw" runs from the layout's start
to the first paint after it, "first paint" from navigation to that paint."""
import csv
import json
import math
import statistics
import sys
from collections import defaultdict

runs_path, cut_path, outdir = sys.argv[1:4]
runs = [json.loads(l) for l in open(runs_path) if l.strip()]

COLS = [
    "reader", "layout", "spec", "run", "status", "load1", "started", "nodes", "links", "drawn_mode",
    "cut_ms", "parse_ms", "layout_ms", "layout_engine_ms", "geometry_ms", "draw_ms", "layout_draw_ms", "to_paint_ms",
    "first_paint_ms", "cuts", "layouts",
    "main_block_max_ms", "js_heap_mb", "memory_mb", "renderer_paint_peak_mb", "renderer_peak_mb", "gpu_peak_mb",
    "zoom_frame_ms", "zoom_repaint_ms", "zoom_settle_ms", "pan_frame_ms", "pan_repaint_ms", "pan_settle_ms", "interaction",
    "error", "screen",
]


def diff(r, a, b):
    return round(r[b] - r[a]) if r.get(a) is not None and r.get(b) is not None else None


def first_cut_end(r):
    ends = [t for name, t in r.get("marks") or [] if name == "cut-end"]
    return ends[0] if ends else r["cut_end"]


def flat(r):
    geometry = r.get("geometry_ms")
    return {
        **{c: r.get(c) for c in COLS},
        "cut_ms": diff(r, "cut_start", "cut_end"),
        "parse_ms": diff(r, "cut_end", "layout_start"),
        "layout_ms": diff(r, "layout_start", "layout_end"),
        "layout_engine_ms": round(r["layout_engine_ms"]) if r.get("layout_engine_ms") is not None else None,
        "geometry_ms": round(geometry) if geometry is not None else diff(r, "layout_end", "geometry_end"),
        "draw_ms": diff(r, "layout_end", "draw_end"),
        "layout_draw_ms": diff(r, "layout_start", "painted"),
        "first_paint_ms": round(r["painted"]) if r.get("painted") is not None else None,
        # from the first cut's end to the first paint: parse, every layout and the draw, whatever the reader redid
        "to_paint_ms": round(r["painted"] - first_cut_end(r)) if r.get("painted") is not None else None,
        "cuts": sum(1 for m in r["marks"] if m[0] == "cut-end") if r.get("marks") else None,
        "layouts": sum(1 for m in r["marks"] if m[0] == "layout-end") if r.get("marks") else None,
        # the renderer's peak over the run; a renderer that crashed on the zoom or pan was read before them
        "memory_mb": r.get("renderer_peak_mb") if r.get("interaction") == "ok" else r.get("renderer_paint_peak_mb"),
        "error": " ".join((r.get("error") or "").split())[:200],
        "screen": " ".join((r.get("screen") or "").split())[:300],
    }


rows = [flat(r) for r in runs]
# a run that timed out with the layout's error on screen failed with that error: measure.mjs read the plugin's
# error from a retry button until it also read the text
for r in rows:
    if r["status"] == "timeout" and "RuntimeError" in r["screen"]:
        r["status"] = "error"
        r["error"] = r["screen"][r["screen"].index("RuntimeError"):]
order = {spec: i for i, spec in enumerate(dict.fromkeys(r["spec"] for r in rows))}
rows.sort(key=lambda r: (r["reader"], r["layout"], r["spec"].split(":")[0], order[r["spec"]], r["run"]))
with open(f"{outdir}/reader-runs.tsv", "w", newline="") as f:
    w = csv.DictWriter(f, COLS, delimiter="\t", lineterminator="\n")
    w.writeheader()
    w.writerows(rows)

cut = list(csv.DictReader(open(cut_path), delimiter="\t"))
cut_points = {}
for spec in dict.fromkeys(c["spec"] for c in cut):
    cs = [c for c in cut if c["spec"] == spec]
    cut_points[spec] = {
        "spec": spec, "nodes": cs[0]["nodes"], "placeholders": cs[0]["placeholders"], "links": cs[0]["links"],
        "walks": cs[0]["walks"], "steps": cs[0]["steps"], "runs": len(cs),
        "cut_ms": round(statistics.median(float(c["cut_ms"]) for c in cs)),
    }
with open(f"{outdir}/cut-points.tsv", "w", newline="") as f:
    w = csv.DictWriter(f, list(next(iter(cut_points.values()))), delimiter="\t", lineterminator="\n")
    w.writeheader()
    w.writerows(cut_points.values())

MEDIANS = ["cut_ms", "parse_ms", "layout_ms", "layout_engine_ms", "geometry_ms", "draw_ms", "layout_draw_ms", "to_paint_ms",
           "first_paint_ms", "main_block_max_ms", "js_heap_mb", "memory_mb", "zoom_frame_ms", "zoom_settle_ms", "pan_frame_ms"]
groups = defaultdict(list)
for r in rows:
    groups[(r["reader"], r["layout"], r["spec"])].append(r)
points = []
for (reader, layout, spec), rs in groups.items():
    ok = [r for r in rs if r["status"] == "ok"]
    bad = [r for r in rs if r["status"] != "ok"]
    point = {
        "reader": reader, "layout": layout, "spec": spec, "cut_nodes": cut_points[spec]["nodes"],
        "runs_ok": len(ok), "outcome": "ok" if ok and not bad else bad[0]["status"],
        "drawn_mode": ok[0]["drawn_mode"] if ok else "",
        "interaction": ",".join(sorted({r["interaction"] or "" for r in ok})),
    }
    for c in MEDIANS:
        vals = [r[c] for r in ok if r[c] is not None]
        point[c] = round(statistics.median(vals)) if vals else None
    vals = [r["to_paint_ms"] for r in ok if r["to_paint_ms"] is not None]
    point["to_paint_min_ms"] = min(vals) if vals else None
    point["to_paint_max_ms"] = max(vals) if vals else None
    point["error"] = bad[0]["error"] if bad else ""
    points.append(point)
points.sort(key=lambda p: (p["reader"], p["layout"], p["spec"].split(":")[0], order[p["spec"]]))
with open(f"{outdir}/reader-points.tsv", "w", newline="") as f:
    w = csv.DictWriter(f, list(points[0]), delimiter="\t", lineterminator="\n")
    w.writeheader()
    w.writerows(points)


def fmt(ms):
    return "-" if ms is None else f"{ms / 1000:.1f} s" if ms >= 1000 else f"{ms} ms"


print("Cut (graph-walks 9.0.0, Node, local disk, budgets lifted), median of runs")
print("window\tnodes\tlinks\tcut")
for p in cut_points.values():
    print(f"{p['spec']}\t{int(p['nodes']):,}\t{int(p['links']):,}\t{fmt(p['cut_ms'])}")

print("\nTo paint: from the cut's end to the first paint (parse, layout, geometry, draw); layout: the layout's own")
print("span; first paint: from navigation. Medians of the runs that drew. Memory: the renderer's peak RSS")
for reader in ("bjs", "plugin"):
    for layout in ("fmmm", "stress", "tubemap", "ordered", "walkrows"):
        ps = [p for p in points if p["reader"] == reader and p["layout"] == layout]
        if not ps:
            continue
        print(f"\n{reader} {layout}")
        print("window\tnodes\toutcome\tdrawn\tto paint\tlayout\tfirst paint\tmain block\tmemory MB\tJS heap MB\tzoom frame\tpan frame\tinteraction")
        for p in ps:
            print("\t".join([
                p["spec"], f"{int(p['cut_nodes']):,}", f"{p['outcome']} ({p['runs_ok']})", p["drawn_mode"] or "",
                fmt(p["to_paint_ms"]), fmt(p["layout_ms"]), fmt(p["first_paint_ms"]), fmt(p["main_block_max_ms"]),
                str(p["memory_mb"] or "-"), str(p["js_heap_mb"] or "-"), fmt(p["zoom_frame_ms"]), fmt(p["pan_frame_ms"]),
                p["interaction"],
            ]))

print("\nThresholds: the windows between which the median time to paint passes each time, by chromosome; in brackets")
print("an estimate of the node count where it does, from a straight line through those two windows in log nodes and log time")


def crossing(ps, limit):
    under = [p for p in ps if p["outcome"] == "ok" and p["to_paint_ms"] <= limit]
    over = [p for p in ps if p["outcome"] != "ok" or p["to_paint_ms"] > limit]
    first_over = over[0] if over else None
    last_under = max((p for p in under if not first_over or int(p["cut_nodes"]) < int(first_over["cut_nodes"])),
                     key=lambda p: int(p["cut_nodes"]), default=None)
    if not first_over:
        return "never", ""
    if not last_under:
        return f"<= {int(first_over['cut_nodes']):,}", ""
    span = f"{int(last_under['cut_nodes']):,}-{int(first_over['cut_nodes']):,}"
    if first_over["outcome"] != "ok":
        return span, ""
    # straight line through the two windows on log nodes against log time
    n0, n1 = int(last_under["cut_nodes"]), int(first_over["cut_nodes"])
    t0, t1 = last_under["to_paint_ms"], first_over["to_paint_ms"]
    at = math.exp(math.log(n0) + (math.log(limit) - math.log(t0)) * (math.log(n1) - math.log(n0)) / (math.log(t1) - math.log(t0)))
    return span, f"~{round(at, -3 if at >= 10000 else -2):,.0f}"


def failure(ps):
    failed = [p for p in ps if p["outcome"] not in ("ok", "not run")]
    words = {"error": "aborts", "timeout": "nothing in 300 s", "crash": "crashes", "fail": "view fails"}
    return f"{int(failed[0]['cut_nodes']):,}, {words.get(failed[0]['outcome'], failed[0]['outcome'])}" if failed else "none"


thresholds = {}
for reader in ("bjs", "plugin"):
    for layout in ("fmmm", "stress", "tubemap", "ordered", "walkrows"):
        for chrom in ("chr22", "chr6"):
            ps = sorted((p for p in points if p["reader"] == reader and p["layout"] == layout and p["spec"].startswith(f"{chrom}:")),
                        key=lambda p: int(p["cut_nodes"]))
            if not ps:
                continue
            found = {limit: crossing(ps, limit) for limit in (1000, 5000, 30000)}
            thresholds[(reader, layout, chrom)] = (found, failure(ps))
            print(f"{reader}\t{layout}\t{chrom}\t" + "\t".join(
                f">{limit // 1000} s: {span}{f' ({est})' if est else ''}" for limit, (span, est) in found.items()
            ) + f"\tfails: {failure(ps)}")

# The report's tables, in markdown, to OUTDIR/tables.md
LAYOUTS = [("fmmm", "FMMM"), ("stress", "stress"), ("tubemap", "tube map"), ("ordered", "ordered"), ("walkrows", "walk rows")]
READERS = [("bjs", "B"), ("plugin", "P")]
by = {(p["reader"], p["layout"], p["spec"]): p for p in points}


def cell(p, column):
    if p is None or p["outcome"] == "not run":
        return ""
    if p["outcome"] != "ok":
        return {"error": "aborts", "timeout": "> 300 s", "crash": "crash", "fail": "fails"}.get(p["outcome"], p["outcome"])
    v = p[column]
    if v is None:
        return "dies" if "crash" in p["interaction"] else "-"
    return fmt(v) if column.endswith("_ms") else f"{v:,}"


def label(spec):
    chrom, _, width = spec.split(":")
    return f"{chrom} {int(width) / 1e6:g} Mb" if int(width) >= 1e6 else f"{chrom} {int(width) // 1000} kb"


def table(column, title):
    head = ["window", "nodes"] + [f"{name} {r}" for _, name in LAYOUTS for _, r in READERS]
    lines = [f"{title}", "", "| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for spec, c in cut_points.items():
        row = [label(spec), f"{int(c['nodes']):,}"] + [cell(by.get((r, l, spec)), column) for l, _ in LAYOUTS for r, _ in READERS]
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines) + "\n"


with open(f"{outdir}/tables.md", "w") as f:
    f.write("Node counts where the median time to paint passes 1, 5 and 30 s (an estimate between the two windows that\n"
            "straddle it, or the windows when one of them did not draw), and the first window that drew nothing\n\n")
    f.write("| layout | reader | 1 s chr22 | 1 s MHC | 5 s chr22 | 5 s MHC | 30 s chr22 | 30 s MHC | fails chr22 | fails MHC |\n")
    f.write("|---|---|---|---|---|---|---|---|---|---|\n")
    for layout, lname in LAYOUTS:
        for reader, rname in (("bjs", "BandageJS"), ("plugin", "plugin")):
            cells = []
            for limit in (1000, 5000, 30000):
                for chrom in ("chr22", "chr6"):
                    span, est = thresholds[(reader, layout, chrom)][0][limit]
                    cells.append(est or span)
            cells += [thresholds[(reader, layout, chrom)][1] for chrom in ("chr22", "chr6")]
            f.write(f"| {lname} | {rname} | " + " | ".join(cells) + " |\n")
    f.write("\n")
    f.write("The windows (node counts) on either side of each crossing\n\n")
    f.write("| layout | reader | | 1 s | 5 s | 30 s |\n|---|---|---|---|---|---|\n")
    for layout, lname in LAYOUTS:
        for reader, rname in (("bjs", "BandageJS"), ("plugin", "plugin")):
            for chrom, cname in (("chr22", "chr22"), ("chr6", "MHC")):
                found = thresholds[(reader, layout, chrom)][0]
                f.write(f"| {lname} | {rname} | {cname} | " + " | ".join(found[limit][0] for limit in (1000, 5000, 30000)) + " |\n")
    f.write("\n")
    f.write(table("to_paint_ms", "Time to paint, median (B BandageJS, P the plugin)") + "\n")
    f.write(table("main_block_max_ms", "Longest main-thread task before the paint, median") + "\n")
    f.write(table("zoom_frame_ms", "A wheel zoom to its next painted frame, median") + "\n")
    f.write(table("pan_frame_ms", "A 60 px drag to its next painted frame, median") + "\n")
    f.write(table("memory_mb", "Renderer peak resident MB, median") + "\n")

with open(f"{outdir}/tables.md", "a") as f:
    f.write("Windows: graph-walks 9.0.0's cut in Node, median\n\n| window | reference bp | nodes | of them placeholders | links | steps | cut |\n|---|---|---|---|---|---|---|\n")
    for spec, c in cut_points.items():
        chrom, start, width = spec.split(":")
        f.write(f"| {label(spec)} | {int(start) + 1:,}-{int(start) + int(width):,} | {int(c['nodes']):,} | {int(c['placeholders']):,} | {int(c['links']):,} | {int(c['steps']):,} | {fmt(c['cut_ms'])} |\n")
