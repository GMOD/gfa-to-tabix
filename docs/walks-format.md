# Walk files

- **In:** a base-level GFA with integer node ids and W or P lines, such as
  `vg convert -f` writes from a Minigraph-Cactus GBZ
- **Out:** one bgzipped, Tabix-indexed file per reference sample,
  `<prefix>.<sample>.walks.bed.gz`, holding every path of the graph cut into
  pieces filed under fixed chunks of that reference
- A region query returns the rows a reader needs to rebuild every step of
  every path through the region exactly
- gfa-to-tabix 1.4 and later write walk format 5, which this page describes

```bash
vg convert -f chr22.gbz > chr22.gfa
gfa-to-tabix chr22.gfa --walks --refs GRCh38,CHM13 -o chr22
```

The command writes a file and its index for each sample in `--refs`:

```
chr22.GRCh38.walks.bed.gz  chr22.GRCh38.walks.bed.gz.tbi
chr22.CHM13.walks.bed.gz   chr22.CHM13.walks.bed.gz.tbi
```

- A chunk holds the reference's path through it once, each distinct route a
  haplotype takes off that path once, and every other path's piece as the list
  of routes it takes
- Every file lists the same paths, including those of the `--refs` samples.
  Rows in `chr22.GRCh38.walks.bed.gz` have GRCh38 coordinates, so a reader on
  GRCh38 downloads that file's index and no other
- A reader lists the haplotypes from the header without reading any rows

| Option            | Effect                                                                   |
| ----------------- | ------------------------------------------------------------------------ |
| `--refs <names>`  | Comma-separated PanSN samples, one file per sample. Required.            |
| `--chunk <bp>`    | Chunk size. Default 65536.                                               |
| `--sequences`     | Add the bases of the reference's nodes and of the nodes routes visit.    |
| `--stay <bp>`     | Keep a piece in its chunk across a short stretch over nodes the reference passes twice. Default 311, the `-k 311` minimum match of the HPRC pggb graphs; 0 turns it off. |
| `--abridge-steps <n>` | Move a chunk's costliest paths to its detail rows until the rest cost at most n interior steps. Default 1000000; 0 turns it off. |
| `--abridge-bytes <bytes>` | ...and until the rest compress to at most this many bytes. Default 3000000; 0 turns it off. |

![Four haplotype paths through a bubble, the walk rows for their chunk, and the paths a reader rebuilds from them](figures/walks-detail.svg)

