"""Bytes htslib's `tabix` reads from the data file per window (strace), for
a candidate's walk and departure regions.

usage: htslib_bytes.py FILE WINDOWS.jsonl MODE OUT.jsonl [REACH] [N_PER_SIZE]
  MODE reach:    walk read [drawn.start - reach, drawn.end) as is (real spans)
  MODE reach1bp: the same, start rounded down to a chunk start (1 bp keys)
  MODE lookback: graph-walks 5's read from the chunk before
"""
import json
import os
import re
import subprocess
import sys
from collections import defaultdict

file, windows, mode, out = sys.argv[1:5]
reach = int(sys.argv[5]) if len(sys.argv) > 5 else 1024
n_per = int(sys.argv[6]) if len(sys.argv) > 6 else 100
chunk = 65536
base = os.path.basename(file)


def chunk_start(x, back=0):
    return max(0, (x // chunk - back) * chunk)


def traced(region):
    trace = out + ".strace"
    p = subprocess.run(
        ["strace", "-f", "-e", "trace=read,pread64,openat", "-o", trace, "tabix", file, region],
        capture_output=True,
        text=True,
    )
    lines = p.stdout.count("\n")
    fds = set()
    total = 0
    for line in open(trace):
        m = re.search(r'openat\(.*"([^"]+)".*\) = (\d+)', line)
        if m and m.group(1).endswith(base):
            fds.add(m.group(2))
            continue
        m = re.match(r"(?:\d+\s+)?(?:p?read64?|read)\((\d+),.*\) = (\d+)", line)
        if m and m.group(1) in fds:
            total += int(m.group(2))
    return total, lines


seen = defaultdict(int)
with open(out, "w") as f:
    for raw in open(windows):
        w = json.loads(raw)
        if seen[w["size"]] >= n_per:
            continue
        seen[w["size"]] += 1
        seq = w["seq"]
        ds, de = max(0, w["start"] - 1000), w["end"] + 1000
        if mode == "reach":
            s = max(0, ds - reach)
        elif mode == "reach1bp":
            s = chunk_start(max(0, ds - reach))
        else:
            s = chunk_start(ds, 1)
        walk, wl = traced(f"{seq}:{s + 1}-{de}")
        dep, dl = traced(f"{seq}~departure:{max(1, ds - reach + 1)}-{de + reach}")
        f.write(json.dumps({"mode": mode, "size": w["size"], "start": w["start"], "walk": walk, "dep": dep, "total": walk + dep}) + "\n")
