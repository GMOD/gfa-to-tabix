# Walk files in brief

A GFA gives the haplotypes of a pangenome graph as W and P lines, each a
path that can run the length of a chromosome. A walk file holds the same
lines cut up along one reference genome, so that a viewer can fetch the
paths through one region from a static web host in a few range requests.

The [specification](walks-format.md) defines every row and column, and is
the authority where this page simplifies.

## Making a walk file

[walks-tile.gfa](figures/walks-tile.gfa) is a 90 bp graph with three W
lines. CHM13 takes node 10 where GRCh38 and HG002 take node 5:

```
W  GRCh38  0  chr1  0  90  >1>2>3>4>5>6>7>8>9
W  CHM13   0  chr1  0  86  >1>2>3>4>10>6>7>8>9
W  HG002   1  chr1  0  90  >1>2>3>4>5>6>7>8>9
```

```bash
gfa-to-tabix walks-tile.gfa --walks --refs GRCh38 --tile 30 -o hprc
```

- **Output:** `hprc.GRCh38.walks.gz`, which is tab-separated text in gzip
  blocks, and `hprc.GRCh38.walks.gz.idx`, a few lines of text with the byte
  ranges a reader starts from
- **One pair of files per reference:** `--refs GRCh38,CHM13` writes a pair
  for each sample. Positions in a file are positions on that file's
  reference, so a viewer that shows GRCh38 reads the GRCh38 file
- **Input:** a base-level GFA with integer node ids and W or P lines, as
  `vg convert -f` writes from a GBZ
- **Hosting:** put the two files side by side on a web server that answers
  range requests ([Hosting](walks-format.md#hosting))
- **Viewers:** the JBrowse graph plugin, BandageJS and ggbandage read walk
  files through the
  [@jbrowse/graph-walks](https://github.com/GMOD/graph-walks) library
  ([Readers](walks-format.md#readers))

## A viewer fetches the tiles over its region

gfa-to-tabix cuts the reference into tiles, compresses each tile separately
and writes a table of the tiles' byte ranges for each chromosome.
`--tile 30` cuts this example every 30 bp, and the default is 65536.

A viewer that opens a walk file reads the `.idx`, the list of haplotypes in
the file's header and the table of one chromosome. For each region it then
fetches the tiles that overlap the region.

![A 90 bp chr1 graph with GRCh38#0, HG002#1 and CHM13#0 as lines through its nodes, CHM13#0 dipping to a separate node between 30 and 60; under it hprc.GRCh38.walks.gz as a bar of header, tile 0-30, tile 30-60, tile 60-90 and table, each tile under its stretch of chr1; tile 30-60 is shaded with the graph above it, and an arrow runs from table to the byte range of that tile](figures/walks-tile.svg)

A walk file has this table and no Tabix index, so `tabix` and htslib's
region API don't read one.

## A tile lists the reference once and each detour once

`zcat hprc.GRCh38.walks.gz` prints the file as text. The tile shaded in the
figure holds these rows, with tabs shown as spaces:

```
GRCh38#0#chr1  30  60  ref    GRCh38#0#chr1  0  30  1  3  8,2,2  10,10,10  .
GRCh38#0#chr1  30  60  nodes  10  6
GRCh38#0#chr1  30  60  route  8  12  -8
GRCh38#0#chr1  30  60  walk   CHM13#0#chr1   0  30  1  3  8  0
GRCh38#0#chr1  30  60  walk   HG002#1#chr1   0  30  1  3  8  .
```

- **`ref`** is the reference's path through the tile: nodes 4, 5 and 6,
  each 10 bp long
- **`route`** is a detour off that path. This one leaves the reference at
  node 4, passes through node 10 and returns at node 6, and the `nodes` row
  gives node 10's length, 6 bp. A tile lists a detour once, however many
  haplotypes take it
- **`walk`** is one haplotype's path through the tile, written as the node
  it starts on and the routes it takes. CHM13 starts on node 4 and takes
  route 0, the tile's first `route` row, so its path is 4, 10, 6. HG002
  takes no route (`.`), so it follows the reference through 4, 5 and 6

A haplotype that matches the reference across a tile is one short row, and
haplotypes that share a variant share its `route` row.

The numbers `8,2,2` and `8 12 -8` are node ids and strands, each written as a
difference from the one before. The specification defines that encoding,
and the columns this page skips, under [Rows](walks-format.md#rows).

From these rows a reader rebuilds every step of every W and P line that
touches the reference.
[scripts/walks-brief.py](../scripts/walks-brief.py) is such a reader in one
short Python file, and it prints the three paths above from this walk file.

## A departure record gives where a path leaves and rejoins the reference

A haplotype can leave the reference in one tile and rejoin it in another,
as a haplotype with a 2 Mb deletion does. The tiles inside the deletion
have no row for that haplotype, so a viewer that read those tiles alone
would draw the region without it.

- A [`departure` record](walks-format.md#departure) gives the two reference
  positions and the length of the haplotype's sequence between them
- A viewer whose region lies anywhere between the two positions reads the
  record with its tiles, so it can draw the haplotype passing over the
  region
- A detour that leaves and returns inside one tile has no record, because
  the tile's `route` and `walk` rows show it

## What a walk file leaves out

- **Bases:** the rows have node ids and lengths. `--sequences` adds the
  bases
- **Links that no path takes:** the file has no L lines, and a reader takes
  a link from two consecutive steps of a path.
  [The node and link index](index-format.md), gfa-to-tabix's other output,
  holds the graph's nodes and links by coordinate
- **Paths off the reference:** a W or P line with no step on a node of the
  reference is absent, and gfa-to-tabix prints how many such lines it left
  out
- **Where a path goes on another chromosome:** a path that moves onto
  another sequence of the reference and stays there looks, on the first
  sequence, like a path that stops
  ([open problem](open-problems.md#a-path-that-crosses-onto-another-reference-sequence))

## Repeats and very large tiles

- **A reference that passes a node more than once:** pggb merges the copies
  of a repeat into shared nodes. gfa-to-tabix places a haplotype's step on
  one copy, and the file marks the node so that a viewer can say the
  position was chosen ([Exact and chosen](walks-format.md#exact-and-chosen))
- **A haplotype on another copy:** a region over another copy of the
  repeat lacks the haplotype
  ([open problem](open-problems.md#placement-of-steps-on-nodes-the-reference-passes-more-than-once)).
  HPRC's Minigraph-Cactus graphs have no such node on the graph's own
  reference, so build from the graph built on your reference where one
  exists
- **A tile too large to send whole:** in a satellite array the rows of one
  tile can be megabytes of text. gfa-to-tabix moves paths out of such a
  tile, and a viewer draws a moved path as blocks along the reference until
  the user asks for its nodes
  ([Abridged tiles](walks-format.md#abridged-tiles))