[Example](#example) lists a harder chunk, whose one route has no entry and is
taken flipped.

## Chunks and pieces

[ADR 0001](adr/0001-step-placement.md) gives the reasons for these rules, the
alternatives tried and their measurements on pggb and Minigraph-Cactus.

- The tool cuts each reference sequence into chunks of `chunk` bp and files
  every row under its chunk's first base, `seq cs cs+1`, so a query on a window
  returns whole chunks. A row spanning the whole chunk would share a Tabix bin
  with the next chunk, and a query would read both
- A step on a reference node takes the chunk holding that node's position. A
  step on any other node takes the chunk of the last reference step before it,
  or of the first one after it for steps that lead the path
- On the reference paths, a step takes the chunk that holds its offset, so
  where the reference passes a node twice each pass lies where it is
- A piece is a run of a path's steps in one chunk. `piece` numbers the pieces
  along the path, so a reader joins consecutive pieces back into one walk
- A path that visits no node of a reference has no rows in that reference's
  file, and the tool counts these paths on stderr
- A node the reference passes once has that pass as its position. For a node
  it passes more than once, the path's last placed step predicts an offset: the
  step's own offset plus the bp the path has walked since, in the direction
  their strands agree on. The step takes the pass on the same reference
  sequence nearest that offset, the earlier on a tie, or the first pass when
  that sequence has none
- Placing starts at the path's first step on a node the reference passes once
  (or on any reference node when there is none) and runs outward in both
  directions
- A run of steps that the rules above file in other chunks stays in the current
  piece, joining its routes, when:
  - the path returns to the piece's chunk
  - the run holds at most `stay` bp of reference nodes, one of them a node the
    reference passes more than once
  - each node in the run that the reference passes once lies on the piece's
    sequence, in the piece's chunk or the next
- Any other run starts a new piece, and the reference's own paths are exempt.
  A reference that passes each node once therefore gets the same rows at any
  `stay`. A window reads every piece with a step on a node in it that the
  reference passes once; a step on a node it passes more than once can lie in
  a piece of another window
- A route can hold another chunk's reference nodes. A reader places a node at
  its reference position from a `ref` row of a chunk it read whenever one
  exists, from the row whose path sorts first, at its earliest start, when
  several do. Other nodes take haplotype offsets

## Paralogs and collapsed repeats

- **Paralog jumps:** in a segmental duplication, a haplotype can step onto the
  reference nodes of a distant paralog and back. The steps after the jump take
  the paralog's chunk, so a window at the haplotype's own locus shows the
  haplotype in more pieces and leaves out some of its inserted nodes. On
  Minigraph-Cactus graphs this is rare and sits almost entirely in low-copy
  repeats such as 22q11's
- **Collapsed repeats:** pggb merges the copies of a repeat into shared nodes,
  so the reference path passes those nodes more than once, often megabases
  apart. pggb graphs have many such nodes; Minigraph-Cactus's GRCh38 path has
  none. Filing every step at the node's first pass, as format 3 did, split each
  haplotype into a piece per hop and made pggb walk files dozens of times
  larger than Minigraph-Cactus's; the nearest pass and `stay` above replace it
- **Satellite arrays:** pggb gives each haplotype a separate long path through
  thousands of tiny nodes, and the tool files all of it in the chunk where the
  haplotype leaves the reference. [Abridged chunks](#abridged-chunks) moves the
  costliest of these paths to detail rows, and a viewer draws each as a
  labelled block until the user opens it
- **What to expect on pggb:** a window shows nearly every haplotype whose
  sequence aligns there, except in satellites and CHM13's short arm, where
  abridged paths show as blocks until opened

## Header

Header lines start with `#`: `tabix -H` prints them and region queries skip
them.

```
#walks	format:i:5	chunk:i:65536	maxnode:i:1024	stay:i:311	abridge:i:1000000	abridgebytes:i:3000000
#reference	GRCh38
#haplotype	CHM13#0
#haplotype	HG00097#1
```

- `format:i:5` marks this format. A reader refuses any other
- `maxnode` is the longest node on the reference paths in bp
- `#long` gives each pass of the reference over a node longer than a chunk:
  sequence, start, end, as in `#long  GRCh38#0#chr22  10510000  11510000`. vg
  chops nodes at 1,024 bp, so its graphs have none; pggb's N runs and
  unaligned stretches are the usual ones
- A reader queries from the chunk before the window's first, and from the
  chunk before each `#long` pass that overlaps the window, whichever is
  earlier ([ADR 0003](adr/0003-long-node-lookback.md)). A file with no `#long`
  lines but `maxnode` over a chunk, from gfa-to-tabix 1.2, needs
  `max(chunk, maxnode)` bp before the window instead
- `stay` is the `--stay` value in bp the file was written with; 0 means no stay.
  A reader ignores it
- `abridge` and `abridgebytes` are the `--abridge-steps` and
  `--abridge-bytes` budgets the file was written with; 0 means none. A reader
  ignores them
- `#reference` names the reference sample
- `#haplotype` lists each other haplotype with rows in the file, as its PanSN
  `sample#haplotype`, once each in byte order

## Rows

Every row starts `seq cs cs+1 kind`. A chunk lists its `ref` rows, then at
most one `nodes` row, then its `route` rows, then its `walk` rows, then its
`abridged` rows.

A handle is `2 × id + r`, with `r` 1 for the reverse strand. A list of handles
is written as delta tokens: each token is `2 × (id − previous id) + r`, and the
first token's previous id is 0 unless a row says otherwise. An empty list is
`.`.

### ref

```
seq cs cs+1 ref path fragStart hapOffset piece nsteps steps lengths [pv] [nx] [pg] [pr] [ng] [nr] [SQ:Z:bases]
```

- One row per piece of the reference paths in the chunk, so usually one
- `path` is `sample#haplotype#contig`. `fragStart` is where the W line starts on
  that contig, or the start in a P line's name (`[start]`, `#start` or
  `:start-end`). `hapOffset` is where the piece starts
- `steps` is the piece's handles as delta tokens, the first from 0
- `lengths` lists each step's node length in bp
- **R**, the chunk's reference path, is every `ref` row's steps joined in
  `hapOffset` order. Positions in R count from 0

### nodes

```
seq cs cs+1 nodes ids lengths [SQ:Z:bases]
```

- The nodes the chunk's routes visit, in ascending id order: `ids` gives each
  id as the difference from the one before, the first from 0, and `lengths`
  their lengths in bp
- With `--sequences`, `SQ:Z:` holds their bases joined in the same order, as
  the S lines give them. On a `ref` row it holds the steps' nodes' bases in
  step order

### route

```
seq cs cs+1 route entry interior exit
```

- A route is a way a piece leaves R: `entry`, the handle on R it leaves from;
  `interior`, the steps off R; and `exit`, the handle on R it returns to
- `entry` or `exit` is `.` for a route that starts or ends the piece off R.
  `interior` is `.` for a route straight from one part of R to another, such as
  a deletion or a jump between repeat copies
- All three columns are delta tokens chained through the chunk's route rows: a
  token's previous id is the id of the token before it, across columns and rows.
  The chunk's first route row starts from 0
- A route's id is its row's index among the chunk's route rows, from 0
- A route is stored the way round whose handles sort first: by `entry` (none
  first), then `interior`, then `exit`. Its flip is the reverse: each handle
  flipped, interior reversed, entry and exit swapped

### walk

```
seq cs cs+1 walk path fragStart hapOffset piece nsteps start end choices [pv] [nx] [pg] [pr] [ng] [nr]
```

- One row per piece of every other path, the other references' included.
  `path`, `fragStart`, `hapOffset`, `piece` and `nsteps` are as on a `ref` row
- `start` is the piece's first handle on R, absolute. `end` is its last handle
  on R minus `start`
- `choices` lists the routes the piece takes in order, `.` for none. Each token
  is `2 × (route id − previous route id) + flip`, the first from 0, where flip
  1 means the piece takes the route the other way round
- A token may end `:n`, and then every token does and `end` ends `:n` too. See
  [Decoding a walk row](#decoding-a-walk-row)

### Neighbours

`pv` and `nx` give the start of the chunk the path's previous and next piece is
filed under, as `pv:i:cs`, or as `pv:Z:seq:cs` on another reference sequence. A
row at either end of its path has no tag there. A reader that cuts a path off
at the edge of what it read follows the tag to the chunk the path goes on in.

### Records

A contig can span several W lines, one per stretch the graph holds, as where
Minigraph-Cactus clips a haplotype. `piece`, `pv` and `nx` run within one line
(one record), so the tool links a contig's records in start order:

- A record's last piece has `ng:i:bp`, the contig bp between this record's end
  and the next record's start, which the graph lacks. `nr` gives the chunk the
  next record's first piece is filed under, written like `nx`
- The next record's first piece mirrors these as `pg` and `pr`
- A record that visits no node of the reference has no rows in the file. Its
  neighbours get `ng` and `pg` but no `nr` or `pr`
- A last piece with neither `nx` nor `ng` ends the contig's last record in the
  graph. The contig itself may go on
- On its first read of the GFA, the tool refuses two records of a contig that
  overlap or start at the same base, and a W line whose end column is not its
  start plus its nodes' lengths, since `ng` would then depend on which one to
  believe. A malformed file therefore fails before the slow second read
- The rows are the same for any order of the W lines, which `vg convert`
  changes from run to run

### abridged

```
seq cs cs+1 abridged path fragStart hapOffset pieces nsteps bp start end detail [pv] [nx] [pg] [pr] [ng] [nr]
```

- One row per path whose pieces in the chunk the tool moved to a detail
  record. See [Abridged chunks](#abridged-chunks)
- `pieces` lists the piece numbers it stands for as deltas, the first from 0,
  so `0,2` is pieces 0 and 2. `hapOffset` is where the first one starts
- `nsteps` and `bp` count the steps of those pieces and their nodes' bp
- `start` is the first piece's first handle on R and `end` the last piece's
  last handle on R, both absolute
- `detail` numbers the chunk's record that holds the pieces' rows
- The `pv`, `pg` and `pr` tags come from the first piece, and `nx`, `ng` and
  `nr` from the last

## Abridged chunks

[ADR 0004](adr/0004-abridged-detours.md) gives the reasons and measurements.

- A piece costs a reader its routes' interior steps, each counted once per
  use, plus its steps along R / 4. graph-walks decodes a step along R faster,
  but a cut still keeps and draws it
- When a chunk's pieces cost more than `abridge` interior steps, or its rows
  would compress to more than `abridgebytes`, the tool moves whole paths out
  of the chunk, costliest first, until the rest fit. A path's pieces in the
  chunk move together
- The chunk keeps its `ref` rows, its other pieces' `nodes`, `route` and `walk`
  rows, encoded without the moved pieces, and an `abridged` row per moved path
  with its steps, bp and where it leaves and rejoins the reference
- The moved pieces' rows go to detail record `detail` of the chunk, under the
  sequence `seq~cs` at position `detail × 16384`, so each record has a Tabix
  leaf bin to itself and a query for one reads no other. A window query names
  only `seq`, so it reads no record, and a viewer fetches a record on request
- A record holds a `nodes` row, `route` rows and `walk` rows. The tool numbers
  its routes from 0 and chains their tokens from 0, as for a chunk of its own,
  and its walk rows decode against the R of chunk `cs` of `seq`

## Decoding a walk row

R's step from position `i` holding handle `h` goes forward when `R[i] = h`,
to `R[i+1]`, and backward otherwise, to `R[i−1]` flipped. Each route below is
taken the way round its flip says.

1. If the first route has no entry, emit its interior
2. Emit `start`, at the first position in R holding its node
3. For each route with an entry:
   - step along R, emitting each handle, until the current handle is the
     route's entry. With `:n`, take exactly `n` steps instead
   - emit the interior
   - with no exit, stop: the piece ends off R
   - emit the exit, and move to the position in R holding its node that lies
     nearest the current position, the later one on a tie
4. Step along R until the current handle is `start + end`, or with `:n` take
   exactly the tail's `n` steps

The encoder decodes every walk row it writes with these rules. Where stepping
until a route's entry would stop at an earlier pass over the same node, as when
a haplotype takes a repeat copy the reference passes twice, it writes the step
counts. On HPRC v2.1's Minigraph-Cactus chr22 neither GRCh38 nor CHM13 passes a
node twice, and no walk row needs counts.

## Example

`tests/walks.rs` builds `tests/data/walks-two-refs.gfa` with `--chunk 10
--stay 0` and checks every row. Chunk 0-10 of R:

```
R#0#chr  0  1  ref    R#0#chr  0    0    0  2  2,2  6,6  nx:i:10
R#0#chr  0  1  nodes  6  6
R#0#chr  0  1  route  .  13  -9
R#0#chr  0  1  walk   H#1#h    100  100  0  2  2  2  .  nx:i:10
R#0#chr  0  1  walk   Q#0#chr  0    0    0  2  2  0  1  nx:i:10
```

- R is `>1 >2`: tokens `2` and `2` are ids 1 and 2, forward
- The one route has no entry, interior `13` (id 6 reversed) and exit `-9` (id 1
  reversed), so it reads `<6 <1`
- Q's piece starts on `>1` (handle 2) and ends there (`end` 0), then takes
  route 0 flipped, `>1 >6` with no exit: its steps are `>1 >6`
- H's piece starts on `>1`, ends on `>2` (`end` 2), and takes no route: its
  steps are `>1 >2`

## Scale

- The tool reads the GFA twice, so it takes a file path and refuses stdin;
  gzip input works
- The tool holds about 16 bytes per node, 24 more per node for each reference,
  and with `--sequences` the graph's bases
- Pieces wait for an external sort in up to 512 MB of memory and then in
  compressed runs in a temporary directory beside the output. The sort's merge
  encodes the chunks on every core
- A Minigraph-Cactus chromosome with two references takes minutes and a few GB
  of memory on a laptop
- The header fits in the file's first BGZF block, and a window reads two
  chunks, so a reader fetches a small fraction of a megabyte per window
  (`docs/format-2/scripts/window_sizes.py` measures it)

## Readers

- [@jbrowse/graph-walks](https://github.com/GMOD/graph-walks) 4 reads format 5
  only, and asks for a rebuild of any other file
- The graph genome viewer plugin,
  [BandageJS](https://jbrowse.org/demos/bandagejs/), ggbandage, ggtubemap and
  the tube map read through @jbrowse/graph-walks
- jbrowse.org hosts HPRC v2.1's files as
  `https://jbrowse.org/demos/hprc/hprc-v2.1-mc-grch38-f5.{GRCh38,CHM13}.walks.bed.gz`

In a JBrowse graph track, `walksUri` takes the prefix up to the reference
sample, so a track on hg38 reads the GRCh38 file and a track on hs1 would name
the CHM13 one. `defaultHaplotypes` lists the haplotypes the track draws until
the user picks others:

```json
"adapter": {
  "type": "RgfaTabixAdapter",
  "walksUri": "https://example.org/hprc-v2.1-mc-grch38.GRCh38",
  "assemblyNameToPanSN": { "hg38": "GRCh38" },
  "defaultHaplotypes": ["HG002", "HG00733"]
}
```
