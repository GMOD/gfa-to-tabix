#!/usr/bin/env python3
"""windows.py: what one 64 kb reference window reads from a walk file and from
a gfaidx index of the same graph.

  windows.py GFAIDX_BIN INDEXED.gfa.gz REGION_NAME WALKS WALKS_WITH_BASES SEQUENCE OUT_PREFIX
             [--reference SAMPLE] [--windows N] [--tmp DIR] [--mount INDEXED.gfa.gz --pagelog LOG]

SEQUENCE is the reference sequence as the walk file's directory names it
(GRCh38#0#chr22) and REGION_NAME the same sequence as gfaidx names it (chr22
with --reference GRCh38, or a P line's name). The windows are N of the walk
file's tiles on SEQUENCE, evenly spaced.

Walk file, per window: the gzip bytes of the tile and departure units a reader
fetches, and how many byte ranges they make once touching units merge; and
the tile's blocks unit, which a reader fetches to draw an abridged piece
without expanding it. Per file: what a reader fetches at open (the directory, the header unit and
SEQUENCE's table).

gfaidx, per window: `get_region --mode all --with_coords` under strace, which
gives every byte range the process reads from the indexed graph and its
sidecars. gfaidx memory-maps some sidecars, and the trace shows a mapping but
not the pages a query touches, so the traced run reads the index through
pagelog.py's mount (--mount, the indexed graph's path under it, and --pagelog,
its log), which gives those pages as 4 KB reads. Ranges that every window
reads count as the open; the rest count for the window. A client that fetched
over HTTP would join ranges that lie close, so the window's ranges are also
counted with every gap of up to 64 KB fetched along with them. Then three untraced
runs on the index's own path for wall time and peak memory, and the size of
the GFA it writes.

Writes OUT_PREFIX.windows.tsv, OUT_PREFIX.files.tsv, OUT_PREFIX.open.tsv and
OUT_PREFIX.summary.txt.
"""
import argparse
import gzip
import os
import re
import statistics
import subprocess
import time
from collections import defaultdict


def merged(intervals, gap=0):
    out = []
    for lo, hi in sorted(intervals):
        if out and lo <= out[-1][1] + gap:
            out[-1][1] = max(out[-1][1], hi)
        elif hi > lo:
            out.append([lo, hi])
    return out


def intersect(a, b):
    out = []
    i = j = 0
    while i < len(a) and j < len(b):
        lo, hi = max(a[i][0], b[j][0]), min(a[i][1], b[j][1])
        if lo < hi:
            out.append([lo, hi])
        if a[i][1] < b[j][1]:
            i += 1
        else:
            j += 1
    return out


def subtract(a, b):
    out = []
    j = 0
    for lo, hi in a:
        at = lo
        while j < len(b) and b[j][1] <= at:
            j += 1
        k = j
        while k < len(b) and b[k][0] < hi:
            if b[k][0] > at:
                out.append([at, b[k][0]])
            at = max(at, b[k][1])
            k += 1
        if at < hi:
            out.append([at, hi])
    return out


def total(intervals):
    return sum(hi - lo for lo, hi in intervals)


def walk_file(path, sequence):
    data = open(path, "rb")

    def unit(offset, length):
        data.seek(int(offset))
        return gzip.decompress(data.read(int(length))).decode().splitlines()[1:]

    directory = [line.split("\t") for line in open(path + ".idx").read().splitlines()]
    tile = int(next(f for f in directory[0] if f.startswith("tile:i:")).split(":")[2])
    opened = os.path.getsize(path + ".idx")
    units = []
    for seq, offset, length in directory[1:]:
        if seq in ("#header", sequence):
            opened += int(length)
        if seq == sequence:
            for entry in unit(offset, length):
                _, _, lo, hi, kind, name, at, n = entry.split("\t")
                if kind in ("tile", "departures", "blocks"):
                    units.append((int(lo), int(hi), kind, name, int(at), int(n)))
    starts = sorted({lo - lo % tile for lo, _, kind, *_ in units if kind == "tile"})

    def window(cs):
        read = merged((at, at + n) for lo, hi, kind, _, at, n in units
                      if kind != "blocks" and lo < cs + tile and hi > cs)
        blocks = sum(n for _, _, kind, name, _, n in units if kind == "blocks" and name == str(cs))
        return total(read), len(read), blocks

    return tile, opened, starts, window


GAP = 65536
CALL = re.compile(r"^\d+\s+(\w+)\((.*)\)\s+= (-?\d+)")
FD = re.compile(r"^(\d+)<([^>]*)>")


