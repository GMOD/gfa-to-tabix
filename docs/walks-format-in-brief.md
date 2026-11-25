# Walk files in brief

A GFA gives the haplotypes of a pangenome graph as W and P lines, each a
path that can run the length of a chromosome. A walk file holds the same
lines cut up along one reference genome, so that a viewer can fetch the
paths through one region from a static web host in a few range requests.

## The example

[walks-example.gfa](figures/walks-example.gfa) has a 90 bp reference of
nine 10 bp nodes, and four more haplotypes:

```
W  GRCh38  0  chr1  0  90  >1>2>3>4>5>6>7>8>9
W  CHM13   0  chr1  0  87  >1>2>3>4>10>6>7>8>9
W  HG002   1  chr1  0  90  >1>2>3>4>5>6>7>8>9
W  HG002   2  chr1  0  40  >1>2>8>9
W  HG003   1  chr1  0  80  >1>2>3>4>6>7>8>9
```

Each `>4` is a step: node 4, walked forward.

```bash
gfa-to-tabix walks-example.gfa --walks --refs GRCh38 --tile 30 -o hprc
```

The command writes two files, the walk data file and its directory index:

```
hprc.GRCh38.walks.gz
hprc.GRCh38.walks.gz.idx
```

![The example graph: nine reference nodes along chr1 under three tiles, tile 0, tile 30 and tile 60; HG002#1 as a straight line, CHM13#0 dipping to node 10 under node 5, HG003#1 dipping under node 5 with no node, and HG002#2 dipping under nodes 3 to 7 with no node; below, hprc.GRCh38.walks.gz as a bar of header, tile 0, departures 0-30, tile 30, departures 30-60, tile 60, departures 60-90 and table; the region chr1:31-60 is shaded over the graph and over tile 30 and departures 30-60, labelled one request](figures/walks-example.svg)

## The format in short

- **Tiles:** gfa-to-tabix cuts the reference into tiles of a fixed length,
  30 bp here and 65536 bp by default, and compresses each tile separately
- **Its own index, not Tabix:** the data file has a table of where each
  tile's bytes are, and the small text file `.idx`
  ([the directory](walks-format.md#the-directory)) gives where each
  chromosome's table is. A tile starts and ends on a BGZF block boundary,
  so a viewer fetches the tiles over its region by range request and
  gunzips them alone, with no `.tbi` or `.gzi`
- **The reference, once:** a tile's `ref` row lists the reference's steps
  through the tile
- **Each detour, once:** a `route` row is one detour off the reference
  inside the tile, however many haplotypes take it. Tile 30 has two: from
  node 4 straight to node 6, and from node 4 through node 10 to node 6
- **A haplotype as the routes it takes:** a `walk` row is one haplotype's
  path through the tile, written as the step it starts on and the routes
  it takes, following the `ref` row between them. `HG002#1` takes none
- **A detour across tiles:** a `departure` row gives where a haplotype
  leaves the reference in one tile and rejoins it in another. `HG002#2`
  leaves at 20 and rejoins at 70, so tile 30 has no `walk` row for it, and
  a copy of the row beside each of the three tiles lets a viewer of tile 30
  still draw it
- **Plain text:** `zcat` prints the whole file as tab-separated rows, each
  starting with its position on the reference
- **One file per reference:** `--refs GRCh38,CHM13` writes a second file,
  with CHM13's positions

## What a walk file leaves out

- **Bases,** unless `--sequences` adds them
- **Links that no path takes.** [The node and link index](index-format.md),
  gfa-to-tabix's other output, has every node and link
- **Paths with no step on the reference.** gfa-to-tabix prints how many it
  left out

## Read more

- [Walk files by example](walks-format-by-example.md) reads this example's
  walk file line by line, with every column explained
- [The specification](walks-format.md) defines every row and column, then
  the rules a valid file keeps
- [Writing walk files](walks-writer.md) and
  [Reading walk files](walks-reading.md) cover gfa-to-tabix's options and
  the reader programs
