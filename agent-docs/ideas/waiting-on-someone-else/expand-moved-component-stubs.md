---
name: expand-moved-component-stubs
description: A component moved by --max-component is drawn as faded dead-end stubs that no reader can expand, because its nodes lie on many contigs and one query cannot fetch it. Filing the moved rows under a sibling sequence would let one more query fetch it; taken up once a graph needs a moved component drawn.
metadata:
  repo: gfa-to-tabix, graph-walks, jbrowse-plugin-graphgenomeviewer
---

# Expanding a component moved by `--max-component`

- The JBrowse plugin draws a moved component as faded dead-end nodes where
  it joins the reference
  ([ADR 0005](../../../docs/adr/0005-giant-components.md))
- A reader can't fetch the component with one more query, because its
  nodes sit on whichever haplotype contig placed each one, and pggb chrY's
  three giants spread over 823 contigs
- Expanding them buys little on the graphs measured: pggb chrY's three
  giants are satellite tangles no budget could draw, and `--max-component`
  already draws mid-size components whole

## The proposal

File the moved components' rows under a sibling sequence, such as
`GRCh38#0#chrY~moved`, which a window query never names, as walk files
file their detail records, so a reader expands a stub by querying the
same window there. It is a change to the index's rows; nothing in `src/`
writes such a sequence (checked 2026-11-25).

## What it waits on

A graph that needs a moved component drawn.
