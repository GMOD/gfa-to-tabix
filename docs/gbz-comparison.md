# Comparison with gbz-base and gbz-haplotype-index

Two routes put a pangenome graph on a static web host for a browser to read by
region, and the JBrowse graph genome viewer plugin reads both:

- **gfa-to-tabix:** bgzipped, Tabix-indexed BED files from any GFA. The
  [node and link index](index-format.md) serves every graph, and the
  [walk files](walks-format.md) add every haplotype's path for a base-level
  graph
- **[gbz-base](https://github.com/jltsiren/gbz-base):** a SQLite database,
  `graph.gbz.db`, that `gbz-base construct` builds from a GBZ.
  [@gmod/gbz-base](https://github.com/GMOD/gbz-base-js) reads it by range
  request
- **[gbz-haplotype-index](https://github.com/GMOD/gbz-haplotype-index):** a
  second SQLite file beside `graph.gbz.db` that names each walk and gives its
  coordinate. Its
  [haplotype-index.md](https://github.com/GMOD/gbz-haplotype-index/blob/main/docs/haplotype-index.md)
  describes its tables

## Choosing

- An rGFA, a pggb graph or any graph without a GBZ: gfa-to-tabix
- HPRC v2.1: the walk files jbrowse.org hosts;
  [readers](walks-format.md#readers) gives their URLs
- A `graph.gbz.db` someone already hosts: gbz-haplotype-index, which works
  beside it and leaves the database as it is
- Thousands of haplotypes: gbz-base

## Differences

|                 | gfa-to-tabix | gbz-base, with gbz-haplotype-index |
| --------------- | ------------ | ---------------------------------- |
| Input           | rGFA, or a plain GFA with P or W lines; walks need a base-level graph | a GBZ |
| Files           | BGZF text and TBI, which htslib, `tabix` and any static web host handle | SQLite |
| Nodes and links | `segs` and `links` rows filed by reference coordinate | a row per node orientation, with its edges |
| Bases           | in walk files with `--sequences` | always |
| Haplotype paths | per 64 kb chunk: the reference's path, distinct routes off it, each piece's choices of route | the GBWT, in the node rows |
| Walk names      | `sample#haplotype#contig` in every row; the header lists them all | `unknown#N` for every walk but the query path without the index; with it, sample, haplotype, contig and coordinate |
| References      | one walk file per `--refs` sample | one database for GRCh38, CHM13 and any generic path |
| Zoomed out      | `build` writes a coarse tier, alleles and bubbles; walk files have none | the index draws every haplotype over a whole chromosome in about a dozen requests, at several zoom levels |
| N haplotypes    | routes grow as N^0.36 and choices as N^0.86, about 20 GB genome-wide at 10,000 | the GBWT grows sublinearly, because haplotypes share runs |
| Paralog jumps   | the steps after a jump take the paralog's chunk ([details](walks-format.md#paralogs-and-collapsed-repeats)); on chr22, fewer than 0.1% of steps, in at most 74 of the 1,130 paths besides GRCh38's, nearly all in 22q11 | reaches those nodes by graph distance |
| Misses          | a haplotype that leaves the reference before a window and rejoins it after has no row in the window's chunks ([ADR 0006](adr/0006-walks-skip-rows.md) proposes rows for it) | the snarl extension once turned a 100 kbp query into 10 Mbp, 75 s and 9 GiB |

The index's keep route, which names a few chosen haplotypes, has a
[proof](https://github.com/GMOD/gbz-haplotype-index/blob/main/docs/proof.md)
and a fuzzer behind it.

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
- Drawn in JBrowse at the HPRC tutorial's loci on 2026-10-08, format 1 walk
  files, three per reference, took 5 to 7 requests and 2.4 to 7.9 s per window,
  and gbz-base with the index 17 to 57 requests and 6.4 to 13.3 s
- On 60 chr22 windows with eight haplotypes, format 1 walk files and gbz-base
  returned the same haplotypes and alignments in 56. The other four lie in the
  22q11 repeats and the immunoglobulin lambda locus
- At the ABCA7 VNTR, all 462 format 1 walk rows match gbz-base's to the bp
- From format 2 walk files, the plugin draws the same graph in 49 of 50 chr22
  windows; the 50th, in 22q11, lacks 3,111 nodes off the reference