def traced_reads(trace, prefix):
    position = {}
    reads = defaultdict(list)
    mapped = set()
    pending = {}
    for raw in open(trace, errors="replace"):
        pid, _, rest = raw.rstrip("\n").partition(" ")
        rest = rest.strip()
        if rest.endswith("<unfinished ...>"):
            pending[pid] = rest[: -len("<unfinished ...>")]
        else:
            resumed = re.match(r"<\.\.\. \w+ resumed>(.*)", rest)
            line = pid + " " + (pending.pop(pid, "") + resumed.group(1) if resumed else rest)
            call = CALL.match(line)
            if call:
                name, args, result = call.group(1), call.group(2), int(call.group(3))
                if name in ("openat", "open"):
                    position[result] = 0
                elif name == "mmap":
                    fd = re.search(r", (\d+)<([^>]*)>, ", args)
                    if fd and fd.group(2).startswith(prefix):
                        mapped.add(fd.group(2)[len(prefix):] or ".gz")
                else:
                    fd = FD.match(args)
                    if fd and result >= 0:
                        n, path = int(fd.group(1)), fd.group(2)
                        if name == "lseek":
                            position[n] = result
                        elif name in ("read", "readv"):
                            at = position.get(n, 0)
                            position[n] = at + result
                            if path.startswith(prefix):
                                reads[path[len(prefix):] or ".gz"].append((at, at + result))
                        elif name in ("pread64", "preadv"):
                            at = int(args.rsplit(", ", 1)[1])
                            if path.startswith(prefix):
                                reads[path[len(prefix):] or ".gz"].append((at, at + result))
    return {suffix: merged(r) for suffix, r in reads.items()}, mapped


def paged_reads(log, name, mapped, sizes):
    reads = defaultdict(list)
    for line in open(log):
        path, offset, size = line.rstrip("\n").split("\t")
        base = os.path.basename(path)
        suffix = base[len(name):] or ".gz"
        if base.startswith(name) and suffix in mapped:
            reads[suffix].append((int(offset), min(int(offset) + int(size), sizes(suffix))))
    return {suffix: merged(r) for suffix, r in reads.items()}


def gfa_counts(path):
    counts = {b"S": 0, b"L": 0, b"W": 0, b"P": 0}
    carry = b"\n"
    with open(path, "rb") as f:
        while chunk := f.read(1 << 24):
            block = carry + chunk
            for kind in counts:
                counts[kind] += block.count(b"\n" + kind + b"\t")
            carry = block[-2:]
    return counts[b"S"], counts[b"L"], counts[b"W"] + counts[b"P"]


