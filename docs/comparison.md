# Comparison with gbz-base and gfaidx

gfa-to-tabix, gbz-base and gfaidx each let a program fetch one region of a
pangenome graph, with the haplotypes that pass through it, without loading
the whole graph. They differ in what they take as input and in which
program reads the result:

- **gfa-to-tabix** converts a GFA into compressed files on a static web
  host, such as an S3 bucket, from which a viewer in a web browser fetches
  only the bytes for the region in view. It writes two kinds of file:
  - a [node and link index](index-format.md) (`gfa-to-tabix build`): the
    graph's nodes and links in a bgzipped BED file with a Tabix index. A
    node on the reference genome is stored at its position there, and a
    node off it at the reference interval of the bubble it sits in
  - [walk files](walks-format.md)
    (`gfa-to-tabix graph.gfa --walks --refs GRCh38`): each haplotype's path,
    split into pieces by the 64 kb stretch of one reference genome they fall
    in, with a `.idx` file that a reader uses to find the bytes of each
    stretch. The JavaScript library
    [@jbrowse/graph-walks](https://github.com/GMOD/graph-walks) reads them

  JBrowse's graph plugin
  ([jbrowse-plugin-graphgenomeviewer](https://github.com/GMOD/jbrowse-plugin-graphgenomeviewer))
  reads both kinds of file, and
  [BandageJS](https://jbrowse.org/demos/bandagejs/) reads walk files
- **[gbz-base](https://github.com/jltsiren/gbz-base)** converts a GBZ, the
  vg toolkit's compressed format for a graph and its haplotypes, into a
  SQLite database. [@gmod/gbz-base](https://github.com/GMOD/gbz-base-js)
  reads the database in a browser by fetching parts of it with HTTP range
  requests, and JBrowse's graph plugin uses it. With the database alone,
  @gmod/gbz-base names the queried path and labels every other haplotype
  `unknown#N`.
  [gbz-haplotype-index](https://github.com/GMOD/gbz-haplotype-index) builds
  an optional second database, kept beside the first, from which
  @gmod/gbz-base names each haplotype and gives its coordinates
- **[gfaidx](https://github.com/fawaz-dabbaghieh/gfaidx)** indexes a GFA for
  programs on the machine that holds it. Its command line, C++ library and
  Python package return a region, a node and its neighbours, or a whole
  path, as GFA. [gfaidx-viz](https://github.com/fawaz-dabbaghieh/gfaidx-viz)
  runs gfaidx on a server: a browser asks the server for a region and
  receives that region's GFA

## Which to use

- Use **gfa-to-tabix** when you start from a GFA and want a browser to show
  the graph and its named haplotypes with the fewest requests and the
  smallest files. A browser reads a window of a walk file in one to four
  range requests, and on HPRC release 2 (v2.1) the walk files are a fraction
  of the size of gbz-base's database and its haplotype index.
  - From minigraph's rGFA, which has no haplotype paths, gfa-to-tabix writes
    only the node and link index. Walk files need a GFA with P or W lines
    and integer node ids, such as Minigraph-Cactus and pggb write
  - You need not run gfa-to-tabix for HPRC v2.1. jbrowse.org hosts walk
    files for its Minigraph-Cactus graphs, where `f8` marks walk format 8.
    Each has a directory at the same URL plus `.idx`, and a JBrowse track
    configuration for them is in [walks-format.md](walks-format.md#readers):
    - GRCh38 coordinates:
      `https://jbrowse.org/demos/hprc/hprc-v2.1-mc-grch38-f8.GRCh38.walks.gz`
    - CHM13 coordinates:
      `https://jbrowse.org/demos/hprc/hprc-v2.1-mc-chm13-f8.CHM13.walks.gz`
- Use **gbz-base** when your graph is already a GBZ, or when you want to use
  a gbz-base database that you or someone else already hosts, such as
  HPRC's. It also does what walk files do not:
  - a query around a node
  - with gbz-haplotype-index, an overview of every haplotype across a whole
    chromosome
  - each haplotype kept whole where it jumps to a paralog (see the table
    below)
  - a database that grows far more slowly than the number of haplotypes.
    gbz-haplotype-index, which names the haplotypes, stores a sample every
    `--interval` bp along every path, so it grows with them
- Use **gfaidx** in a script or pipeline on the machine that holds the
  graph, to get a region, a node's neighbourhood or a whole path as GFA.
  gfaidx also reads graphs that gfa-to-tabix cannot: an assembly graph, or
  any graph with neither paths nor rGFA position tags, because gfa-to-tabix
  stores everything by its position on a reference genome. gfaidx returns
  the nodes, links and paths with their GFA tags
- To look up a region by its coordinates on any haplotype, such as HG002's,
  use gfaidx. gbz-base looks up regions on the GBZ's reference and generic
  paths, GRCh38 and CHM13 in HPRC v2.1. gfa-to-tabix looks up regions on the
  reference genomes chosen with `--refs` when it writes the walk files, one
  walk file per genome

## What we measured

We indexed two HPRC chromosomes with gfa-to-tabix and gfaidx: chr22 from
the v2.1 Minigraph-Cactus graph and chrY from the release 2 pggb graph, with
GRCh38 as the reference. We compared gfa-to-tabix with gbz-base on the whole
v2.1 Minigraph-Cactus graph. The tables, methods and scripts are in
[Comparison details](comparison-details.md).

- **Time per window:** with both reading from local disk, gfaidx returns the
  median 64 kb chr22 window in under half the time @jbrowse/graph-walks
  takes to read it from a walk file. graph-walks is faster in most chrY
  windows. In chrY's repeats, gfaidx returns each haplotype from its first
  to its last visit to the window, with everything it visits between
  distant copies, where a walk file returns only the haplotype's pieces in
  the window. We have no timing of gbz-base against current walk files; in
  an earlier test, JBrowse drew windows faster from walk files than from
  gbz-base
- **Requests per window:** after reading the `.idx` file once on opening, a
  browser reads a 64 kb window from a walk file in one to four range
  requests. gbz-base with its haplotype index takes tens of round trips.
  gfaidx, which reads local files, reads hundreds of byte ranges from five
  files
- **Size:** a walk file is about an order of magnitude smaller than gfaidx's
  index, because gfaidx stores every step of every path and the walk file
  stores each distinct route a haplotype takes off the reference once per
  64 kb stretch. gfa-to-tabix also leaves out of a walk file the paths that
  share no node with its reference genome. On the whole v2.1 graph, the
  GRCh38 and CHM13 walk files, written without bases, are together a third
  of the size of the gbz-base database, which holds the bases, and smaller
  than its haplotype index
- **Building:** written without `--sequences`, so with no bases, a walk file
  builds faster than gfaidx's index on both chromosomes, but takes several
  times gfaidx's memory on chrY. We did not build the gbz-base database,
  which HPRC hosts

## Differences

|                 | gfa-to-tabix | gbz-base, with gbz-haplotype-index | gfaidx |
| --------------- | ------------ | ---------------------------------- | ------ |
| Read by         | JBrowse's graph plugin, and BandageJS for walk files, in a web browser by HTTP range request | @gmod/gbz-base in a web browser by HTTP range request; `gbz-base query`, or `gbz-base-query` from @gmod/gbz-base, on the command line | its command line, C++ library or Python package, on local files; gfaidx-viz's server runs it for a browser |
| Input           | rGFA, or GFA with P or W lines; walk files need P or W lines and integer node ids | a GBZ | any GFA 1 with at least one L line, with or without paths |
| Region queries  | a region of a reference genome chosen with `--refs` | a region of a reference or generic path, or a node, with the graph within a given number of bp around it | a region on any path or rGFA sequence, a node and its neighbourhood, a whole path, or the paths through a set of nodes |
| Bases           | in walk files written with `--sequences` | always | always |
| Haplotype names | `sample#haplotype#contig` on every row | with gbz-haplotype-index, sample, haplotype, contig and coordinate; without it, `unknown#N` for every haplotype but the path queried | each path's sample, haplotype and sequence; `--with_coords` adds coordinates |
| GFA tags        | uses `SN`, `SO`, `SR` and `LN`, and keeps no other tag | none, because a GBZ holds no GFA tags | returns S, L and P lines with their tags as written |
| Zoomed-out views | `gfa-to-tabix build` writes a coarser node and link index, with variants below a size threshold folded into the reference, and a BED file of the graph's bubbles; walk files have no zoomed-out version | with gbz-haplotype-index, @gmod/gbz-base reads an overview of every haplotype across a whole chromosome in about a dozen requests | none: a query returns every node, link and step of its region |
| More haplotypes | measured on chr22 up to 5,000 synthetic haplotypes ([details](placement/scale-past-464.md)): a view of a few haplotypes stays small, but the file and the table a reader fetches at open grow faster than the haplotypes under the writer's default abridging | the database grows far more slowly, because haplotypes share runs of nodes; the haplotype index grows with every path | the path index grows with the total steps of all paths, because it stores every step |
| A haplotype that jumps to a paralog | gfa-to-tabix stores the steps after the jump at the paralog's position, so at the haplotype's own locus a browser shows it in several pieces, with a record of each jump; under 0.1% of steps on HPRC v2.1 Minigraph-Cactus chr22 | kept whole | `--mode all` returns each path from its first to its last node in the region, and `--haplotype_gap` cuts it where more bp than the gap lie between two of those nodes |

How each tool stores the graph and each tool's known limits are in
[Comparison details](comparison-details.md#storage-paralogs-and-known-limits).
