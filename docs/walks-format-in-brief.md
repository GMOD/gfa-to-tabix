# Walk files in brief

A walk file holds the W and P lines of a GFA, arranged by where they lie on
one reference path, so that a viewer can fetch the haplotype paths through a
window of that reference with a few HTTP range requests.

[walks-format.md](walks-format.md) is the specification, and it is the
authority wherever this page is less exact.

[scripts/walks-brief.py](../scripts/walks-brief.py) implements this page in
about 150 lines of Python and prints every W and P line back from a walk
file.

## One small file

Every example below comes from one small graph,
[walks-schematic.gfa](figures/walks-schematic.gfa), which has a 90 bp
reference of nine 10 bp nodes. CHM13 takes node 10 in place of node 5, and
HG002 takes the 5 bp node 11 in place of nodes 4 to 6:

```
W  GRCh38  0  chr1  0  90  >1>2>3>4>5>6>7>8>9
W  CHM13   0  chr1  0  90  >1>2>3>4>10>6>7>8>9
W  HG002   1  chr1  0  65  >1>2>3>11>7>8>9
```

```bash
gfa-to-tabix walks-schematic.gfa --walks --refs GRCh38 --tile 30 -o hprc
```

The command writes `hprc.GRCh38.walks.gz`, which is text lines in gzip
blocks, and `hprc.GRCh38.walks.gz.idx`, a small text directory of byte
ranges. `--tile 30` cuts the reference every 30 bp, so this example has
three tiles; the default is 65536.

The figure shows the graph under its tiles, the two files, and the one byte
range a viewer fetches for chr1:31-60:

