#!/usr/bin/env python3
"""windows.py PRESET | NAME:LO-HI:COUNT ...  -> stratum<TAB>start<TAB>end, 10 kb windows
evenly spaced, the first at LO and the last ending at HI. Mb units in specs."""
import sys

WIDTH = 10_000
PRESETS = {
    "chr22": [
        "arm:10.5-50.8:50",
        "LCR22A:18.1-18.9:10",
        "LCR22B-D:20.2-21.6:10",
        "IGL:22.0-22.9:10",
        "pericentromeric:15.1-17.0:10",
        "control:29-33:10",
    ],
    "chrY": [
        "arm:2.8-56.8:50",
        "Yp11:2.8-10.2:10",
        "Yq11:11.7-26.6:10",
        "Yq12-het:26.7-56.8:10",
    ],
}

specs = [s for a in sys.argv[1:] for s in PRESETS.get(a, [a])]
for spec in specs:
    name, span, count = spec.split(":")
    lo, hi = (round(float(x) * 1e6) for x in span.split("-"))
    count = int(count)
    step = (hi - lo - WIDTH) // max(count - 1, 1)
    for i in range(count):
        print(f"{name}\t{lo + i * step}\t{lo + i * step + WIDTH}")
