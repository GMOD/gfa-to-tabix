# Three reviews of the day's work, 2026-11-11

Three Fable reviewers, none briefed with the session's conclusions, were
asked about the work as a whole rather than one decision. Each is given
here in substance.

## Is this on track

Asked for a check of the day against
[ADR 0011](../../adr/0011-format-7-is-frozen.md)'s account of how the
format kept being redesigned. Its verdict: not on track for a freeze.
The unit is a sound idea and the day's hygiene far better than the
rejected format 8's, but the row was specified, built genome-wide and
written into an accepted ADR before any reader had decoded one, and the
plan hosted the files before the consumers existed.

- **Hosting before integrating:** no swap or release until graph-walks,
  bandage-core and the plugin, linked locally, pass the handoff's tests
  and renders on the rebuilt files
- **The acceptance test had never passed:** the cross-examination's
  2,344 of 2,344 collapsed loaded cuts and read no `blocks` row, and the
  reader's first harness had a mode that trimmed the truth to what the
  row stated
- **The reader's cost was unmeasured** on the windows that made the case
  against loading
- **Stale artifacts:** files with a superseded row at the paths the
  handoff named, and a local main that wrote it
- **The spec half-updated:** the reader's sections still described 6.2
- **Winces at the row:** bp off R said two ways, a suffix after the
  block it precedes, a delta before a sign, no measurement of deltas
  against absolute starts. All four were then measured or ruled on

## Is the end state right

Asked, after the format had gone from 8 to 7 and back, whether the place
it landed is right. Its verdict: yes, and nothing should be put back;
it is not yet earned as a freeze, and the one change is to stop ruling
on the row and build bandage-core and the plugin on it.

- **The mechanism:** `blocks`. No abridging puts 14.9 / 12.1 MB tiles in
  front of every view; reader-only shows nothing without loading
- **Each reversal:** reader-only to `blocks`, a correction; format 8 to
  a format 7 addition, churn, since it weighed released readers the
  owner never valued; the end columns, a correction found by the reader;
  moving them into the list hours later, the right result after a wasted
  round; back to format 8, a correction
- **The tie-break on `hapOffset` and `nsteps`** is right: a named cut
  picks detail units from the `abridged` row alone
- **Before freezing:** the list in
  [ADR 0012](../../adr/0012-abridged-blocks.md#acceptance-before-anything-is-hosted)
- **To stop:** further rounds on the row's spelling; genome rebuilds
  until chr22 passes through all three consumers; format 7
  compatibility tests and wording
- **The biggest risk:** one consumer has been built and the row changed
  twice because of it; two are unstarted, so a third change is likelier
  than not, and the week will tempt a freeze by calendar

## Prior art

Asked the owner's question: with GFA and rGFA defined, is this a
rebuilding of them in a strange way? It fetched GFA 1, rGFA and GAF, and
PAF. Its answer: mostly no. The walk file is a lossless re-encoding of
GFA W-line fragments for range access, as BAM is of SAM, and the plain
GFA equivalent costs 32 times the bytes. But the `blocks` list, a step's
position and the handle are things PAF and chain, rGFA and GBWT already
define, and the spec never said so.

| Walk file | Nearest standard | Relation |
|---|---|---|
| tile | a subgraph by reference interval | a container; not in GFA |
| `ref` row | the reference's W fragment, with S `LN` and rGFA `SN`/`SO` at rank 0 | re-encoding |
| `nodes` | S lines with `LN` | re-encoding, integer ids only |
| `route` | an allele's traversal | a dictionary; none of the standards has it |
| `walk` and its choices | a W fragment; a GAF path | lossless re-encoding |
| `@k`, `:k`, pass counts, placement | none; rGFA forbids a reference passing a node twice | extension |
| `abridged`, detail unit | none | a container, for lazy loading |
| `blocks` | a PAF `cg`; a UCSC chain | the same idea in another notation |
| `departure` | a breakend pair | the same idea, per haplotype, binned |
| a step's position | rGFA's stable coordinate at rank 0 | identical where the reference passes the node once |

- **`blocks` against PAF:** all 2,572 chr22 rows are one colinear run
  and convert exactly. What it adds is a direction and a signed jump for
  each block, so a piece that turns stays one row; the hosted GRCh38
  file has 936 hairpins. What it lacks is its own start on the
  haplotype, which the `abridged` row has, and parsers
- **Bytes, from 60 of chr22's 776 tiles** (none abridged, lighter than
  the mean), per tile:

| | KB | × |
|---|---|---|
| Walk format, as stored | 14.9 | 1 |
| GFA S and W fragments, no routes | 476 | 32 |
| GAF by segment id | 484 | 32 |
| GAF, reference runs as stable intervals | 98.5 | 6.6 |
| PAF `cg` clipped to the tile, no node ids | 19.8 | 1.33 |

- **chr22's `blocks` rows** as a PAF `cg`, 0.99 times the bytes; as a
  UCSC chain, 1.09; as a literal GAF stable path, 5.65
- **Tabix GAF** is not a standard layout either: htslib's GAF preset
  keys on node ids, not reference coordinates
- **Vocabulary:** "block" means a BGZF block, a departure pyramid's
  block and a `blocks` item, and the pyramid's are tabix-style bins;
  pass, occurrence, copy and revisited are one idea in four words; and
  position, `blocks`, runs off R, departure, route, piece and
  `fragStart` each have a standard's word to be glossed by
- **Verdict:** sound, should borrow, nothing replaced. Open the spec
  with the mapping, define `blocks` as a chain that may turn, and call
  the pyramid's blocks bins
- **For a reader who knows GFA:** a walk file is the graph's W lines
  re-encoded for range requests, as BAM re-encodes SAM. Each tile of the
  reference holds a GFA subgraph: the reference's walk once, each
  distinct route off it once, and every haplotype's walk fragment as the
  routes it takes, from which the W lines are recovered step for step.
  Positions are rGFA stable coordinates on the reference; where the
  reference passes a node more than once, which rGFA excludes, the file
  states the writer's choice and marks it
