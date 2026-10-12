# Walks

`--walks` indexes every haplotype's path through a base-level graph with integer
node ids and W or P lines, such as `vg convert -f` writes from a
Minigraph-Cactus GBZ:

```bash
vg convert -f chr22.gbz > chr22.gfa
gfa-to-tabix chr22.gfa --walks --refs GRCh38,CHM13 -o chr22
```

The command writes one file and its index for each sample in `--refs`,
`<prefix>.<sample>.walks.bed.gz`:

```
chr22.GRCh38.walks.bed.gz  chr22.GRCh38.walks.bed.gz.tbi
chr22.CHM13.walks.bed.gz   chr22.CHM13.walks.bed.gz.tbi
```

- The tool cuts each path into pieces, one for each stretch the path spends in
  a 64 kb chunk of a reference, and files each piece under its chunk. A region
  query returns every path's steps through the region
- A chunk holds the reference's path through it once, each distinct route a
  haplotype takes off that path once, and every other path's piece as the list
  of routes it takes. A reader rebuilds every step exactly
- A sample's file holds only the rows filed under its own chunks, so a reader
  on GRCh38 downloads an index that covers GRCh38 alone
- [walks-format.md](walks-format.md) describes the rows and how to decode them

| Option            | Effect                                                                   |
| ----------------- | ------------------------------------------------------------------------ |
| `--refs <names>`  | Comma-separated PanSN samples, each with its own file. Required.         |
| `--chunk <bp>`    | Chunk size. Default 65536.                                               |
| `--sequences`     | Add the bases of the reference's nodes and of the nodes routes visit.    |

## Where a step is filed

- A step on a reference node takes that node's chunk, and a step on any other
  node takes the chunk of the last reference step before it. A query over a
  window therefore returns every path that visits a reference node in it
- On the reference's own paths, a step takes the chunk of its own offset, so
  where the reference passes a node more than once, as in a satellite array,
  each pass is filed where it lies
- A node has one coordinate, from the first-named reference path's earliest
  visit, so another haplotype that passes such a collapsed node again is filed
  under the reference's first copy. On HPRC v2.1's Minigraph-Cactus chr22
  neither GRCh38 nor CHM13 passes a node twice, so no step there is filed this
  way
- In a segmental duplication, a haplotype can step onto the reference nodes of
  a distant paralog and back. The steps after the jump take the paralog's
  chunk, so a window at the haplotype's own locus shows it in more pieces and
  leaves out some of its inserted nodes. On HPRC v2.1 chr22 this files under
  0.1% of steps away from their locus, in at most 74 of 1,130 paths, nearly all
  in the 22q11 low-copy repeats
- A path that visits no node of a reference has no rows under it, and the tool
  counts these on stderr

Every row is filed under the first base of its chunk, `anchorSeq chunkStart
chunkStart+1`. A row spanning the whole chunk would share a Tabix bin with the
next chunk, and a query would read both. A reader fetching a window therefore
queries from the start of the chunk before the window.

## Header

The file opens with header lines, which start with `#`: `tabix -H` prints them
and region queries skip them. The first gives the format, the chunk size and
the longest node in bp. The next names the reference sample, and the rest each
other haplotype with rows in the file, the other `--refs` samples included, as
its PanSN `sample#haplotype`, once each in byte order:

```
#walks	format:i:2	chunk:i:65536	maxnode:i:1024
#reference	GRCh38
#haplotype	CHM13#0
#haplotype	HG00097#1
#haplotype	HG00097#2
...
```

- A node that overlaps a window starts at most `maxnode` bp before it, so the
  chunk holding its rows is at most that far back: a reader queries from
  `max(chunk, maxnode)` bp before the window, rounded down to a chunk start.
  vg chops nodes at 1,024 bp, so for its graphs that is the one chunk back
  described above; a graph with longer nodes needs more
- A reader can list the haplotypes from the header without reading any rows. On
  the chr22 graph under [Scale](#scale) the header is 465 lines and 9,778
  bytes, which the file's first BGZF block holds

## Pieces and ordering

- Each row of a piece names the chunks its path's previous and next pieces are
  filed under, as `pv` and `nx`. A reader that cuts a path off at the edge of
  what it read, such as a haplotype that leaves the reference inside a window
  and rejoins it in a chunk the read did not reach, reads on to that chunk, and
  knows a contig that ends from one that goes on
- The rows do not depend on the order of the W lines, which `vg convert`
  changes from run to run

## Scale

The tool reads the GFA twice, so it takes a file, not stdin; gzip is fine. It
holds about 16 bytes per node, 24 more per node for each reference, and with
`--sequences` the graph's bases. Pieces wait for an external sort in up to
512 MB of memory and then in compressed runs in a temporary directory beside
the output. The sort's merge encodes the chunks on every core.

On a Minigraph-Cactus chr22 (3.1 M nodes, 4.7 M links, 1,131 paths, 630 M
steps, a 5.0 GB GFA) with `--refs GRCh38,CHM13`:

- It runs in about 2.5 min from the gzipped GFA and peaks at 1.8 GB on a
  16-core laptop
- The two files total 71 MB, where format 1's six took 408 MB. GRCh38's index
  is 10 KB
- A read of two chunks, which every window makes, fetches 0.05 MB at the
  median and 0.5 MB at the 99th percentile, about 0.14 of format 1's
  (`docs/format-2/scripts/window_sizes.py`)

## Format 1 and readers

Files from gfa-to-tabix 0.12 and earlier are format 1: three files per
reference, the walks with every step, the nodes they visit and the links
between them. Readers:

- The graph genome viewer plugin reads format 2 from 6.27.0. Releases that
  read through [@jbrowse/graph-walks](https://github.com/GMOD/graph-walks)
  refuse format 1
- [BandageJS](https://jbrowse.org/demos/bandagejs/) and the tube map read
  format 2 only, through @jbrowse/graph-walks
- jbrowse.org hosts HPRC v2.1's files as
  `https://jbrowse.org/demos/hprc/hprc-v2.1-mc-grch38-f2.{GRCh38,CHM13}.walks.bed.gz`