![The walk file of walks-schematic.gfa, built with --tile 30, read for chr1:31-60: the three tiles over the graph, the .idx line giving chr1's table at bytes 854-1003, the data file as a bar of header, tile 0, departures 0-30, tile 30, departures 30-60, tile 60, departures 60-90 and table with their byte offsets, tile 30 and departures 30-60 shaded as the one request for bytes 406-632, then the ref, route, walk and departure rows of those two units with a label under each column](figures/walks-bytes.svg)

## How the file is organised

- **Tiles.** gfa-to-tabix cuts each reference path into tiles of `tile` bp.
  A tile holds the reference steps that start inside it, so a node is never
  split between two tiles. The writer compresses each tile separately, and
  a table lists the byte range of each one.
- **The reference path through a tile.** The tile's `ref` rows list the
  reference's steps there with their lengths. This page and the
  specification call that list R.
- **Routes.** A `route` row is one detour off R: where it leaves R, the
  steps off R, and where it returns. A tile lists each distinct detour once,
  however many haplotypes take it.
- **Walks.** A `walk` row is one piece of a W or P line: a run of its steps
  in one tile. The row gives the piece's first step on R and the routes it
  takes, in order. Between routes the piece follows R, so a haplotype that
  matches the reference across a tile is one short row.
- **Departure records.** When a path leaves the reference in one piece and
  rejoins in another, a `departure` row holds the two positions, so a
  reader that has one of the two pieces can draw where the path goes.

## The whole file

`zcat hprc.GRCh38.walks.gz` prints these lines. The columns are separated
by tabs, shown here as spaces:

```
#walks      format:i:8  tile:i:30  revisited:i:0  stay:i:311  abridge:i:1000000  abridgebytes:i:3000000  graph:Z:512ec671d5add2f7  leftout:i:0
#reference  GRCh38
#haplotype  CHM13#0
#haplotype  HG002#1
#unit  GRCh38#0#chr1  0   30  tile        0
GRCh38#0#chr1  0   30  ref        GRCh38#0#chr1  0  0   0  3  2,2,2   10,10,10  .
GRCh38#0#chr1  0   30  nodes      11  5
GRCh38#0#chr1  0   30  route      .  23  -15
GRCh38#0#chr1  0   30  walk       CHM13#0#chr1   0  0   0  3  2   .
GRCh38#0#chr1  0   30  walk       HG002#1#chr1   0  0   0  4  2   1
#unit  GRCh38#0#chr1  0   30  departures  .
GRCh38#0#chr1  20  70  departure  HG002#1#chr1   30  5  0  30  +  1  60  +  1  0
#unit  GRCh38#0#chr1  30  60  tile        30
GRCh38#0#chr1  30  60  ref        GRCh38#0#chr1  0  30  1  3  8,2,2   10,10,10  .
GRCh38#0#chr1  30  60  nodes      10  10
GRCh38#0#chr1  30  60  route      8  12  -8
GRCh38#0#chr1  30  60  walk       CHM13#0#chr1   0  30  1  3  8   0
#unit  GRCh38#0#chr1  30  60  departures  .
GRCh38#0#chr1  20  70  departure  HG002#1#chr1   30  5  0  30  +  1  60  +  1  0
#unit  GRCh38#0#chr1  60  90  tile        60
GRCh38#0#chr1  60  90  ref        GRCh38#0#chr1  0  60  2  3  14,2,2  10,10,10  .
GRCh38#0#chr1  60  90  walk       CHM13#0#chr1   0  60  2  3  14  .
GRCh38#0#chr1  60  90  walk       HG002#1#chr1   0  35  1  3  14  .
#unit  GRCh38#0#chr1  60  90  departures  .
GRCh38#0#chr1  20  70  departure  HG002#1#chr1   30  5  0  30  +  1  60  +  1  0
#unit  GRCh38#0#chr1  0   90  table       .
#entry GRCh38#0#chr1  0   30  tile        0   169  139
#entry GRCh38#0#chr1  0   30  departures  .   308  98
#entry GRCh38#0#chr1  30  60  tile        30  406  129
#entry GRCh38#0#chr1  30  60  departures  .   535  98
#entry GRCh38#0#chr1  60  90  tile        60  633  121
#entry GRCh38#0#chr1  60  90  departures  .   754  100
```

The byte numbers in the `#entry` lines are from this build and depend on
the compressor.

## Units, the table and the directory

- **A unit** is a run of lines that the writer compresses separately, as
  one or more whole gzip members in BGZF form, so a reader can fetch and
  gunzip one unit without the rest. A byte range that holds several units
  gunzips to their lines one after another.
- **The header** is the first unit, from byte 0: the `#walks`, `#reference`
  and `#haplotype` lines above.
- **A unit after the header** starts with `#unit seq start end kind name`.
  The kinds are `tile`, `departures` and `table`, and for a large tile
  `detail` and `blocks`. A reader skips a unit of any other kind.
- **A `tile` unit's name** is the multiple of `tile` it was cut at. Its
  `start end` runs from the start of its first reference step to the end
  of its last, which can lie past the next multiple of `tile`.
- **The table** is the last unit of each reference sequence. It has one
  `#entry` line per unit of that sequence: the `#unit` columns, then the
  unit's byte offset and length in `hprc.GRCh38.walks.gz`, as compressed
  bytes.
- **The end of the file** is BGZF's 28-byte end-of-file block, after the
  last table.
- **The `.idx` directory** is plain text. Line 1 is the `#walks` line with
  the data file's length added as `bytes:i:`, and line 2 gives the header's
  byte range. Each later line names one reference sequence of the file and
  gives the offset and length of its table; a reader ignores a later line
  that starts with `#`:

```
#walks  format:i:8  tile:i:30  …  leftout:i:0  bytes:i:1032
#header         0    169
GRCh38#0#chr1   854  150
```

The `…` stands for the tags between `tile` and `leftout`, left out here.

To read chr1:31-60, which is 30 to 60 in the file's 0-based, half-open
coordinates on `GRCh38#0#chr1`, a viewer does this:

- GET the `.idx`, then the header and that sequence's table at the byte
  ranges the `.idx` gives.
- Pick the `tile` and `departures` units whose `start end` overlap the
  window. Here they are `tile 30`, at offset 406 with length 129, and the
  `departures` unit over 30-60, at 535 with length 98. The two are adjacent
  in the file, so one request for bytes 406 to 632 fetches them.
- Gunzip each unit and decode its rows.

A reader picks tiles by the `start end` in the table. A node that starts
in one tile and runs past the next multiple of `tile` is in that tile, and
a reader that computes `floor(position / tile)` looks for it in the next.

## The header

- `#walks` has tags written `NAME:TYPE:value`, as in SAM. `format` is the
  format number and `tile` the tile size. A reader refuses a file whose
  `format` is not 8, and ignores a tag it does not know.
- `revisited` counts the nodes the reference passes more than once, and
  `leftout` counts the W and P lines absent from the file because they have
  no step on a node of the reference.
- `stay`, `abridge`, `abridgebytes` and `graph` describe how the file was
  written and which GFA it came from. A reader can ignore them.
- `#reference` names the reference sample. The reference's own lines are
  the `ref` rows. Each `#haplotype` line names a `sample#haplotype` among
  the other lines, or the sample alone for a line whose name has fewer than
  three `#`-separated fields.
- A `#hole` line, which this file lacks, gives a stretch of a reference
  sequence that no line of the reference covers.

## Rows

Every row starts `seq start end kind`: the reference sequence, a stretch of
it (0-based and half-open, as in BED) and the row's kind. A tile holds
`ref`, `nodes`, `route`, `walk` and `abridged` rows, in that order.

```
seq start end ref       path fragStart hapOffset piece nsteps steps lengths passes
seq start end nodes     ids lengths
seq start end route     entry interior exit
seq start end walk      path fragStart hapOffset piece nsteps startHandle choices
seq start end departure path hapStart ownBp missingBp leavePos leaveStrand leavePasses rejoinPos rejoinStrand rejoinPasses ownTiles
```

- **`start end`** of a `walk` row is the stretch its piece's steps on R
  cover. A `ref`, `nodes` or `route` row repeats its unit's `start end`.
- **A line's name.** `path` and `fragStart` identify one W or P line: its
  path name, which for a W line is its `sample#haplotype#contig`, and the
  offset on that contig where the line starts. `seq` is the reference
  line's name of the same form.
- **A piece.** `hapOffset` is the offset on the contig where the piece
  starts, `piece` numbers the line's pieces from 0, and `nsteps` counts the
  piece's steps.
- **A route.** `entry` is the handle on R where the route leaves R,
  `interior` the handles it visits off R, and `exit` the handle on R where
  it returns.
- **A list** separates its items with commas, and `.` is an empty list or a
  missing value.
- **A handle** is a node and a strand as one number, `2 × id + strand`,
  where strand 1 is the reverse strand. The id is the GFA's segment name,
  which has to be an integer.
- **A list of handles** stores differences. Each token is
  `2 × (id − previous id) + strand`, and the first token of a `steps` list
  counts from id 0.
- **A token can be negative,** so a reader takes the difference as
  `floor(token / 2)` and the strand as `token − 2 × floor(token / 2)`.
- **`startHandle`** is a plain handle, with no difference taken.
- **A `nodes` row** gives the length of each node in the interior of one of
  the unit's routes. Its `ids` are plain differences from 0, with no strand
  bit.
- **Several `ref` rows** are in a tile where the reference is more than one
  W line and more than one has steps there. R is their steps joined in
  order of `hapOffset`, and following R passes from one row's last step to
  the next row's first.
- **A step's offsets.** A step's offset on its contig is the piece's
  `hapOffset` plus the lengths of the steps before it. A step on R also has
  R's offset on the reference.
- **`passes`** lists, for each step of a `ref` row, how many times the
  reference passes that node in the whole file. `.` means 1 for each.

## Tile 30, decoded

- **`ref`:** the steps `8,2,2` are `>4` (8 = 2 × 4), then `>5` and `>6`
  (each token 2 is a difference of 1). The first step is at the row's
  `hapOffset`, 30, and each later step starts where the one before ends: R
  is `>4 >5 >6` at 30, 40 and 50.
- **`nodes`:** node 10 is 10 bp.
- **`route`:** the tokens `8 12 -8` are one chain of differences across the
  three columns. 8 is `>4`, 12 is a difference of 6, so `>10`, and −8 is a
  difference of −4, so `>6`. The route leaves R at `>4`, visits `>10` and
  returns at `>6`.
- **The chain** starts from id 0 at a unit's first `route` row and continues
  from each `route` row to the next. A column that is `.` is skipped.
- **`walk`:** piece 1 of `CHM13#0#chr1` starts at offset 30 of its contig
  and has 3 steps. It starts on handle 8, `>4`, and takes route 0. Its steps
  are `>4 >10 >6`.

A unit's routes are numbered from 0 in row order. HG002 has no row in tile
30, because it has no step on a reference node there. Its `departure`
record, explained below, has the positions where it leaves and rejoins.

The decoding rule, for any walk row:

- Read the choices. Each token is
  `2 × (route number − previous route number) + flip`, the first counting
  from route 0, and it splits as a handle token does.
- With flip 1 the piece takes the route the other way round: from its
  `exit` to its `entry`, the interior reversed, and every strand reversed.
- If the first route, as the piece travels it, does not start on R, emit
  its interior first: the piece starts off R and arrives on `startHandle`.
- Emit `startHandle`, the piece's first step on R.
- Then, until the piece has `nsteps` steps, look at the current step:
    - where it is the handle at which the next route leaves R, emit the
      route's interior and then the handle where the route returns, which
      is the new current step. A route that does not return ends the piece
      off R
    - otherwise follow R one step. A step that has the strand R has there
      goes forward to R's next step. A step on the other strand goes
      backward: the next step is R's previous one, on the strand opposite
      to R's

The two ends of a route are handles on nodes of R, on either strand. A
piece that returns to R on the reverse strand follows R backward from
there. A piece's steps on R are all on its own tile's R, so following R
stays between R's first and last step.

## Tile 0: a piece that ends off the reference

- **`route`:** `. 23 -15` has no entry. 23 is node 11 reversed, `<11`, and
  −15 is a difference of −8 on the reverse strand, `<3`. As stored, the
  route arrives from off R through `<11` and returns to R at `<3`.
- **`walk` of HG002:** 4 steps, starting on handle 2, `>1`, with the one
  choice `1`: route 0, flipped. Flipped, the route leaves R at `>3`, visits
  `>11` and does not return. The piece follows R through `>1 >2 >3`, takes
  the route to `>11`, and ends there: `>1 >2 >3 >11`.
- **`walk` of CHM13:** 3 steps from `>1` with no route: `>1 >2 >3`.

The writer stores each route one way round, and the flip bit of a choice is
1 where the piece travels the route the other way.

## Joining pieces

- `path`, `fragStart` and `piece` are a piece's key. The writer starts a
  new piece where a line's next step on the reference lies in another
  tile, so a line that leaves a tile and comes back has several pieces
  there.
- Pieces with consecutive numbers are consecutive stretches of the line:
  each starts on its contig where the one before ends. HG002's piece 0
  holds offsets 0 to 35 of its contig, and its piece 1, in tile 60, has
  `hapOffset` 35.
- A reader that holds two consecutive pieces joins them. The path steps
  from the last step of one to the first step of the next.
- Where a piece stops at the edge of the tiles a reader fetched, the path
  may continue along the reference in the next tile.
- Where a piece stops inside the window and the reader lacks the next
  piece, a `departure` record has the position where the path rejoins. With
  no record, the line has no later step on that reference sequence.

## Departure records

HG002 leaves the reference after node 3 and rejoins at node 7, and the two
steps are in different pieces:

```
GRCh38#0#chr1  20  70  departure  HG002#1#chr1  30  5  0  30  +  1  60  +  1  0
```

- `leavePos` 30 and `leaveStrand` `+`: the path leaves at 30, walking along
  the reference. `rejoinPos` 60 and `rejoinStrand` `+`: it rejoins at 60,
  walking along the reference.
- A position is the node boundary the path crosses. Walking along the
  reference, a path leaves at the end of its last node and rejoins at the
  start of its next one. Walking against the reference (`-`), it leaves at a
  node's start and rejoins at a node's end.
- `hapStart` 30 and `ownBp` 5: between the two steps the path has 5 bp of
  its own, node 11, starting at offset 30 of its contig. `ownBp` 0 is a
  jump with no sequence between.
- `missingBp` is the part of `ownBp` that falls between two W lines of the
  contig, where the graph has no sequence for the path.
- `leavePasses` and `rejoinPasses` count how often the reference passes
  each end's node, as `passes` does.
- `start end`, 20 to 70, is the smallest stretch that holds the two end
  nodes, node 3 and node 7.
- `ownTiles` lists, by tile name, the tiles whose pieces hold the path's
  own steps between the two ends: the leave step's tile, the rejoin step's
  tile, the two with a comma between, or `.`. Here it is tile 0, where
  HG002's piece ends with `>11`.

The file has a record for two steps of a path where:

- the two are on one reference sequence, with no step of the path on that
  sequence between them
- they are in different pieces
- either the path has sequence of its own between them, or the second is
  not the first's neighbour on the reference: the next base, on the same
  strand, with any `#hole` between the two left out

A reader works out a departure between two steps of one piece from the
piece.

The record above is in all three `departures` units, because its stretch
touches all three tiles. A window anywhere from 20 to 70 therefore reads
it, and a reader that fetched two of the units drops the line it has read
already, which is the same text in each.

## Three additions, each for one case

**A reference that passes a node more than once.** pggb merges the copies of
a repeat into shared nodes, so R can hold a node at several places. The
writer chooses which copy each haplotype step lies on, and the walk row
states the choice.

A place is numbered among the steps of the tile's R on that node, on either
strand, from 0 in R's order:

- `startHandle@k`: the piece starts on place k. With no `@k` it starts on
  the first.
- `:k` on a choice: the piece leaves R from place k of the node where the
  route, as travelled, leaves. With no `:k` it leaves from the first such
  step it comes to, the current step included.
- `@k` on a choice: the route returns to place k. With no `@k` it returns
  to the place the fewest steps of R from where it left, the later one in R
  on a tie.
- A choice with both suffixes is written `-10:1@2`.

`tests/data/walks-loop.gfa` has a reference that takes nodes 2 and 3 twice.
Built with `--refs R`, it is one tile. Below are four of its W lines, then
the tile's `ref`, `nodes` and `route` rows and the walk rows of those three
haplotypes, with each row's `seq start end` and each walk row's
`fragStart hapOffset piece` left out:

```
W  R  0  chr  0  45  >1>2>3>2>3>4
W  A  1  a    0  57  >1>2>3>2>3>2>3>4
W  E  1  e    0  47  >1>2>5>3>2>3>4
W  F  1  f    0  47  >1>2>3>2>5>3>4
```

```
ref    R#0#chr  0  0  0  6  2,2,2,-2,2,2  6,6,6,6,6,15  1,2,2,2,2,1
nodes  5  2
route  2   .  4
route  -2  6  -4
route  -1  .  3
route  0   .  2
walk   A#1#a  8  2  5:1
walk   E#1#e  7  2  2
walk   F#1#f  7  2  2:1
```

- **R** is `>1 >2 >3 >2 >3 >4`. Node 2 is at places 0 and 1, the second and
  fourth steps of R, and node 3 at the third and fifth.
- **Routes:** 0 is `>1` straight to `>3`, 1 is `>2 >5 >3`, 2 is `<2`
  straight to `<3`, and 3 is `>3` straight to `>4`.
- **E** takes route 1 at the first `>2` it comes to and returns to the
  nearest `>3`, the third step of R: `>1 >2 >5 >3 >2 >3 >4`.
- **F** takes route 1 with `:1`, so it follows R to the second `>2` before
  it leaves. The two `>3` are each one step of R from there, and the later
  one is taken: `>1 >2 >3 >2 >5 >3 >4`.
- **A** takes route 2 flipped, `>3` straight to `>2`, with `:1`: it follows
  R to the second `>3` and jumps back to the nearest `>2`, the fourth step
  of R, then follows R to the end: `>1 >2 >3 >2 >3 >2 >3 >4`.

Where `passes` is above 1, a viewer says that the position is one copy
among several.

A file whose header has `revisited:i:0` has no such node, and in it the
tiles over a window hold a row for every line of the file that steps on a
reference node there. Files built from HPRC's Minigraph-Cactus graphs on
the graph's own reference have that tag.

**A tile too large to send whole.** In a satellite array a tile's rows can
be several megabytes of text.

- The writer moves whole lines out of such a tile into `detail` units, one
  line per unit, starting with the lines that take a reader the most work
  to decode ([Abridged tiles](walks-format.md#abridged-tiles) defines the
  measure).
- In the tile, an `abridged` row stands in place of each moved walk row:
  `path fragStart hapOffset piece nsteps hapBp detail`. `hapBp` is the bp
  of the piece's steps, and `detail` numbers the unit that holds its walk
  row. That unit's name is the tile's name and the number, as `65536:0`.
- A `detail` unit has `nodes`, `route` and `walk` rows of its own, and its
  walk rows decode against the tile's R.
- The tile's `blocks` unit has one row per moved piece that lists where on
  R its steps lie, as a chain of aligned blocks and gaps. A viewer draws
  the piece from that row, and fetches the `detail` unit when the user asks
  for the nodes.

**A departure that spans many tiles.** A reader has to find a record from a
window anywhere between its two ends.

- `departures` units come in four sizes, 1, 8, 64 and 512 tiles, each
  starting at a multiple of its size. A unit's `start end` is the stretch
  it covers.
- The writer widens a record's stretch to whole tiles and covers it from
  left to right with the largest unit that starts at that point and fits
  inside. It writes the record's line into each of those units.
- A reader picks the `departures` units whose `start end` overlap its
  window, at most one of each size for a window inside one tile, and drops
  a line identical to one it has read.

## What a walk file leaves out

- **Bases.** Rows have node ids and lengths. With `--sequences` the writer
  adds the bases as an `SQ:Z:` tag on `ref` and `nodes` rows.
- **Links.** The file has no L lines. A link is two consecutive steps of a
  path in the file, and a link that no such path takes is absent.
  gfa-to-tabix's other output, [the node and link index](index-format.md),
  holds the graph's nodes and links by coordinate.
- **Lines off the reference.** A W or P line with no step on a node of the
  reference is absent, and the header's `leftout` tag counts these lines.
- **A haplotype on another copy.** On a reference with repeated nodes, a
  haplotype step on a repeated node is placed on one copy, and a window
  over another copy lacks that haplotype there
  ([open problem](open-problems.md#placement-of-steps-on-nodes-the-reference-passes-more-than-once)).
- **Where a path goes on another sequence.** A record lies between two
  steps on one reference sequence. A path that moves to another reference
  sequence and stays there has no record on the first
  ([open problem](open-problems.md#a-path-that-crosses-onto-another-reference-sequence)).

## In the specification and absent here

- [Path names](walks-format.md#path-names): how gfa-to-tabix reads a start
  offset from a P line's name.
- [Tiles and pieces](walks-format.md#tiles-and-pieces): how gfa-to-tabix
  chooses a copy for a step on a repeated node, and which GFAs it refuses.
- [route](walks-format.md#route) and [walk](walks-format.md#walk): the tie
  breaks that give each piece exactly one encoding, none of which a reader
  needs to decode a row.
- [abridged](walks-format.md#abridged) and [blocks](walks-format.md#blocks):
  the columns of the rows for a large tile.
- [nodes](walks-format.md#nodes): how the `SQ:Z:` tag lays out the bases.
- [Header](walks-format.md#header): every header tag, and how a later
  version may add tags, lines and units.
- [What a reader relies on](walks-format.md#what-a-reader-relies-on) and
  [What the writer guarantees](walks-format.md#what-the-writer-guarantees):
  every invariant, and the check that tests each one.
