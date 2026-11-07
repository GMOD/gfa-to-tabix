# Collects the reshape numbers into one table, from the files under out/.
import json, os
O = "out/"
def summ(path):
    return json.load(open(path))["summary"] if path.endswith(".json") else json.loads(open(path).read())["summary"]
def row(name, size, s):
    cells = []
    for w in ("1000", "65536", "1000000"):
        x = s[w]
        cells.append("%.1f / %.1f" % (x["med"], x["p90"]))
    return f"| {name} | {size/1e6:.2f} MB | " + " | ".join(cells) + " |"
print("Window bytes, KB (1000 B) median / p90, tile + departures units overlapping window +- 1 kb, arbA seeded windows, 300 per size")
print("| file | data file | 1 kb | 64 kb | 1 Mb |")
print("|---|---|---|---|---|")
for g in ("mc22", "pggbY"):
    print(row(f"{g} format 7 (base)", os.path.getsize(f"{O}base.{g}.GRCh38.walks.gz"), summ(f"{O}win.base.{g}.sum")))
    if g == "pggbY":
        print(row(f"{g} R1", os.path.getsize(f"{O}r1.{g}.GRCh38.walks.gz"), summ(f"{O}win.r1.{g}.sum")))
    else:
        print(row(f"{g} R1 (byte-identical)", os.path.getsize(f"{O}r1.{g}.GRCh38.walks.gz"), summ(f"{O}win.base.{g}.sum")))
    r2 = json.load(open(f"{O}r2.base.{g}.json"))
    print(row(f"{g} R2 over base (simulated)", r2["bytes_new"], r2["summary"]))
    if g == "pggbY":
        r = json.load(open(f"{O}r2.r1.{g}.json"))
        print(row(f"{g} R1+R2 (simulated)", r["bytes_new"], r["summary"]))
print()
for f in ("deps.base.mc22.json", "deps.base.pggbY.json", "deps.r1.pggbY.json"):
    print(f, open(O + f).read().strip())
for f in ("r2.base.mc22.json", "r2.base.pggbY.json", "r2.r1.pggbY.json"):
    d = json.load(open(O + f))
    print(f, {k: d[k] for k in ("bytes_old", "bytes_new", "parts_old", "parts_new", "gap_units", "dep_units_old", "tile_text_added", "stats")})
for f in ("base.mc22.log", "r1.mc22.log", "base.pggbY.log", "r1.pggbY.log", "r1stay0.pggbY.log"):
    print(f, [l.strip() for l in open(O + f) if l.startswith("stats") or "departure records" in l or "lines in" in l or "peak" in l and ":" in l and l[0] != "["])
