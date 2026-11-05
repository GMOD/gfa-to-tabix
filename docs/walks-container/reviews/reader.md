# The walks file: what a reader needs and what it pays

Reviewer: reader. Lead angle: graph-walks' window read, end to end, measured
on format 6 as shipped, then the requirements that follow and the design that
meets them best.

Everything below was measured on ada unless marked **estimate**. Scripts and
raw results are in this directory (see [Method](#method)).

## Diagnosis

### What a window read does today

graph-walks 5.0.2 `WalkReader.cut`, over @gmod/tabix 3.13.1, for a window
`[start, end)`:

- Reads the header once, and the `.tbi` once
- **Walk read:** one `getLines` from the start of the chunk before the one
  holding `start − 1000` (or before a `#long` pass) to `end + 1000`. Because
  every row is filed at `cs cs+1`, this returns whole 64 kb chunks: the
  window's chunk(s) plus a whole lookback chunk
- **Departure read:** one `getLines` on `seq~departure` over the window ±
  1 kb ± `maxnode`, in parallel with the walk read
- Decodes every step of every row of every chunk read (`decodeChunk` →
  `decodeWalk`), then cuts to the window and its 1 kb context
- **Attach reads:** for each departure record with own sequence ≤ 64 kb
  whose leave piece the walk read lacks, it fetches that chunk again with a
  lookback of `ceil(maxnode / chunk)` chunks (up to 8 such reads, a second
  serial round trip)
- Requests: @gmod/tabix fetches each merged index chunk as one range
  request; on MC the walk read and the departure read were one request each
  in every window I measured, on pggb the departure read often two

### What it pays, MC chr22 (GRCh38, 463 haplotypes), format 6 at 64 kb

100 windows at 1 kb and 10 kb, 50 at 100 kb, 20 at 1 Mb, uniform over
chunks holding ≥ 50 walk rows; budgets lifted so every window reads.
KB are median / p90 / p99.

| window | total KB | requests med / max | decoded steps (median) | kept ÷ decoded | cut time ms |
|---|---|---|---|---|---|
| 1 kb | 98 / 464 / 1,189 | 1 / 7 | 2.15 M | 1.9% (0.6% in window) | 338 / 804 / 1,277 |
| 10 kb | 106 / 389 / 1,107 | 2 / 9 | 2.20 M | 8.1% | 363 / 844 / 1,878 |
| 100 kb | 154 / 358 / 1,064 | 2 / 8 | 3.47 M | 41% | 701 / 1,390 / 1,954 |
| 1 Mb | 580 / 889 / 1,655 | 2 / 4 | 19.0 M | 87% | 4,215 / 11,905 / 15,218 |

Where the bytes go (median KB per window; chunk bytes attributed from the
file's own BGZF blocks):

| window | window's chunks | lookback chunk | read past the last row | attach reads (p90) | departure read |
|---|---|---|---|---|---|
| 1 kb | 30 | 27 | 28 | 0 (327) | 0 |
| 10 kb | 29 | 28 | 28 | 0 (276) | 8 |
| 100 kb | 80 | 29 | 29 | 0 (189) | 8 |
| 1 Mb | 476 | 26 | 29 | 0 (189) | 22 |

- **Inherent:** every haplotype crosses every window (464 kept at the
  median at every size). The content a window needs, the routes and choices
  over the window plus one head per haplotype, is about 0.32 KB per kb of
  reference plus ~3 KB of heads (**estimate** from the column study below):
  ~4 KB at 1 kb, ~35 KB at 100 kb, ~320 KB at 1 Mb
- **Format and reader overhead at 1 kb–10 kb is ~25×:** a 1 kb window
  fetches about three chunks' worth (98 KB) to use 3 kb of one: the
  window's chunk, a whole lookback chunk, and ~28 KB more that @gmod/tabix
  fetches but returns no row from, mostly past the last row: it can't know
  where the last BGZF block ends, so `clampChunkEnds` ends the read at the
  next block boundary the index names, typically the block where the
  following chunk's rows resume
- **The tail is attach reads:** 23% of 1 kb windows pay them; p90 total goes
  from 137 KB without them to 464 KB with, and requests from 2 to 7–9, as a
  second serial round trip. They exist because a departure record lacks the
  steps of its own sequence
- **Decode, not bytes, is what a user feels at small windows:** 100 KB is
  one fast request; decoding 2.15 M steps to keep 36 k takes ~340 ms. At
  1 Mb nearly everything read is used (87%) and the cost, 15–19 M steps and
  4 s, is inherent: graph-walks' default budgets refuse all 20 of the 1 Mb
  windows ("zoom in to about 170–360 kbp")

### What it pays, pggb chrY (136 haplotypes), format 6 at 64 kb

Same method, default budgets (the reader as shipped):

| window | total KB | requests | refused | walk read | attach reads | departure read |
|---|---|---|---|---|---|---|
| 1 kb | 4,036 / 7,336 / 8,401 | 10 / 13 | 24 of 100 | 7 + 6 lookback + 13 past | 3,208 median | 607 median |
| 10 kb | 3,942 / 8,164 / 8,548 | 10 / 12 | 25 of 100 | similar | 3,208 | 710 |

- The walk read itself is small (~25 KB). Nearly all of a pggb window is
  departures: graph-walks widens the departure read by the header's
  `maxnode`, 1,000,000 bp on chrY, so a 1 kb window reads departures over
  2 Mb, and 24% of windows hit the 2 MB departure budget. Each attach read
  looks back `ceil(maxnode / chunk)` = 16 chunks, ignoring `#long`
- With both made `#long`-aware (a 30-line change to my copy,
  `walkReaderFixed.diff`), the same windows cost 1,040 / 2,185 / 4,019 KB in
  11 requests, 1 refused of 100: attach reads 681 KB median, departure read
  258 KB median, walk read ~28 KB. The remaining cost is departure records
  and their missing own steps, not the walk layout

### Is the one-base filing a misuse of Tabix?

- **Yes, by contract.** Tabix promises a region query returns the rows
  overlapping it. Format 6 rows state 1 bp and hold 64 kb. A plain
  `tabix file seq:a-b` over a 1 kb region (3 kb with context) returns rows
  only when a chunk start falls inside it (3 kb in 64 kb, about 5% of
  regions), and then the rows of the chunk after the region's start, never
  the chunk covering it (74 of 100 such queries fetch nothing at all)
- **The bin-sharing claim is true, for @gmod/tabix, at 64 kb only.** A 64 kb
  row aligned at 64 kb spans four 16 kb leaf bins, so Tabix files it in the
  128 kb bin it shares with its neighbour, and @gmod/tabix fetches a merged
  index chunk whole, up to `max_off`. Measured by refiling the same file
  (`refile.sh`) and asking @gmod/tabix what it fetches:

| 1 kb window, @gmod/tabix | median | p90 | p99 |
|---|---|---|---|
| format 6, `cs cs+1`, read from the chunk before (as shipped) | 88 | 121 | 205 |
| same rows at their true chunk span `cs cs+65536`, no lookback | 84 | 129 | 272 |
| true span plus 1 kb, as a straddling node would claim | 284 | 472 | 668 |

- **What it bought: nothing at the median, 8–25% at p90/p99**, because the
  one-base row can't tell the index it reaches into the next chunk, so the
  reader must always read a whole lookback chunk, which costs what the shared
  bin did. The lookback rule, `#long` and the `maxnode`-based reaches all
  descend from it (commits 3953bb1 and 842a19b, 2026-10-08, the day `--walks`
  landed; no ADR, no measurement)
- **htslib streams and stops at the first row past the region**, so for it
  the true span is cheaper: 42 KB median against 70 KB for the one-base file
  read from the chunk before (40 windows, bytes read counted with `strace`)
- **The real cause is that 65,536 is not a Tabix bin size.** At 16,384 (a
  leaf bin) and 131,072 (a level-4 bin) the true span costs exactly what the
  one-base filing does, at every window size:

| @gmod/tabix KB, median, read from the chunk before | 1 kb | 10 kb | 100 kb | 1 Mb |
|---|---|---|---|---|
| 16 kb chunks, `cs cs+1` | 45 | 54 | 124 | 899 |
| 16 kb chunks, `cs cs+16384` | 45 | 54 | 124 | 899 |
| 128 kb chunks, `cs cs+1` | 150 | 155 | 189 | 568 |
| 128 kb chunks, `cs cs+131072` | 150 | 155 | 189 | 568 |

- A row can't claim more than its tile, though: any overhang crosses a bin
  boundary and lands a level up (the "+1 kb" row above, 284 KB). So the
  right filing is the tile's exact span, with the reader widening its query
  by the longest node that is not a `#long` pass, as BAM readers widen by
  read length

### Chunk size: where the bytes and the decode go

Format 6 rebuilt with the 3.0.0 binary at four chunk sizes (`builds.sh`):

| chunk | file MB | window rows MB | departures MB | detail MB | walk rows | departure records |
|---|---|---|---|---|---|---|
| 4 kb | 137.2 | 104.3 | 4.8 | 28.0 | 3,988,946 | 340,738 |
| 16 kb | 70.7 | 36.6 | 1.4 | 31.4 | 1,000,639 | 93,166 |
| 64 kb | 59.2 | 18.7 | 0.5 | 38.0 | 250,281 | 24,648 |
| 128 kb | 63.4 | 16.1 | 0.3 | 42.8 | 123,426 | 13,945 |

- Each walk row's head, `path fragStart hapOffset piece nsteps start`, costs
  ~21 B compressed whatever the chunk (`colstudy.py`: 21.0, 20.9, 20.8 B).
  The choices themselves cost the same in total at every size (6.7, 6.4,
  7.8 MB). Smaller chunks only multiply heads: 5.3 → 20.9 → 83 MB
- A lean head, a fragment index (delta from the row before) instead of
  `path fragStart`, `hapOffset` as a residual against the fragment's base,
  and `=` for a start on R's first handle, costs 6.6 B as columns; as text
  rows, as Tabix keeps them, the 16 kb tiles' walk rows drop from 29.5 to
  14.1 MB
- Per window, format 6 as built at each size (graph-walks' real cut):

| median KB / median decode ms | 1 kb | 10 kb | 100 kb | 1 Mb |
|---|---|---|---|---|
| 64 kb | 98 / 338 | 106 / 363 | 154 / 701 | 580 / 4,215 |
| 16 kb | 61 / 84 | 71 / 114 | 152 / 423 | 998 / 4,606 |
| 4 kb | 146 / 36 | 155 / 51 | 417 / 375 | 2,967 / 4,315 |

- 16 kb halves small-window bytes and quarters decode, and costs 1.7× at
  1 Mb because of the heads. 4 kb is worse everywhere in bytes: Tabix can't
  address less than its 16 kb leaf, so a 1 kb window fetches 92 KB past
  its rows
- Decoding is also a reader choice. Format 6 rows can be decoded for a
  window without emitting the rest: `traverse` already jumps along R by
  occurrence. A windowed scan of the same 1 kb windows' rows (`bench.ts`)
  emits 35–77 k steps instead of 1.8–4.3 M and takes 18–98 ms against
  70–288 ms for `decodeChunk`: 2–4× less

## Requirements a format must meet

Derived from the above, for HPRC-scale graphs and 1 kb–1 Mb views:

- **R1, bytes ∝ window plus one tile of heads.** A 1 kb window should cost
  tens of KB, not ~100; a 1 Mb window should stay within ~1.5× its content.
  That needs small tiles *and* cheap per-haplotype heads, since heads × tiles
  is what makes small tiles expensive at 1 Mb
- **R2, one round trip.** The walk read and the departure read in parallel,
  and no data-dependent second round. Format 6's attach reads violate this in
  23% of MC windows and in nearly every pggb window
- **R3, decode work ∝ window.** Tiles ≤ 16 kb, rows decodable for a
  window without emitting the rest
- **R4, honest intervals.** A row's interval covers what it holds, so the
  index computes lookback, generic `tabix` returns the right rows, and the
  reader needs no chunk arithmetic; tiles must be Tabix bin sizes so honest
  intervals cost nothing
- **R5, local hints.** Reaches derive from the region (`#long` passes), never
  from one global `maxnode`, which on pggb turned a 1 kb window into a 2 Mb
  departure read
- **R6, budgets before bytes.** The index estimates a read's bytes exactly
  (it does today, `bytesForRegions` matched the fetched bytes in every
  window)
- **R7, bounded worst case.** Satellites and rDNA keep abridged rows; a
  departure's large own sequence becomes detail fetched on request
- **R8, a coarse view.** At 1 Mb, 15–19 M steps are inherent and the reader
  refuses all-haplotype windows over ~200–350 kb. A view there needs a
  summary that isn't steps; format 6's departure read (22 KB median at 1 Mb)
  is most of one

## The design I propose: honest 16 kb tiles with lean heads

### Container and unit

- **Keep BGZF + Tabix.** Static hosting works; the reader stack exists; the
  measured overheads attributable to Tabix are either fixable inside it
  (tile = bin size) or in @gmod/tabix (the read past the last row). A custom
  tile directory or bigBed would buy an exact end byte and sub-16 kb tiles,
  ~10–15 KB per small window (**estimate**: the prototype's 18 KB walk read
  at 1 kb against a ~4–7 KB floor), not worth a new index and reader now
- **Unit: a fixed reference tile with a shared dictionary.** Every
  haplotype crosses every window, so a grid tile holds a dense, even load;
  sites and bubbles are unbounded on pggb, nodes are too fine, and
  per-haplotype pieces filed alone would repeat each route's interior per
  haplotype that takes it. The tile's R, `nodes` and `route` rows are the
  dictionary its walk rows index, as in format 6
- **Tile: 16,384 bp**, a Tabix leaf bin. The writer refuses `--chunk` other
  than 16,384 or 131,072, the two bin sizes useful for tiles

### Records

- Every window row of the tile `[cs, cs+16384)` is filed at exactly
  `seq cs cs+16384` (clipped to the sequence's end)
- `ref`, `nodes`, `route`, `abridged` rows as format 6
- `walk frag hres piece nsteps start[@k] choices`:
  - `frag`: the W-line fragment's index in the sequence's fragment table, as the
    difference from the previous walk row's in the tile
  - `hres`: `hapOffset − cs − base(frag)`
  - `start`: `=` when it is R's first handle, else as format 6
- Fragment table: `seq~paths k k+1 path <sample#hap#contig> <fragStart>
  <base>`, one row per W-line fragment in first-tile order; 1,074 rows,
  83 KB of text and 20 KB compressed on MC chr22, read once per sequence
- Departure records as format 6, plus:
  - own sequence ≤ 4 kb inline as delta tokens (MC chr22 at 16 kb: 75,229
    rows carry 0.9 Mb of it, ~0.1 MB compressed, **estimate**)
  - own sequence over 4 kb (1,988 rows carrying 61 Mb) as a detail record
    under `seq~own` at a slot of its own, fetched when a viewer opens it,
    as abridged pieces are; the record carries `ownBp` for drawing it
    closed
- Header: `maxnode` becomes the longest node not listed in `#long`
  (≤ the tile); `#long` as now

### A reader's window query

- Read the header and the `seq~paths` table once per sequence
- Walk read: `seq` over `[start − ctx − maxnode, end + ctx + maxnode)`,
  widened to cover any `#long` pass it overlaps. The index returns exactly
  the tiles that hold steps there; no chunk arithmetic
- Departure read, in parallel: `seq~departure` over the same extent
- Decode each tile: R and routes once, then each walk row with a windowed
  traversal that emits steps only within the extent; map `frag` to the
  path name and `hapOffset = cs + base + hres`
- Rebuild paths as graph-walks does now: join a fragment's pieces by
  `piece`, compute departures inside a piece from its steps, take the rest
  from records, with own steps inline or shown closed

## Measurements against format 6

### Method

- Data: HPRC v2.1 MC chr22 GFA and HPRC pggb chrY GFA on ada
  (`~/work/arb-format-opus/in`), built with the gfa-to-tabix 3.0.0 binary
  (`builds.sh`; 64 kb rebuild byte-identical in size to `~/work/rel3`'s)
- Windows: `measure.ts` and `tbxcost.ts` draw the same seeded windows for
  every file of a graph: 100 at 1 kb (seed 7), 100 at 10 kb (8), 50 at
  100 kb (9), 20 at 1 Mb (10), starts uniform over chunks holding ≥ 50 walk
  rows (`data/*.sample.tsv` on ada)
- `measure.ts` runs graph-walks 5.0.2's `WalkReader.cut` (my rsync'd copy on
  ada) on @gmod/tabix 3.13.1 through a filehandle that counts range reads and
  bytes, a fresh `TabixIndexedFile` per window (no cache), header and index
  reads excluded; budgets lifted on MC, default on pggb
- `tbxcost.ts` asks @gmod/tabix's own `blocksForRange` what it would fetch,
  without decoding, for layouts no reader decodes yet; `bytesForRegions`
  agreed with the counted bytes in every measured window
- `chunkbytes.py` attributes each BGZF block's compressed bytes to the rows
  in it, per chunk; `summeasure.py` splits each window's bytes with it
- `colstudy.py` compresses each chunk's rows alone (zlib 6) as text and as
  column streams; `proto.py` writes the proposed layout from a 16 kb format 6
  build (true span, lean walk rows, `seq~paths`, a BGZF block flushed at each
  tile start) for `tbxcost.ts`; `compare.py` builds the table below
- `htsread.sh` counts the bytes htslib's `tabix` reads with `strace`
- Timing on ada while it ran other users' jobs (load 12–31): treat ms as
  relative

### MC chr22, per window, KB median / p90 / p99

| layout | 1 kb | 10 kb | 100 kb | 1 Mb |
|---|---|---|---|---|
| format 6 as shipped, everything fetched | 98 / 464 / 1,189 | 106 / 389 / 1,107 | 154 / 358 / 1,064 | 580 / 889 / 1,655 |
| format 6, walk + departure reads only | 92 / 137 / 227 | 99 / 160 / 316 | 147 / 196 / 251 | 565 / 752 / 1,536 |
| format 6 at 16 kb, everything fetched | 61 / 255 / 706 | 71 / 300 / 714 | 152 / 232 / 679 | 998 / 1,163 / 2,174 |
| proposal, walk read (prototype file) | 18 / 29 / 53 | 22 / 30 / 249 | 65 / 88 / 116 | 495 / 694 / 1,644 |
| proposal, departure read (prototype file) | 8 / 38 / 53 | 8 / 38 / 57 | 15 / 45 / 53 | 52 / 98 / 98 |
| content floor (**estimate**) | ~4 | ~7 | ~35 | ~320 |

- Requests: format 6 1–2 per window at the median and up to 7–10 with
  attach reads; the proposal 2, both in the first round, no attach reads
- Proposal file: 56.8 MB against format 6's 59.2 MB (`.tbi` 58 KB against
  41 KB): window rows 22.5 MB against 18.7 MB (36.6 MB for format 6 at
  16 kb), departures 1.4 MB against 0.5 MB, detail 31.4 MB against 38.0 MB,
  fragment table 0.02 MB
- Decode: format 6 at 16 kb measured 0.58 M steps and 84 ms at 1 kb against
  2.15 M and 338 ms at 64 kb; windowed traversal a further 2–4×
  (**estimate** for the proposal: ~25–40 ms at 1 kb)
- Block alignment alone does not remove @gmod/tabix's read past the last
  row: format 6 rewritten with a block flushed at every chunk start read
  88 KB median at 1 kb, the same as before. That fix belongs in
  @gmod/tabix (end a chunk at `maxv.blockPosition` when `maxv.dataPosition`
  is 0)

### pggb chrY

| layout, `tbxcost.ts`, reach capped at a tile | walk read, 1 kb | 100 kb | 1 Mb | departure read, 1 kb |
|---|---|---|---|---|
| format 6, from the chunk before | 29 / 113 / 1,637 | 59 / 359 / 1,523 | 226 / 667 / 2,796 | 258 / 706 / 1,701 |
| proposal (prototype file) | 11 / 40 / 996 | 38 / 109 / 1,444 | 225 / 709 / 3,145 | 197 / 446 / 1,934 |

- File: 199.0 MB against 192.2 MB (format 6 at 16 kb: 203.5 MB). Detail
  records are 162–179 MB of each; window rows 16.9 MB against 11.5 MB,
  departures 16.1 MB against 12.1 MB
- Format 6's reader as shipped pays 4.0 MB and 10 requests at the median
  for a 1 kb window, 3.2 MB of it attach reads; `#long`-aware reaches cut
  that to 1.0 MB; the proposal removes the attach reads, leaving
  ~210–300 KB (**estimate**: walk + departure reads above), which is the
  departure records of collapsed repeats, a placement question, not a
  layout one

## Tradeoffs and failure modes

- **1 Mb windows cost about the same, not less:** 495 KB walk read against
  540, p99 1,644 against 1,469. Heads are cheap but 64 tiles still carry 64
  sets; 128 kb tiles would win at 1 Mb and lose 3× at 1 kb
- **More departure records:** pieces end at 4× as many tile boundaries, so
  records rise 3.8× on MC (93 k) and 2× on pggb (858 k); the departure read
  at 1 kb goes from 0 to 8 KB median on MC. A rule that skips records
  between pieces in adjacent tiles would recover it but would make a reader
  read both tiles; I'd keep format 6's simple rule
- **Fragment table:** a reader can't name a walk row without `seq~paths`;
  one more read per sequence (83 KB of text on chr22, larger on chr1)
- **Repeats (pggb):** `@k`/`:k` copies named rise 300 k → 424 k at 16 kb;
  the prototype file is 3.5% larger. Unchanged in kind
- **Long nodes:** `#long` lines rise 37 → 43 on pggb chrY; MC has none.
  The reach rule handles them as now, from the region
- **Inversions:** no change; a strand switch inside a piece decodes as now
- **Huge tiles:** abridging works per tile as now; 16 kb tiles abridge
  fewer paths (MC 1,448 against 2,468)
- **Generic tools:** `tabix seq:a-b` returns every tile overlapping, which
  is honest; decoding still needs graph-walks
- **Not measured end to end:** no reader decodes the prototype; its bytes
  are real, its decode time is an estimate. Inline own steps are an
  estimate from `ownBp`
- **Format break:** format 7; gfa-to-tabix, graph-walks, bandage-core and the
  plugin release together, and hosted data is rebuilt (allowed)

## Other questions

- **Should walks and `.graph.bed.gz` stay separate?** Yes. They file
  differently (tiles against whole components under one interval, which on
  a base-level slice makes a 1 kb window fetch ~1.5 MB, ADR 0002) and serve
  different needs (the coarse tier, carriers, rGFA graphs without walks).
  The walks file already holds all a window's drawing needs (R, nodes,
  routes); merging would force one filing on both
- **Tabix or something else?** Tabix, with tiles at a bin size and honest
  intervals. Parquet row groups are MB-scale and need footer and page-index
  reads before data; a GBWT answers haplotype queries, not region reads over
  HTTP; bigBed's R-tree is a heavier writer for a regular grid with the same
  result. A custom fixed-grid directory is the one to revisit if sub-16 kb
  tiles ever matter

## Verdict

- Format 6's `cs cs+1` filing is a misuse of Tabix that bought nothing at
  the median: the shared 128 kb bin it avoids is an artifact of 65,536 not
  being a bin size, and the whole-chunk lookback it forces costs what the
  shared bin did (88 KB against 84 KB for a 1 kb window). htslib does better
  with honest rows (42 against 70 KB)
- What a reader actually pays at 1–10 kb is ~25× the window's content:
  whole 64 kb chunks, a whole lookback chunk, @gmod/tabix's read past the
  last row, every step decoded (2.15 M to keep 36 k), and in a quarter of
  windows serial attach reads of whole remote chunks. At 1 Mb the cost is
  inherent (15–19 M steps) and the reader refuses all-haplotype windows
  anyway
- On pggb the walk layout hardly matters: the departure read and attach
  reads are 95% of the bytes, made worse by graph-walks deriving reaches
  from the global `maxnode` (1 Mb)
- **The project should move to honest 16 kb tiles:** rows at
  `seq cs cs+16384`, a reach-based query instead of the chunk-before rule,
  lean walk heads with a per-sequence fragment table, and departure records
  that carry small own sequence and defer large. Measured on MC chr22: a
  1 kb window's walk read 88 → 18 KB, 10 kb 92 → 22 KB, 100 kb 132 → 65 KB,
  1 Mb 540 → 495 KB, the file 59.2 → 56.8 MB, and no attach round trip
- **Smallest first step, no format change:** in graph-walks, take the
  departure read's reach and the attach reads' lookback from `#long` instead
  of `maxnode` (`walkReaderFixed.diff`). On pggb chrY it cuts a 1 kb window
  from 4.0 MB to 1.0 MB and refusals from 24 to 1 in 100. Then, as format 7,
  the writer change is small: `--chunk 16384` and the end column
  `cs + chunk`, with graph-walks querying by reach; lean heads and departure
  own steps follow in the same break
