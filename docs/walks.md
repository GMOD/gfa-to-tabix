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
  query returns every path's steps through the region, except steps that
  [`--stay`](#where-a-step-is-filed) files under the piece's chunk
- A chunk holds the reference's path through it once, each distinct route a
  haplotype takes off that path once, and every other path's piece as the list
  of routes it takes. A reader rebuilds every step exactly
- Every file lists the same paths, including those of the `--refs` samples.
  Rows in `chr22.GRCh38.walks.bed.gz` have GRCh38 coordinates, so a reader on
  GRCh38 downloads that file's index and no other
- [walks-format.md](walks-format.md) describes the rows and how to decode them

| Option            | Effect                                                                   |
| ----------------- | ------------------------------------------------------------------------ |
| `--refs <names>`  | Comma-separated PanSN samples, one file per sample. Required.            |
| `--chunk <bp>`    | Chunk size. Default 65536.                                               |
| `--sequences`     | Add the bases of the reference's nodes and of the nodes routes visit.    |
| `--stay <bp>`     | Keep a piece in its chunk across a stretch elsewhere of at most this many bp of reference nodes. Default 311; 0 turns it off. |

## Where a step is filed

- A step on a reference node takes that node's chunk, and a step on any other
  node takes the chunk of the last reference step before it. A query over a
  window therefore returns every path that visits a reference node in it. A
  step that `--stay` absorbs is filed under the piece's chunk instead, so a
  window can list a path and lack its absorbed steps
- On the reference paths, a step takes the chunk that holds its offset, so
  where the reference passes a node more than once, as in a satellite array,
  each pass is filed where it lies
- Where the reference passes a node more than once, a haplotype's step on it
  takes the pass on the same reference sequence nearest the offset that the
  path's last placed step and the bp walked since predict
- A path's piece keeps its chunk across a stretch elsewhere that returns to
  that chunk with at most `--stay` bp of reference nodes (default 311, the
  `-k 311` minimum match of the HPRC pggb graphs; 0 turns it off). A stretch that never returns starts a
  new piece, and the reference's own paths are exempt
- In a segmental duplication, a haplotype can step onto the reference nodes of
  a distant paralog and back. The steps after the jump take the paralog's
  chunk, so a window at the haplotype's own locus shows it in more pieces and
  leaves out some of its inserted nodes. Before `--stay`, on HPRC v2.1 chr22 this
  filed under 0.1% of steps away from their locus, in at most 74 of 1,130 paths, nearly all
  in the 22q11 low-copy repeats
- A path that visits no node of a reference has no rows under it, and the tool
  counts these on stderr

Every row is filed under the first base of its chunk, `anchorSeq chunkStart
chunkStart+1`. A row spanning the whole chunk would share a Tabix bin with the
next chunk, and a query would read both. A reader fetching a window therefore
queries from the start of the chunk before the window.

## Header

The file opens with header lines, which start with `#`: `tabix -H` prints them
and region queries skip them. The first gives the format, the chunk size, the
longest reference node in bp and the stay in bp. The next is the reference sample, and the rest each
other haplotype with rows in the file, the other `--refs` samples included, as
its PanSN `sample#haplotype`, once each in byte order:

```
#walks	format:i:3	chunk:i:65536	maxnode:i:1024	stay:i:311
#reference	GRCh38
#haplotype	CHM13#0
#haplotype	HG00097#1
#haplotype	HG00097#2
...
```

- A reference node that overlaps a window starts at most `maxnode` bp before
  it, so the chunk holding its rows is at most that far back: a reader queries from
  `max(chunk, maxnode)` bp before the window, rounded down to a chunk start.
  vg chops nodes at 1,024 bp, so for its graphs that is the one chunk back
  described above; a graph with longer nodes needs more
- A reader can list the haplotypes from the header without reading any rows. On
  the chr22 graph under [Scale](#scale) the header is under 10 KB, which the
  file's first BGZF block holds

## Pieces and ordering

- Each row of a piece lists the chunks its path's previous and next pieces are
  filed under, as `pv` and `nx`. A reader that cuts a path off at the edge of
  what it read, such as a haplotype that leaves the reference inside a window
  and rejoins it in a chunk the read did not reach, reads on to that chunk, and
  knows a contig that ends from one that goes on
- A contig in several W lines, as Minigraph-Cactus writes where it clips a
  haplotype, has pieces numbered per line. The last piece of a line gives the
  bp the graph lacks before the contig's next line, as `ng`, and the chunk that
  line starts in, as `nr`; the next line's first piece mirrors them as `pg` and
  `pr`. A last piece with neither `nx` nor `ng` ends the contig's last line in
  the graph; the contig itself may go on
- The rows are the same for any order of the W lines, which `vg convert`
  changes from run to run

## Scale

The tool reads the GFA twice, so it takes a file path; gzip input works. It
holds about 16 bytes per node, 24 more per node for each reference, and with
`--sequences` the graph's bases. Pieces wait for an external sort in up to
512 MB of memory and then in compressed runs in a temporary directory beside
the output. The sort's merge encodes the chunks on every core.

On a Minigraph-Cactus chr22 (3.1 M nodes, 4.7 M links, 1,131 paths, 630 M
steps, a 5.0 GB GFA) with `--refs GRCh38,CHM13`:

- It runs in about 2.5 min from the gzipped GFA and peaks at 1.8 GB on a
  16-core laptop
- The first read refuses a W line that repeats or overlaps another of its
  contig, or whose end column disagrees with its steps, so a bad chr22 fails
  in about 30 s, before the second read
- The two files total 71 MB, where format 1's six took 408 MB. GRCh38's index
  is 10 KB
- A read of two chunks, which every window makes, fetches 0.05 MB at the
  median and 0.5 MB at the 99th percentile, about 0.14 of format 1's
  (`docs/format-2/scripts/window_sizes.py`)

## Readers

- [@jbrowse/graph-walks](https://github.com/GMOD/graph-walks) 2 reads format 3
  only, and asks for a rebuild of a file from gfa-to-tabix 1.0 or earlier
- The graph genome viewer plugin,
  [BandageJS](https://jbrowse.org/demos/bandagejs/), ggbandage, ggtubemap and
  the tube map read through @jbrowse/graph-walks
- jbrowse.org hosts HPRC v2.1's files as
  `https://jbrowse.org/demos/hprc/hprc-v2.1-mc-grch38-f3.{GRCh38,CHM13}.walks.bed.gz`
