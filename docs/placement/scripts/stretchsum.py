"""stretchsum.py OUT_DIR NAME...: lost nodes by where the haplotype carries
them relative to the window, from lostcheck's `stretches`"""
import json
import sys
from collections import Counter

out = sys.argv[1]
for name in sys.argv[2:]:
    with open(f"{out}/{name}.lostcheck.json") as f:
        rows = json.load(f)
    lost = sum(r["lost"] for r in rows)
    where = Counter()
    for r in rows:
        for k, v in r["stretches"].items():
            where[k] += v
    placed = sum(where.values())
    print(f"{name}: {lost} lost nodes; on the haplotype's steps in read chunks {placed}: "
          + ", ".join(f"{k} {v}" for k, v in where.most_common())
          + f"; not on read steps {lost - placed}")
