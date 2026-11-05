"""The cross-examination table: per candidate and window size, bytes with
graph-walks' attach fetches (what a window costs) and without (the walk and
departure reads alone, arbA's measure), requests and round trips.

usage: python3 -I xtable.py LABEL FILE[:cand=alias,...] ...
"""
import json
import sys
from collections import defaultdict


def pct(xs, p):
    xs = sorted(xs)
    k = (len(xs) - 1) * p
    lo = int(k)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


label = sys.argv[1]
g = defaultdict(list)
for spec in sys.argv[2:]:
    path, _, rename = spec.partition(":")
    aliases = dict(x.split("=") for x in rename.split(",")) if rename else {}
    for line in open(path):
        r = json.loads(line)
        name = aliases.get(r["candidate"], r["candidate"])
        if aliases and r["candidate"] not in aliases:
            continue
        g[(name, r["size"])].append(r)


def kb(x):
    return f"{x / 1000:.0f}"


print(f"| {label}: candidate | window | with attach fetches, KB med / p90 / p99 | walk + departure reads only | requests med / max | round trips med / max |")
print("|---|---|---|---|---|---|")
order = []
for k in g:
    if k[0] not in order:
        order.append(k[0])
for name in order:
    for size in (1000, 10000, 100000, 1000000):
        rs = g.get((name, size))
        if not rs:
            continue
        tot = [r["bytes"] for r in rs]
        wd = [r["walk"]["bytes"] + r["dep"]["bytes"] for r in rs]
        req = [r["requests"] for r in rs]
        rnd = [r["rounds"] for r in rs]
        print(f"| {name} | {size // 1000} kb | {kb(pct(tot, .5))} / {kb(pct(tot, .9))} / {kb(pct(tot, .99))} | {kb(pct(wd, .5))} / {kb(pct(wd, .9))} / {kb(pct(wd, .99))} | {pct(req, .5):.0f} / {max(req)} | {pct(rnd, .5):.0f} / {max(rnd)} |")
