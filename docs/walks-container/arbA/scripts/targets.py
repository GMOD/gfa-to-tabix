import gzip, json, random, sys
d = sys.argv[1]
random.seed(99)
out = []
def add(size, start, tag):
    out.append({"size": size, "i": len(out), "start": int(start), "end": int(start) + size, "tag": tag})
regions = {"mc22": [(18_000_000, 19_000_000, "LCR22A"), (20_300_000, 21_600_000, "LCR22B-D"), (22_500_000, 23_000_000, "22q11-IGL")],
           "pggbY": [(23_000_000, 26_600_000, "ampliconic"), (10_250_000, 10_650_000, "cen-long"), (6_000_000, 7_500_000, "TSPY/X-transposed")]}[d]
for lo, hi, tag in regions:
    for size in (1000, 10000, 100000):
        for _ in range(40 if size < 100000 else 15):
            add(size, random.uniform(lo, hi - size), tag)
sw = []
for l in gzip.open(f"out/{d}/depu.bed.gz", "rt"):
    if l.startswith("#"): continue
    c = l.rstrip("\n").split("\t")
    if c[9] != c[12]: sw.append(int(c[8]))
for p in random.sample(sw, min(80, len(sw))):
    size = random.choice((1000, 10000))
    add(size, max(0, p - size // 2), "switch")
print(len(out), "windows,", len(sw), "strand-switch records", file=sys.stderr)
for w in out: print(json.dumps(w))
