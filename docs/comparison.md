# Comparison with gbz-base and gfaidx

gfa-to-tabix writes static files that a web browser reads by region from any
web host. gbz-base and gfaidx also return a region of a pangenome graph with
the haplotypes through it, each to a different kind of reader:

- **gfa-to-tabix:** static files from any GFA. The
  [node and link index](index-format.md), a bgzipped, Tabix-indexed BED
  file, serves every graph, and the [walk files](walks-format.md), gzip
  units with a table of their byte ranges, add every haplotype's path for a
  base-level graph
- **[gbz-base](https://github.com/jltsiren/gbz-base):** a SQLite database,
  `graph.gbz.db`, that `gbz-base construct` builds from a GBZ.
  [@gmod/gbz-base](https://github.com/GMOD/gbz-base-js) reads it by range
  request
- **[gbz-haplotype-index](https://github.com/GMOD/gbz-haplotype-index):** a
  second SQLite file beside `graph.gbz.db` that names each walk and gives its
  coordinate. Its
  [haplotype-index.md](https://github.com/GMOD/gbz-haplotype-index/blob/main/docs/haplotype-index.md)
  describes its tables
- **[gfaidx](https://github.com/fawaz-dabbaghieh/gfaidx):** an index of a
  whole GFA, read by programs on the machine that holds it.
  [gfaidx-viz](https://github.com/fawaz-dabbaghieh/gfaidx-viz) puts it behind
  a server: a browser asks for a region, the server runs gfaidx and sends
  back the GFA, and the browser lays it out. `gfaidx index_gfa`
  groups the nodes into communities of linked nodes, writes each community's
  segments and links as one gzip member, and writes sidecar files that map
  node names, paths and coordinates to those members. Its command line, C++
  library and Python package return a region, the neighbourhood of a node or
  a path as GFA

The JBrowse graph genome viewer plugin reads gfa-to-tabix's files and
gbz-base's database.

## Choosing

- A graph drawn in a browser from a static web host, from an rGFA, a pggb
  graph or any graph without a GBZ: gfa-to-tabix
- HPRC v2.1: the walk files jbrowse.org hosts;
  [readers](walks-format.md#readers) gives their URLs
- A `graph.gbz.db` someone already hosts: gbz-haplotype-index, which works
  beside it and leaves the database as it is
- Thousands of haplotypes: gbz-base
- A script or pipeline on the machine that holds the graph, which needs a
  region, a node's neighbourhood or a whole path as GFA: gfaidx
- An assembly graph, or any graph with neither paths nor rGFA tags: gfaidx,
  since gfa-to-tabix files every row under a reference coordinate
- A region named on any path, with no reference picked when the index is
  built: gfaidx or gbz-base. A few chosen samples' coordinates: a walk file
  for each, named in `--refs`
- GFA tags kept with the nodes, links and paths returned: gfaidx

## Differences

|                 | gfa-to-tabix | gbz-base, with gbz-haplotype-index | gfaidx |
| --------------- | ------------ | ---------------------------------- | ------ |
| Read by         | a browser, by HTTP range request | a browser, by HTTP range request, or the `gbz-base` command line | its command line, C++ library and Python package, from local files; gfaidx-viz's server runs it for a browser |
| Input           | rGFA, or a plain GFA with P or W lines; walks need a base-level graph | a GBZ | any GFA 1 with at least one L line: P or W lines, rGFA, or no paths |
| Files           | BGZF text any static web host serves: the index with a TBI, which htslib and `tabix` read, and walk files with a unit table, which `zcat` reads whole | SQLite | a gzip file of the S and L lines, which `zcat` reads whole, a text table of its members, and binary sidecars for node names, node lengths, paths and coordinates |
| Nodes and links | `N` and `L` rows filed by reference coordinate | a row per node orientation, with its edges | S and L lines grouped by community, one gzip member each, and the links between communities in one more member |
| Queries         | a reference region | a reference interval or a node, with context in bp | a region on any P or W line or rGFA sequence, a node with its neighbourhood, a whole path, or the paths through a set of nodes |
| Bases           | in walk files with `--sequences` | always | always |
| Haplotype paths | per 64 kb tile: the reference's path, distinct routes off it, each piece's choices of route | the GBWT, in the node rows | every step of every P and W line, and for each node the lines and steps that visit it |
| Walk names      | `sample#haplotype#contig` in every row; the header lists them all | `unknown#N` for every walk but the query path without the index; with it, sample, haplotype, contig and coordinate | each line's sample, haplotype and sequence; `--with_coords` adds the coordinates of each piece returned |
| References      | one walk file per `--refs` sample | one database for GRCh38, CHM13 and any generic path | one index for every path, and a `.cdx` sidecar of chosen paths' coordinates, which an rGFA needs and which makes W and P line queries faster |
| GFA tags        | reads `SN`, `SO`, `SR` and `LN`, and keeps no other tag of an S, L, P or W line | none: a GBZ keeps no GFA tags | returns S, L and P lines with their tags as written |
| Zoomed out      | `build` writes a coarse tier, alleles and bubbles; walk files have none | the index draws every haplotype over a whole chromosome in about a dozen requests, at several zoom levels | a query returns every node, link and step of its region |
| N haplotypes    | routes grow as N^0.36 and choices as N^0.86, about 20 GB genome-wide at 10,000 | the GBWT grows sublinearly, because haplotypes share runs | the path index stores each step, so it grows with the total steps of all paths |
| Paralog jumps   | the steps after a jump take the paralog's tile ([details](walks-format.md#paralogs-and-collapsed-repeats)); on chr22, fewer than 0.1% of steps, in at most 74 of the 1,130 paths besides GRCh38's, nearly all in 22q11 | reaches those nodes by graph distance | the default `--mode all` keeps each path from its first to its last node on the reference interval, and `--haplotype_gap` cuts the path where more bp than the gap lie between two such nodes |
| Misses          | a path that crosses onto another sequence of the reference reads as ending there ([open problems](open-problems.md#a-path-that-crosses-onto-another-reference-sequence)); where the reference passes a node more than once, a step's position is the writer's choice ([Exact and chosen](walks-format.md#exact-and-chosen)) | the snarl extension once turned a 100 kbp query into 10 Mbp, 75 s and 9 GiB | every region query reads the member of links between communities whole; a 64 kb window in a repeat can write hundreds of MB of GFA, with `--haplotype_gap 10kb` too ([below](#reading-a-64-kb-window)); `.ndx` holds two hashes of each node name in place of the name, so two names with the same hashes would match one entry; P lines with overlaps get no coordinates |

The index's keep route, which names a few chosen haplotypes, has a
[proof](https://github.com/GMOD/gbz-haplotype-index/blob/main/docs/proof.md)
and a fuzzer behind it.

## gfaidx and gfa-to-tabix on two graphs

We indexed two graphs with both tools on one machine, with GRCh38 as the
reference: HPRC v2.1's Minigraph-Cactus chr22, as `vg convert -f` writes it
with W lines, and HPRC release 2's pggb chrY, with P lines.
[comparison/scripts](comparison/scripts) holds the scripts,
[comparison/results](comparison/results) what they wrote, and `tables.py`
writes the tables below from those results.

<!-- generated:versions -->
- gfaidx 2.3.2, the release's Linux x86-64 binary (sha256 60df8bc2efbb41fb), with index_gfa --threads 8
- gfa-to-tabix 5.0.0 at commit 427efd8
- 24 cores and 125 GB of memory
- @jbrowse/graph-walks at commit 730e752, on Node v24.22.1
<!-- /generated -->

<!-- generated:graphs -->
| graph | segments | links | bp in segments | P and W lines | steps |
| --- | --- | --- | --- | --- | --- |
| MC chr22 | 3.1 M | 4.7 M | 58.9 M | 1,131 | 630.1 M |
| pggb chrY | 4.1 M | 7.7 M | 2.84 billion | 1,053 | 544.6 M |
<!-- /generated -->

### Building

<!-- generated:build -->
| time and peak memory | MC chr22 | pggb chrY |
| --- | --- | --- |
| gfaidx `index_gfa --threads 8` | 172 s, 0.8 GiB | 215 s, 0.9 GiB |
| gfaidx `index_coordinates` | 2 s, 0.1 GiB | 5 s, 0.1 GiB |
| gfa-to-tabix `--walks` | 53 s, 1.0 GiB | 130 s, 6.7 GiB |
| gfa-to-tabix `--walks --sequences` | 54 s, 1.5 GiB | 247 s, 13.6 GiB |
| gfa-to-tabix, the node and link index | 145 s, 7.8 GiB | 112 s, 7.0 GiB |
<!-- /generated -->

<!-- generated:sizes -->
| files | MC chr22 | pggb chrY |
| --- | --- | --- |
| gfaidx: segments and links, with bases (`.gfa.gz`, `.idx`) | 42 MB | 153 MB |
| gfaidx: paths (`.pdx`, `.pcx`) | 1.10 GB | 2.17 GB |
| gfaidx: node names, lengths and coordinates (`.ndx`, `.lnx`, `.cdx`) | 85 MB | 96 MB |
| gfaidx: all of them | 1.23 GB | 2.42 GB |
| gfa-to-tabix: walk file | 59 MB | 194 MB |
| gfa-to-tabix: walk file with bases | 105 MB | 387 MB |
| gfa-to-tabix: node and link index | 184 MB | 350 MB |
<!-- /generated -->

- **Memory:** gfaidx sorts on disk and stays under 1 GiB on both graphs.
  The walk writer takes several times that on pggb chrY, and twice as much
  again with bases. The node and link index holds the whole graph in memory
- **Time:** without bases, the walk writer finishes first on both graphs. It
  ran on 24 cores, and `gfaidx index_gfa` on 8 threads, which it uses for
  the path index. The machine is shared, so the times are rough
- **Size:** a walk file is about 20 times smaller than gfaidx's files on MC
  chr22 and about 12 times smaller on pggb chrY, because it holds less
- **What each stores:** gfaidx stores every step of every P and W line, and
  for every node the lines and steps that visit it, so its path index is
  nearly all of its bytes. A walk file stores each distinct route through a
  tile once and the route each piece of a haplotype takes, for one reference
- **Lines left out:** a walk file leaves out a line that visits no node of
  its reference, 36 of MC chr22's lines and about half of pggb chrY's
  ([MC chr22](comparison/results/mc22.gfa-to-tabix.walks.log),
  [pggb chrY](comparison/results/pggbY.gfa-to-tabix.walks.log)). gfaidx
  keeps every line
- **Nodes and links:** the node and link index is larger than gfaidx's graph
  file, which has the bases too. Each index row is a line of text with its
  reference interval, and on a plain GFA with a bitmask of the assemblies
  through the node

### Reading a 64 kb window

A window is one tile of the walk file, 65,536 bp of GRCh38, and the windows
are spaced evenly along the chromosome.

- **Walk file:** the bytes of the units the format's
  [read rule](walks-format.md#reading-a-window) selects for the window, a
  tile and the departure bins over it, taken from the file's unit table
- **gfaidx:** `gfaidx get_region --mode all --with_coords` on the same
  window, and again with `--haplotype_gap 10kb`, which gfaidx's README
  gives for repeats and gfaidx-viz's server adds to every query for all
  haplotypes. Each writes the window's nodes and links and every haplotype
  through them, with coordinates. A syscall trace gives each byte range the
  command reads, and a logging filesystem gives each 4 KB page it touches
  in the three sidecars it memory-maps. A range that every window reads
  counts as read at open
- **Time:** each is the median of three runs with the files in the page
  cache. gfaidx's is the whole command, from process start to the GFA on
  disk. The walk file's is
  [@jbrowse/graph-walks](https://github.com/GMOD/graph-walks) in Node,
  cutting the window with every haplotype kept, context 0 and no budget:
  from a new reader, which first reads the directory, the header and the
  table, and on a reader already open
- **Over HTTP:** the MC chr22 windows were also cut from the whole-genome
  GRCh38 file jbrowse.org hosts, which holds the same chr22
- **Nodes:** the distinct nodes a cut's fragments step on, against the
  segments of gfaidx's GFA

<!-- generated:window-mc22 -->
| MC chr22, 40 windows: median (largest) | walk file | walk file with bases | gfaidx | gfaidx, `--haplotype_gap 10kb` |
| --- | --- | --- | --- | --- |
| read at open | 48 KB | 48 KB | 329 KB | 329 KB |
| bytes read | 52 KB (86 KB) | 91 KB (125 KB) | 3.6 MB (40 MB) | 3.6 MB (37 MB) |
| byte ranges | 2 (3) | 2 (3) | 964 (46,802) | 964 (4,167) |
| the tile's blocks unit, read to draw abridged pieces | 0 (64 KB) | 0 (64 KB) |  |  |
| byte ranges, gaps of up to 64 KB joined |  |  | 489 (548) | 489 (514) |
| bytes read, gaps of up to 64 KB joined |  |  | 15 MB (50 MB) | 15 MB (45 MB) |
| files read | 1 | 1 | 5 (5) | 5 (5) |
| time on local disk, reader already open | 158 ms (1.6 s) | 159 ms (1.6 s) |  |  |
| time on local disk, from a new reader or process | 165 ms (1.5 s) | 165 ms (1.5 s) | 68 ms (791 ms) | 75 ms (738 ms) |
| time over HTTP from jbrowse.org's whole-genome file, from a new reader | 176 ms (1.4 s) |  |  |  |
| time to build the tables a viewer draws from | 67 ms (950 ms) | 67 ms (921 ms) |  |  |
| distinct nodes returned | 2,664 (36,550) | 2,664 (36,550) | 2,664 (150,088) | 2,664 (103,624) |
| steps returned | 796,286 (8.7 M) | 796,286 (8.7 M) |  |  |
| GFA written |  |  | 8.2 MB (111 MB) | 8.2 MB (99 MB) |

- Against gfaidx: from a new reader, the walk cut takes less time in 11 of the 40 windows, and the nodes its fragments step on are the segments of the GFA, id for id, in 38. In the others the GFA has more
- Against gfaidx, `--haplotype_gap 10kb`: from a new reader, the walk cut takes less time in 11 of the 40 windows, and the nodes its fragments step on are the segments of the GFA, id for id, in 39. In the others the GFA has more
<!-- /generated -->

<!-- generated:window-pggbY -->
| pggb chrY, 40 windows: median (largest) | walk file | walk file with bases | gfaidx | gfaidx, `--haplotype_gap 10kb` |
| --- | --- | --- | --- | --- |
| read at open | 22 KB | 26 KB | 1.7 MB | 1.7 MB |
| bytes read | 78 KB (1.6 MB) | 127 KB (1.6 MB) | 1.2 MB (136 MB) | 1.1 MB (136 MB) |
| byte ranges | 3 (4) | 3 (4) | 894 (189,697) | 657 (9,465) |
| the tile's blocks unit, read to draw abridged pieces | 0 (626 KB) | 0 (626 KB) |  |  |
| byte ranges, gaps of up to 64 KB joined |  |  | 218 (411) | 218 (325) |
| bytes read, gaps of up to 64 KB joined |  |  | 3.7 MB (140 MB) | 3.5 MB (140 MB) |
| files read | 1 | 1 | 5 (5) | 5 (5) |
| time on local disk, reader already open | 47 ms (8.6 s) | 48 ms (9.2 s) |  |  |
| time on local disk, from a new reader or process | 56 ms (7.7 s) | 51 ms (8.2 s) | 94 ms (3.5 s) | 94 ms (2.3 s) |
| time to build the tables a viewer draws from | 9 ms (896 ms) | 10 ms (902 ms) |  |  |
| distinct nodes returned | 686 (7,636) | 686 (7,636) | 1,288 (379,765) | 697 (16,296) |
| steps returned | 53,184 (10.5 M) | 53,184 (10.5 M) |  |  |
| GFA written |  |  | 818 KB (530 MB) | 527 KB (274 MB) |

- Against gfaidx: from a new reader, the walk cut takes less time in 38 of the 40 windows, and the nodes its fragments step on are the segments of the GFA, id for id, in 20. In the others the GFA has more
- Against gfaidx, `--haplotype_gap 10kb`: from a new reader, the walk cut takes less time in 31 of the 40 windows, and the nodes its fragments step on are the segments of the GFA, id for id, in 22. In the others the GFA has more
<!-- /generated -->

Where gfaidx's bytes come from:

<!-- generated:files-mc22 -->
| MC chr22: gfaidx file | size | how | every window reads | bytes per window: median (largest) | byte ranges per window |
| --- | --- | --- | --- | --- | --- |
| `.cdx` | 22 MB | read | 2 KB | 48 KB (535 KB) | 19 (25) |
| `.gfa.gz` | 41 MB | read | 33 KB | 77 KB (1.9 MB) | 2 (50) |
| `.idx` | 29 KB | read | 29 KB | 0 (0) | 0 (0) |
| `.lnx` | 12 MB | memory-mapped | 4 KB | 57 KB (508 KB) | 5 (35) |
| `.ndx` | 50 MB | memory-mapped | 11 KB | 0 (0) | 0 (0) |
| `.pcx` | 1.3 MB | memory-mapped | 33 KB | 1.2 MB (1.2 MB) | 3 (77) |
| `.pdx` | 1.10 GB | read | 216 KB | 2.2 MB (36 MB) | 933 (46,623) |
<!-- /generated -->

<!-- generated:files-pggbY -->
| pggb chrY: gfaidx file | size | how | every window reads | bytes per window: median (largest) | byte ranges per window |
| --- | --- | --- | --- | --- | --- |
| `.cdx` | 13 MB | read | 2 KB | 28 KB (896 KB) | 19 (21) |
| `.gfa.gz` | 153 MB | read | 1.5 MB | 176 KB (16 MB) | 1 (116) |
| `.idx` | 11 KB | read | 11 KB | 0 (0) | 0 (0) |
| `.lnx` | 16 MB | memory-mapped | 4 KB | 72 KB (311 KB) | 5 (27) |
| `.ndx` | 66 MB | memory-mapped | 8 KB | 0 (0) | 0 (0) |
| `.pcx` | 1.1 MB | memory-mapped | 78 KB | 397 KB (745 KB) | 77 (84) |
| `.pdx` | 2.17 GB | read | 164 KB | 470 KB (134 MB) | 794 (189,471) |
<!-- /generated -->

- **Bytes:** for the median window gfaidx reads about 70 times the walk
  file's bytes on MC chr22 and about 15 times on pggb chrY, from five files.
  The path index is the largest share on both, and on MC chr22 a third are
  the `.pcx` checkpoints, which a query reads nearly whole
- **Byte ranges:** a walk reader fetches one to four ranges, all of them
  listed in the table it read at open. gfaidx reads hundreds. A client that
  joins ranges up to 64 KB apart makes half as many requests on MC chr22 and
  fetches four times the bytes
- **Stages:** gfaidx finds its ranges in stages. The coordinate index gives
  the window's reference nodes, their postings give the lines and steps
  through them, the steps give the other nodes, and the nodes give the gzip
  members to read
- **Repeats in gfaidx:** in pggb chrY's repeats one 64 kb window has gfaidx
  read over 100 MB and write up to half a gigabyte of GFA, because
  `--mode all` returns each haplotype whole from its first to its last visit
  to the window's reference nodes. `--haplotype_gap 10kb` cuts each
  haplotype where it strays far between those visits: the largest GFA
  halves and the nodes returned fall to a few times the walk cut's, but
  gfaidx reads about as many bytes
- **Repeats in a walk file:** the largest window on pggb chrY is under 2 MB
  ([every window](comparison/results/pggbY.cost.txt)). The writer moves the
  longest pieces out of a tile that passes its budget, into units a reader
  fetches when a viewer expands that haplotype
  ([Abridged tiles](walks-format.md#abridged-tiles))
- **Time on MC chr22:** on local disk gfaidx answers the median window in
  under half the reader's time. The reader decodes about 800,000 steps for
  the median window, those of 464 haplotypes, and its time grows with the
  steps it decodes
- **Time on pggb chrY:** the reader is faster in nearly every window
  against gfaidx's default and in most against `--haplotype_gap 10kb`, and
  far faster where gfaidx returns megabytes of GFA
- **Time over HTTP:** over the bench machine's fast connection, cutting from
  jbrowse.org takes about as long as cutting from local disk, so the
  reader's time is its decoding and not its reads
- **The slowest windows** are in repeats. gfaidx's takes a few seconds and
  writes hundreds of MB, with or without `--haplotype_gap 10kb`. The reader's takes longer, on a pggb chrY window
  with over 10 million steps, which its default step budget of 4 million
  refuses with a notice to zoom in
- **The content returned:** where the two differ in nodes, gfaidx's GFA has
  up to a hundred times as many by default, the nodes of each haplotype
  between two distant visits to the window, and a few times as many with
  `--haplotype_gap 10kb`. Steps and links were not compared;
  [walks-truth.py](../scripts/walks-truth.py) `rebuild` checks a walk file
  against its GFA step for step

## gbz-base and gfa-to-tabix on HPRC v2.1

The Minigraph-Cactus GRCh38 graph: 139.5 M nodes, 464 haplotypes.

| measure                 | gfa-to-tabix walk files                 | gbz-base             | gbz-haplotype-index |
| ----------------------- | --------------------------------------- | -------------------- | ------------------- |
| size                    | 1.58 GB GRCh38, 1.78 GB CHM13, no bases | 10.05 GB with bases  | 5.1 GB              |
| build                   | GRCh38 in 47 min at a 7.3 GiB peak, CHM13 in 63 min at 8.6 GiB, on 24 cores | HPRC hosts the file  | 35 min, 22 threads  |
| reads per window        | a tile and the departure bins over it, in one to four byte ranges on the windows above, after three reads at open | 18 to 43 round trips |                     |
| bytes per 64 kb window  | 0.05 MB median; 0.14 MB p99 and 0.36 MB at most on GRCh38, 0.17 MB p99 and 0.59 MB at most on CHM13 |                      |                     |

- The walk files' sizes, build and bytes are those of the whole-genome
  format 8 files, built by the writer at
  [d7ef618](comparison/results/genome8.commit.txt):
  [sizes](comparison/results/genome8.sizes.tsv), the
  [GRCh38](comparison/results/genome8.build-grch38.log) and
  [CHM13](comparison/results/genome8.build-chm13.log) build logs, and
  `walks-truth.py cost` on the
  [GRCh38](comparison/results/genome8.cost-grch38.txt) and
  [CHM13](comparison/results/genome8.cost-chm13.txt) files
- Cut by graph-walks over HTTP from the hosted GRCh38 file, a 64 kb chr22
  window with every haplotype takes about as long as from local disk
  ([above](#reading-a-64-kb-window))
- The GBZ-base paper (Sirén and Paten, bioRxiv 2026.07.10.737775 v2) gives
  10.7 GiB for gbz-base, 5.7 GiB for the GBZ and 3.35 GiB for an experimental
  GBZ v3 on the CHM13 graph, with bases
- Drawn in JBrowse at the HPRC tutorial's loci on 2026-10-08, format 1 walk
  files, three per reference, took 5 to 7 requests and 2.4 to 7.9 s per window,
  and gbz-base with the index 17 to 57 requests and 6.4 to 13.3 s
- On 60 chr22 windows with eight haplotypes, format 1 walk files and gbz-base
  returned the same haplotypes and alignments in 56. The other four lie in the
  22q11 repeats and the immunoglobulin lambda locus
- At the ABCA7 VNTR, all 462 format 1 walk rows match gbz-base's to the bp
- From format 2 walk files, the plugin draws the same graph in 49 of 50 chr22
  windows; the 50th, in 22q11, lacks 3,111 nodes off the reference
