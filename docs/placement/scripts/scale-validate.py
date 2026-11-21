#!/usr/bin/env python3
"""Checks every W line of a GFA against its S and L lines.

scale-validate.py GFA [GFA ...]

Per GFA, one tab-separated line: W lines; haplotypes (sample#hap); lines
repeating another's path (sample#hap#seq) and start; lines whose end -
start is not their steps' bp; names that are not bytes 0x21-0x7E or start
with #; steps; links walked; links walked that no L line gives, and the
distinct such links. Exits 1 if a line repeats a path and start, disagrees
on bp or is misnamed, or a link walked is in no L line.
Needs numpy and pigz.
"""

import subprocess
import sys

import numpy as np

TO_SPACE = bytes.maketrans(b"<>", b"  ")


def key(h1, h2):
    return np.minimum(h1 * (1 << 28) + h2, (h2 ^ 1) * (1 << 28) + (h1 ^ 1))


def bad_name(b):
    return b[:1] == b"#" or any(c < 0x21 or c > 0x7E for c in b)


def lines(path):
    reader = subprocess.Popen(["pigz", "-dc", path], stdout=subprocess.PIPE, bufsize=1 << 24)
    yield from reader.stdout
    assert reader.wait() == 0


def check(path):
    lengths = {}
    links = []
    for line in lines(path):
        kind = line[:2]
        if kind == b"S\t":
            cols = line.rstrip(b"\n").split(b"\t")
            n = len(cols[2]) if cols[2] != b"*" else int(next(c for c in cols[3:] if c.startswith(b"LN:i:"))[5:])
            lengths[int(cols[1])] = n
        elif kind == b"L\t":
            cols = line.split(b"\t", 5)
            links.append((int(cols[1]) * 2 + (cols[2] == b"-"), int(cols[3]) * 2 + (cols[4] == b"-")))
    length = np.zeros(max(lengths) + 1, dtype=np.int64)
    for k, v in lengths.items():
        length[k] = v
    pairs = np.array(links, dtype=np.int64)
    keys = np.unique(key(pairs[:, 0], pairs[:, 1]))
    names = set()
    haps = set()
    w_lines = twice = bad_bp = bad_names = steps = walked = missing = 0
    missing_keys = set()
    for line in lines(path):
        if line[:2] != b"W\t":
            continue
        w_lines += 1
        cols = line.rstrip(b"\n").split(b"\t")
        sample, hap, seq, start, end, text = cols[1], cols[2], cols[3], int(cols[4]), int(cols[5]), cols[6]
        name = (sample, hap, seq, start)
        twice += name in names
        names.add(name)
        haps.add((sample, hap))
        bad_names += bad_name(sample) or bad_name(sample + b"#" + hap + b"#" + seq)
        raw = np.frombuffer(text, dtype=np.uint8)
        reverse = raw[(raw == 62) | (raw == 60)] == 60
        ids = np.fromstring(text.translate(TO_SPACE), dtype=np.int64, sep=" ")
        bad_bp += int(length[ids].sum()) != end - start
        handles = ids * 2 + reverse
        k = key(handles[:-1], handles[1:])
        found = np.searchsorted(keys, k)
        ok = (found < len(keys)) & (keys[np.minimum(found, len(keys) - 1)] == k)
        steps += len(ids)
        walked += len(k)
        missing += int((~ok).sum())
        missing_keys.update(k[~ok].tolist())
    return [w_lines, len(haps), twice, bad_bp, bad_names, steps, walked, missing, len(missing_keys)]


def main():
    cols = ["gfa", "w_lines", "haplotypes", "same_path_and_start", "bp_mismatch", "bad_names", "steps", "links_walked", "links_not_in_L", "distinct_links_not_in_L"]
    print("\t".join(cols))
    failed = False
    for path in sys.argv[1:]:
        row = check(path)
        print("\t".join([path.rsplit("/", 1)[-1]] + [str(x) for x in row]), flush=True)
        failed = failed or row[2] or row[3] or row[4] or row[7]
    sys.exit(1 if failed else 0)


main()
