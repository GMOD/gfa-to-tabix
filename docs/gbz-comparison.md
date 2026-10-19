# Comparison with gbz-base and gbz-haplotype-index

Two ways to put a pangenome graph on a static web host for a browser to read by
region:

- **gfa-to-tabix:** bgzipped, Tabix-indexed BED files from any GFA. The node and
  link index serves every graph, and the walk files add every haplotype's path
  for a base-level graph
- **[gbz-base](https://github.com/jltsiren/gbz-base):** a SQLite database,
  `graph.gbz.db`, that `gbz-base construct` builds from a GBZ.
  [@gmod/gbz-base](https://github.com/GMOD/gbz-base-js) reads it by range
  request
- **[gbz-haplotype-index](https://github.com/GMOD/gbz-haplotype-index):** a
  second SQLite file beside `graph.gbz.db`. With the database alone, gbz-base
  names the query path and labels every other walk `unknown#N`; with the index,
  @gmod/gbz-base names each walk and gives its coordinate

The JBrowse graph genome viewer plugin reads both routes.

## What the files hold

|                       | gfa-to-tabix                                                                                 | gbz-base                                   | with gbz-haplotype-index                                |
| --------------------- | -------------------------------------------------------------------------------------------- | ------------------------------------------ | ------------------------------------------------------- |
| Input                 | rGFA, or a plain GFA with P or W lines; walks need a base-level graph                        | a GBZ                                      | the GBZ and its `graph.gbz.db`                          |
| Container             | BGZF text and TBI                                                                            | SQLite                                     | SQLite                                                  |
| Nodes and links       | `segs` and `links` rows filed by reference coordinate                                        | a row per node orientation, with its edges |                                                         |
| Bases                 | in walk files with `--sequences`                                                             | always                                     |                                                         |
| Haplotype paths       | per 64 kb chunk: the reference's path, distinct routes off it, each piece's choices of route | the GBWT, in the node rows                 | samples, anchors and bins that name each walk           |
| Walk names            | in every row as `sample#haplotype#contig`; the header lists them all                         | `unknown#N`, but for the query path        | sample, haplotype, contig and coordinate                |
| Reference coordinates | one walk file per `--refs` sample                                                            | one file for every indexed reference path  | anchors on each reference sample                        |
| Zoomed-out views      | `build` writes a coarse tier, alleles and bubbles; walks have none                           | none                                       | a per-bin class of every haplotype, several zoom levels |

- [walks-format.md](walks-format.md) describes the walk rows and
  [index-format.md](index-format.md) the node and link rows
- gbz-haplotype-index's
  [haplotype-index.md](https://github.com/GMOD/gbz-haplotype-index/blob/main/docs/haplotype-index.md)
  describes its tables

## Measured on HPRC v2.1

The Minigraph-Cactus GRCh38 graph: 139.5 M nodes, 464 haplotypes.

| measure                 | gfa-to-tabix walk files                 | gbz-base             | gbz-haplotype-index |
| ----------------------- | --------------------------------------- | -------------------- | ------------------- |
| size                    | 1.22 GB GRCh38, 1.63 GB CHM13, no bases | 10.05 GB with bases  | 5.1 GB              |
| build                   | 28.6 min, 12.9 GB peak, 24 cores        | HPRC hosts the file  | 35 min, 22 threads  |
| reads per window        | one index, one range of two chunks      | 18 to 43 round trips |                     |
| bytes per window, chr22 | 0.05 MB median, 0.5 MB p99              |                      |                     |

- The GBZ-base paper (Sirén and Paten, bioRxiv 2026.07.10.737775 v2) gives
  10.7 GiB for gbz-base, 5.7 GiB for the GBZ and 3.35 GiB for an experimental
  GBZ v3 on the CHM13 graph, with bases
- Drawn in JBrowse at the HPRC tutorial's loci on 2026-10-08, the walk files
  took 5 to 7 requests and 2.4 to 7.9 s per window, and gbz-base with the index
  17 to 57 requests and 6.4 to 13.3 s. Those walk files were format 1, three
  files per reference where format 2 has one

## Agreement

- On 60 chr22 windows with eight haplotypes, both returned the same haplotypes
  and alignments in 56. The other four lie in the 22q11 repeats and the
  immunoglobulin lambda locus
- At the ABCA7 VNTR, all 462 walk rows match gbz-base's to the bp
- Both measurements read format 1 walk files. The plugin draws the same graph
  from format 2 in 49 of 50 chr22 windows; the 50th, in 22q11, lacks 3,111 nodes
  off the reference

## Where gfa-to-tabix comes out ahead

- **Any GFA:** the node and link index takes a minigraph rGFA or a pggb, odgi or
  vg GFA, with no GBZ
- **Standard files:** htslib, `tabix` and any static web host handle BGZF and
  Tabix, and a reader needs no SQLite
- **Names in every row:** naming a walk takes no second file
- **Fewer requests:** a window reads one range of one file
- **Size:** the two references' walk files total 2.85 GB, against 15 GB for the
  database and the index together. The walk files hold no bases unless
  `--sequences` is given

## Where gbz-base and gbz-haplotype-index come out ahead

- **Growth with haplotypes:** with N haplotypes, the walk files' routes grow as
  N^0.36 but their choices as N^0.86, about 20 GB genome-wide at 10,000. The
  GBWT grows sublinearly, because haplotypes share runs
- **One file for every reference:** one `graph.gbz.db` serves queries on GRCh38,
  CHM13 and any generic path
- **Paralog jumps:** where a haplotype steps onto a distant paralog's reference
  nodes and back, the walk files file the steps after the jump under the
  paralog's chunk, so a window at the haplotype's own locus shows it in more
  pieces and misses some of its inserted nodes. gbz-base reaches those nodes by
  graph distance. On chr22 the walk files file fewer than 0.1% of steps away from
  their locus, in at most 74 of the 1,130 paths besides GRCh38's, nearly all in 22q11
- **Bases:** the database always holds every node's bases
- **Zoomed-out haplotypes:** the index's overview draws every haplotype over a
  whole chromosome in about a dozen requests. Walk files have no coarse tier
- **Proof:** the keep route that names a few chosen haplotypes has a
  [proof](https://github.com/GMOD/gbz-haplotype-index/blob/main/docs/proof.md)
  and a fuzzer behind it

## Where both fall short

- A haplotype that leaves the reference before a window and rejoins it after has
  no row in the window's chunks of a walk file
- gbz-base errs the other way: its snarl extension once turned a 100 kbp query
  into 10 Mbp, 75 s and 9 GiB

## Choosing

- An rGFA, a pggb graph or any graph without a GBZ: gfa-to-tabix
- A graph whose `graph.gbz.db` someone already hosts, such as HPRC's:
  gbz-haplotype-index, which leaves the database as it is
- Thousands of haplotypes: gbz-base
