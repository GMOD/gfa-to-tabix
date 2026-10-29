# ADR 0007: Node and link format 2

- **Status:** accepted, 2026-10-28; the default from gfa-to-tabix 2.0
- **Decides:** the next node and link format: one file, a header, and a plain
  GFA's carriers as bits
- **Measured by:** HPRC release 2's pggb chrY and chr22 and HPRC v2.1's
  Minigraph-Cactus chr22 on GRCh38, through htslib's `tabix` over 50 windows
  of 10 kb with the default `--max-component`, and graph-walks 4.4's cuts of
  both formats compared window by window

## Context

- A plain GFA's rows list every assembly carrying the node by name, as
  `SM:Z:HG002.1,HG00097.1,...`, and each link row repeats the lists of both its
  nodes. Bgzipped:

| | pggb chrY nodes | pggb chrY links | pggb chr22 nodes | pggb chr22 links |
|---|---|---|---|---|
| lists' share of the raw text | 64% of 0.97 GB | 90% of 10.5 GB | 94% of 22 GB | 95% of 77 GB |
| with `SM:Z:` lists | 86 MB | 378 MB | 1.29 GB | 3.9 GB |
| without them | 54 MB | 122 MB | 154 MB | 346 MB |

- A browser parses the lists whatever gzip saves, and a median pggb chr22
  window read 4.4 MB of link text, most of it lists
- graph-walks' `parseSegmentRow` tells the anchored layout from the contig
  layout by column count, so a contig row with three tag columns would read
  as anchored, and no file names the graph it came from
- [ADR 0002](0002-two-index-files.md) kept nodes and links in two files until
  the format next changed for another reason

## Decision

- gfa-to-tabix writes `<prefix>.graph.bed.gz`, nodes and links in one file,
  each row's kind, `N` or `L`, after its interval and format 1's columns
  after that. `--format 1` writes format 1's two files
- The first line is `#gfa-to-tabix  format:i:2  layout:Z:<layout>
  graph:Z:<hash>`, the hash an FNV-1a sum over each segment's id and length,
  which the order of the S lines doesn't change
- A plain GFA adds `#samples` with its assemblies in byte order, and a row
  states carriers as `SB:H:`, hex digit i / 4 holding the assembly numbered i
  as bit i % 4, trailing zero digits dropped: once on a node row, and for both
  ends on a link row
- Readers refuse a format they don't know and skip header lines and tags they
  don't know. A file with no `#gfa-to-tabix` line is format 1
- `build` writes its fine index and coarse tier as format 2 and says so in
  `graph.json` and the track config. Its contig pair, which the allele
  inventory reads, stays format 1

## Evidence

| chr22 | files, format 1 | format 2 | text per window, format 1: median, p90, max | format 2 |
|---|---|---|---|---|
| pggb | 2.05 GB | 333 MB | 5.18, 148, 595 MB | 0.31, 8.58, 32.3 MB |
| Minigraph-Cactus | 1.20 GB | 184 MB | 5.03, 12.2, 31.0 MB | 0.27, 0.72, 6.76 MB |

- Format 1's sizes are both files together, and a window's text is what one
  query on each returns
- The build's peak memory doesn't change: 18.6 GB for pggb chr22 and 8.2 GB
  for MC chr22
- graph-walks 4.4 cut format 1 and format 2 of the same graphs into the same
  segments and links in every window compared: 400 on the E. coli fixture, 50
  of 10 kb on pggb chrY and 100 on MC chr22
- Without bits on link rows, those cuts lost the samples of 83% of pggb chrY's
  segments and 1.4% of MC chr22's. In collapsed repeats a link reaches a copy
  megabases away, which no node row of the query returns. With the bits, no
  segment lost its samples, for 11% more bytes on chrY

## Consequences

- Hosted indexes are rebuilt to take format 2; format 1 files keep working in
  every reader
- graph-walks 4.4 and the JBrowse plugin 8.2 read format 2, and the plugin 8.3
  takes a `build` manifest's format 2 coarse tier
- ADR 0002's two-file split ends with format 2

## Alternatives rejected

- **Keep `SM:Z:` and rely on gzip:** the browser still parses the lists, 95%
  of a pggb link file's text
- **Reuse the `SM` tag for the bitmask:** graph-walks' `segmentSamples`,
  bandage-core's `carriedSamples` and the plugin's carriage lane parse `SM:Z:`
  as a list of names
- **No carriers on link rows:** a reader can't name the carriers of a far end
  that no node row of the query returns, 83% of the segments of a pggb chrY cut
- **Keep two files:** ADR 0002 measured one file at 45% fewer bytes per window
  on HPRC's SV graph and 3-18% on base-level chr22, with one range request
  and one index instead of two
