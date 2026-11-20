# Walk files by example

This page reads one small walk file line by line and accounts for every
number shown. [Walk files in brief](walks-format-in-brief.md) gives the
ideas of the format in short, and the
[specification](walks-format.md) is the authority where this page
simplifies.

## The example

[walks-example.gfa](figures/walks-example.gfa) has a 90 bp reference of
nine 10 bp nodes, and four more haplotypes:

```
W  GRCh38  0  chr1  0  90  >1>2>3>4>5>6>7>8>9
W  CHM13   0  chr1  0  87  >1>2>3>4>10>6>7>8>9
W  HG002   1  chr1  0  90  >1>2>3>4>5>6>7>8>9
W  HG002   2  chr1  0  40  >1>2>8>9
W  HG003   1  chr1  0  80  >1>2>3>4>6>7>8>9
```

Each `>4` is a step: node 4, walked forward.

- `CHM13#0` takes node 10, which is 7 bp, in place of node 5
- `HG002#1` follows the reference
- `HG002#2` goes from node 2 straight to node 8, so it lacks nodes 3 to 7
- `HG003#1` goes from node 4 straight to node 6, so it lacks node 5

```bash
gfa-to-tabix walks-example.gfa --walks --refs GRCh38 --tile 30 -o hprc
```

The command writes the walk file, `hprc.GRCh38.walks.gz`, and a small text
file beside it, `hprc.GRCh38.walks.gz.idx`.

