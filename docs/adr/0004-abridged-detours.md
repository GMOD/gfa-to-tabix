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
- graph-walks' read budget counts a step along R as a quarter, as the writer
  does

## Evidence

Built with gfa-to-tabix 1.4 from HPRC pggb chr22, `--stay 311`, at the default
budget. A window is chunks c−1 and c, plus the `#long` lookback, as graph-walks
reads it, and its cost is the compressed bytes its Tabix index points at.

| measure | GRCh38: 1.3 → 1.4 | CHM13: 1.3 → 1.4 |
|---|---|---|
| windows over 8 MB | 25 → 0 | 21 → 0 |
| largest window | 166 → 1.6 MB | 43 → 3.0 MB |
| windows reading over 32 M steps | 22 → 0 | 47 → 0 |
| paths abridged | 17,098 | 33,634 |

graph-walks 4 cutting CHM13 windows for every haplotype in Node, as walk rows:

| window | 1.3 rows, budgets raised | 1.4 |
|---|---|---|
| satellite, 2359296 | 87 s (the 12.6 MB window) | 3.5 s |
| p-arm, 5636096 | 77 s (weighted at a 40th) | 4.8 s |
| costliest, 6881280 | | 8.6 s |
| ordinary, 30015488 | 0.7 s | 0.7 s |

- Expanding HG00097#1 in the satellite window reads its 284 k steps from the
  detail records, in 3.7 s for the whole cut
- A graph cut of the satellite windows asks to zoom in to about 20 kb, which
  fits
- The build takes 18 min and 19 GB, against 12 min and 15 GB. The files grow
  from 745 to 1,409 MB (GRCh38) and from 422 to 704 MB (CHM13), since each
  holds its detail records
- The simulations that chose the design are on ada in
  `~/giant-review/design-fable/`, and the five reviews' work in
  `~/giant-review/design-*/`. The build and costs are in `~/giant-review/f5/`

## Consequences

- Every pggb chr22 window opens without a notice. Users lose step-level paths
  by default in 29–53 chunks per reference, which they can't open today, and
  each path is one click away
- Recall as `walks-truth.py` scores it can fall only by the pairs left with no
  kept piece, at most 0.5%

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
