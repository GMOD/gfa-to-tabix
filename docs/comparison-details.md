# Comparison details

This page holds the measurements and storage details behind
[Comparison with gbz-base and gfaidx](comparison.md), which covers which
tool to use.

## Storage, paralogs and known limits

In the gfa-to-tabix column, a tile is a 64 kb stretch of the reference
genome. Each haplotype is cut into pieces, one per tile it passes through,
and a route is a path that a haplotype takes off the reference within a
tile.

|                 | gfa-to-tabix | gbz-base, with gbz-haplotype-index | gfaidx |
| --------------- | ------------ | ---------------------------------- | ------ |
| Files           | BGZF text any static web host serves: the index with a TBI, which htslib and `tabix` read, and walk files with a unit table, which `zcat` reads whole | SQLite | a gzip file of the S and L lines, which `zcat` reads whole, a text table of its members, and binary sidecars for node names, node lengths, paths and coordinates |
| Nodes and links | `N` and `L` rows filed by reference coordinate | a row per node orientation, with its edges | S and L lines grouped into communities of linked nodes, one gzip member per community, and the links between communities in one more member |
| Haplotype paths | per 64 kb tile of the reference: the reference's path, each distinct route a haplotype takes off it, and the routes each piece of a haplotype takes | the GBWT, in the node rows | every step of every P and W line, and for each node the lines and steps that visit it |
| Growth with N haplotypes | distinct routes grow as N^0.36 and the lists of routes each piece takes as N^0.86, about 20 GB genome-wide at 10,000 haplotypes | the GBWT grows sublinearly, because haplotypes share runs | the path index stores each step, so it grows with the total steps of all paths |
| Paralog jumps   | the steps after a jump take the paralog's tile ([details](walks-format.md#paralogs-and-collapsed-repeats)); on chr22, fewer than 0.1% of steps, in at most 74 of the 1,130 paths besides GRCh38's, nearly all in 22q11 | reaches those nodes by graph distance | the default `--mode all` keeps each path from its first to its last node on the reference interval, and `--haplotype_gap` cuts the path where more bp than the gap lie between two such nodes |
| Known limits    | a path that crosses onto another sequence of the reference reads as ending there ([open problems](open-problems.md#a-path-that-crosses-onto-another-reference-sequence)); where the reference passes a node more than once, a step's position is the writer's choice ([Exact and chosen](walks-format.md#exact-and-chosen)) | none measured here | every region query reads the member of links between communities whole; a 64 kb window in a repeat can write hundreds of MB of GFA, with `--haplotype_gap 10kb` too ([below](#reading-a-64-kb-window)); `.ndx` holds two hashes of each node name in place of the name, so two names with the same hashes would match one entry; P lines with overlaps get no coordinates |

## gfa-to-tabix and gfaidx on two graphs

We indexed two graphs with both tools on one machine, with GRCh38 as the
reference: HPRC v2.1's Minigraph-Cactus chr22, as `vg convert -f` writes it
with W lines, and HPRC release 2's pggb chrY, with P lines. The scripts are
in [comparison/scripts](comparison/scripts) and their output is in
[comparison/results](comparison/results). `tables.py` writes the tables
below from that output.

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
  The walk writer peaks at several times that on pggb chrY, and at twice as
  much again with bases. The node and link index writer holds the whole
  graph in memory
- **Time:** without bases, the walk writer finishes first on both graphs.
  It ran on 24 cores, and `gfaidx index_gfa` ran on 8 threads, which it
  uses to build the path index. Other jobs shared the machine, so the times
  are rough
- **Size:** a walk file is about 20 times smaller than gfaidx's files on MC
  chr22 and about 12 times smaller on pggb chrY, because it holds less.
  gfaidx stores every step of every P and W line, and for every node the
  lines and steps that visit it, so its path index is nearly all of its
  bytes. A walk file stores each distinct route through a tile once and the
  routes each piece of a haplotype takes, for one reference
- **Lines left out:** a walk file leaves out each line that visits no node
  of its reference: 36 of MC chr22's lines and about half of pggb chrY's
  ([MC chr22](comparison/results/mc22.gfa-to-tabix.walks.log),
  [pggb chrY](comparison/results/pggbY.gfa-to-tabix.walks.log)). gfaidx
  keeps every line
- **Nodes and links:** the node and link index is larger than gfaidx's graph
  file, though gfaidx's file also holds the bases. Each index row is a line
  of text with its reference interval and, on a plain GFA, a bitmask of the
  assemblies through the node

### Reading a 64 kb window

A walk reader reads a window in a few byte ranges of one file, and gfaidx
reads hundreds of ranges from five files. gfaidx answers the median MC
chr22 window in under half the walk reader's time, and the walk reader is
faster in most pggb chrY windows, where repeats make gfaidx return far more
of the graph.

Each window is one tile of the walk file, 65,536 bp of GRCh38, and the
windows are spaced evenly along the chromosome.

- **Walk file:** a reader fetches the units that the format's
  [read rule](walks-format.md#reading-a-window) selects for the window, at
  the byte ranges the file's unit table gives. These are the tile and the
  bins of departure records over it, which list where haplotypes leave the
  reference
- **gfaidx:** `gfaidx get_region --mode all --with_coords` writes the same
  window's nodes and links and every haplotype through them, with
  coordinates. We ran it again with `--haplotype_gap 10kb`, which gfaidx's
  README gives for repeats and gfaidx-viz's server adds to every query for
  all haplotypes
- **Counting gfaidx's reads:** a syscall trace gives each byte range the
  command reads, and a logging filesystem gives each 4 KB page it touches
  in the three sidecars it memory-maps. A range that every window reads
  counts as read at open
- **Time:** the median of three runs with the files in the page cache. For
  gfaidx it is the whole command, from process start to the GFA on disk
- **Walk reader time:**
  [@jbrowse/graph-walks](https://github.com/GMOD/graph-walks) in Node cuts
  the window with every haplotype kept, context 0 and no step budget. We
  timed it from a new reader, which first reads the directory, the header
  and the unit table, and again on a reader already open
- **Over HTTP:** we also cut the MC chr22 windows from the whole-genome
  GRCh38 file that jbrowse.org hosts, which holds the same chr22
- **Nodes:** the distinct nodes the walk cut's fragments step on, compared
  with the segments in gfaidx's GFA

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

- Against gfaidx: from a new reader, the walk cut is faster in 11 of the 40 windows. The nodes its fragments step on match the GFA's segments id for id in 38, and the GFA has more nodes in the other 2
- Against gfaidx, `--haplotype_gap 10kb`: from a new reader, the walk cut is faster in 11 of the 40 windows. The nodes its fragments step on match the GFA's segments id for id in 39, and the GFA has more nodes in the other 1
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

- Against gfaidx: from a new reader, the walk cut is faster in 38 of the 40 windows. The nodes its fragments step on match the GFA's segments id for id in 20, and the GFA has more nodes in the other 20
- Against gfaidx, `--haplotype_gap 10kb`: from a new reader, the walk cut is faster in 31 of the 40 windows. The nodes its fragments step on match the GFA's segments id for id in 22, and the GFA has more nodes in the other 18
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
  The path index is the largest share on both, and on MC chr22 a third of
  the bytes are the `.pcx` checkpoints, which a query reads nearly whole
- **Byte ranges:** a walk reader fetches one to four ranges, all of them
  listed in the table it read at open. gfaidx reads hundreds. A client that
  joins ranges up to 64 KB apart makes half as many requests on MC chr22 and
  fetches four times the bytes
- **How gfaidx finds its ranges:** gfaidx makes four lookups, each on the
  result of the last. The coordinate index gives the window's reference
  nodes, their postings give the lines and steps through them, the steps
  give the other nodes, and the nodes give the gzip members to read
- **Repeats in gfaidx:** in pggb chrY's repeats one 64 kb window has gfaidx
  read over 100 MB and write up to half a gigabyte of GFA, because
  `--mode all` returns each haplotype whole from its first to its last visit
  to the window's reference nodes. `--haplotype_gap 10kb` cuts each
  haplotype where it strays far between those visits: the largest GFA
  halves and the nodes returned fall to a few times the walk cut's, but
  gfaidx reads about as many bytes
- **Repeats in a walk file:** a walk reader reads under 2 MB for every
  pggb chrY window
  ([every window](comparison/results/pggbY.cost.txt)). The writer moves the
  longest pieces out of a tile over its `--abridge-steps` or
  `--abridge-bytes` budget, into units a reader fetches when a viewer
  expands that haplotype
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
  reader spends its time decoding, not reading
- **The slowest windows** for both tools are in repeats. gfaidx's slowest
  takes a few seconds and writes hundreds of MB of GFA, with or without
  `--haplotype_gap 10kb`. The reader's slowest takes longer: a pggb chrY
  window with over 10 million steps, timed with no step budget. The
  reader's default budget of 4 million steps refuses that window with a
  notice to zoom in
- **The content returned:** in windows where the node sets differ, gfaidx's
  GFA has up to a hundred times as many nodes by default, because it
  includes each haplotype's nodes between two distant visits to the window.
  With `--haplotype_gap 10kb` it has a few times as many. We did not compare
  steps or links; [walks-truth.py](../scripts/walks-truth.py) `rebuild`
  checks a walk file against its GFA step for step

## What gfaidx-viz's views need from a walk file

[gfaidx-viz](https://github.com/fawaz-dabbaghieh/gfaidx-viz) draws the GFA a
gfaidx server returns for a region, and began as a fork of BandageJS's
earlier wasm engine. The list below gives, for each of its views, what a
walk-file reader would need and whether the file has it:

- **Copy-number track:** for each chosen path, how many times it visits each
  reference node, averaged into bins along the reference. A walk-file cut
  holds every visit a haplotype makes to the window's reference nodes. We
  checked this against the GFA's lines on every tile of MC chr22 and pggb
  chrY, with every haplotype, and on stretches cut inside tiles
  ([visits](comparison/visits), [results](comparison/visits/results)).
  Where the reference passes a node more than once, the writer chooses
  which pass holds a visit, and the `ref` rows' `passes` mark such nodes.
  gfaidx-viz gives each pass of such a node the node's whole count
- **Paths across a link, by direction:** a cut's fragments give each
  haplotype's consecutive steps with their strands, so a reader can build
  this list. Where both ends are reference nodes of the window and the
  file's reference passes no node twice, the list is complete; with an end
  off the reference it is a lower bound
  ([open problems](open-problems.md#every-link-of-a-loaded-node-and-a-bubble-layer)).
  We have not yet checked it against the GFA
- **A straightened reference with a ruler:** `ref` rows give the
  reference's nodes, lengths and offsets, so a ruler can be exact in bp.
  gfaidx-viz spaces reference nodes by their drawn length and reads bp
  between node centres, so its ticks are not evenly spaced in bp
- **Any path as the coordinates:** gfa-to-tabix writes a walk file for
  each `--refs` sample. A side file that maps a haplotype's coordinates to
  tiles could be built from walk rows' `path` and `hapOffset`
- **GFA tags, such as depth for colouring:** walk files keep none
  ([open problems](open-problems.md#gfa-tags-neither-file-keeps))

## gfa-to-tabix and gbz-base on HPRC v2.1

HPRC v2.1's Minigraph-Cactus GRCh38 graph has 139.5 M nodes and 464
haplotypes.

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
- graph-walks cuts a 64 kb chr22 window with every haplotype from the
  hosted GRCh38 file over HTTP in about the time it takes from local disk
  ([above](#reading-a-64-kb-window))
- The GBZ-base paper (Sirén and Paten, bioRxiv 2026.07.10.737775 v2) gives
  10.7 GiB for gbz-base, 5.7 GiB for the GBZ and 3.35 GiB for an experimental
  GBZ v3 on the CHM13 graph, with bases

gbz-haplotype-index's `keep` option returns the reference and a few chosen
haplotypes. A [proof](https://github.com/GMOD/gbz-haplotype-index/blob/main/docs/proof.md)
shows that it returns every piece of each chosen haplotype's walk, and a
fuzzer tests it.

We compared format 1 walk files, three per reference, with gbz-base and its
index directly:

- Drawing the HPRC tutorial's loci in JBrowse on 2026-10-08 took 5 to 7
  requests and 2.4 to 7.9 s per window from the walk files, and 17 to 57
  requests and 6.4 to 13.3 s from gbz-base with the index
- On 60 chr22 windows with eight haplotypes, the walk files and gbz-base
  returned the same haplotypes and alignments in 56. The other four lie in
  the 22q11 repeats and the immunoglobulin lambda locus
- At the ABCA7 VNTR, all 462 walk rows match gbz-base's to the bp
- The plugin draws the same graph from format 2 walk files as from format 1
  in 49 of 50 chr22 windows; the 50th, in 22q11, lacks 3,111 nodes off the
  reference
