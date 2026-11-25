# Writing walk files

How gfa-to-tabix writes [walk format 8](walks-format.md): its options,
how it reads the GFA and its path names, where it files a step, and what
it checks. Where a step is filed, what `--stay` keeps together and which
pieces a tile abridges are this tool's choices. A reader takes positions
and pieces from the rows and relies on
[the format's rules](walks-format.md#what-a-reader-relies-on), not on
this page.

```bash
vg convert -f chr22.gbz > chr22.gfa
gfa-to-tabix chr22.gfa --walks --refs GRCh38,CHM13 -o chr22
```

- **In:** a base-level GFA with integer node ids and W or P lines, such
  as `vg convert -f` writes from a Minigraph-Cactus GBZ
- **Out:** a data file and its directory for each sample in `--refs`,
  and no other file <!-- C143 -->:

```
chr22.GRCh38.walks.gz  chr22.GRCh38.walks.gz.idx
chr22.CHM13.walks.gz   chr22.CHM13.walks.gz.idx
```

- Lines in `chr22.GRCh38.walks.gz` have GRCh38 coordinates, so a reader
  on GRCh38 reads that file and no other

## Options

| Option            | Effect                                                                   |
| ----------------- | ------------------------------------------------------------------------ |
| `--refs <names>`  | Comma-separated PanSN samples, one file per sample. Required.            |
| `--tile <bp>`     | Tile size. Default 65536.                                                |
| `--sequences`     | Add the bases of the reference's nodes and of the nodes routes visit, as `SQ:Z:` tags. Refuses a graph with a segment whose sequence is `*`. |
| `--stay <bp>`     | Keep a piece in its tile across a short stretch elsewhere over nodes the reference passes more than once, each moved to a pass in the tile. Default 311, the `-k 311` minimum match of the HPRC pggb graphs; 0 turns it off. |
| `--abridge-steps <n>` | Move a tile's costliest paths to its detail units until the rest cost at most n interior steps. Default 1000000; 0 turns it off. |
| `--abridge-bytes <bytes>` | ...and until the rest hold at most this many bytes of rows, uncompressed, as [Abridging](#abridging) says. Default 3000000; 0 turns it off. |

<!-- C6 C7 C8 C65 -->

Each option takes at most 2^40, which the tool refuses above.
<!-- C153 --> The header's `stay`, `abridge` and `abridgebytes` tags
state the values a file was written with, and the tool writes `graph`
and `leftout` from 5.0.0 on
([ADR 0015](adr/0015-walk-files-name-their-graph.md)).

## Reading the GFA

- The tool reads the GFA more than once, so it takes a file path and
  refuses stdin; gzip input works <!-- C105 -->
- **The reference** is every path of a `--refs` sample with a W or P line
  that has steps: each is a reference sequence of that sample's file.
  <!-- C9 --> `--refs` always takes a whole sample, so the tool writes no
  file whose reference is one haplotype of several, which the format
  allows
  ([open problem](open-problems.md#a-reference-of-one-haplotype-of-a-sample-cant-be-written))
  <!-- C9 -->
- **A contig can span several W lines,** one per stretch the graph holds,
  as where Minigraph-Cactus clips a haplotype. The files are the same for
  any order of the W lines, which `vg convert` changes from run to run
  <!-- C19 -->
- **A line with steps but none on a node of a reference** has no rows in
  that reference's file, and the tool counts these lines on stderr and
  in `leftout` <!-- C20 -->. A line left out is one W or P line, and its
  contig's other lines keep their rows <!-- C140 -->
- **A segment of 0 bp is dropped** as the tool reads the GFA: its steps
  leave every W and P line, so the steps either side of one become
  consecutive, and a line left with no steps is skipped. <!-- C152 --> A
  reference sequence left with no bases has no units and no directory
  line. The header's `graph` still names every S line, 0 bp or not
  <!-- C190 -->
- **A W or P line with an empty steps field is skipped** once its end
  column is checked: it has no rows, no departure record and no `#hole`,
  it names no reference sequence, it is not counted on stderr, and the
  overlap refusal doesn't apply to it. <!-- C118 --> `*` there is refused
  as a step

The tool stops with an error on:

- a W line whose end column is not its start plus its nodes' lengths
  <!-- C18 -->, or whose start column is `*` <!-- C181 -->
- two lines of a `path` with steps, W or P, that overlap or start at the
  same base <!-- C17 -->
- a W or P line that starts or ends past 2^53 on its contig, or a
  reference sequence whose last tile ends past it, so no coordinate a
  file states is above 2^53 <!-- C172 -->
- a node id of 2^31 or more <!-- C126 -->
- a W or P line that gives a name that is empty, starts with `#` or
  holds a byte outside 0x21 to 0x7E; the message names the line
  <!-- C95 C200 -->
- a W or P line that steps on a segment whose sequence is `*` and that
  has no `LN:i:`
- a P line whose steps hold a `;`, GFA 1.2's jump. A jump joins two
  segments no link joins, over a distance the line doesn't state, so no
  step after it has an offset <!-- C189 -->

## Path names

[ADR 0014](adr/0014-p-line-names.md) gives the reasons for this reading,
the vg and odgi runs behind it and the readings turned down. What a
reader does with a `path` is in the format's
[Path names](walks-format.md#path-names).

- **A W line's** `path` is its `sample#haplotype#contig` and its
  `fragStart` its start column <!-- C181 -->
- **A P line** has one name and no column for a start, so the tool reads
  the name from its right end, once it has summed the bp of the line's
  steps, `bp` below. A **name number** is one to nineteen of the digits
  `0` to `9`, read in base 10, leading zeros allowed. Text that would be
  a suffix but for digits that are no name number is no suffix. The tool
  takes three steps in this order, each at most once, each on the text
  the step before left: <!-- C182 -->
  - **`:a-b`, the cut `odgi extract` writes.** Where the name ends in
    `:`, a name number `a`, `-` and a name number `b`, with `b − a` equal
    to `bp` and above 0, that text leaves the name and adds `a`. Where
    `b − a` is anything else the text stays in the name and adds nothing,
    so a 1-based range, as `samtools faidx` names a region, is not read
    <!-- C183 -->
  - **`[s]` or `[s-e]`, vg's subrange.** Where the text ends in `[`, a
    name number `s` and `]`, or in `[`, `s`, `-`, a name number `e` and
    `]`, that text leaves the name and adds `s`. With an `e`, and no
    `:a-b` read before it, the tool refuses the line unless `e − s`
    equals `bp`, as it refuses a W line's end column. Beneath a `:a-b` it
    reads no `e`: the bracket is of the piece the cut was taken from, and
    `e` is that piece's end <!-- C184 -->
  - **A fourth field.** Where the text holds exactly three `#` and a
    name number after the last, that `#` and the name number leave the
    name and the name number is added. <!-- C185 --> `#0`, which vg
    appends to the name of a haplotype it reads from a P line, adds 0
    <!-- C185 -->
- The text left is `path` and the sum is `fragStart`. The tool refuses a
  line that leaves no text, such as one named `[5]`, and a sum past 2^53.
  <!-- C186 --> A P line with no suffix is its name whole, from 0. The
  tool reads no suffix beneath a fourth field and no second suffix of a
  kind: a `:a-b` there is part of `path`, as it is of the contig in the W
  line of the same path <!-- C186 -->
- The fixtures of [dialect](walks-container/dialect/) hold the same paths
  as vg wrote them in W lines and in P lines, and as odgi cut vg's P
  lines. The forms of one graph give one walk file, byte for byte
  <!-- C187 -->

| P line name | bp of its steps | `path` | `fragStart` | where such a name comes from |
| --- | --- | --- | --- | --- |
| `H#1#c` | 16 | `H#1#c` | 0 | pggb, from a PanSN FASTA record |
| `H#1#c#0` | 16 | `H#1#c` | 0 | vg, of a P line it read |
| `H#1#c#100` | 14 | `H#1#c` | 100 | vg, of a GBZ haplotype clipped from 100 |
| `H#1#c[100-116]` | 16 | `H#1#c` | 100 | vg, a subrange |
| `H#1#c#100[16-22]` | 6 | `H#1#c` | 116 | `vg chunk` of that clipped haplotype |
| `H#1#c:5-21` | 16 | `H#1#c` | 5 | `odgi extract` |
| `H#1#c#0[100-114]:6-14` | 8 | `H#1#c` | 106 | `odgi extract` of a vg subrange |
| `H#1#c:5-21#0` | 16 | `H#1#c:5-21` | 0 | vg, of an `odgi extract` |
| `H#1#c:6-21` | 16 | `H#1#c:6-21` | 0 | a 1-based region name |
| `H#1#c[100-900]` | 16 | refused | | a stated end its steps contradict |
| `[5]` | 16 | refused | | a suffix alone |

- `path` is `sample#haplotype#contig` where the line is a W line or its
  name has three fields. A P line's `path` can have any number of fields:
  pggb copies FASTA record names unchanged, and odgi's and vg's own
  examples include `sample#contig`
- **A limit: phase blocks.** For haplotypes from a VCF-phased GBWT, vg
  numbers the phase blocks of a contig 0, 1, 2 and writes that counter in
  the fourth field of a P line's name and in a W line's start column.
  Nothing in such a line tells a counter from a start, and the tool reads
  a start. It refuses the graph where two blocks' stretches then overlap,
  with a message that says this. A block alone, or blocks that don't
  collide, are placed at their counter, which is false. The fourth field
  of a haplotype clipped out of a Minigraph-Cactus GBZ is a start, and
  those are the graphs this reading is for

## Where a step is filed

[ADR 0001](adr/0001-step-placement.md) gives the reasons for these rules,
the alternatives tried and their measurements on pggb and
Minigraph-Cactus. "Line" below is a W or P line.

- The tool cuts each reference sequence into tiles of `tile` bp, at
  multiples of `tile` <!-- C12 -->
- **A step on a reference node** takes a pass of the reference over the
  node, its **position**, and the tile holding the pass's start
  <!-- C13 -->
- **A step on any other node** takes the tile of the last step before it
  in its line that has a position, on any sequence of the reference, or
  of the first one after it for steps that lead the line. So a step after
  a step on another sequence takes that sequence's tile, and a line with
  no step on the reference has no tile <!-- C14 -->
- **On the reference's own lines** a step takes the tile that holds its
  offset, so where the reference passes a node twice each pass lies where
  it is <!-- C15 -->
- **Which pass:** a node the reference passes once has that pass as its
  position. For a node it passes more than once, the path's last placed
  step predicts an offset: the step's own offset plus the bp the path has
  walked since, in the direction their strands agree on. The step takes
  the pass on the same reference sequence nearest that offset, the lower
  offset on a tie, or, when that sequence has none, the node's first
  pass: the pass of the reference line whose name sorts first in bytes,
  at its lowest offset <!-- C21 -->
- Placing starts at the line's first step on a node the reference passes
  once (or on any reference node when there is none) and runs outward in
  both directions <!-- C22 -->
- **`--stay`:** a run of steps that the rules above file in other tiles
  stays in the current piece, its home, when:
  - the path returns to the home tile
  - the run holds at most `stay` bp of reference nodes, none of them a
    node the reference passes once
  - each of its steps on a node the home tile's reference path holds has
    a pass there within `stay` bp of the offset the run's previous placed
    step predicts for it <!-- C23 -->
- Such a step moves to the nearest such pass, the lower offset on a tie,
  and a step on a node the home tile's reference path lacks becomes route
  interior. Any other run starts a new piece, and the reference's own
  lines are exempt. <!-- C23 --> A reference that passes each node once
  therefore gets the same rows at any `stay` <!-- C24 -->
- **Route interior:** a step the placement leaves off the reference is
  route interior, which it does only where the step's tile has no pass of
  its node: no route interior holds a node of its own tile's reference
  path <!-- C26 -->
- **A node the reference passes once is never route interior,** in any
  file the tool writes, whatever its `revisited`: a route can hold
  another tile's reference nodes, each of them a node the reference
  passes more than once. <!-- C197 --> A reader can't lean on this past
  what [the format promises](walks-format.md#what-a-reader-relies-on):
  the header names no writer, so nothing in a file with revisited nodes
  says this tool wrote it
- **A reference sample with several haplotypes,** such as `--refs HG002`
  names, makes its haplotypes' lines reference sequences of one file,
  and a node two of them pass counts as passed twice. Another path's step
  there can take a pass on either, so a path can lie wholly under one of
  them and show in no window of the other, with no departure record
- **A departure record's own steps** follow the same rules: one on no
  reference node takes the tile of the last step before it in its line
  that has a position, the leave's tile unless a step on another sequence
  of the reference comes between. <!-- C85 --> Own steps leading the next
  W line, for a record across W lines, take the tile of the first step
  after them with a position, the rejoin's unless a step on another
  sequence comes first; a record can have both, and so two tiles, the
  leave's first <!-- C86 -->

## Abridging

[ADR 0004](adr/0004-abridged-detours.md) gives the reasons and
measurements. What a file holds for a moved piece is format
([Abridged tiles](walks-format.md#abridged-tiles)).

- A piece costs a reader its routes' interior steps, each counted once
  per use, plus a quarter of all its steps, interior ones included
  <!-- C99 -->
- When a tile's pieces cost more than `--abridge-steps` interior steps,
  or its rows other than `abridged` rows, from `kind` on with their
  newlines, hold more than `--abridge-bytes` bytes, the tool moves whole
  lines' pieces out of the tile, costliest first, the fewest that bring
  the rest within both, or all of them where none do. It counts the bytes
  of the rows it keeps, not an estimate, and uncompressed, so any reader
  or check counts the same <!-- C100 -->
- A tile's detail units are numbered from 0, the costliest line first
  <!-- C131 -->
- The `blocks` unit counts toward neither budget and can be larger than
  its tile

## What the writer guarantees

The rules of [the format](walks-format.md) are checked on the files the
tool writes, and [claims7.md](departures/claims7.md) names the check for
a rule. A check is one of three kinds <!-- C151 -->:

- **build:** the tool, which fails the build where the rule doesn't hold
- **tests:** `verify()` and the other checks in `tests/walks.rs`, on
  every file the tests build <!-- C151 -->
- **files:** `verify7.py` and `claims7.py` on any file, which
  `scripts/check-walks.sh` runs in CI on every fixture under four option
  sets and on random graphs. <!-- C151 --> `spec8.py`, a reader written from the format
  page alone, runs beside them

Two checks rebuild the graph's paths from a file:

- `walks-truth.py rebuild` decodes every walk row and detail unit by the
  rules of the format page and demands every W or P line back step for
  step, the reference's own lines from their `ref` rows with their
  lengths, and no line more or fewer. <!-- C1 --> It shards by path, so
  it runs on a whole chromosome
- `scripts/graph-walks-rebuild.mjs` opens every fixture's files with
  @jbrowse/graph-walks in CI, cuts each reference sequence whole with
  every abridged piece expanded and demands every path, placement and
  departure back as the GFA states them, then cuts it again with none
  expanded and demands the same cut, each run off R as its bp
  <!-- C1 -->

What the tool checks as it writes, and what it guarantees past the
format:

- **It decodes every walk row it writes** by
  [Decoding a walk row](walks-format.md#decoding-a-walk-row), compares
  each step's handle and position, takes the row's span from them, and
  fails the build on any difference. <!-- C112 C25 --> It gives an
  abridged row the span
  of its piece's blocks. No other row's `start end` is checked at build
  <!-- C112 C25 -->
- **It reads back every `blocks` list it writes** and fails the build
  where the list differs from its piece, its blocks don't begin at the
  piece's first step on R and end at its last, or its items don't add up
  to the `abridged` row's `hapBp` <!-- C165 C171 -->
- **The container:** the header, the units, the tables and the EOF block
  partition the data file, and every unit starts and ends a gzip member
  and starts with its `#unit` line <!-- C93 -->. Each table lists every
  unit of its sequence, in file order, before it, and the directory lists
  every reference sequence <!-- C94 -->. No two units of a kind and
  sequence share a name other than `.` <!-- C136 -->
- **Extents:** every tile, detail and blocks line lies within its unit's
  `start end` <!-- C137 -->, and every departure line overlaps each bin
  it is in <!-- C89 -->
- **Records:** each record's `ownTiles` are the tiles holding its own
  steps, in the path's order <!-- C97 -->
- **Order, names and encoding:** walk rows in path order within a tile;
  tile names decimal with no leading zero; one line per detail unit;
  `#hole` lines sorted and disjoint <!-- C139 -->
- **The files are written whole:** the data file is written under a
  temporary name and renamed, then the directory likewise, so a directory
  never names a data file still being written <!-- C96 -->
- **Offsets and lengths** are the BGZF writer's u64 block starts, written
  as decimal, so a file past 2^32 bytes needs nothing different; a unit
  test writes one whose blocks start past 2^31, 2^32 and 2^40
  <!-- C98 -->

## Scale

- What the tool holds per node follows the number of segments, not their
  ids, and with `--sequences` it holds the graph's bases
  ([timing](walks-container/writer/results/node-ids.mc22.txt))
- Pieces and departure records wait for an external sort in up to 512 MB
  and 128 MB of memory and then in compressed runs in a temporary
  directory beside the output. <!-- C106 --> The sort's merge encodes the
  tiles on all cores, and the densest tiles set the peak
- [walks-container/writer/](walks-container/writer/README.md) gives the
  time, peak memory and file sizes of whole chromosomes

## Repeats in pggb graphs
<!-- background -->

- **Collapsed repeats:** pggb merges the copies of a repeat into shared
  nodes, so the reference path passes those nodes more than once, often
  megabases apart. pggb graphs have many such nodes; Minigraph-Cactus's
  GRCh38 path has none, and no walk row of HPRC v2.1's chr22 needs `@k`
  or `:k`. <!-- C142 --> Which copy a step takes is the tool's choice: the file states
  it, and the pass counts on `ref` rows and departure records let a
  viewer say where a position or a departure is one
  ([Exact and chosen](walks-format.md#exact-and-chosen))
- **Paralog jumps:** in a segmental duplication, a haplotype can step
  onto the reference nodes of a distant paralog and back. The steps after
  the jump take the paralog's tile, so a window at the haplotype's own
  locus shows the haplotype in more pieces, and a departure record for
  each jump. On Minigraph-Cactus graphs this is rare and sits almost
  entirely in low-copy repeats such as 22q11's
- **Satellite arrays:** pggb gives each haplotype a separate long path
  through thousands of tiny nodes, and the tool files all of it in the
  tile where the haplotype leaves the reference. [Abridging](#abridging)
  moves the costliest of these paths to detail units, and a viewer draws
  each as blocks until the user opens it
- **What to expect on pggb:** a window shows nearly all haplotypes whose
  sequence aligns there, except in satellites and CHM13's short arm,
  where abridged paths show as blocks until opened

## Earlier formats
<!-- record -->

- gfa-to-tabix 5.0 and later write format 8. 4.x wrote format 7, 3.x
  format 6 and 1.4 to 2.x format 5; the released readers open format 8
  alone
- [ADR 0009](adr/0009-departure-records.md),
  [ADR 0010](adr/0010-walks-unit-table.md),
  [ADR 0012](adr/0012-abridged-blocks.md) and
  [ADR 0013](adr/0013-abridged-hapbp.md) record what each format changed
  and why
- `--tile` was `--chunk` in 3.x