![The example graph: nine reference nodes along chr1 under three tiles, tile 0, tile 30 and tile 60; HG002#1 as a straight line, CHM13#0 dipping to node 10 under node 5, HG003#1 dipping under node 5 with no node, and HG002#2 dipping under nodes 3 to 7 with no node; below, hprc.GRCh38.walks.gz as a bar of header, tile 0, departures 0-30, tile 30, departures 30-60, tile 60, departures 60-90 and table; the region chr1:31-60 is shaded over the graph and over tile 30 and departures 30-60, labelled one request](figures/walks-example.svg)

## The file is a series of units

`zcat hprc.GRCh38.walks.gz` prints the whole file as tab-separated text,
in which `.` in a column means empty. The file has a table of byte ranges
and no Tabix index, so `tabix` doesn't read it.

gfa-to-tabix compresses the file unit by unit, so a viewer can fetch one
unit and gunzip it without the others. The bar in the figure shows the
units in file order:

- **The header** names the reference and lists the other haplotypes
- **A tile** has the paths through one stretch of the reference. A node is
  never split between two tiles: a tile has the reference steps that start
  inside it, so its stretch can run past the next cut
- **A `departures` unit** has the `departure` rows of one stretch of the
  reference, and is in the file only where there is such a row. `HG002#2`'s
  row is over all three tiles, so this file has three of these units
- **The table** lists the byte range of every tile and `departures` unit of
  one chromosome

The header of this file, after a first line of tags that
[Header](walks-format.md#header) lists, among them the format number and
the tile length:

```
#reference  GRCh38
#haplotype  CHM13#0
#haplotype  HG002#1
#haplotype  HG002#2
#haplotype  HG003#1
```

## Reading one region

A viewer starts from the `.idx`, which gives the byte range of the header
and of each chromosome's table, as an offset and a length. Its first line
repeats the header's first line, and the rest of it is:

```
#header        0    175
GRCh38#0#chr1  898  151
```

The viewer reads the header, for the list of haplotypes, and the table of
the chromosome it shows. The table lists the units of chr1:

```
#unit   GRCh38#0#chr1  0   90  table       .
#entry  GRCh38#0#chr1  0   30  tile        0   175  122
#entry  GRCh38#0#chr1  0   30  departures  .   297  100
#entry  GRCh38#0#chr1  30  60  tile        30  397  154
#entry  GRCh38#0#chr1  30  60  departures  .   551  101
#entry  GRCh38#0#chr1  60  90  tile        60  652  145
#entry  GRCh38#0#chr1  60  90  departures  .   797  101
```

An `#entry` line gives one unit: the stretch of chr1 it covers, its kind,
its name, and then its byte offset and its length in the `.gz` file. The
name of a tile is the position it was cut at, and the other units have
none.

To draw chr1:31-60, which is 30 to 60 in the file's 0-based coordinates:

- The viewer picks the entries that overlap 30 to 60, which are the `tile`
  and `departures` entries of `30 60`
- The two units are adjacent in the file, so one request fetches both:
  from the offset of the first to the end of the second

## What the viewer gets

Gunzipped, the two units are these ten lines:

```
#unit  GRCh38#0#chr1  30  60  tile  30
GRCh38#0#chr1  30  60  ref        GRCh38#0#chr1  0  30  1  3  8,2,2  10,10,10  .
GRCh38#0#chr1  30  60  nodes      10  7
GRCh38#0#chr1  30  60  route      8  .  4
GRCh38#0#chr1  30  60  route      -4  12  -8
GRCh38#0#chr1  30  60  walk       CHM13#0#chr1   0  30  1  3  8  2
GRCh38#0#chr1  30  60  walk       HG002#1#chr1   0  30  1  3  8  .
GRCh38#0#chr1  30  60  walk       HG003#1#chr1   0  30  1  2  8  0
#unit  GRCh38#0#chr1  30  60  departures  .
GRCh38#0#chr1  10  80  departure  HG002#2#chr1   20  0  0  20  +  1  70  +  1  .
```

The numbers in these lines are encoded: a step is written as twice its
node id, and a later number in a list as a difference from the one before.
The sections below decode each line, and arrive at this:

| Line | Meaning |
|---|---|
| `#unit`, `tile` | the tile cut at 30 starts here |
| `ref` | the reference goes `>4 >5 >6` through the tile, and each node is 10 bp |
| `nodes` | node 10 is 7 bp |
| first `route` | route 0 goes from `>4` straight to `>6` |
| second `route` | route 1 goes from `>4` through `>10` to `>6` |
| `walk`, `CHM13#0` | three steps from `>4`, taking route 1: `>4 >10 >6` |
| `walk`, `HG002#1` | three steps from `>4`, taking no route: `>4 >5 >6` |
| `walk`, `HG003#1` | two steps from `>4`, taking route 0: `>4 >6` |
| `#unit`, `departures` | the `departures` unit over 30 to 60 starts here |
| `departure` | `HG002#2` left the reference at 20 and rejoins it at 70, with no sequence between leaving and rejoining |

## The columns every row starts with

Every row starts with the same four columns, `seq start end kind`:

- **`seq`** is the reference sequence, named `sample#haplotype#contig`.
  `GRCh38#0#chr1` is the line `W GRCh38 0 chr1`
- **`start end`** is the stretch of that sequence the row is about, 0-based
  and half-open as in BED, so chr1:31-60 is `30 60`
- **`kind`** is `ref`, `nodes`, `route`, `walk` or `departure`

Each row has its position, so `zcat` and `awk` can filter the rows of any
region.

- **Row order:** a tile has its `ref` row, then `nodes`, `route` and
  `walk` rows. It has `nodes` and `route` rows only where one of its `walk`
  rows takes a route, so tiles 0 and 60 of this file have neither
- **`#unit` lines:** a `#unit` line starts each unit after the header, with
  `seq start end`, then the unit's kind, `tile`, `departures` or `table`,
  then its name. A `departure` row refers to a tile by its name
- **Pieces:** gfa-to-tabix cuts a W line into pieces, one in each tile
  where the line has a step on the reference. A `ref` row or a `walk` row
  is one piece

## How a row writes a step

A W line writes a step as `>4` or `<4`, which is node 4 forward or
reversed. A row writes a step as one number: twice the node id, plus 1 if
the step is reversed. `>4` is `8` and `<4` is `9`. The specification calls
this number a handle.

In a list of steps, each number after the first is a difference from the
node id before it: twice the difference, plus 1 if the step is reversed.
Commas separate the steps of a list inside one column.

| Written | Read as |
|---|---|
| `8,2,2` | `>4`, then one id up to `>5`, then one id up to `>6` |
| `8,12,-8` | `>4`, then six ids up to `>10`, then four ids down to `>6` |
| `9,3` | `<4`, then one id up and reversed, `<5` |

To read a number, halve it and round down, toward minus infinity. The half
is the id, or the difference in ids, and a remainder of 1 means reversed.
`-15` halves to −8 with a remainder of 1, so it is eight ids down,
reversed.

## `ref`: the reference through the tile

```
GRCh38#0#chr1  30  60  ref  GRCh38#0#chr1  0  30  1  3  8,2,2  10,10,10  .
```

| Column | Here | Meaning |
|---|---|---|
| `path` | `GRCh38#0#chr1` | the W line this row is a piece of |
| `fragStart` | `0` | where that W line starts on its contig, as the W line's start column gives it |
| `hapOffset` | `30` | the position on the path's contig where this piece starts, counted from the start of the contig. On a `ref` row it equals `start` |
| `piece` | `1` | the number of this piece along its W line, counted from 0. Piece 0 is in tile 0 |
| `nsteps` | `3` | the number of steps in the piece |
| `steps` | `8,2,2` | the steps, `>4 >5 >6` |
| `lengths` | `10,10,10` | the length of each step's node in bp, written as it is |
| `passes` | `.` | how many times the reference passes each node, as a list. `.` stands for a list of ones, as here. A reference passes a node twice only in [a graph that merges repeats](#cases-the-example-lacks) |

## `nodes` and `route`: each detour, listed once

```
GRCh38#0#chr1  30  60  nodes  10  7
GRCh38#0#chr1  30  60  route  8  .  4
GRCh38#0#chr1  30  60  route  -4  12  -8
```

The `nodes` row has two columns, `ids` and `lengths`, for the nodes off
the reference that the tile's routes visit: node 10 is 7 bp.

- A node has no strand, so the row writes the id itself, `10`, where a step
  on node 10 is `20`
- With several nodes, each later id is its difference from the one before,
  and the lengths are written as they are: `10,2,1` and `7,4,9` are nodes
  10, 12 and 13, of 7, 4 and 9 bp
- The lengths of the reference's nodes are in the `ref` row

A `route` row has three columns:

| Column | Meaning |
|---|---|
| `entry` | the step on the reference where the detour leaves |
| `interior` | the steps off the reference. Commas separate several, and `.` is none |
| `exit` | the step on the reference where the detour returns |

The first number of a `route` row is a difference from the last step of
the `route` row above it. Read the `route` columns of a tile left to right
and top to bottom as one list, skipping `.`. Here the list is
`8,4,-4,12,-8`, so the `-4` that starts the second row counts from the `>6`
that ends the first:

| Row | Numbers | Steps | The detour |
|---|---|---|---|
| route 0 | `8 . 4` | `>4`, then two ids up to `>6` | from node 4 straight to node 6, with nothing between |
| route 1 | `-4 12 -8` | two ids down to `>4`, six up to `>10`, four down to `>6` | from node 4 through node 10 to node 6 |

- A tile's routes are numbered from 0 in the order of their rows
- A tile has one row for a detour however many haplotypes take it
- A route with `.` for its interior goes straight from its entry to its
  exit, as a deletion that starts and ends inside the tile does

## `walk`: a haplotype as the routes it takes

```
GRCh38#0#chr1  30  60  walk  CHM13#0#chr1  0  30  1  3  8  2
GRCh38#0#chr1  30  60  walk  HG002#1#chr1  0  30  1  3  8  .
GRCh38#0#chr1  30  60  walk  HG003#1#chr1  0  30  1  2  8  0
```

The first five columns after `walk` are those of a `ref` row: `path`,
`fragStart`, `hapOffset`, `piece` and `nsteps`. Two more follow:

| Column | Meaning |
|---|---|
| `startHandle` | the piece's first step on the reference, as the step's number. Here `8` is `>4` |
| `choices` | the routes the piece takes, in order, or `.` for none |

`choices` lists route numbers the way `steps` lists node ids: twice the
difference from the route number before it, plus 1 if the piece travels
the route backwards, from its exit to its entry with each step reversed.
Each `walk` row's list starts afresh, with its first number counted from
route 0.

| Written | Read as |
|---|---|
| `0` | route 0 |
| `2` | route 1 |
| `2,2` | route 1, then route 2 |
| `3` | route 1, travelled backwards |

A reader rebuilds the piece from the tile's `ref` and `route` rows:

- Start on `startHandle` and follow the reference one step at a time
- At the entry of the next route in `choices`, take the route's interior
  and continue from its exit
- Stop after `nsteps` steps, which counts every step of the piece, on the
  reference or off it

| Haplotype | `nsteps` | `choices` | Steps |
|---|---|---|---|
| `CHM13#0` | 3 | `2`, route 1 | `>4 >10 >6` |
| `HG002#1` | 3 | `.`, no route | `>4 >5 >6`, the reference's steps |
| `HG003#1` | 2 | `0`, route 0 | `>4 >6` |

### A W line is one piece in each tile it touches

gfa-to-tabix numbers a W line's pieces along the line from 0. Two rows of
tile 60:

```
GRCh38#0#chr1  60  90  walk  CHM13#0#chr1  0  57  2  3  14  .
GRCh38#0#chr1  70  90  walk  HG002#2#chr1  0  20  1  2  16  .
```

- `CHM13#0` has pieces 0, 1 and 2, in tiles 0, 30 and 60. Piece 2 starts
  on `>7` at 57 on CHM13's contig, where the reference is at 60, because
  node 10 is 3 bp shorter than node 5
- `HG002#2` has pieces 0 and 1, in tiles 0 and 60, and none in tile 30.
  Piece 1 starts on `>8`, partway through the tile, at 20 on its contig
- A `walk` row's `start end` is the stretch of the reference its piece
  covers, so the second row has `70 90`
- A piece's steps on the reference are all in its tile
- A reader that has several pieces of a line joins them in order of `piece`

## `departure`: a path that leaves in one tile and rejoins in another

`HG002#2` has no `walk` row in tile 30, because a `walk` row needs a step
on the tile's reference and `HG002#2` has none there. A viewer that read
tile 30's rows alone would draw chr1:31-60 without it. The `departure` row
gives where the path went:

```
GRCh38#0#chr1  10  80  departure  HG002#2#chr1  20  0  0  20  +  1  70  +  1  .
```

| Column | Here | Meaning |
|---|---|---|
| `start end` | `10 80` | from the start of the last reference node before the path leaves, node 2, to the end of the first after it rejoins, node 8. A viewer that shows either node gets the row |
| `path` | `HG002#2#chr1` | the W line, or all the W lines of its contig taken as one path |
| `hapStart` | `20` | the position on the path's contig where it leaves the reference, as `hapOffset` is a position on the contig. It is 20 on the reference too, because `HG002#2` matches the reference up to there |
| `ownBp` | `0` | the bp the path has between leaving and rejoining. 0 is a jump straight from node 2 to node 8 |
| `missingBp` | `0` | the part of `ownBp` that lies in a gap between two W lines of the contig, which is sequence the graph lacks. 0 for a contig that is one W line |
| `leavePos` `leaveStrand` | `20` `+` | the path leaves the reference at 20, walking forward along it |
| `leavePasses` | `1` | how many times the reference passes the node the path leaves from. It is a number in every row, where `passes` can be `.` |
| `rejoinPos` `rejoinStrand` | `70` `+` | the path rejoins the reference at 70, walking forward along it |
| `rejoinPasses` | `1` | the same count for the node it rejoins on |
| `ownTiles` | `.` | the names of the tiles whose `walk` rows have the path's steps between the two positions, with commas between. None here, since `ownBp` is 0 |

- **Which paths have one:** a path that leaves the reference in one tile
  and rejoins it in another, whether the next tile or one far along. A
  path that follows the reference from one tile into the next has none,
  and neither has a path that leaves the reference and never rejoins it
- **What a viewer draws:** from this row alone, a viewer of chr1:31-60
  draws `HG002#2` crossing the whole region with no nodes, since it left
  at 20 and rejoins at 70
- **Where the row is:** gfa-to-tabix copies the row into a `departures`
  unit over every tile that the row's `start end` touches, which is all
  three in this file. A viewer whose region overlaps 10 to 80 gets the row
  with its tiles, and keeps one copy if it fetched several
- **A detour inside one tile has no `departure` row,** because the tile's
  `route` and `walk` rows show it, as they show `CHM13#0`'s and `HG003#1`'s

## What a walk file leaves out

- **Bases:** the rows have node ids and lengths. `--sequences` adds the
  bases to the `ref` and `nodes` rows
- **Links that no path takes:** the file has no L lines, and a reader takes
  a link from two consecutive steps of a path.
  [The node and link index](index-format.md), gfa-to-tabix's other output,
  holds the graph's nodes and links by coordinate
- **Paths off the reference:** a W or P line with no step on a node of the
  reference is absent, and gfa-to-tabix prints how many such lines it left
  out
- **Where a path goes on another chromosome:** a path that moves onto
  another sequence of the reference and stays there looks, on the first
  sequence, like a path that stops
  ([open problem](open-problems.md#a-path-that-crosses-onto-another-reference-sequence))

## Cases the example lacks

- **A path with sequence between leaving and rejoining,** such as an
  insertion that spans a tile edge. `ownBp` is its length, and `ownTiles`
  names the tile whose `walk` row has its steps: the tile the path leaves
  from, or the one it rejoins in
- **A route with `.` for its entry or its exit,** for a piece that leaves
  the reference onto other nodes and does not return inside the tile.
  `HG002#2`'s piece in tile 0 needs none, because it ends on the reference,
  on `>2`
- **A route travelled backwards.** The specification's
  [Example](walks-format.md#example) decodes a tile with a route that has
  no entry and is travelled backwards
- **A reference that passes a node more than once,** as in a pggb graph,
  which merges the copies of a repeat into shared nodes. gfa-to-tabix
  places each haplotype step on one copy, and a region over another copy
  lacks the haplotype
  ([Exact and chosen](walks-format.md#exact-and-chosen),
  [open problem](open-problems.md#placement-of-steps-on-nodes-the-reference-passes-more-than-once))
- **A tile too large to send whole,** as in a satellite array. gfa-to-tabix
  moves paths out of the tile into units of two more kinds, and a viewer draws a
  moved path as blocks along the reference until the user asks for its
  nodes ([Abridged tiles](walks-format.md#abridged-tiles))
- **A P line,** whose name gives the sample, haplotype and contig
  ([Path names](walks-format.md#path-names))
- **A reader to start from:**
  [scripts/walks-brief.py](../scripts/walks-brief.py) is one short Python
  file that prints every W and P line back from a walk file
