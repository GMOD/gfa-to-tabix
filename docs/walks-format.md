# Walk format 8

A walk file holds the W and P lines of a GFA cut into tiles along one
reference genome, so that a reader rebuilds the paths through a region
from a few range requests to a static web host. This page specifies the
format: what a file holds, whoever wrote it.

- [Walk files in brief](walks-format-in-brief.md) gives the ideas on one
  small example, and
  [Walk files by example](walks-format-by-example.md) reads that example's
  file line by line
- [Writing walk files](walks-writer.md) covers gfa-to-tabix: its options,
  where it places steps, how it reads path names, and its checks
- [Reading walk files](walks-reading.md) covers reading a window, the
  reader programs and hosting

The first part of the page, up to the [Example](#example), is what a
file holds and how a reader decodes it. The second part,
[Rules a valid file keeps](#rules-a-valid-file-keeps), is the fine print:
limits, orders, the one text a value has, what a reader may rely on and
what it refuses or ignores.

## The format in short

- **Two files per reference sample:** the data file
  `<prefix>.<sample>.walks.gz` and its directory
  `<prefix>.<sample>.walks.gz.idx`. Together they hold every W or P line
  of the graph that steps on a node of that reference, cut into pieces
  filed under fixed tiles of that reference <!-- C116 -->
- **Text in gzip units:** the data file is tab-separated text, compressed
  as a series of units with a table of their byte ranges. A reader
  fetches the units over its window and gunzips them alone. It is not a
  Tabix file
- **A tile** holds the reference's path through it once, each distinct
  route a haplotype takes off that path once, and every other piece filed
  there as the list of routes it takes <!-- C3 -->
- **A departure record** gives a place where a path leaves the reference
  in one piece and rejoins it in another
- **An abridged piece** is one moved out of a tile too large to send
  whole into a `detail` unit, which a reader fetches on request
- **Nothing over a window is lost:** a reader rebuilds every piece of
  every path over a window from the tiles whose extents overlap it, an
  abridged piece by expanding its `detail` unit. <!-- C1 --> Each step
  sits on the pass of the reference the writer gave it, and the departure
  records give every place a path departs from the reference that the
  tiles' rows can't show <!-- C1 -->
- **Chosen positions are marked:** every node on the reference and every
  end of a departure record states how many times the reference passes
  it. <!-- C2 --> Where that is 1, the position is a fact of the graph,
  and above 1 it is the writer's choice
  ([Exact and chosen](#exact-and-chosen))
- **Which lines:** a file lists every W or P line with a step on a node
  of its reference, the lines of another reference sample included; a
  line with none has no rows in that file, and the other lines of its
  contig keep theirs. <!-- C4 --> A reader lists the haplotypes with rows
  in the file from the header without reading any tile <!-- C5 -->

![Four haplotype paths through a bubble, the walk rows for their tile, and the paths a reader rebuilds from them](figures/walks-detail.svg)

A row begins `seq start end kind`. The seven kinds, with their units and
the columns that follow:

| kind | unit | columns |
|---|---|---|
| [`ref`](#ref) | `tile` | `path fragStart hapOffset piece nsteps steps lengths passes` |
| [`nodes`](#nodes) | `tile`, `detail` | `ids lengths` |
| [`route`](#route) | `tile`, `detail` | `entry interior exit` |
| [`walk`](#walk) | `tile`, `detail` | `path fragStart hapOffset piece nsteps startHandle choices` |
| [`abridged`](#abridged) | `tile` | `path fragStart hapOffset piece nsteps hapBp detail` |
| [`blocks`](#blocks) | `blocks` | `path fragStart piece list` |
| [`departure`](#departure) | `departures` | `path hapStart ownBp missingBp leavePos leaveStrand leavePasses rejoinPos rejoinStrand rejoinPasses ownTiles` |

### Terms

- **Line:** a W or P line of the GFA. A **contig** is the sequence a
  line is a stretch of, which its `path` names, and several lines can be
  stretches of one contig
- **The reference:** the paths a file's `ref` rows are cut from: one or
  more whole haplotypes of the `#reference` sample
  ([Whole haplotypes](#whole-haplotypes)) <!-- C157 -->
- **Reference sequence:** one path of the reference, such as
  `GRCh38#0#chr22`. Its length is where its last line ends, which its
  table's `#unit` line states <!-- C9 -->
- **Tile:** the `tile` bp of a reference sequence from a multiple of
  `tile`, and the unit holding the rows of the pieces filed there
- **Piece:** a run of a line's steps in one tile. `piece` numbers the
  pieces along one line from 0, on whichever reference sequence each is
  filed <!-- C16 -->, so a reader keys a piece by `path`, `fragStart` and
  `piece`, and joins consecutive pieces back into one walk
- **R:** a tile's reference path, its `ref` rows' steps joined in offset
  order. A **position** is an index into R: one pass of the reference
  over a node. A step is **placed** on a reference sequence where its row
  gives it a position there
- **Span:** a piece's stretch of its reference sequence, from the first
  base its steps placed on R cover to the last, over all of them
  <!-- C10 -->
- **Extent:** a unit's `start end`, or a departure line's
- **Own steps:** a departure record's path's steps strictly between its
  leave step and its rejoin step <!-- C11 -->

## Files and units

The data file is a series of units, then a BGZF EOF block. <!-- C28 -->
Each unit is a whole run of BGZF members, the gzip members of at most
64 KiB that the SAM specification defines: it starts and ends a member
<!-- C29 -->, so a reader fetches a unit by its byte range and gunzips it
alone, and `zcat` reads the whole file as text. Fields are separated by
tabs; the examples on this page align their columns with spaces.

![The walk file of walks-schematic.gfa, built with --tile 30, read for chr1:31-60: the .idx line giving chr1's table at bytes 854-1003, the data file as a bar of its units with their byte offsets, the header, tile 0, departures 0-30, tile 30, departures 30-60, tile 60, departures 60-90 and the table, with tile 30 and departures 30-60 shaded as the one request for bytes 406-632, then the ref, route, walk and departure rows of those two units](figures/walks-bytes.svg)

The header unit is first, from byte 0, and `#walks` is its first line.
<!-- C30 --> Every other unit starts with a line
`#unit seq start end kind name` <!-- C34 -->:

| kind | `start end` | `name` | holds |
|---|---|---|---|
| `tile` | the tile's extent | the tile's start, a multiple of `tile` in decimal with no leading zero | its `ref`, `nodes`, `route`, `walk` and `abridged` rows |
| `departures` | the bin | `.` | the departure records of one bin |
| `detail` | from the first base its walk rows' spans cover to the last | `cs:d`, the tile's `name` and the `abridged` rows' `detail` | one line's moved pieces in tile `cs` |
| `blocks` | from the first base its rows' blocks cover to the last | `cs`, the tile's `name` | a `blocks` row per `abridged` row of tile `cs` |
| `table` | 0 to the sequence's length | `.` | one `#entry` line per unit of the sequence |

<!-- C35 C36 C37 C38 C159 -->

- **File order:** after the header, each reference sequence in byte
  order of the names <!-- C31 -->: its `tile` and `departures` units in
  order of position, a tile at its `name` and a departure bin at its
  `start`; then its `detail` units in order of their tile's start and
  then of their number `d`, a tile's followed by its `blocks` unit; then
  its `table` unit, which lists them <!-- C32 C114 -->
- **A tile's extent** runs from the first base of its `ref` rows' steps
  to the last, over any gap between two lines of the reference.
  <!-- C40 --> A tile has the reference steps that start inside it, so
  its extent can run past the next multiple of `tile`. Readers address
  tiles by extent, never by `floor(base / tile)` <!-- C145 -->
- **Departure bins** are `tile × 8^L` bp for L from 0 to 3 (64 kb,
  512 kb, 4 Mb and 32 Mb at the default tile), each at a multiple of its
  size. <!-- C43 --> A record's line is in every bin of its cover, a run
  of bins end to end over its line's `start end`
  ([Units and their order](#units-and-their-order)), and no other, the same text in each,
  tags included, and a reader drops exact duplicates. <!-- C88 --> So the `departures` units that overlap a
  window hold every record whose line overlaps it <!-- C88 -->
- **A table** lists each unit of its sequence before it, in file order,
  as `#entry seq start end kind name offset length`: the unit's `#unit`
  columns, then its byte offset and length in the data file, compressed.
  <!-- C45 --> Entries are not sorted by `start`, so a reader scans a
  table and doesn't bisect it
- **Later additions:** a reader ignores a tag, a header line or a `#`
  directory line it doesn't know, and skips a unit of a kind it doesn't
  know ([Later additions](#later-additions))

### The directory

`<prefix>.<sample>.walks.gz.idx` is plain text, and is not a `.tbi` or
`.gzi` index:

```
#walks  format:i:8  tile:i:65536  …  bytes:i:<data file length>
#header  0  <length>
GRCh38#0#chr22  <offset>  <length>
```

- **Line 1** is the data file's `#walks` line, plus `bytes:i:` with the
  data file's length <!-- C47 -->
- **`#header 0 <length>`** is the header unit
- **One `seq offset length` line per reference sequence** gives its
  table. Every reference sequence is listed, in file order <!-- C48 -->

A reader opens the directory, the header unit and the table of the
sequence it shows, then fetches the `tile` and `departures` units whose
extents overlap its window ([Reading a window](walks-reading.md#reading-a-window)).

## Header

The header unit's lines start with `#`, here the first of HPRC v2.1's
GRCh38-referenced file:

```
#walks  format:i:8  tile:i:65536  revisited:i:0  stay:i:311  abridge:i:1000000  abridgebytes:i:3000000  graph:Z:c9aa0d5f6907f27c  leftout:i:1698
#reference  GRCh38
#haplotype  CHM13#0
#haplotype  HG00097#1
```

The `#walks` line is `#walks` and then tags alone, written
`NAME:T:value` as in SAM, in any order: a reader finds a tag by its name.

| Tag | Meaning |
|---|---|
| `format:i:8` | This format. Required |
| `tile:i:` | The tile size in bp. Required |
| `revisited:i:` | How many nodes the reference's paths pass more than once, all its sequences counted. 0 means every position in the file is a fact of the graph ([Exact and chosen](#exact-and-chosen)) |
| `graph:Z:` | A hash of the GFA's segments, the one the full-resolution [node and link index](index-format.md#what-the-file-holds) of the same GFA states ([Header rules](#header-rules)) |
| `leftout:i:` | How many of the GFA's W and P lines with a step visit no node of the reference, and so have no piece in the file |
| `stay:i:` `abridge:i:` `abridgebytes:i:` | The writer's settings ([options](walks-writer.md#options)); 0 means none. A reader ignores them |

<!-- C50 -->

| Line | Meaning |
|---|---|
| `#reference sample` | The reference sample: the `path` of each reference sequence up to its first `#`. A file has one `#reference` line, however many haplotypes or sequences its reference has |
| `#haplotype name` | What each path with `walk` or `abridged` rows in the file is listed under, once each in byte order |
| `#hole seq start end` | Each stretch of a reference sequence that no line of the reference covers, between its lines and before its first, as a clipped haplotype has. A window inside one has no reference sequence there, and a hole is not a departure of any haplotype |

<!-- C157 C51 C52 -->

A path is **listed under** its `path` up to the second `#`, its PanSN
`sample#haplotype`; with one `#`, its text up to that `#`, the sample;
with none, its whole name. <!-- C188 --> A path's **sample** is its
`path` up to the first `#`, or its whole name <!-- C188 -->

## Rows

Every line not starting with `#`, in a unit of a kind this page gives,
begins `seq start end kind`: the reference sequence, the stretch of it
the line is about, 0-based and half-open as in BED, and its kind.
<!-- C54 --> `start end` are data, not an index key, so `zcat | grep`
places any line.

| kind | `start end` |
|---|---|
| `walk` | the piece's span: the first base its steps placed on R cover to the last, over all of them. Route interiors that hold another tile's reference nodes, which a file with `revisited:i:0` has none of, lie outside it |
| `abridged` | the piece's span, as a `walk` row's and as its `blocks` row's |
| `blocks` | the piece's span: from the first base its blocks cover to the last |
| `ref`, `nodes`, `route` | the unit's extent: these rows describe the unit, not a piece |
| `departure` | from the first base of its leave or rejoin node, whichever is first, to the last base of the other |

<!-- C55 C56 C57 C58 C160 -->

**A step** is written as a handle, `2 × id + r`, with `r` 1 for the
reverse strand: `>4` is `8` and `<4` is `9`. Commas separate the items of
a list within a column, and an empty list is `.`. A list of handles is
written as delta tokens: each token is `2 × (id − previous id) + r`, and
the first token's previous id is 0 unless a row says otherwise.
<!-- C60 --> A difference can be negative, so a reader splits a token `t`
by rounding down: the difference is `floor(t / 2)` and `r` is
`t − 2 × floor(t / 2)`. The token `-5` is a difference of −3 on the
reverse strand. A token can reach 2^32 either side of 0, so a 32-bit
shift is not enough to split one.

A tile lists its `ref` rows, then at most one `nodes` row, then its
`route` rows, then its `walk` rows, then its `abridged` rows.
<!-- C59 --> A decoder needs that order as it needs a column. A `walk`
row decodes alone, whatever the order of the tile's `walk` rows
([Row rules](#row-rules)).

**A piece** is a `ref`, `walk` or `abridged` row, and those rows start
with the same five columns:

| Column | Meaning |
|---|---|
| `path` `fragStart` | the line the piece is cut from: `path` is the sequence the line is a stretch of, and `fragStart` the 0-based offset on that sequence of the line's first base ([Path names](#path-names)) |
| `hapOffset` | where the piece starts on that sequence |
| `piece` | the piece's number along its line, from 0 |
| `nsteps` | how many steps the piece has, on R or off it |

### ref

```
seq start end ref path fragStart hapOffset piece nsteps steps lengths passes [SQ:Z:bases]
```

- One row per piece of the reference's own lines in the tile, so usually
  one, at least one per tile, and all of them pieces of the tile's
  sequence <!-- C61 -->
- `steps` is the piece's handles as delta tokens, the first from 0
- `lengths` lists each step's node length in bp <!-- C146 -->
- `passes` lists for each step the number of steps on its node in the
  `ref` rows of the whole file, every tile of every sequence counted, or
  is `.` exactly when every one is 1. <!-- C62 --> So a 1 says that no
  other `ref` row step of the file is on the node
- **R**, the tile's reference path, is every `ref` row's steps joined in
  `hapOffset` order. <!-- C63 --> Positions in R count from 0, and each
  has its offset on the sequence from its row's `hapOffset` and the
  lengths before it <!-- C63 -->

### nodes

```
seq start end nodes ids lengths [SQ:Z:bases]
```

- The nodes the unit's route interiors visit, in ascending id order, and
  no other: `ids` gives each id as the difference from the one before,
  the first from 0, and `lengths` their lengths in bp. <!-- C64 --> A
  tile or detail unit has its `nodes` row exactly when a route has an
  interior step <!-- C64 -->
- `SQ:Z:`, where a writer adds bases, holds the nodes' bases joined in
  the same order, as the S lines give them. On a `ref` row it holds the
  steps' nodes' bases in step order, each forward as its S line gives it,
  whatever the step's strand <!-- C65 -->

### route

```
seq start end route entry interior exit
```

- A route is a way a piece leaves R: `entry`, the handle on R it leaves
  from; `interior`, the steps off R; and `exit`, the handle on R it
  returns to. `entry` and `exit`, where given, are on R <!-- C128 -->
- `entry` or `exit` is `.` for a route that starts or ends the piece off
  R, and such a route has an interior step. `interior` is `.` for a route
  straight from one part of R to another, such as a jump over the
  reference or between repeat copies <!-- C66 -->
- All three columns are delta tokens chained through the unit's route
  rows: a token's previous id is the id of the token before it, across
  columns and rows, and the unit's first route row starts from 0
  <!-- C67 -->
- A route's id is its row's index among the unit's route rows, from 0
- A route's **flip** is its reverse: each handle flipped, the interior
  reversed, entry and exit swapped. <!-- C68 --> A route and its flip are
  one route, which a tile or detail unit lists once <!-- C68 -->

### walk

```
seq start end walk path fragStart hapOffset piece nsteps startHandle[@k] choices
```

- One row per piece of every other line, the other references' included
  <!-- C147 -->
- `startHandle` is the piece's first handle on R, absolute; every piece
  has one <!-- C69 -->
- `choices` lists the routes the piece takes in order, `.` for none. Each
  token is `2 × (route id − previous route id) + flip`, the first from 0,
  where flip 1 means the piece takes the route the other way round
  <!-- C148 -->
- The walk continues along R only where R's next position is the step's,
  and otherwise takes a route, with an empty interior if need be; after
  its last route it follows R until it has `nsteps` steps <!-- C71 -->

Where R holds a node more than once, a `k` names an occurrence of the
node, counting R's positions that hold it, in either orientation, from 0.
A choice token may end `:k`, then `@k`, both optional and `k` a number,
as `-10:1@2`. A suffix is written only where it differs from its default
<!-- C70 -->:

| Written | The occurrence | Its default |
|---|---|---|
| `startHandle@k` | the piece starts on | R's first |
| `:k` on a choice | of the entry's node, that the walk leaves R from | the first one where stepping along R, from where the walk last landed, reads the entry |
| `@k` on a choice | the route's exit lands on | the one nearest the entry's position in R, counted in positions, the later on a tie |

<!-- C70 -->

A route with no entry takes neither suffix and one with no exit takes no
`@k`. A reference that passes every node once has no `@k` or `:k`
<!-- C70 -->

### Decoding a walk row

R's step from position `i` holding handle `h` goes forward when
`R[i] = h`, to `R[i+1]`, and backward otherwise, to `R[i−1]` flipped.
Each route below is taken the way round its flip says. <!-- C141 -->
Every handle on R is emitted with its position in R, and so with its
offset and pass. <!-- C141 -->

In this order:

- If the first route has no entry, emit its interior. Its exit is
  `startHandle`, which the next step emits: the handle is emitted once
- Emit `startHandle`, at occurrence `k` of its node in R with `@k`, else
  at the first
- For each route with an entry <!-- C141 -->:
    - step along R, emitting each handle, until the current handle is the
      route's entry, or with `:k` until the position is occurrence `k` of
      the entry's node
    - emit the interior
    - with no exit, stop: the piece ends off R
    - emit the exit, at occurrence `k` of its node in R with `@k`, else
      at its node's occurrence nearest the current position in R, counted
      in positions, the one at the higher position on a tie
- Step along R until the piece has `nsteps` steps

<!-- C141 -->

The row's `start end` is the span of the positions it decodes to.
<!-- C25 -->

### departure

```
seq start end departure path hapStart ownBp missingBp leavePos leaveStrand leavePasses rejoinPos rejoinStrand rejoinPasses ownTiles
```

A record for each place a path other than the reference's own departs
from a reference sequence that its walk rows can't show: where two of
its steps placed on the sequence, with none placed on it between them,
are not adjacent there at the passes they took and lie in different
pieces. <!-- C77 --> A departure inside
one piece has no record: a reader computes it from the piece's steps
([ADR 0009](adr/0009-departure-records.md)). <!-- C77 -->

![The W lines of a GFA where HG002#1 leaves GRCh38 after node 2 and rejoins at node 6 across the tile edge at 30 bp; the walk file read for chr1:1-60: the .idx line, chr1's table with two tiles and two departure bins, and those four units, the departure line highlighted in both bins; and the graph graph-walks cuts for chr1:1-60 drawn by bandage-core, HG002 running from node 2 through its node 7 below the row to node 6, 25 bp shorter than GRCh38](figures/walks-leave-figure.svg)

| Column | Meaning |
|---|---|
| `path` | the path that departs. A contig's lines count as one path, in start order |
| `hapStart` | where the path's own sequence between the ends starts on its contig, right after the leave step |
| `ownBp` | how far that sequence runs, 0 for a direct jump: every base between the ends, on nodes of the path's own, on the reference's other sequences, in lines with no step on this one, or in no line |
| `missingBp` | the part of `ownBp` between two lines of the contig, which the graph lacks |
| `leavePos` `rejoinPos` | the end's breakpoint, where the path's sequence stops following the reference sequence: the node's end for a leave step along the sequence, its start for one against it, and the other way round for the rejoin |
| `leaveStrand` `rejoinStrand` | `+` or `-`, for an end step along or against the sequence's orientation at its pass |
| `leavePasses` `rejoinPasses` | how many times the reference's paths pass the end's node, as on a `ref` row. Above 1, the end's pass is the writer's choice, and so is the departure |
| `ownTiles` | the names of the tiles of the sequence that hold the record's own steps, comma-separated, or `.` for none |

<!-- C78 C79 C80 C84 -->

- **The ends** are steps placed on the sequence: the leave is the step
  before the departure and the rejoin the step after, in the path's
  order. A step in a route interior is not placed, though its node can be
  a node of the sequence where the reference passes it more than once.
  The leave step is the last step on R of its piece and the rejoin step
  the first on R of its piece <!-- C74 C138 -->
- **Per reference sequence:** a sequence's records are of the path's
  steps placed on it, in order, with its steps on the reference's other
  sequences counted as its own sequence <!-- C78 -->
- **Adjacent steps:** two such steps, one after the other, are adjacent,
  and depart nowhere, when `ownBp` is 0, the strands are equal and the
  breakpoints are equal, [holes](#header) removed <!-- C81 -->
- **A path's ends:** a contig's sequence before its first step on the
  sequence or after its last is no departure and has no record.
  <!-- C82 --> The piece holding that step shows where the path comes
  from or goes on, as a route with no entry or no exit, and a piece on
  another sequence holds its steps there, which no row of this one points
  to
- **`start end`** runs from the first base of the record's end nodes,
  each the end step's own node at its pass, to the last base of the other
  <!-- C83 -->
- **`ownTiles`** is in the path's order, each tile once, where the path
  first has an own step in it. <!-- C84 --> A piece has a step on R, so
  those steps are in the leave step's piece or in the rejoin step's
  piece: `ownTiles` is the leave's tile, the rejoin's tile, the two in
  that order, or `.` <!-- C85 C86 -->. Own steps on the reference's other
  sequences lie in those sequences' tiles, and own steps in a line with
  no step on the reference, and own sequence in no line, are in no tile;
  `ownTiles` lists none of them <!-- C87 -->
- **No column names the kind of departure.** Strands that differ are a
  strand switch. Otherwise the path jumps back, over reference it walks
  again, when `rejoinPos < leavePos` for a `+` leave or
  `rejoinPos > leavePos` for a `-` leave; equal breakpoints are sequence
  of its own between adjacent steps; and any other case is a jump
  forward. Positions compare with the holes before them removed

## Abridged tiles

A writer can move pieces out of a tile that would cost a reader too much
to read whole, as in a satellite array. Which pieces it moves is its
policy ([Abridging](walks-writer.md#abridging)); what the file then holds
is format:

- The tile keeps its `ref` rows, its other pieces' `nodes`, `route` and
  `walk` rows, encoded without the moved pieces, and an `abridged` row
  per moved piece <!-- C101 -->
- The moved pieces' rows go to a `detail` unit `cs:d` of the tile's
  sequence, `cs` the tile's name and `d` the unit's number. One line's
  moved pieces in one tile share one detail unit, one unit per line: a
  contig with two lines there has two. <!-- C76 --> A reader reads a
  detail unit only when it expands that path <!-- C150 -->
- A detail unit holds at most one `nodes` row, one exactly when its
  routes have an interior step, then `route` rows and `walk` rows.
  <!-- C102 --> Its routes are numbered from 0 and their tokens chained
  from 0, as for a tile of its own, and its walk rows decode against the
  R of tile `cs` <!-- C103 -->
- The tile's `blocks` unit gives where on R the moved pieces lie. A
  reader reads it to draw a moved piece it doesn't expand, and for
  nothing else: a moved piece's span, its stretch of its contig and a
  departure record's own run in it are in the `abridged` rows and the
  records

### abridged

```
seq start end abridged path fragStart hapOffset piece nsteps hapBp detail
```

- One row per moved piece, in place of its walk row, with the leading
  columns of that walk row. A reader keys it by `path`, `fragStart` and
  `piece` as it does a walk row, so every piece of a line has one row in
  its tile, walk or abridged <!-- C72 -->
- `start end`, `hapOffset` and `nsteps` are the piece's, as its walk row
  states them. <!-- C73 --> From `nsteps` a reader learns the cost of
  expanding the piece before it reads the detail unit <!-- C75 -->
- `hapBp` is the sum of the lengths of all the piece's steps, on R or
  off it, and at least 1. <!-- C167 --> The piece covers the half-open
  stretch `[hapOffset, hapOffset + hapBp)` of its contig, forward along
  the contig whichever way its steps run <!-- C167 -->. It is not a
  length on the reference: a piece that walks four 10 bp nodes of R, 7 bp
  of its own and the four nodes back has a span of 40 bp and a `hapBp`
  of 87
- `detail` is the number `d` of the detail unit `cs:d` that holds the
  piece's walk row. A tile's detail units are numbered from 0 with none
  missing <!-- C131 -->; which line takes which number is the writer's
  choice
- **The three rows agree.** `hapBp` is the bp of the detail walk row's
  steps and the sum of the `blocks` row's items, and the `blocks` list is
  what that walk row decodes to, with each run off R as its bp
  <!-- C167 C164 -->

### blocks

```
seq start end blocks path fragStart piece list
```

One row per `abridged` row of a tile, in the `blocks` unit named by the
tile's name. A reader matches the two by `path`, `fragStart` and
`piece`, and the unit lists its rows in the tile's order of them. A tile
with no `abridged` row has no `blocks` unit <!-- C161 -->

`list` is the piece in path order, with its steps gathered into two
kinds of item:

- **A block,** `<d><+|-><len>`: a run of consecutive steps on R, where a
  step begins where the one before ended and they all run one way. It
  covers a half-open stretch `[lo, hi)` of the sequence, of `len` bp. `+`
  is along R, from `lo` to `hi`, and `-` is against R, from `hi` to `lo`.
  `d` is where the block begins, less where the block before ended, or
  less 0 for the first. A reader splits a block at its first `+` or `-`
  after its first character
- **A run off R,** a bare number: the bp of consecutive steps with no
  place on the tile's R. It doesn't move where the next `d` counts from

R is `>1>2>3>4>5>6`, six nodes of 6 bp in one tile, and a piece walks
`>12>1>2<2<1>11>5>6>3>13>14`, where nodes 11 to 14 are off R, of 10, 7,
20 and 30 bp:

```
#unit  R#0#c  0  36  blocks  0
R#0#c  0  36  blocks  H#1#c  0  0  7,0+12,0-12,10,24+12,-24+6,50
```

| Item | Reads as |
|---|---|
| `7` | node 12, before the piece's first step on R |
| `0+12` | nodes 1 and 2 along R, from 0 |
| `0-12` | back over 2 and 1 against R: it covers `[0, 12)` and begins at 12, where the block before ended, so `d` is 0, and it ends at 0 |
| `10` | node 11 |
| `24+12` | nodes 5 and 6 from 24, 24 bp on from 0, where the block before ended |
| `-24+6` | node 3 from 12, 24 bp back from 36 |
| `50` | nodes 13 and 14, after the piece's last step on R |

The items add up to 109 bp, so the piece runs from 0 to 109 on its
contig, and its `abridged` row is
`R#0#c 0 36 abridged H#1#c 0 0 0 11 109 0`: 11 steps and 109 bp, in
detail unit 0.

- Where a block begins and ends are boundaries between bases, as a BED
  `start` and `end` are. `d` is counted along the sequence whichever way
  the blocks run, so a negative `d` before a `+` block, or a positive one
  before a `-` block, is a jump back
- A block's stretch is whole steps of R: the positions of R whose
  stretches lie in it, ascending for `+` and descending for `-`, are the
  piece's steps there, which also says which pass a step is on
- Two lines of the reference that abut are one stretch to a block. Two
  with a gap between them end it, and a reader takes the `#hole` out
  before it calls the gap a departure
- A run before the first block or after the last is the piece's steps
  off R at its ends. Only a line's first piece has a leading run
  <!-- C166 -->
- A run is off the tile's R. In a file with revisited nodes it can hold
  a node of another tile's reference, so a run isn't proof of sequence
  the reference lacks; in a file that states `revisited:i:0` it holds
  none. Two rows with the same list can differ in the nodes of their runs
- A list is a chain, as UCSC's chain format and a PAF `cg` tag give one,
  except that a block has its own direction and `d` can be negative, so
  a piece that turns or jumps back stays one row

## Exact and chosen

A walk file projects the paths onto one reference. Where the reference
passes a node once, a step on it has one place, and a departure between
two such steps is a fact of the graph. Where it passes a node more than
once, the writer picks the pass, and the departures it files there follow
from the pick: on a collapsed repeat, a path that follows one copy can
show as hopping between copies.

- A file with `revisited:i:0` states every position and every departure
  as a fact of the graph, as the Minigraph-Cactus graphs do on their own
  reference <!-- C53 -->
- Otherwise each `ref` row's `passes` and each record's `leavePasses` and
  `rejoinPasses` say which steps and ends lie on such nodes.
  <!-- C120 --> A reader states a departure with an end passed more than
  once as a placement choice, not as a jump the haplotype makes
  <!-- C120 -->
- The file does not promise that a pick is the copy a haplotype came
  from. For a reference other than the graph's own, build from the graph
  built on that reference where one exists

## Example

`tests/walks.rs` builds `tests/data/walks-two-refs.gfa` with `--tile 10
--stay 0` and checks every row. <!-- C104 --> Part of GRCh38's file: the
directory, part of the tile at 0 (D's and I's walk rows left out) and two
of the departure bin 0-10's four lines, with the byte offsets and
lengths, which depend on the compressor, elided:

```
#walks  format:i:8  tile:i:10  revisited:i:0  stay:i:0  abridge:i:1000000  abridgebytes:i:3000000  graph:Z:7619ff637c3b074b  leftout:i:1  bytes:i:…
#header  0  …
GRCh38#0#chr  …  …
```

```
#unit  GRCh38#0#chr  0  12  tile        0
GRCh38#0#chr  0  12  ref        GRCh38#0#chr  0    0    0  2   2,2  6,6  .
GRCh38#0#chr  0  12  nodes      6             6
GRCh38#0#chr  0  12  route      .             13   -9
GRCh38#0#chr  0  12  walk       H#1#h         100  100  0  2   2    .
GRCh38#0#chr  0  6   walk       Q#0#chr       0    0    0  2   2    1
#unit  GRCh38#0#chr  0  10  departures  .
GRCh38#0#chr  0  18  departure  Q#0#chr       6    6    0  6   +    1    12  +  1  0
GRCh38#0#chr  0  24  departure  D#1#d         24   0    0  24  +    1    0   +  1  .
```

- R is `>1 >2`, nodes of 6 bp at 0 and 6: tokens `2` and `2` are ids 1
  and 2, forward, and R passes each once, so `passes` is `.` and every
  record's ends say 1. <!-- C104 --> The tile's extent, and so its `ref`,
  `nodes` and `route` rows' `start end`, is R's stretch, 0-12
- The one route has no entry, interior `13` (id 6 reversed) and exit
  `-9` (id 1 reversed), so it reads `<6 <1`
- Q's piece starts on `>1` (handle 2) and takes route 0 flipped, `>1 >6`
  with no exit: its steps are `>1 >6`, and its one step on R spans 0-6
- H's piece starts on `>1` and takes no route, so it follows R for its 2
  steps: `>1 >2`, spanning 0-12
- Q leaves R at 1's end, 6, walks 6 bp of its own, node 6, and rejoins
  at 3's start, 12, in a piece filed under tile 10. Its record's extent
  runs from 1's first base to 3's last, 0-18, so it lies in bins 0-10 and
  10-20. Its own step, 6, is in its piece in tile 0, so `ownTiles` is 0
- D jumps back from 4's end, 24, to 1's start, 0, over nothing of its
  own: 0-24, in the bins at 0, 10 and 20, with `ownTiles` `.`

### A reference that takes two nodes twice

`tests/data/walks-loop.gfa` has a reference that takes nodes 2 and 3
twice. Four of its W lines:

```
W  R  0  chr  0  45  >1>2>3>2>3>4
W  A  1  a    0  57  >1>2>3>2>3>2>3>4
W  E  1  e    0  47  >1>2>5>3>2>3>4
W  F  1  f    0  47  >1>2>3>2>5>3>4
```

Built with `--refs R` the graph is one tile. Its `ref`, `nodes` and
`route` rows, and the `walk` rows of A, E and F:

```
#unit  R#0#chr  0  45  tile  0
R#0#chr  0  45  ref    R#0#chr  0  0  0  6  2,2,2,-2,2,2  6,6,6,6,6,15  1,2,2,2,2,1
R#0#chr  0  45  nodes  5        2
R#0#chr  0  45  route  2        .  4
R#0#chr  0  45  route  -2       6  -4
R#0#chr  0  45  route  -1       .  3
R#0#chr  0  45  route  0        .  2
R#0#chr  0  45  walk   A#1#a    0  0  0  8  2  5:1
R#0#chr  0  45  walk   E#1#e    0  0  0  7  2  2
R#0#chr  0  45  walk   F#1#f    0  0  0  7  2  2:1
```

- R is `>1 >2 >3 >2 >3 >4`. Node 2 is at occurrences 0 and 1, the second
  and fourth positions of R, and node 3 at the third and fifth
- Route 0 is `>1` straight to `>3`, route 1 is `>2 >5 >3`, route 2 is
  `<2` straight to `<3`, and route 3 is `>3` straight to `>4`
- E takes route 1 at the first `>2` it comes to and lands on the nearest
  `>3`, the third position of R: `>1 >2 >5 >3 >2 >3 >4`
- F takes route 1 with `:1`, so it steps along R to the second `>2`
  before it leaves. Both `>3` are one position of R from there, and the
  later one is taken: `>1 >2 >3 >2 >5 >3 >4`
- A takes route 2 flipped, `>3` straight to `>2`, with `:1`. It steps
  along R to the second `>3`, lands on the nearest `>2`, the fourth
  position of R, then steps along R to the end:
  `>1 >2 >3 >2 >3 >2 >3 >4`

### With stock tools

```
awk -F'\t' -v s="GRCh38#0#chr22" '$1==s {print $2, $3}' f.walks.gz.idx   # a sequence's table
tail -c +$((off+1)) f.walks.gz | head -c $len | gzip -dc                  # any unit
zcat f.walks.gz | awk -F'\t' '$1=="GRCh38#0#chr22" && $2<20001000 && $3>20000000'
```

`tabix`, htslib's region API and pysam don't read the file.
[scripts/walks-brief.py](../scripts/walks-brief.py) is one short Python
file that prints the W and P lines back from a walk file.

## Rules a valid file keeps

A file that breaks a rule of this page is not format 8. The first part
gives what a reader needs to decode a file. These are the rest: what a
writer keeps, a checker tests and a reader refuses or ignores.

### Text

- **Lines:** every line of the data file and of the directory is fields
  separated by one tab, and ends in one newline. <!-- C206 --> No line is
  empty and no field is empty <!-- C206 -->
- **Names:** a name is one or more bytes from 0x21 to 0x7E, the printable
  ASCII characters without the space, and does not start with `#`. Every
  sequence name, every `path`, and every name a `#reference`,
  `#haplotype` or `#hole` line or a directory line states is one
  <!-- C200 -->. So two names are the same name exactly when they are the
  same bytes, and the byte order this page sorts names by is the order of
  their characters in any text encoding <!-- C200 -->. These are the
  bytes GFA 1 allows in a name, without its ban on a leading `*` or `=`
- **Numbers:** a number is decimal digits with no sign, no leading zero
  and no space, and zero is `0`: a tag's `i` value, a `start`, an
  `nsteps`, a length in a list, a byte offset, a `k`. Only a delta token, a choice token and a
  block's `d` can begin with `-`, for a value below 0, and none is `-0`
  <!-- C203 -->. So a number has one text, and two lines that state the
  same thing are the same bytes
- **Limits:** every node id is below 2^31 <!-- C126 -->. No coordinate
  is above 2^53: no `start` or `end`, no `fragStart` or `hapOffset`, no
  end of a piece on its contig, no `hapStart + ownBp`, no breakpoint and
  no byte offset or length, so a reader
  holding numbers as doubles reads each one exactly <!-- C172 C45 -->
- **Tags:** a tag's name is letters and digits and starts with a letter,
  its type is one letter, and its value holds no tab. Tags follow a row's
  fixed columns, or the stated fields of a `#reference`, `#haplotype` or
  `#hole` line, in any order. A reader ignores the ones it doesn't know,
  on a row of any kind, on those three lines and on the `#walks` line
  <!-- C195 -->. A line carries a tag name at most once <!-- C199 -->.
  `#unit` lines, `#entry` lines and the directory's lines for the header
  and the sequences take no tags

### Units and their order

- **BGZF:** a file whose units are gzip members of another kind is not
  format 8 <!-- C29 -->
- **`#unit`:** the header unit has no `#unit` line, and no line of the
  file begins `#unit` except the first line of a unit, whatever a unit of
  a later kind holds <!-- C207 -->. So the file delimits itself: a BGZF
  member begins a unit where it begins `#unit` and the member before it
  ended in a newline, and the tables can be rebuilt from the data file,
  as a `.fai` can from its FASTA
- **Order:** at one start a tile comes before the departure bins that
  start there, and smaller bins before larger <!-- C33 -->
- **Names:** a unit's `name` is the key other lines point at it by, and
  `.` where nothing points at the unit. Every other name is unique within
  its kind and sequence <!-- C39 -->
- **No unit of a kind this page gives is empty.** After its `#unit` line
  a tile holds a `ref` row, a departure bin a record, a detail unit a
  `walk` row, a blocks unit a row and a table an entry <!-- C210 -->. So
  a bin with no record is not in the file, and neither is a tile in
  which no step of the reference starts
- **Spans:** every piece's span lies inside its tile's extent, since
  every placed step is on R <!-- C41 -->
- **Departure bins:** the four sizes are format, and a file with a bin
  of another size is not format 8. A record's cover runs from
  `floor(start / tile) × tile` to `ceil(end / tile) × tile` over its
  line's `start end`, taking at each point the largest bin aligned there
  that fits <!-- C43 -->. Within a bin lines are in order of `start`,
  `end`, then text <!-- C44 -->
- **Tables:** each entry's length is above 0. <!-- C45 --> A table's
  entries tile the
  bytes from the end of the table before it, or of the header unit, to
  its own offset, with no gap and no overlap <!-- C194 -->. Every
  sequence in the file has at least one tile, so no table is empty
  <!-- C46 -->

### Header rules

- **Required tags:** a reader refuses a file whose `#walks` line lacks
  `format:i:8` or `tile:i:`, or states another format. <!-- C198 --> It
  needs no other tag: a file whose line lacks `revisited`, `stay`,
  `abridge`, `abridgebytes`, `graph` or `leftout` is format 8, and a
  reader doesn't refuse it. <!-- C201 C192 --> A tag left out states
  nothing, which is not the same as stating 0: a file with no `revisited`
  can have revisited nodes or none, and a reader takes from it nothing
  that 0 promises
- **What `format:i:8` marks:** the units, row kinds and columns of this
  page and its rules, with the orders and names they give. A file that
  breaks one, or holds a row
  kind this page doesn't give in a unit it does, is not format 8.
  <!-- C49 --> A unit kind this page doesn't give is a later addition,
  which a reader skips <!-- C123 -->
- **Types:** `graph` is `Z`, and `format`, `tile`, `revisited`, `stay`,
  `abridge`, `abridgebytes`, `leftout` and the directory's `bytes` are
  `i`, with a number for a value <!-- C204 -->
- **`tile`** is from 1 to 2^40, which keeps a departure bin of 512 tiles
  past any coordinate below 2^64 <!-- C205 -->
- **`bytes`** is the directory's: the data file's `#walks` line carries
  no `bytes` tag <!-- C211 -->
- **`stay`, `abridge` and `abridgebytes`** bind no row: a file that
  states `abridge:i:0` and `abridgebytes:i:0` and holds `abridged` rows
  is format 8, and so is one with a tile that costs more than a budget
  it states <!-- C202 -->
- **`graph`** is FNV-1a 64 over each S line's id as written, a byte 0xff
  and the length of its sequence, or of its last `LN:i:` where the
  sequence is `*`, as 8 bytes little-endian, summed over the S lines
  modulo 2^64 and written as 16 lowercase hex digits. <!-- C190 --> An S
  line whose sequence is `*` and that has no `LN:i:` hashes 2^64 − 1 for
  its length. The value is the same whatever order the S lines come in.
  <!-- C190 --> It names the set of segments: two GFAs with the same
  segments and other links or paths share it, and an index of a folded
  graph states the folded graph's
  ([ADR 0015](adr/0015-walk-files-name-their-graph.md#consequences))
- **`leftout`** does not count a line whose every step is on a segment
  of 0 bp, which has no step <!-- C191 -->
- **No writer, no version:** the header names neither. A file's rows
  depend only on the GFA and the options it was written with, and its
  bytes also on the compressor, so a writer release that changes no row
  and not the compression leaves every file as it was <!-- C193 -->
- **`#reference`** names a sample and not a haplotype, so a file whose
  line names `HG002#1` is not format 8 <!-- C157 -->
- **`#hole`** lines have `start` below `end` and are in order of sequence
  name in bytes and then start, no two of a sequence overlapping
  <!-- C52 -->

### Path names

- For a W line, `path` and `fragStart` are its `sample#haplotype#contig`
  and its start column, and for a P line what its name reads as, by the
  three steps of [Path names](walks-writer.md#path-names) and no other
  rule <!-- C158 -->
- A `path` is final: a reader takes it whole and reads no start, range
  or field out of it, whatever its text looks like <!-- C180 -->

### Whole haplotypes

The reference is one or more whole haplotypes of the `#reference`
sample. Take what a reference sequence is listed under: no path with
`walk` or `abridged` rows is that text, or begins with that text and a
`#`, and no `#haplotype` line is or begins so. <!-- C157 C51 --> A reader
tells the reference's lines from the others by that prefix, so:

- a file with reference sequences `HG002#1#chr1` and `HG002#1#chr2` and
  walk rows of `HG002#1#alt1` is not format 8
- where a reference sequence has no haplotype field, as `chm13#chr1`,
  which is listed under `chm13`, no path of its sample has `walk` or
  `abridged` rows: `chm13#2#chrX` begins `chm13#`
- beside a reference sequence `HG002#1#chr1`, a path named `HG002#1`
  whole has no `walk` or `abridged` rows, and any other path of two
  fields, as `HG002#alt`, can
- the reference need not be every haplotype of its sample. <!-- C9 --> It
  can be `HG002#1` alone, and a path of `HG002#2` is then a line like any
  other, with `walk` rows, departure records and a `#haplotype` line

### Row rules

- **Order in a tile:** after the order by kind ([Rows](#rows)), its
  `ref` rows are in `hapOffset` order, and each piece's steps start in
  `[name, name + tile)`. <!-- C127 --> Its `walk` rows are
  in order of `path` in bytes, then `fragStart`, `hapOffset` and `piece`,
  so the first walk to take a route is the same for any reader
  <!-- C125 -->. Its `abridged` rows are in order of `detail`, then
  `hapOffset`
- **Route order** compares two routes, or the two ways round of one, by
  `entry`, then `interior`, then `exit`. An `entry` or `exit` that is `.`
  comes before any handle, and handles compare as integers. Two interiors
  compare handle by handle from the first, and where one is the start of
  the other the shorter comes first, an empty one before any
- **A unit's route rows** are in order of the first position in R of
  their entry's or exit's node, whichever is first, then in route order
  <!-- C129 -->. A route is stored the way round that comes first in
  route order, so no route row's flip comes before it <!-- C68 -->
- **One encoding of a walk row:** a `@k` or `:k` is written only where
  it differs from its default, and flip is 0 on a route that is its own
  flip, as `>2 . <2` is, a turn on node 2. <!-- C70 --> So a row that names a default,
  as `startHandle@0` does, or takes such a route with flip 1, is not
  format 8 <!-- C70 -->
- **`ref` rows and departures:** the `ref` rows of a sequence hold one
  node ending at a `+` leave's or `-` rejoin's breakpoint and one
  starting at the other kind's <!-- C91 -->
- **A `blocks` list:** a block is as long as its steps allow and a run holds all the steps off R between two blocks,
  so no two blocks in a row join and no two runs stand side by side. A
  list has a block, and no run of 0 bp <!-- C162 -->. The items add up to
  the piece's bp, its `abridged` row's `hapBp` <!-- C163 -->. Its
  grammar, in ABNF:

  ```
  list   = item *( "," item )
  item   = block / run
  block  = d sign len
  d      = "0" / [ "-" ] number
  sign   = "+" / "-"
  len    = number
  run    = number
  number = %x31-39 *DIGIT   ; a number as Text writes one, above 0
  ```

  `d` is never `-0`, a `len` or a run is at least 1, and an item of
  digits alone is a run <!-- C170 -->
- **The attach rule.** A departure record's own steps in a piece of its
  path filed on its sequence are the piece's steps within
  `[hapStart, hapStart + ownBp) ∩ [hapOffset, hapOffset + hapBp)`, both
  stretches of the path's contig. <!-- C169 --> Where that is not empty
  it is one run of steps off R at one end of the piece, and never the
  whole piece: the steps after the piece's last step on R, where that
  step is the record's leave, or the steps before its first, where that
  step is the record's rejoin. <!-- C169 --> So it is the whole trailing
  run of the piece's `blocks` list or its whole leading run, and a reader
  has its place and its bp from the `abridged` row and the record without
  reading the list <!-- C169 -->

### What a reader relies on

The format is what holds of any file that says `format:i:8`, whoever
wrote it: the rules of this page, with the orders and names they give,
which the file checks read off a file
([claims7.md](departures/claims7.md)). A reader may build on them, and
on nothing else about how a file was made. The ones a reader leans on
most:

- **Positions are stated.** A walk row decodes by
  [Decoding a walk row](#decoding-a-walk-row) to its piece's steps, each
  on R at a stated position or off R, so a reader never chooses a pass
  <!-- C25 -->
- **In a file that states `revisited:i:0`, a step on a reference node is
  on R.** No route interior, of a tile or of a detail unit, on any
  sequence of the file, holds a node the reference passes once, which in
  such a file is every node a `ref` row steps. <!-- C27 --> So a line of
  the file that steps a reference node has a row, `ref`, `walk` or
  `abridged`, in the tile whose `ref` rows hold that node, and the tiles
  a window's read selects hold a row of every line of the file that steps
  a reference node over the window. <!-- C27 --> From those tiles' rows
  and their `blocks` rows a reader can say how many of the file's
  haplotypes step such a node. That counts the lines the file holds:
  whether it holds every line of its graph that steps the reference is
  checked against the GFA and is not read off the file <!-- C4 -->
- **Any other file makes no such promise.** Where `revisited` is above
  0, or the header states none, a route interior can hold a node the
  reference passes once, and the tiles over a window can then lack a line
  that steps it
  ([ADR 0016](adr/0016-format-8-is-frozen.md#the-ruling-on-c27)).
  `passes` still says which nodes the reference passes once. A departure
  there can pass over a once-passed node its line steps, so two ends
  passed once do not make its own sequence free of reference nodes
- **A step is 1 bp or more.** Every length a `ref` or `nodes` row states
  is at least 1, so no two positions of R start at one offset and no
  piece covers 0 bp of its contig <!-- C208 -->
- **R ascends.** No two `ref` rows of a sequence cover a base twice, so
  the positions of a tile's R, in order, start at ascending offsets, and
  a reader finds the position at an offset by bisection <!-- C209 -->
- **A line's pieces tile it.** They are numbered from 0, piece 0 starts
  at `fragStart`, and each piece ends on its contig where the next
  begins, on whichever sequence that piece is filed: a walk row's after
  its steps' bp, an abridged row's at `hapOffset + hapBp`.
  <!-- C16 C163 C168 --> The last piece ends where the line does
  <!-- C168 -->

What a writer chooses, and two writers of format 8 can choose
differently with no reader the wiser:

- **Placement:** which pass a step takes where the reference passes its
  node more than once, and so where a line is cut into pieces. The
  `passes` columns say where a position is such a choice
- **Which pieces a tile abridges,** and the order it numbers their
  detail units in. A reader finds a detail unit by the `detail` its
  `abridged` row names
- **The header's `stay`, `abridge` and `abridgebytes` tags** record
  gfa-to-tabix's settings for a person reading the file
  ([Writing walk files](walks-writer.md))

### What a reader refuses

- A directory whose line 1, its tab-separated fields without the
  `bytes:i:` one, differs from the header unit's `#walks` line, or whose
  `bytes` differs from the data file's length, as a server's
  Content-Range gives it. A reader that can't learn the length skips the
  length check <!-- C122 -->
- A unit whose `#unit` line doesn't state its table entry's
  `seq start end kind name`, or whose text doesn't end in a newline, as a
  unit cut short does <!-- C154 -->
- A row of a unit that belongs to another sequence, or is of a kind its
  unit doesn't hold: a tile holds `ref`, `nodes`, `route`, `walk` and
  `abridged` rows, a departure bin `departure` rows, a detail unit
  `nodes`, `route` and `walk` rows, a blocks unit `blocks` rows
  <!-- C155 -->
- A table that doesn't start with its own
  `#unit seq 0 <sequence length> table .` line, or holds a line that isn't an `#entry`. A reader can tell a
  missing entry by the gap it leaves in the bytes the entries tile, and
  may refuse the table <!-- C156 -->

A reader need not detect a file that is not format 8. Past this list and
the header's required tags it may read a file that breaks a rule as if
it kept it: @jbrowse/graph-walks opens a file that states `tile:i:0`,
writes a number `0100` or holds a space in a name. What holds a file to
this page is the file checks, run by whoever writes or hosts it
([What the writer guarantees](walks-writer.md#what-the-writer-guarantees)).

### Later additions

Later additions are tags, header lines, unit kinds or files, and a reader
of format 8 reads a file that has them as it reads one that doesn't
<!-- C124 -->:

- a reader ignores a tag it doesn't know, and a header line whose first
  word it doesn't know, which follows the `#walks` line. It ignores a
  directory line that starts with `#` and a word it doesn't know
- a reader skips a unit of a kind it doesn't know, whatever rows it
  holds. Its `#entry` carries its sequence and integer
  `start end offset length` like any other. A later unit of a sequence
  lies before that sequence's table and is listed there <!-- C196 -->, so
  a unit about no sequence is a file of its own
- an addition doesn't change what a row this page gives means, so a
  reader that ignores it draws nothing false. A change that can't keep to
  that is another format
- only this page gives a unit kind, a row kind, a header line word or a
  tag name a meaning in format 8. <!-- C124 --> A file that holds a unit
  kind, a header line word or a tag name the page doesn't give, or a row
  kind it doesn't give in a unit of such a kind, is format 8 still, and
  what it means there is not the format's. A later kind, of unit or of
  row, takes a word that is no kind of unit or row here
- a file with no unit of a later kind says nothing by lacking it, since
  it can predate the addition. An addition whose units claim to be
  complete says in the header what they are complete over, and a reader
  takes completeness from that statement and from no unit's absence
- a file added beside a walk file is about that walk file's bytes: the
  same rows compressed again are another file to it
  ([Hosting](walks-reading.md#hosting))
