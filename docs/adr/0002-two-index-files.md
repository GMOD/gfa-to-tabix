# ADR 0002: Nodes and links in two files

- **Status:** accepted, 2026-10-20
- **Decides:** whether the node and link index is one Tabix file or two,
  `<prefix>.segs.bed.gz` and `<prefix>.links.bed.gz`
- **Decision:** two files for now. Merge into one when the node and link
  format next changes for another reason
- **Priority:** the graph displays. No reader that draws only flat segments
  decides the format

## Context

- The tool writes both of a link's nodes into each link row, with their id,
  rank, coordinate and carriers. For drawing a graph, the link file holds
  nearly everything the node file does
- Every graph drawing reads both files for each window, so one file looked
  like a free saving, and no doc said why the split exists

## Readers

What reads each file in the JBrowse plugin
(`jbrowse-plugin-graphgenomeviewer`) and graph-walks:

| reader | node file | link file |
|---|---|---|
| Graph genome view: graph-walks `rgfaCut` | yes | yes |
| graph track in a linear genome view, default `LinearGraphDisplay`: graph-walks `rgfaCut` | yes | yes |
| coarse tier: the same code over the `fold` pair | yes | yes |
| carriage lane: a `FeatureTrack` on `RgfaTabixAdapter`, colored by `sampleCount` (jbrowse-components' E. coli demo, the pangenome_prepare_graph tutorial), through `segmentFeatures` | yes | no |
| graph track, secondary `LinearBasicDisplay`: the same `segmentFeatures` | yes | no |
| their size check: `getRegionByteSize` | yes | no |
| reference names: `getRefNames`, from the node file's index header | yes | no, but a merged index names them too |

- `segmentFeatures` runs only on graphs without walks. It draws reference
  segments as flat features and drops every allele row it downloads
- The carriage lane is a documented feature, so a merge has to keep it
  working, at the measured cost: 15–25% more bytes per window on HPRC and
  2.4–3.5 × on a base-level graph
- `LinearGraphDisplay` limits a window by its span in bp, not by bytes

## Evidence

A spike, not merged, added a `--one-file` flag, which writes
`<prefix>.graph.bed.gz` with an `N` or `L` column after each row's interval
and otherwise today's columns and filing rules. Measured with graph-walks' own
`anchoredCut` and `@gmod/tabix`, chunk cache off, 400 random windows from
1 kb to 1 Mb on each graph, local disk:

| measure | HPRC v2.1 MC SV graph | base-level chr22, 20–23 Mb |
|---|---|---|
| graph drawing: same subgraph as two files | 400 of 400 windows | 400 of 400 windows |
| graph drawing: range reads per window | 2 → 1 | about 11 → 6 |
| graph drawing: bytes per window | about 45% fewer | 3–18% fewer |
| index loaded up front | 484 KB → 258 KB | 8 KB → 6 KB |

On the base-level slice a 1 kb window fetches about 1.5 MB in either format:
the anchored layout files each allele under its whole bubble's span, and the
earliest row overlapping a window starts a median 151 kb before it.

## Why not merge now

- graph-walks `rgfaCut` issues its node and link reads together (graph-walks
  f34459b), so a window already waits on one round trip. A merge removes a
  range request and an index load, not a wait
- What remains is bytes: moderate on HPRC, small on base-level graphs, where
  bubble-wide filing costs far more than the split
- The cost is a format break in gfa-to-tabix, graph-walks and the plugin,
  a plugin release that reads both formats, and every hosted set rebuilt.
  That is worth paying once, alongside another format change

## Alternatives

| option | outcome |
|---|---|
| one file with a row-type column | the merge to make; deferred, see above |
| the tool writes each node's filing interval into its link rows, and node rows only for nodes without links | fewer bytes than a type column, but it changes the reader's rule for keeping links; measure before choosing it |
| node rows that list their neighbours | rejected: an edge to a neighbour outside the window dangles |

## History

The first version of this ADR, the same day, kept two files because "the
linear track" read only nodes. Every graph drawing in the linear genome view
reads both files; that reader was `LinearBasicDisplay`, a secondary flat
display.
