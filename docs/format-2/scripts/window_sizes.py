"""Compares the bytes a two-chunk read fetches from format 1 and format 2:
each chunk's rows gzipped at level 6 on their own, summed over a chunk and the
one before it, for every chunk of one reference sequence.

usage: window_sizes.py SEQ NEW.walks.bed.gz OLD.walks.bed.gz OLD.nodes.bed.gz OLD.links.bed.gz [--json out]
"""
import gzip
import json
import sys
import zlib
from collections import defaultdict


def per_chunk(paths, seq):
    text = defaultdict(list)
    for path in paths:
        with gzip.open(path, "rt") as f:
            for line in f:
                if line.startswith(seq + "\t"):
                    start = int(line.split("\t", 2)[1])
                    text[start].append(line)
    return {start: len(zlib.compress("".join(lines).encode(), 6)) for start, lines in text.items()}


def quantiles(values):
    values = sorted(values)
    q = lambda p: values[min(len(values) - 1, int(p * len(values)))]
    return {"median": q(0.5), "p90": q(0.9), "p99": q(0.99), "max": values[-1]}


if __name__ == "__main__":
    args = sys.argv[1:]
    jpath = None
    if "--json" in args:
        i = args.index("--json")
        jpath = args[i + 1]
        del args[i : i + 2]
    seq, new, *old = args
    f2 = per_chunk([new], seq)
    f1 = per_chunk(old, seq)
    starts = sorted(set(f1) | set(f2))
    chunk = min(b - a for a, b in zip(starts, starts[1:]))
    windows = []
    for s in starts:
        a = f1.get(s, 0) + f1.get(s - chunk, 0)
        b = f2.get(s, 0) + f2.get(s - chunk, 0)
        if a > 0:
            windows.append((s, a, b))
    ratios = [b / a for _, a, b in windows if a > 10_000]
    print(f"{seq}: {len(windows)} windows; total format 1 {sum(f1.values())/1e6:.1f} MB, format 2 {sum(f2.values())/1e6:.1f} MB ({sum(f2.values())/sum(f1.values()):.3f})")
    print("  two-chunk read, format 2 over format 1:", {k: round(v, 3) for k, v in quantiles(ratios).items()})
    print("  two-chunk read, format 1 MB:", {k: round(v / 1e6, 2) for k, v in quantiles([a for _, a, _ in windows]).items()})
    print("  two-chunk read, format 2 MB:", {k: round(v / 1e6, 2) for k, v in quantiles([b for _, _, b in windows]).items()})
    over = [(s, a, b) for s, a, b in windows if b > 8e6]
    print(f"  windows over 8 MB: format 1 {sum(1 for _, a, _ in windows if a > 8e6)}, format 2 {len(over)}")
    worst = sorted(windows, key=lambda w: -w[2] / max(1, w[1]))[:5]
    print("  highest ratios:", [(s, round(b / a, 2), round(b / 1e6, 2)) for s, a, b in worst if a > 10_000])
    if jpath:
        with open(jpath, "w") as f:
            json.dump({"seq": seq, "format1": f1, "format2": f2}, f)
