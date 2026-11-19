# Comparison with gbz-base and gfaidx

gfa-to-tabix, gbz-base and gfaidx each fetch one region of a pangenome graph,
with the haplotypes that pass through it, without loading the whole graph.
They differ in what they take as input and in which program reads the
result:

- **gfa-to-tabix** converts a GFA into compressed text files that a web
  browser reads straight from a static web host, such as an S3 bucket,
  fetching only the bytes for the region in view. It writes two kinds of
  file:
  - a [node and link index](index-format.md): the graph's nodes and links,
    each filed under its position on a reference genome, in a bgzipped BED
    file with a Tabix index
  - [walk files](walks-format.md): every haplotype's path through the
    graph, cut into 64 kb stretches of one reference genome, with a table of
    byte offsets so that a reader fetches only the stretches it needs
- **[gbz-base](https://github.com/jltsiren/gbz-base)** converts a GBZ, the
  vg toolkit's compressed format for a graph and its haplotypes, into a
  SQLite database. [@gmod/gbz-base](https://github.com/GMOD/gbz-base-js)
  reads the database in a browser by fetching parts of it with HTTP range
  requests. [gbz-haplotype-index](https://github.com/GMOD/gbz-haplotype-index)
  is an optional second database beside it that adds each haplotype's name
  and coordinates
- **[gfaidx](https://github.com/fawaz-dabbaghieh/gfaidx)** indexes a GFA for
  programs on the machine that holds it. Its command line, C++ library and
  Python package return a region, a node and its neighbours, or a whole
  path, as GFA. [gfaidx-viz](https://github.com/fawaz-dabbaghieh/gfaidx-viz)
  runs gfaidx on a server, which sends a browser the GFA of each region it
  asks for

[JBrowse](https://jbrowse.org), a genome browser, draws graphs from
gfa-to-tabix's files and from gbz-base databases with its graph genome
plugin.

## Which to use

- Use **gfa-to-tabix** to show a graph in a web browser from files on a
  static web host, with no server program to run. It reads the GFA that
  pangenome pipelines write: minigraph's rGFA, and the GFA with P or W lines
  from Minigraph-Cactus or pggb. HPRC release 2.1 needs no conversion,
  because jbrowse.org hosts walk files for its Minigraph-Cactus graphs, each
  with a `.idx` file beside it:
  - GRCh38 coordinates:
    `https://jbrowse.org/demos/hprc/hprc-v2.1-mc-grch38-f8.GRCh38.walks.gz`
  - CHM13 coordinates:
    `https://jbrowse.org/demos/hprc/hprc-v2.1-mc-chm13-f8.CHM13.walks.gz`
- Use **gbz-base** for a graph with thousands of haplotypes. Its database
  grows more slowly than the number of haplotypes, because haplotypes that
  follow the same nodes share storage. It reads a GBZ: HPRC publishes its
  Minigraph-Cactus graphs as GBZ, and vg converts a GFA with P or W lines
  with `vg gbwt -G graph.gfa --gbz-format -g graph.gbz`. Where a gbz-base
  database is already online, gbz-haplotype-index adds haplotype names and
  coordinates without changing it
- Use **gfaidx** in a script or pipeline on the machine that holds the
  graph, to get a region, a node's neighbourhood or a whole path as GFA.
  gfaidx also reads graphs that gfa-to-tabix cannot: an assembly graph, or
  any graph with neither paths nor rGFA position tags, because gfa-to-tabix
  places everything by its position on a reference genome. gfaidx returns
  the nodes, links and paths with their GFA tags
- To look up a region by its coordinates on any haplotype, use gfaidx or
  gbz-base. gfa-to-tabix gives coordinates only on the reference genomes
  chosen with its `--refs` option when the files are written, one walk file
  per genome

## What we measured

We indexed two HPRC chromosomes with gfa-to-tabix and gfaidx: chr22 from
the Minigraph-Cactus graph and chrY from the pggb graph. We compared
gfa-to-tabix with gbz-base on the whole HPRC v2.1 Minigraph-Cactus graph.
The tables, methods and scripts behind these results are in
[Comparison details](comparison-details.md).

- **Time per window:** gfaidx answers the median Minigraph-Cactus chr22
  window in under half the time a walk file reader takes. The walk file
  reader is faster in most pggb chrY windows, where repeats make gfaidx
  return far more of the graph
- **Reading a window:** a browser reads a 64 kb window from a walk file in a
  few byte ranges of one file. gfaidx reads hundreds of ranges from five
  files, and gbz-base takes tens of round trips
- **Size:** a walk file is about an order of magnitude smaller than
  gfaidx's index, because gfaidx stores every step of every path and the
  walk file stores each distinct route once. The walk file also leaves out
  the paths that never touch its reference genome. On the whole HPRC v2.1
  graph, the GRCh38 and CHM13 walk files together are a fraction of the size
  of the gbz-base database, which also holds the bases
- **Building:** without bases, gfa-to-tabix writes the walk file faster than
  gfaidx builds its index on both chromosomes, but takes several times
  gfaidx's memory on pggb chrY

## Differences

|                 | gfa-to-tabix | gbz-base, with gbz-haplotype-index | gfaidx |
| --------------- | ------------ | ---------------------------------- | ------ |
| Read by         | a web browser, by HTTP range request | a web browser, by HTTP range request, or the `gbz-base` command line | its command line, C++ library or Python package, on local files; gfaidx-viz's server runs it for a browser |
| Input           | rGFA, or GFA with P or W lines; walk files need a base-level graph, with small variants as well as large ones, such as Minigraph-Cactus or pggb write | a GBZ | any GFA 1 with at least one L line, with or without paths |
| Region queries  | a region of a reference genome | a region of a reference path, or a node, with context in bp | a region on any path or rGFA sequence, a node and its neighbourhood, a whole path, or the paths through a set of nodes |
| Coordinates     | on each reference genome chosen with `--refs`, one walk file each | one database for GRCh38, CHM13 and any path vg stores as a generic path | one index for every path, and an optional `.cdx` file of chosen paths' coordinates, which an rGFA needs and which speeds up path queries |
| Bases           | in walk files written with `--sequences` | always | always |
| Haplotype names | `sample#haplotype#contig` on every row | with gbz-haplotype-index, sample, haplotype, contig and coordinate; without it, `unknown#N` for every haplotype but the path queried | each path's sample, haplotype and sequence; `--with_coords` adds coordinates |
| GFA tags        | uses `SN`, `SO`, `SR` and `LN`, and keeps no other tag | none, because a GBZ holds no GFA tags | returns S, L and P lines with their tags as written |
| Zoomed-out views | `gfa-to-tabix build` writes a coarser copy of the node and link index, with small variants folded into the reference, and a file of bubbles; walk files have no zoomed-out version | with gbz-haplotype-index, a viewer draws every haplotype across a whole chromosome from about a dozen requests, at several zoom levels | a query returns every node, link and step of its region |
| More haplotypes | the walk files grow more slowly than the number of haplotypes, to about 20 GB genome-wide at 10,000 | the database grows more slowly than the number of haplotypes, because haplotypes share runs of nodes | the path index grows with the total steps of all paths, because it stores every step |

How each tool stores the graph, how each handles a haplotype that jumps to
a paralog, and each tool's known limits are in
[Comparison details](comparison-details.md#storage-paralogs-and-known-limits).
