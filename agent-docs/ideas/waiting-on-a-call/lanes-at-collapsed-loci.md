---
name: lanes-at-collapsed-loci
description: Where a graph keeps identical sequence on separate nodes, as at amylase, lanes read from its walks show a gap beside unmatched sequence for what the bases would align; whether lanes should be offered there, marked, or pointed at the walk rows is the owner's call.
metadata:
  repo: jbrowse-plugin-graphgenomeviewer, jbrowse-components
---

# Lanes where the graph keeps the same sequence on separate nodes

- At `chr1:103,500,000-103,800,000` seven of eight haplotypes never step the
  nodes that hold GRCh38's 94 kb. minimap2 aligns HG01960.1's whole lane to
  GRCh38 as one forward row, and its lane shows 94 kb gone and 94 kb new.
  `todo/lanes-headers-and-fit-at-inversions.md` has the measurements.
- A reader of walks cannot say more without the bases. A Fable review on
  2026-11-22 called lanes "not a sound reading" at such a locus.
- The tutorial's part 3 reads amylase from walk rows, and nothing in the
  lanes points there.

## Options

- Offer lanes everywhere and say, in the header, that a stretch shares no
  node, with no event name. This is what the headers todo does.
- Mark a window where a walk steps a node twice, about a hundred of some
  9,600 windows of 300 kb, and point to the walk rows.
- Align the bases of unshared stretches in the reader, which needs each
  haplotype's sequence beside the walk file.
