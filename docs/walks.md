# Walks

- **In:** a base-level graph with integer node ids and W or P lines, such as
  `vg convert -f` writes from a Minigraph-Cactus GBZ
- **Out:** one Tabix-indexed file per reference sample, holding every
  haplotype's path cut into pieces filed under 64 kb chunks of that reference
- A region query returns the rows a reader needs to rebuild every path through
  the region
- [walks-format.md](walks-format.md) describes the rows and how to decode them

```bash
vg convert -f chr22.gbz > chr22.gfa
gfa-to-tabix chr22.gfa --walks --refs GRCh38,CHM13 -o chr22
```

The command writes `<prefix>.<sample>.walks.bed.gz` and its index for each
sample in `--refs`:

```
chr22.GRCh38.walks.bed.gz  chr22.GRCh38.walks.bed.gz.tbi
chr22.CHM13.walks.bed.gz   chr22.CHM13.walks.bed.gz.tbi
```

- A chunk holds the reference's path through it once, each distinct route a
  haplotype takes off that path once, and every other path's piece as the list
  of routes it takes
- Every file lists the same paths, including those of the `--refs` samples.
  Rows in `chr22.GRCh38.walks.bed.gz` have GRCh38 coordinates, so a reader on
  GRCh38 downloads that file's index and no other
- A reader lists the haplotypes from the header without reading any rows

![Four haplotype paths through a bubble, the rows the GRCh38 file has for one 64 kb stretch of chr1, and the paths a reader rebuilds from those rows](figures/walks.svg)

| Option            | Effect                                                                   |
| ----------------- | ------------------------------------------------------------------------ |
| `--refs <names>`  | Comma-separated PanSN samples, one file per sample. Required.            |
| `--chunk <bp>`    | Chunk size. Default 65536.                                               |
| `--sequences`     | Add the bases of the reference's nodes and of the nodes routes visit.    |
| `--stay <bp>`     | Keep a piece in its chunk across a short stretch over nodes the reference passes twice. Default 311; 0 turns it off. |
| `--abridge-steps <n>` | Move a chunk's costliest paths to its detail rows until the rest cost at most n interior steps. Default 1000000; 0 turns it off. |
| `--abridge-bytes <bytes>` | ...and until the rest compress to at most this many bytes. Default 3000000; 0 turns it off. |

## Where a step is filed

[Chunks and pieces](walks-format.md#chunks-and-pieces) gives the exact rules.

- A step on a reference node takes that node's chunk, and a step on any other
  node takes the chunk of the last reference step before it. A query over a
  window therefore returns every path that visits a reference node in it
- `--stay` keeps a piece in its chunk across a stretch elsewhere that returns
  to that chunk and holds a node the reference passes more than once. Any
  node in the stretch that the reference passes once has to lie within the
  chunks a window reads back. The default, 311 bp of reference nodes, is the
  `-k 311` minimum match of the HPRC pggb graphs
- A path that visits no node of a reference has no rows under it, and the tool
  counts these on stderr

## Paralogs and collapsed repeats

- **Paralog jumps:** in a segmental duplication, a haplotype can step onto the
  reference nodes of a distant paralog and back. The steps after the jump take
  the paralog's chunk, so a window at the haplotype's own locus shows the
  haplotype in more pieces and leaves out some of its inserted nodes. On
  Minigraph-Cactus graphs this is rare and sits almost entirely in low-copy
  repeats such as 22q11's
- **Collapsed repeats:** pggb merges the copies of a repeat into shared nodes,
  so the reference path passes those nodes more than once, often megabases
  apart. pggb graphs have many such nodes; Minigraph-Cactus's GRCh38 path has
  none
- **Nearest pass:** a step on such a node takes the pass nearest the offset the
  path's last placed step predicts. Filing every step at the node's first pass
  instead split each haplotype into a piece per hop and made pggb walk files
  dozens of times larger than Minigraph-Cactus's
- **Stay:** `--stay` then keeps short runs over such nodes in the current
  piece. A reference that passes no node twice, such as Minigraph-Cactus's
  GRCh38, gets the same rows at any stay
- **Abridged chunks:** in a satellite array, pggb gives each haplotype its own
  long path through thousands of tiny nodes, and the tool files all of it in
  the chunk where the haplotype leaves the reference. Past `--abridge-steps`
  or `--abridge-bytes`, the tool moves the costliest paths' rows to detail
  rows that a window query skips, and leaves a row per path with its steps,
  bp and where it leaves and rejoins the reference. A viewer draws that row as
  a labelled block and fetches the detail on request.
  [Abridged chunks](walks-format.md#abridged-chunks) gives the rules
- **What to expect on pggb:** a window shows nearly every haplotype whose
  sequence aligns there, except in satellites and CHM13's short arm, where
  abridged paths show as blocks until opened
- [ADR 0001](adr/0001-step-placement.md) gives the placement rules, the
  alternatives tried and the measurements behind these points

## Scale

- The tool reads the GFA twice, so it takes a file path; gzip input works
- The tool holds about 16 bytes per node, 24 more per node for each reference,
  and with `--sequences` the graph's bases
- Pieces wait for an external sort in up to 512 MB of memory and then in
  compressed runs in a temporary directory beside the output. The sort's merge
  encodes the chunks on every core
- A Minigraph-Cactus chromosome with two references takes minutes and a few GB
  of memory on a laptop
- The first read refuses a W line that repeats or overlaps another of its
  contig, or whose end column disagrees with its steps, so a malformed file
  fails before the slow second read
- The header fits in the file's first BGZF block, and a window reads two
  chunks, so a reader fetches a small fraction of a megabyte per window
  (`docs/format-2/scripts/window_sizes.py` measures it)

## Readers

- [@jbrowse/graph-walks](https://github.com/GMOD/graph-walks) 4 reads format 5
  only, and asks for a rebuild of any other file
- The graph genome viewer plugin,
  [BandageJS](https://jbrowse.org/demos/bandagejs/), ggbandage, ggtubemap and
  the tube map read through @jbrowse/graph-walks
- jbrowse.org hosts HPRC v2.1's files as
  `https://jbrowse.org/demos/hprc/hprc-v2.1-mc-grch38-f5.{GRCh38,CHM13}.walks.bed.gz`
