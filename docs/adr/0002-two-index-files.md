# ADR 0002: Nodes and links stay in two files

- **Status:** accepted, 2026-10-20
- **Decides:** whether the node and link index is one Tabix file or two,
  `<prefix>.segs.bed.gz` and `<prefix>.links.bed.gz`
- **Rule:** keep two files while any reader reads node rows without link rows.
  Before proposing a merge, check the [readers](#readers) list against the
  current code

## Context

- The tool writes both of a link's nodes into each link row, with their id,
  rank, coordinate and carriers. For the graph view, the link file holds
  nearly everything the node file does
- The graph view queries both files for every window, so merging them looked
  like a free saving. That made the split look like an accident of history,
  and no doc said why it exists
- Without a recorded reason, the question cost a round of reviews, a
  measurement and a spike before the reader that settles it turned up

## Readers

What reads each file, in the JBrowse plugin
(`jbrowse-plugin-graphgenomeviewer`) and graph-walks:

| reader | node file | link file |
|---|---|---|
| linear track features: `segmentFeatures` in `src/RgfaTabixAdapter/RgfaTabixAdapter.ts` | yes | **no** |
| reference names: `getRefNames`, from the node file's index | yes | **no** |
| region size gate: `getRegionByteSize`, against the node file's index | yes | **no** |
| graph view: graph-walks `rgfaCut`, anchored layout | yes | yes |
| graph view: graph-walks `rgfaCut`, contig layout hops | first read only | yes |
| coarse tier: same code over the `fold` pair | yes | yes |

The linear track is the deciding reader. In one file, Tabix returns every row
under the window, so the track would download every link row and discard it.

## Decision

The index stays two files. The node file holds one row per node and the link
file one row per link. A reader that needs only nodes reads only the node file.

## Evidence

A spike, not merged, added a `--one-file` flag,
which writes `<prefix>.graph.bed.gz` with an `N` or `L` column after each
row's interval and otherwise today's columns and filing rules. Measured with
graph-walks' own `anchoredCut` and `@gmod/tabix`, chunk cache off, 400 random
windows from 1 kb to 1 Mb on each graph, local disk:

| measure | HPRC v2.1 MC SV graph | base-level chr22, 20–23 Mb |
|---|---|---|
| graph view: same subgraph as two files | 400 of 400 windows | 400 of 400 windows |
| graph view: reads per window | 2 → 1 | about 11 → 6 |
| graph view: bytes per window | about 45% fewer | 3–18% fewer |
| linear track: bytes per window | 15–25% more | 2.4–3.5 × more |
| linear track: time per window | slightly slower | about 3 × slower |
| index loaded up front | 484 KB → 258 KB | 8 KB → 6 KB |

One file helps the graph view and costs the linear track most on base-level
graphs, where link rows dominate.

## Alternatives

| option | outcome |
|---|---|
| one file with a row-type column | rejected: the linear track reads every link row |
| the tool writes each node's filing interval into its link rows, and node rows only for nodes without links | rejected for the same reason, and it changes the reader's rule for keeping links |
| node rows that list their neighbours | rejected: an edge to a neighbour outside the window dangles |
| one file, and the linear track draws from the graph view's fetch | couples the track to the graph view; not pursued |

## Consequences

- A graph-view window costs two index loads and two range reads. graph-walks
  `rgfaCut` issues the node read and then the link read, one after the
  other; issuing them together would remove a round trip without a format
  change
- Revisit this ADR only if every reader in the [readers](#readers) table
  reads link rows too
