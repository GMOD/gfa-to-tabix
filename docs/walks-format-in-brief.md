# Walk files in brief

A walk file holds the haplotype paths of a pangenome graph, the W and P
lines of its GFA, arranged by where they lie on one reference genome. A
viewer fetches the paths through a region of that reference from a static
web host with a few HTTP range requests.

```bash
gfa-to-tabix chr22.gfa --walks --refs GRCh38 -o chr22
```

The command writes two files:

- `chr22.GRCh38.walks.gz` has the paths as lines of text in gzip blocks, so
  `zcat` prints all of it
- `chr22.GRCh38.walks.gz.idx` is a small text directory of byte ranges in
  the first file

This page explains the ideas of the format on one small graph.
[walks-format.md](walks-format.md) is the specification, with every column
and rule.

## One small graph

[walks-schematic.gfa](figures/walks-schematic.gfa) has a 90 bp reference of
nine 10 bp nodes. CHM13 takes node 10 in place of node 5, and HG002 takes
the 5 bp node 11 in place of nodes 4 to 6.

The figure shows the graph, the two files that gfa-to-tabix writes from it,
and what a viewer fetches to draw chr1:31-60:

![The walk file of walks-schematic.gfa, built with --tile 30, read for chr1:31-60: three tiles over the graph of nine reference nodes, with CHM13 dipping to node 10 under node 5 and HG002 dipping to node 11 under nodes 4 to 6; the .idx line with the byte range of chr1's table; the data file as a bar of header, tile 0, departures 0-30, tile 30, departures 30-60, tile 60, departures 60-90 and table, with tile 30 and departures 30-60 shaded as one request; then the ref, route, walk and departure rows of those two units with a label under each column](figures/walks-bytes.svg)

## The file is cut into tiles along the reference

- gfa-to-tabix cuts each reference sequence into tiles and compresses each
  tile separately. A tile is 65536 bp by default, and 30 bp in the figure.
- A table after the tiles of each reference sequence lists their byte
  ranges, and the `.idx` gives the byte range of each table.
- To draw chr1:31-60, a viewer reads the `.idx`, then the table, then the
  tiles that overlap the window. In the figure that is tile 30, the shaded
  request.

## A tile stores the reference once and each detour once

A tile has three kinds of row:

- **`ref` rows** list the nodes of the reference through the tile, with
  their lengths.
- **A `route` row** is one detour off the reference: the node where it
  leaves, the nodes it visits, and the node where it returns. A tile lists
  each distinct detour once, however many haplotypes take it.
- **A `walk` row** is one haplotype's path through the tile, as the node it
  starts on and the routes it takes. Between routes the path follows the
  reference, so a haplotype that matches the reference across a tile is one
  short row.

In tile 30 of the figure, the reference is nodes 4, 5 and 6, and the one
route leaves at node 4, visits node 10 and returns at node 6. CHM13's walk
row has 3 steps, starts on node 4 and takes that route, so a reader rebuilds
its path as nodes 4, 10 and 6.

A row writes a node as its id and strand in one number, and a list of nodes
as differences between neighbours, which is why the figure's `8,2,2` reads
as nodes 4, 5 and 6. [Rows](walks-format.md#rows) has the rule.

## A departure record gives where a path leaves and rejoins the reference

HG002 leaves the reference after node 3, in tile 0, and rejoins at node 7,
in tile 60. It has no row in tile 30, because it has no step on a reference
node there, so a viewer that read tile 30 alone would draw chr1:31-60
without HG002.

- **A `departure` row** gives the two positions on the reference where a
  path leaves and rejoins, and how many bp the path has in between. HG002's
  row gives 30, 60 and 5 bp.
- The file has `departures` units beside its tiles. The writer puts a
  record in the units along its whole stretch, so a viewer whose window
  lies anywhere between the two ends reads it. HG002's record is in all
  three units of the figure.
- A detour that leaves and returns inside one tile has no record, because
  the tile's `route` and `walk` rows show it.

## One file per reference

- Every position in `chr22.GRCh38.walks.gz` is a GRCh38 coordinate, 0-based
  and half-open as in BED. `--refs GRCh38,CHM13` writes a second file with
  CHM13 coordinates.
- The header of a file lists its haplotypes, so a viewer can list them
  before it reads a tile.

## What a walk file leaves out

- **Bases.** Rows have node ids and lengths. With `--sequences` the writer
  adds the bases of each node.
- **Links.** The file has no L lines. A link is two consecutive steps of a
  path in the file, and a link that no such path takes is absent.
  gfa-to-tabix's other output, [the node and link index](index-format.md),
  holds the graph's nodes and links by coordinate.
- **Lines off the reference.** A W or P line with no step on a node of the
  reference is absent, and the header's `leftout` tag counts these lines.
- **A haplotype on another copy of a repeat.** Where the reference passes a
  node more than once, as in a pggb graph, the writer places each haplotype
  step on one copy, and a window over another copy lacks that haplotype
  ([open problem](open-problems.md#placement-of-steps-on-nodes-the-reference-passes-more-than-once)).
- **Where a path goes on another sequence.** A departure record lies
  between two steps on one reference sequence. A path that moves to another
  reference sequence and stays there has no record on the first
  ([open problem](open-problems.md#a-path-that-crosses-onto-another-reference-sequence)).

## In the specification

- [Rows](walks-format.md#rows) and
  [Decoding a walk row](walks-format.md#decoding-a-walk-row): every column,
  and the steps that turn a walk row back into a path.
- [Example](walks-format.md#example): two tiles decoded row by row, one of
  them on a reference that takes two nodes twice.
- [Exact and chosen](walks-format.md#exact-and-chosen): how a file marks a
  position on a node that the reference passes more than once.
- [Abridged tiles](walks-format.md#abridged-tiles): a tile too large to
  send whole, as in a satellite array. The writer moves whole lines out of
  the tile into separate units, and a viewer draws them from a summary
  until the user asks for their nodes.
- [Reading a window](walks-format.md#reading-a-window) and
  [Readers](walks-format.md#readers): how a reader joins a path across
  tiles, and the programs that read walk files.
- [scripts/walks-brief.py](../scripts/walks-brief.py): a reader in about
  150 lines of Python that prints every W and P line back from a walk file.
