"""lostsum.py OUT_DIR NAME...: lost (node, haplotype) pairs by where the walk
file holds them: in chunks the cut read, in chunks its skip rows name, or
elsewhere"""
import json
import sys

out = sys.argv[1]
for name in sys.argv[2:]:
    with open(f"{out}/{name}.lostcheck.json") as f:
        data = json.load(f)
    rows = data if isinstance(data, list) else data.get("rows") or data.get("pairs") or []
    lost = sum(r["lost"] for r in rows)
    read = sum(r["inRead"] for r in rows)
    skip = sum(r["inSkipFrom"] for r in rows)
    print(f"{name}: {len(rows)} pairs, {lost} lost nodes; in read chunks {read} "
          f"({100 * read / max(lost, 1):.0f}%), in skip chunks {skip}, elsewhere {lost - read - skip} "
          f"({100 * (lost - read - skip) / max(lost, 1):.0f}%)")
