"""Summarise measure.mjs output: per candidate and window size, bytes
(median / p90 / p99), requests, sequential round trips, and the split
between the walk read, the departure read and attach fetches.

usage: python3 -I summarize.py OUT.jsonl [--md]
"""
import json
import sys
from collections import defaultdict


def pct(xs, p):
    xs = sorted(xs)
    if not xs:
        return 0
    k = (len(xs) - 1) * p
    lo = int(k)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def kb(x):
    return f"{x / 1000:.0f}"


rows = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
md = "--md" in sys.argv
groups = defaultdict(list)
order = []
for r in rows:
    key = (r["candidate"], r["size"])
    if key not in groups:
        order.append(key)
    groups[key].append(r)

if md:
    print("| candidate | window | total KB med / p90 / p99 | requests med / max | rounds med / max | walk KB med | dep KB med | attach KB med / p90 | walk rows med | open KB |")
    print("|---|---|---|---|---|---|---|---|---|---|")
else:
    print(f"{'candidate':10} {'size':>8} | {'total KB med/p90/p99':>22} | {'req med/max':>11} | {'rounds':>7} | {'walk':>5} {'dep':>5} {'att med/p90':>11} | {'rows':>6} | open KB")
for key in order:
    g = groups[key]
    total = [r["bytes"] for r in g]
    req = [r["requests"] for r in g]
    rnd = [r["rounds"] for r in g]
    walk = [r["walk"]["bytes"] for r in g]
    dep = [r["dep"]["bytes"] for r in g]
    att = [r["attach"]["bytes"] for r in g]
    lines = [r["walk"]["lines"] for r in g]
    open_kb = kb(g[0]["open"]["bytes"])
    t = f"{kb(pct(total, .5))} / {kb(pct(total, .9))} / {kb(pct(total, .99))}"
    if md:
        print(f"| {key[0]} | {key[1] // 1000} kb | {t} | {pct(req, .5):.0f} / {max(req)} | {pct(rnd, .5):.0f} / {max(rnd)} | {kb(pct(walk, .5))} | {kb(pct(dep, .5))} | {kb(pct(att, .5))} / {kb(pct(att, .9))} | {pct(lines, .5):.0f} | {open_kb} |")
    else:
        print(f"{key[0]:10} {key[1]:>8} | {t:>22} | {pct(req, .5):>5.0f}/{max(req):<5} | {pct(rnd, .5):.0f}/{max(rnd):<4} | {kb(pct(walk, .5)):>5} {kb(pct(dep, .5)):>5} {kb(pct(att, .5)):>5}/{kb(pct(att, .9)):<5} | {pct(lines, .5):>6.0f} | {open_kb}")
