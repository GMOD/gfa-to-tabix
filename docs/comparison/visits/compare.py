#!/usr/bin/env python3
"""compare.py truth.tsv cut.tsv: per (window, passes), are the sketches equal?

Exits 1 when a window of nodes the reference passes once differs, or there
are none. Nodes passed more than once are reported, not judged: truth counts
every visit at every pass's window, and a cut holds the visits placed there.
"""

import sys

failed = False


def load(path):
    with open(path) as f:
        next(f)
        return {(int(w), p): (int(n), int(a), int(b)) for w, p, n, a, b in (l.split() for l in f)}


truth, cut = load(sys.argv[1]), load(sys.argv[2])
for passes in ("single", "multi"):
    keys = sorted({k for k in truth.keys() | cut.keys() if k[1] == passes})
    bad = [k for k in keys if truth.get(k) != cut.get(k)]
    if passes == "single" and (bad or not keys):
        failed = True
    n_truth = sum(truth.get(k, (0,))[0] for k in keys)
    n_cut = sum(cut.get(k, (0,))[0] for k in keys)
    print(f"{passes}: windows {len(keys)}, differing {len(bad)}, visits truth {n_truth} cut {n_cut}")
    for k in bad[:10]:
        t, c = truth.get(k, (0, 0, 0)), cut.get(k, (0, 0, 0))
        print(f"  window {k[0]} ({k[0] * 65536}): truth n {t[0]}, cut n {c[0]}")
sys.exit(1 if failed else 0)
