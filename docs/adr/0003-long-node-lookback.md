# ADR 0003: Read back to a long node only where it overlaps the window

- **Status:** accepted, 2026-10-20
- **Decides:** how far before a window a walk-file reader reads, and how far
  ahead the stay's guard lets a piece reach
- **Amends:** [ADR 0001](0001-step-placement.md), whose guard admitted a node
  up to `max(chunk, maxnode) / chunk` chunks after the piece's

## Context

- A walk file's `maxnode` set every window's lookback. pggb chr22 has 21
  reference passes over nodes longer than a 64 kb chunk on GRCh38 (N runs, up
  to 1 Mb) and 6 on CHM13 (an unaligned stretch, up to 1.97 Mb), so every
  window read 16 and 31 chunks back
- The stay's guard used the same number, so pieces reached up to 15 and 30
  chunks ahead, and only that long lookback could see them
- On CHM13 the long lookback alone put 225 windows over graph-walks' 8 MB
  byte budget, which refuses them before downloading

## Decision

- The guard admits a node the reference passes once only in the piece's chunk
  or the next
- A `#long` header line gives each reference pass over a node longer than a
  chunk: sequence, start, end
- A reader reads from the chunk before the window, or from the chunk before
  a `#long` pass the window overlaps, whichever is earlier. A file without
  `#long` lines keeps the `maxnode` lookback

The format stays 4: graph-walks 3.0 ignores `#long` and reads further back
than it needs to, and MC files, whose `maxnode` is at most a chunk, get the
same rows and no `#long` lines.

## Evidence

pggb chr22, stay 311, scored as ADR 0001 scores (`scripts/walks-truth.py`, 12
haplotypes), against the 1.2 file read at its own lookback. Window cost is the
compressed bytes a reader fetches for one 64 kb window:

| measure | GRCh38: 1.2 → this | CHM13: 1.2 → this |
|---|---|---|
| window cost, median | 0.82 → 0.09 MB | 1.99 → 0.11 MB |
| window cost, p90 | 6.2 → 0.68 MB | 84 → 3.2 MB |
| windows over 8 MB | 42 → 25 | 225 → 23 |
| windows over 100 MB | 16 → 4 | 28 → 0 |
| windows over 32 M steps | 102 → 22 | 516 → 47 |
| strict recall | 97.47% → 97.25% | 98.53% → 93.91% |
| pieces | 3.42 M → 4.88 M | 10.65 M → 8.09 M |
| file | 728 MB → 745 MB | 460 MB → 422 MB |

- Read one chunk back, the 1.2 file scores the same strict recall as this one
  on both references: the lost points are pieces only a 31-chunk read saw
- CHM13's loss by region, 1.2 → this:
  - short arm: 94.55% → 76.85% of 1,486 pairs, about three quarters of the
    loss. The 1.2 reader refuses 186 of its 190 windows over the byte budget
  - pericentromere: 92.05% → 81.92% of 365 pairs, in windows the 1.2 reader
    served
  - elsewhere: 99.96% → 98.87% of 4,684 pairs, also served
- Build: 12:06 and 15.3 GB peak on ada

## Alternatives

A guard of 2 or 4 chunks, with a reader that reads as many back, on CHM13:

| guard | strict recall | pericentromere | window median | windows over 8 MB |
|---|---|---|---|---|
| 1 (this) | 93.91% | 81.92% | 0.11 MB | 23 |
| 2 | 94.22% | 83.29% | 0.17 MB | 44 |
| 4 | 94.68% | 85.75% | 0.30 MB | 75 |
| 1.2 file, 31 chunks back | 98.53% | 92.05% | 1.99 MB | 225 |

The lost pairs sit in pieces filed more than 4 chunks from where they align,
so a wider guard buys under a point of recall for up to three times the
refused windows. GRCh38 moves the same way (97.25%, 97.32%, 97.41%).

## Consequences

- The remaining giant windows hold satellite and rDNA arrays that pggb
  collapses into small looping nodes: 25 GRCh38 windows and 23 CHM13 windows
  over 8 MB, at most 168 MB. Filing can't shrink them; a reader has to
  explain them or a later format has to summarize them
- graph-walks 3.1 reads `#long`; its `queryStart` takes the window's
  `refName` and `end` so a byte estimate covers the same read
