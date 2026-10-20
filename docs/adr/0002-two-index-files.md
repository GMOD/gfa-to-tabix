# ADR 0002: Nodes and links in two files

- **Status:** under review, 2026-10-20. Accepted earlier the same day on a
  misread reader; see [correction](#correction)
- **Decides:** whether the node and link index is one Tabix file or two,
  `<prefix>.segs.bed.gz` and `<prefix>.links.bed.gz`
- **Rule:** keep two files while any reader reads node rows without link rows.
  Before proposing a merge, check the [readers](#readers) table against the
  current code

## Context

- The tool writes both of a link's nodes into each link row, with their id,
  rank, coordinate and carriers. For drawing a graph, the link file holds
  nearly everything the node file does
- Every graph drawing queries both files for each window, so merging them
  looked like a free saving, and no doc said why the split exists

## Readers

What reads each file in the JBrowse plugin
(`jbrowse-plugin-graphgenomeviewer`) and graph-walks. A graph track in a
linear genome view has two displays: `LinearGraphDisplay`, the default, which
draws the graph, and `LinearBasicDisplay`, which a user picks from the track's
display types and which draws reference segments as flat features.

| reader | node file | link file |
|---|---|---|
| Graph genome view: graph-walks `rgfaCut` | yes | yes |
| graph track, default `LinearGraphDisplay`: graph-walks `rgfaCut` | yes | yes |
| coarse tier: the same code over the `fold` pair | yes | yes |
| graph track, `LinearBasicDisplay`: `segmentFeatures` in `src/RgfaTabixAdapter/RgfaTabixAdapter.ts` | yes | **no** |
| region size check: `getRegionByteSize`, against the node file's index | yes | **no** |
| reference names: `getRefNames`, from the node file's index header | yes | no, but a merged index names them too |

`LinearBasicDisplay` is the only reader that needs node rows alone. In one
file, Tabix returns every row under the window, so that display would
download every link row and discard it.

## Correction

The first version of this ADR called the deciding reader "the linear track".
Every graph drawing, including the graph track's default display in the linear
genome view, reads both files. The node-only reader is the secondary flat
display, `LinearBasicDisplay`, which no plugin doc or demo uses. Whether that
display should read links, or go, is under review; if it reads links or goes,
nothing reads node rows alone and this ADR's rule allows a merge.

## Evidence

A spike, not merged, added a `--one-file` flag, which writes
`<prefix>.graph.bed.gz` with an `N` or `L` column after each row's interval
and otherwise today's columns and filing rules. Measured with graph-walks' own
`anchoredCut` and `@gmod/tabix`, chunk cache off, 400 random windows from
1 kb to 1 Mb on each graph, local disk:

| measure | HPRC v2.1 MC SV graph | base-level chr22, 20–23 Mb |
|---|---|---|
| graph drawing: same subgraph as two files | 400 of 400 windows | 400 of 400 windows |
| graph drawing: reads per window | 2 → 1 | about 11 → 6 |
| graph drawing: bytes per window | about 45% fewer | 3–18% fewer |
| `LinearBasicDisplay`: bytes per window | 15–25% more | 2.4–3.5 × more |
| `LinearBasicDisplay`: time per window | slightly slower | about 3 × slower |
| index loaded up front | 484 KB → 258 KB | 8 KB → 6 KB |

## Alternatives

| option | outcome |
|---|---|
| one file with a row-type column | measured above; waits on `LinearBasicDisplay` |
| the tool writes each node's filing interval into its link rows, and node rows only for nodes without links | fewer bytes than a type column, but it changes the reader's rule for keeping links; unmeasured |
| node rows that list their neighbours | rejected: an edge to a neighbour outside the window dangles |

## Consequences

- A graph drawing costs two index loads and two range reads per window.
  graph-walks `rgfaCut` now issues the two reads together (graph-walks
  f34459b), so they cost one round trip, not two
- `getRegionByteSize` sizes only the node file, so it undercounts what a graph
  drawing fetches
