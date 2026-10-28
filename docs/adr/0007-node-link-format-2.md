# ADR 0007: Node and link format 2

- **Status:** accepted, 2026-10-28
- **Decides:** the next node and link format: one file, a header, and a plain
  GFA's carriers as bits on node rows
- **Measured by:** HPRC release 2's pggb chrY and chr22 and HPRC v2.1's
  Minigraph-Cactus chr22 on GRCh38, through htslib's `tabix` over 50 windows
  of 10 kb, with the default `--max-component`

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

- `--format 2` writes `<prefix>.graph.bed.gz`, nodes and links in one file,
  each row's kind, `N` or `L`, after its interval and format 1's columns
  after that
- The first line is `#gfa-to-tabix  format:i:2  layout:Z:<layout>
  graph:Z:<hash>`, the hash an FNV-1a sum over each segment's id and length,
  which the order of the S lines doesn't change
- A plain GFA adds `#samples` with its assemblies in byte order, and a node
  row states its carriers as `SB:H:`, hex digit i / 4 holding the assembly
  numbered i as bit i % 4, trailing zero digits dropped
- The tool writes no carriers on link rows. A reader takes them from the node
  rows of the same query, which hold every node under the window. A link's
  far end past the window, on the backbone or in a moved component, comes
  without carriers
- Readers refuse a format they don't know and skip header lines and tags they
  don't know. A file with no `#gfa-to-tabix` line is format 1
- Format 1 stays the default until graph-walks and the JBrowse plugin read
  format 2, and then the default switches

## Evidence

| chr22 | files, format 1 | format 2 | text per window, format 1: median, p90, max | format 2 |
|---|---|---|---|---|
| pggb | 2.05 GB | 247 MB | 5.18, 148, 595 MB | 0.17, 3.65, 12.8 MB |
| Minigraph-Cactus | 1.20 GB | 143 MB | 5.03, 12.2, 31.0 MB | 0.15, 0.39, 3.72 MB |

- Format 1's sizes are both files together, and a window's text is what one
  query on each returns
- The build's peak memory doesn't change: 18.7 GB for pggb chr22 and 7.7 GB
  for MC chr22

## Consequences

- Hosted indexes are rebuilt once, when the default switches
- graph-walks, bandage-core's `carriedSamples` and the plugin's carriage lane
  and add-track workflow each read the new file before the switch
- ADR 0002's two-file split ends with format 2

## Alternatives rejected

- **Keep `SM:Z:` and rely on gzip:** the browser still parses the lists, 95%
  of a pggb link file's text
- **Reuse the `SM` tag for the bitmask:** graph-walks' `segmentSamples`,
  bandage-core's `carriedSamples` and the plugin's carriage lane parse `SM:Z:`
  as a list of names
- **Bits on link rows too:** format 1's link carriers repeat its two nodes'
  lists, which the node rows of the same query already hold for every node
  under the window
- **Keep two files:** ADR 0002 measured one file at 45% fewer bytes per window
  on HPRC's SV graph and 3-18% on base-level chr22, with one range request
  and one index instead of two