def quantiles(values):
    s = sorted(values)
    return statistics.median(s), s[min(len(s) - 1, int(0.9 * len(s)))], s[-1]


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for name in ("gfaidx", "indexed", "region_name", "walks", "walks_bases", "sequence", "out"):
        p.add_argument(name)
    p.add_argument("--reference")
    p.add_argument("--windows", type=int, default=40)
    p.add_argument("--tmp", default="tmp")
    p.add_argument("--timeout", type=int, default=900)
    p.add_argument("--mount")
    p.add_argument("--pagelog")
    args = p.parse_args()

    tile, opened, starts, window = walk_file(args.walks, args.sequence)
    _, opened_bases, _, window_bases = walk_file(args.walks_bases, args.sequence)
    step = max(1, len(starts) // args.windows)
    chosen = starts[step // 2 :: step][: args.windows]
    gfa = os.path.join(args.tmp, "region.gfa")
    trace = os.path.join(args.tmp, "trace.txt")
    timing = os.path.join(args.tmp, "window-time.txt")
    indexed = os.path.abspath(args.indexed)
    traced = os.path.abspath(args.mount) if args.mount else indexed

    def size_of(suffix):
        return os.path.getsize(indexed if suffix == ".gz" else indexed + suffix)

    def query(cs, prefix, index):
        command = prefix + [args.gfaidx, "get_region", index, f"{args.region_name}:{cs}-{cs + tile}", gfa,
                            "--mode", "all", "--with_coords"] + (["--reference", args.reference] if args.reference else [])
        os.path.exists(gfa) and os.remove(gfa)
        began = time.perf_counter()
        done = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=args.timeout)
        return time.perf_counter() - began, done.returncode

    rows = []
    for cs in chosen:
        if args.pagelog:
            open(args.pagelog, "w").close()
        _, status = query(cs, ["strace", "-f", "-y", "-o", trace, "-e",
                               "trace=open,openat,read,readv,pread64,preadv,lseek,mmap"], traced)
        reads, mapped = traced_reads(trace, traced)
        if args.pagelog:
            reads.update(paged_reads(args.pagelog, os.path.basename(indexed), mapped, size_of))
        runs = []
        peak = 0
        while status == 0 and len(runs) < 3 and sum(runs) < 120:
            seconds, status = query(cs, ["/usr/bin/time", "-f", "%M", "-o", timing], indexed)
            runs.append(seconds)
            peak = max(peak, int(open(timing).read().split()[-1]))
        size = os.path.getsize(gfa) if os.path.exists(gfa) else 0
        rows.append(dict(cs=cs, status=status, reads=reads, mapped=mapped, runs=runs, peak=peak, size=size,
                         counts=gfa_counts(gfa) if size else (0, 0, 0)))

    good = [r for r in rows if r["status"] == 0]
    suffixes = sorted({s for r in good for s in r["reads"]})
    common = {s: None for s in suffixes}
    for r in good:
        for s in suffixes:
            mine = r["reads"].get(s, [])
            common[s] = mine if common[s] is None else intersect(common[s], mine)
    for r in good:
        r["own"] = {s: subtract(r["reads"].get(s, []), common[s]) for s in suffixes}

    with open(args.out + ".windows.tsv", "w") as out:
        print("start", "walks_bytes", "walks_ranges", "walks_blocks_bytes", "walks_bases_bytes", "walks_bases_ranges",
              "walks_bases_blocks_bytes", "gfaidx_status",
              "gfaidx_bytes", "gfaidx_ranges", "gfaidx_mapped_bytes", "gfaidx_bytes_gaps_joined",
              "gfaidx_ranges_gaps_joined", "gfaidx_files", "gfaidx_ms_first", "gfaidx_ms_median", "gfaidx_peak_kb",
              "gfaidx_gfa_bytes", "gfaidx_gfa_S", "gfaidx_gfa_L", "gfaidx_gfa_paths", sep="\t", file=out)
        for r in rows:
            own = r.get("own", {})
            print(r["cs"], *window(r["cs"]), *window_bases(r["cs"]), r["status"],
                  sum(total(v) for v in own.values()), sum(len(v) for v in own.values()),
                  sum(total(v) for s, v in own.items() if s in r["mapped"]),
                  sum(total(merged(v, GAP)) for v in own.values()), sum(len(merged(v, GAP)) for v in own.values()),
                  sum(1 for v in own.values() if v),
                  round(1000 * r["runs"][0]) if r["runs"] else "", round(1000 * statistics.median(r["runs"])) if r["runs"] else "",
                  r["peak"], r["size"], *r["counts"], sep="\t", file=out)

    with open(args.out + ".files.tsv", "w") as out:
        print("file", "size", "open_bytes", "open_ranges", "window_bytes_median", "window_bytes_max",
              "window_ranges_median", "window_ranges_max", "memory_mapped", sep="\t", file=out)
        for s in suffixes:
            per = [total(r["own"][s]) for r in good]
            ranges = [len(r["own"][s]) for r in good]
            path = indexed if s == ".gz" else indexed + s
            print(os.path.basename(path), size_of(s), total(common[s]), len(common[s]),
                  round(statistics.median(per)), max(per), round(statistics.median(ranges)), max(ranges),
                  "yes" if any(s in r["mapped"] for r in good) else "no", sep="\t", file=out)

    with open(args.out + ".open.tsv", "w") as out:
        print("reader", "bytes", "ranges", sep="\t", file=out)
        print("walks", opened, 3, sep="\t", file=out)
        print("walks_bases", opened_bases, 3, sep="\t", file=out)
        print("gfaidx", sum(total(v) for v in common.values()), sum(len(v) for v in common.values()), sep="\t", file=out)

    with open(args.out + ".summary.txt", "w") as out:
        def line(label, values, unit=""):
            m, p90, top = quantiles(values)
            print(f"  {label:34} median {m:>14,.0f}  p90 {p90:>14,.0f}  max {top:>14,.0f}{unit}", file=out)

        print(f"{len(rows)} windows of {tile} bp on {args.sequence}, {len(rows) - len(good)} failed in gfaidx", file=out)
        print(f"walk file ({os.path.basename(args.walks)}): {opened:,} bytes at open", file=out)
        line("bytes per window", [window(r["cs"])[0] for r in rows])
        line("byte ranges per window", [window(r["cs"])[1] for r in rows])
        line("blocks unit of the tile, bytes", [window(r["cs"])[2] for r in rows])
        print(f"walk file with bases ({os.path.basename(args.walks_bases)}): {opened_bases:,} bytes at open", file=out)
        line("bytes per window", [window_bases(r["cs"])[0] for r in rows])
        line("byte ranges per window", [window_bases(r["cs"])[1] for r in rows])
        print(f"gfaidx get_region --mode all --with_coords: {sum(total(v) for v in common.values()):,} bytes in "
              f"{sum(len(v) for v in common.values())} ranges read by every window", file=out)
        if good:
            line("bytes per window", [sum(total(v) for v in r["own"].values()) for r in good])
            line("  of them in memory-mapped files", [sum(total(v) for s, v in r["own"].items() if s in r["mapped"]) for r in good])
            line("byte ranges per window", [sum(len(v) for v in r["own"].values()) for r in good])
            line("bytes, gaps to 64 KB joined", [sum(total(merged(v, GAP)) for v in r["own"].values()) for r in good])
            line("byte ranges, gaps to 64 KB joined", [sum(len(merged(v, GAP)) for v in r["own"].values()) for r in good])
            line("files per window", [sum(1 for v in r["own"].values() if v) for r in good])
            line("wall ms, first run", [1000 * r["runs"][0] for r in good])
            line("wall ms, median of runs", [1000 * statistics.median(r["runs"]) for r in good])
            line("peak memory, KB", [r["peak"] for r in good])
            line("GFA written, bytes", [r["size"] for r in good])
            line("segments in the GFA", [r["counts"][0] for r in good])
            line("path lines in the GFA", [r["counts"][2] for r in good])


if __name__ == "__main__":
    main()
