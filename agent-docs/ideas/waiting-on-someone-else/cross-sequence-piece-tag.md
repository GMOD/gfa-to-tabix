---
name: cross-sequence-piece-tag
description: A path that moves onto another sequence of the reference and stays there reads, on the first sequence, like a path that ends, since no row says a piece follows elsewhere. A tag on the piece's walk row naming the step before or after it on the other sequence would say so; an addition to format 8, taken up when a graph with such paths on a chromosome is to be hosted.
metadata:
  repo: gfa-to-tabix, graph-walks
---

# A path that crosses onto another reference sequence

```
W  R  0  chrA  0  30  >1>2>3
W  R  0  chrB  0  22  >5>6>7
W  T  1  c     0  30  >1>2>6>7
W  B  1  c     0  32  >1>2>6>3
```

- T steps from chrA's node 2 onto chrB's node 6 and stays there. It has a
  piece in each sequence's tiles and no departure record, since a record
  lies between two steps on one sequence
  ([departure](../../../docs/walks-format.md#departure)), and neither
  piece's row says that another follows on a different sequence
- A reader of chrA therefore sees T end at node 2, as a contig that ends
  there does. graph-walks 6.2 returned T's fragment with no departure, no
  gap and nothing trimmed, and the link from node 2 to node 6 came back
  from a cut of neither sequence
- B crosses and comes back, so it has a record on chrA: 2 bp of its own
  between adjacent steps, with `ownTiles` `.`. The 2 bp are chrB's node 6,
  which the record can't say, and an attach fetch reads no tile for them
- The reading page states the limit: a reader can say a line has no later
  step on the sequence, not that it ends there nor where on the reference
  it goes ([What a cut returns](../../../docs/walks-reading.md#what-a-cut-returns))

## How often

- In the hosted GRCh38 file, 49 of the 51,257 lines with walk rows have
  pieces on more than one sequence, crossing 1,454 times, every time
  between unplaced or unlocalized scaffolds and never onto a chromosome
  ([count](../../../docs/walks-container/writer/results/hosted.cross-sequence-grch38.txt),
  from `docs/walks-container/writer/scripts/cross-sequence.py`)
- Minigraph-Cactus assigns each contig to one reference chromosome before
  it builds that chromosome's graph, so its graphs hold no path between
  chromosomes. A pggb community of several chromosomes, or any graph with
  a translocation, would

## The proposal

A tag on a piece's walk row giving the sequence, position and strand of
the step before it or after it in its W line, where that step is on
another sequence of the reference. A reader ignores a tag it doesn't know
([Later additions](../../../docs/walks-format.md#later-additions)), so the
format number stays; it is still an addition to the format, to be measured
and decided under ADR 0011's rules.

## What it waits on

No hosted file shows this on a chromosome, so by ADR 0011 nothing changes
until a graph with such paths is to be hosted.
