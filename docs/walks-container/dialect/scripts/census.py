#!/usr/bin/env python3
"""The path lines of a GFA, by the shape of their names.

Reads a GFA, gzip or not, from the file named or from stdin (`-`), and prints:
its S, P and W line counts and how many S lines carry an SN tag; each P line
name's shape, counted, with an example; how many P names are written twice;
for a P name that ends in a `:a-b` or a `[s-e]`, whether its steps span the
range; and, for W lines, how many start above 0 and how many pairs of one
sample#haplotype#contig overlap or share a start.

With --no-lengths it holds no segment's length, for a graph too large to,
and leaves the ranges unchecked.

Usage: census.py LABEL GFA|- [--no-lengths]
"""
import collections
import gzip
import re
import sys

label, path = sys.argv[1:3]
hold_lengths = "--no-lengths" not in sys.argv
SHAPES = [
    ("sample#hap#contig:a-b", r"[^#]*#[^#]*#[^#]*:[0-9]+-[0-9]+"),
    ("sample#hap#contig#N[s-e]", r"[^#]*#[^#]*#[^#]*#[0-9]+\[[0-9]+(-[0-9]+)?\]"),
    ("sample#hap#contig#N", r"[^#]*#[^#]*#[^#]*#[0-9]+"),
    ("sample#hap#contig[s-e]", r"[^#]*#[^#]*#[^#]*\[[0-9]+(-[0-9]+)?\]"),
    ("sample#hap#contig", r"[^#]*#[^#]*#[^#:\[]*"),
    ("sample#contig:a-b", r"[^#]*#[^#]*:[0-9]+-[0-9]+"),
    ("sample#contig", r"[^#]*#[^#:\[]*"),
    ("name:a-b", r"[^#]*:[0-9]+-[0-9]+"),
    ("name", r"[^#:\[]*"),
]
RANGED = re.compile(r".*(?::([0-9]+)-([0-9]+)|\[([0-9]+)-([0-9]+)\])")
stream = sys.stdin.buffer if path == "-" else gzip.open(path, "rb") if path.endswith(".gz") else open(path, "rb")
counts = collections.Counter()
shapes, examples, written = collections.Counter(), {}, collections.Counter()
lengths, ranged, walks = {}, [], collections.defaultdict(list)
for line in stream:
    kind = line[:2]
    if kind == b"S\t":
        counts["S"] += 1
        counts["S with SN"] += b"\tSN:Z:" in line
        if hold_lengths:
            c = line.rstrip(b"\r\n").split(b"\t")
            ln = next((int(t[5:]) for t in c[3:] if t.startswith(b"LN:i:")), None)
            lengths[c[1]] = len(c[2]) if c[2] != b"*" else ln
    elif kind == b"P\t":
        counts["P"] += 1
        c = line.split(b"\t", 3)
        name = c[1].decode("utf-8", "surrogateescape")
        written[name] += 1
        shape = next((s for s, pattern in SHAPES if re.fullmatch(pattern, name)), "other")
        shapes[shape] += 1
        examples.setdefault(shape, name)
        if RANGED.fullmatch(name):
            ranged.append((name, [s[:-1] for s in c[2].split(b",") if s]))
    elif kind == b"W\t":
        counts["W"] += 1
        c = line.split(b"\t", 6)
        if c[4] == b"*":
            counts["W with a * start"] += 1
        else:
            counts["W starting above 0"] += int(c[4]) > 0
            walks[b"#".join(c[1:4])].append((int(c[4]), int(c[5]) if c[5] != b"*" else int(c[4])))
print(f"== {label}")
print(", ".join(f"{n} {what}" for what, n in counts.items()) or "no S, P or W line")
for shape, n in shapes.most_common():
    print(f"  {n}\tP {shape}\te.g. {examples[shape]}")
print(f"  {sum(1 for n in written.values() if n > 1)} P names written more than once")
verdicts = collections.Counter()
for name, steps in ranged:
    m = RANGED.fullmatch(name)
    a, b = (int(m.group(1)), int(m.group(2))) if m.group(1) else (int(m.group(3)), int(m.group(4)))
    bp = sum(lengths[s] for s in steps) if all(s in lengths for s in steps) else None
    verdicts["unchecked, its S lines weren't read" if bp is None else "0-based, end - start is its bp" if b - a == bp
             else "1-based, end - start + 1 is its bp" if b - a + 1 == bp else "neither"] += 1
for verdict, n in verdicts.items():
    print(f"  {n}\tP names ending in a range: {verdict}")
collide = 0
for spans in walks.values():
    spans.sort()
    collide += sum(1 for (a, b), (c, d) in zip(spans, spans[1:]) if c == a or c < b)
if walks:
    print(f"  {len(walks)} W paths; {collide} pairs of one path's lines overlap or share a start")
