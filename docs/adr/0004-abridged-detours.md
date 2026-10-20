# ADR 0004: Abridge a chunk's costliest pieces into a detail tier

- **Status:** accepted, 2026-10-20
- **Decides:** what a walk file holds for a chunk too costly for a browser to
  read, and how readers show it
- **Decision:** the writer gives each chunk a cost budget. Over it, the writer
  moves the costliest pieces, whole, to a detail tier that window queries never
  read, and leaves one summary row per path. Walk format 5
- **Supersedes:** the zoom-in and byte-budget notices for windows that no zoom
  fits, which graph-walks shows today

## Context

- After [ADR 0003](0003-long-node-lookback.md), 21 CHM13 and 25 GRCh38 windows
  of pggb chr22 still cost over graph-walks' 8 MB byte budget, up to 166 MB.
  Every one is refused even at the narrowest zoom
- Every one lies in a satellite array. pggb gives each haplotype its own path
  through the array, a median of 137 kb and up to 943 kb long, over about
  100 k nodes that are mostly 1 bp. CHM13 lacks that sequence, so the writer files the whole array under
  the chunk where the haplotype leaves the reference
- One CHM13 chunk holds 66 M steps and one GRCh38 chunk 466 M
- Raising the budget doesn't help:
  - a graph cut then hits the step budget
  - a walk-rows cut of a 12.6 MB window takes 87 s and 869 MB in Node
- A leaner encoding doesn't help either:
  - pggb has already unchopped these graphs
  - at 83% of steps the path takes a branch, so the steps hold real information
  - cross-haplotype copies cut bytes about 5×, but leave every step to decode

## Decision

**Writer**

- A piece's cost is its routes' interior steps, plus its steps along R / 4.
  graph-walks decodes steps along R 30–50× faster than interior steps, but a
  cut keeps and draws every one: weighted at a 40th, a CHM13 p-arm window
  still held 91 M steps and took 77 s to cut
- Each chunk gets a budget: 1 M cost units and 3 MB compressed. Over budget,
  the writer moves the costliest piece to the detail tier, then the next,
  until the chunk fits
- The chunk keeps one summary row per path whose pieces moved, listing:
  - the pieces' count, steps and bp
  - the first and last handle on R
  - where the detail lives
- A route that a kept piece uses stays in the chunk
- The header states the budget. A chunk under it gets the same rows as format 4

**Detail tier**

- The writer files each moved path's rows for the chunk, encoded to stand
  alone, under a sibling sequence name in the same file. A window query names
  only the reference sequence, so it never reads them

**Readers**

- graph-walks returns a summary row as a short walk with its counts, and fetches
  its detail on request
- A viewer draws an abridged haplotype as a labelled block, such as
  `HG00097#1: 140 k steps, 2.1 Mb off reference`. Clicking the block loads the
  detail
- The step budget counts interior steps, and the reader keeps R's stretches as
  ranges. After abridging, some p-arm windows still hold 32–65 M steps along R,
  which decode in about 3 s

## Evidence

The writer was simulated on the long311 builds (ADR 0003 rules) and on HPRC
v2.1 Minigraph-Cactus genome-wide (`mcu311`). A window is chunks c−1 and c,
plus the `#long` lookback, as graph-walks 3.1 reads it. Bytes are the chunk's
rows compressed in 64 kB blocks, as bgzip does.

| measure | pggb CHM13 | pggb GRCh38 |
|---|---|---|
| windows over 8 MB, before → after | 21 → 0 | 25 → 0 |
| largest window, before → after | 43 → 6.2 MB | 166 → 7.8 MB |
| most interior steps in a window, before → after | 57 M → 1.7 M | 267 M → 1.9 M |
| chunks abridged | 53 of 739 | 29 of 610 |
| (haplotype, chunk) pairs left with no kept piece | 259 of 324 k | 1,357 of 274 k |

- On Minigraph-Cactus the writer abridges 107 of 43,475 CHM13 chunks and 176 of
  47,440 GRCh38 chunks, in the chr2, chr9 and chr14 repeat windows. CHM13
  windows over 8 MB go from 2 to 0. These figures come from a run that measured
  bytes as one zlib stream
- The writer leaves every other chunk's rows byte-identical
- The largest moved piece, in GRCh38 chunk 12648448, has 1.14 M steps. Encoded
  alone it is 0.99 MB gzipped, and graph-walks decodes it in 0.5 s using
  180 MB

The scripts and outputs are on ada: `~/giant-review/design-fable/` (`abridge3b.py`,
`summarize.py`, `v3b.pggb.*.tsv`), and the five reviews' directories under
`~/giant-review/design-*/`.

## Consequences

- Every pggb chr22 window opens without a notice. Users lose step-level paths
  by default in 29–53 chunks per reference, which they can't open today, and
  each path is one click away
- Recall as `walks-truth.py` scores it can fall only by the pairs left with no
  kept piece, at most 0.5%. Not yet rescored
- Not yet measured:
  - how long the JBrowse plugin takes to open the p-arm windows that hold
    32–65 M steps along R
  - the detail tier's total size

## Alternatives rejected

- **Load anyway:** a raised budget cut takes minutes and up to 1 GB, and the
  graph cut is still refused
- **Unchop or compact the graph:** removes 1,027 of 66 M steps in the worst
  chunk
- **Cross-haplotype copy coding:** fixes bytes, not decode or layout time
- **Spread an off-reference array over the reference it bridges:** many chunks
  stay over 10 M steps, because their paths loop over the reference's own array
- **A coarse summary (per-node depth or a quotient graph) as the only view:**
  hides haplotypes' paths everywhere it applies. The detail tier keeps them
  one click away
