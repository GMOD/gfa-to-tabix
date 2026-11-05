# Proposal: an interval-native walks file

Reviewer: native. Lead angle: every row filed at its real span, a plain
`tabix file region` returns exactly what the region needs, each row decodable
alone or with a small named set of companions. Everything below is measured on
the 3.0.0 format 6 files for HPRC v2.1 Minigraph-Cactus chr22 (463
haplotypes, `mc22.GRCh38.walks.bed.gz`, 59.2 MB) and HPRC release 2 pggb chrY
(136 haplotypes, `pggbY.GRCh38.walks.bed.gz`, 192 MB), with a prototype that
rewrites each into the proposed layout. Scripts and outputs are in this
directory (`scripts/`, `*.jsonl`, `verify-*.log`).

## Diagnosis

- **What drove `seq cs cs+1`:** commit 3953bb1 (2026-10-08), one day after
  `--walks` landed: "A full-chunk interval shares a 128 kb Tabix bin with the
  neighbouring chunk, so a query pulled both." No measurement then or since;
  the README line in 842a19b and the spec sentence are that claim restated.
  At the time a row was a piece's full step list (format 1); routes, chunk-local
  route ids and the cross-row delta chains came later and now depend on the
  whole chunk arriving together
- **The claim is half true, and the cure is wrong.** Measured with a counting
  filehandle under the real @gmod/tabix 3.13.1 (`scripts/measure.mjs`) and
  under htslib's `tabix` by strace (`scripts/htslib_bytes.py`), on the same
  rows filed at 64 kb spans (`native64`): a 1 kb window costs @gmod/tabix 95 KB,
  the same as format 6's 98 KB, because @gmod/tabix merges every chunk of the
  128 kb bin that lies within 65 KB of file into one range and reads it from
  the bin's first row. htslib reads 30 KB for the same query: it prunes with
  the linear index and stops at the first row past the window. So "a query
  pulled both" describes @gmod/tabix's merge heuristic, not Tabix. The fix is
  not to file rows at one base but to keep every row inside a 16 kb leaf bin:
  then @gmod/tabix reads 25 KB and htslib 19 KB (`native16b` below)
- **What 1 bp filing costs:**
  - a plain `tabix file chr22:15-35` is wrong: for 1 kb and 10 kb windows the
    median query returns 0 rows (`f6-gmod-plain.jsonl`); only a reader that
    knows `chunk:i:` and rounds down gets anything, and it then reads the chunk
    before as well (graph-walks' `walkQueryStart`)
  - every window pays the chunk pair whatever its size: 98 KB median for
    1 kb, 10 kb and 100 kb alike under @gmod/tabix (81 KB under htslib), in
    two requests (walk read and `~departure` read)
  - a departure that spans the window is invisible to the walk read, so the
    file needs the `~departure` sibling, bin-cut records, `#long` lookback
    and `#hole` lines, and the reader a second read and a dedup rule
  - the chunk is the decoding unit: a walk row's route ids are indexes into
    the chunk's route rows, whose tokens chain across rows; a `nodes` row holds
    lengths for the chunk's routes. Nothing in a chunk decodes alone
- **What it buys:** one contiguous run of rows per chunk, and a chunk-local
  encoding that is denser than a self-describing one: format 6's window-read
  rows (ref, nodes, route, walk, departure) are 17.3 MB of the 59.2 MB file
  (the other 37.8 MB is the abridged detail tier no window reads); the
  prototype's window-read rows are 25.7 MB. That density is the one real
  argument for the chunk, and it only pays at windows of a chunk or more
- **What is right in format 6 and stays:** departure records are already
  interval-native (filed at their stretch, cut at aligned bin-sized blocks,
  deduped by key); the detail tier for abridged paths; positions stated by the
  file so a reader never chooses a pass; one file per reference sample; the
  header's haplotype list; `passes` on reference nodes

## The ideal design

One sequence per reference contig, three row kinds, every row at its real
span and never wider than the index's 16 kb leaf bin except a site that is
genuinely longer, which is cut at aligned bin-sized blocks exactly as format
6 cuts departure records. Cell = 16,384 bp, the Tabix leaf bin.

### Header

```
#walks      format:i:7  cell:i:16384  abridge:i:250000  abridgebytes:i:750000
#reference  GRCh38
#haplotype  CHM13#0            (index 0, 1, ... in file order)
#fragment   CHM13#0#chr22  15729441   (index 0, 1, ...: each W line, path and fragStart)
#long, #hole: not needed; see below
```

### Rows

```
S a b R steps lengths passes firstDelta
S a b H frag,off,strand,shift;frag,off,strand,shift;...
S a b V leaveDelta leaveStrand rejoinDelta rejoinStrand alleles lengths carriers
```

- **`R`, one per cell:** the reference nodes that overlap `[cs, cs+16384)`,
  so a node straddling a cell boundary is listed in both cells and a node
  longer than a cell in every cell it covers; `a = max(cs, first node start)`,
  `b = min(cs + 16384, last node end)`, `firstDelta` = the first node's start
  minus `a` (0 or negative). `steps` are delta handle tokens from 0 as today,
  `lengths` and `passes` as on a format 6 `ref` row. A reader dedups nodes by
  offset. This replaces `#long` and the lookback: a window inside a 1 Mb N run
  gets that node from its own cell's row
- **`H`, one per cell, `[cs, cs+16384)`:** for each fragment with a step on a
  node overlapping the cell, its first such step in walk order: `frag` the
  fragment index as a delta from the previous entry, `off` the node's start
  minus `cs` (negative for a straddling node), `strand` the direction it walks
  R there, `shift` = its own offset at that step minus the reference offset.
  This is the only per-haplotype-per-cell cost, and the only place haplotype
  coordinates come from
- **`V`, one per site:** a site is a pair of reference breakpoints a path
  leaves R at and rejoins at (format 6's departure ends: breakpoint and strand,
  with `leaveDelta = leaveBp − a` and `rejoinDelta = rejoinBp − leaveBp`),
  `alleles` the distinct interiors taken between them as delta handle tokens
  (`.` for a direct jump; `;`-separated), `lengths` their node lengths,
  `carriers` the fragments taking each allele: sorted index deltas, or a hex
  bitmap `#...` when more than 60 (common alleles). Every fragment also has
  a start half-site, with no leave end, and an end half-site, with no rejoin
  end: their allele is the fragment's leading or trailing steps off R, or
  `.` when it starts or ends on R. They mark where a fragment begins and
  ends on S, which no other row does (the first prototype lacked them and
  its walks ran on along R into the next fragment). Filed at
  `[min(bp), max(bp))`, or one base when the breakpoints coincide
- **Cutting:** a site longer than 16 kb is cut at aligned multiples of 2^14,
  2^17, 2^20, 2^23 and 2^26 bp, greedy largest block first, as
  `src/departures.rs::blocks` does from 2^17. The block holding the site's
  start carries the alleles; every later block is a **stub**: the same head,
  `*@start/steps/bp` per allele and the same carriers. A reader dedups sites
  by `(leaveBp, leaveStrand, rejoinBp, rejoinStrand)`; a stub tells it which
  fragments cross the window, in which direction, with how much own sequence,
  which is what a departure record tells it today; the interior is one range
  request away at `start`
- **Abridging:** where a cell's alleles exceed the budget (250 k interior
  steps or 750 KB of text per 16 kb cell, a quarter of format 6's chunk
  budget), the largest alleles move to `S~detail` records at `rec × 16384`
  and the site lists `*rec/steps/bp` in their place. Same mechanism as ADR
  0004, at allele rather than path granularity, so a satellite array that
  136 haplotypes each cross on their own path is one site whose 136 alleles
  are each a record
- **No `nodes`, `route`, `walk`, `abridged` or `departure` rows, no sibling
  `~departure`, no `#long`, no `#hole`:** a reference hole is simply a gap
  between R rows; a departure across it is a site like any other
- With `--sequences`, `SQ:Z:` on `R` rows (the nodes' bases in order) and on
  `V` rows (each allele's bases, `;`-separated)

### Why sites and not pieces at their spans

- A piece filed at its real span is still only decodable with its chunk's
  routes, or carries its own full step list. Keeping the chunk-local route
  ids while filing rows at spans gives nothing: `native64` above
- A site is the natural unit: it is what a route already is in format 6 (an
  entry, an interior, an exit), with the walk rows transposed into it. Every
  (haplotype, route) incidence that format 6 spends a choice token on, this
  layout spends a carrier token on: 25,993,363 incidences on chr22 either way
- A deletion or jump is then a site that overlaps every window inside it, so
  the window query itself returns "fragment f crosses here from x to y", with
  no second sibling read, no dedup against the walk read, and no rule about
  which read a departure belongs to
- pggb's copies need no `@k`/`:k`: a site's breakpoints are offsets, so the
  pass is stated by position, and `passes` on the R row says where the
  position was the placement's choice

### The query a reader runs for a window [w0, w1)

- One range query over the cells the window overlaps:
  `[floor(w0 / 16384) × 16384, ceil(w1 / 16384) × 16384)`, as
  `tabix file S:q0+1-q1` or `getLines(S, q0, q1)`. Rounding to the cell
  costs nothing under @gmod/tabix (it fetches whole BGZF blocks and the index
  resolves to 16 kb anyway: 25 KB median either way, `n16c-gmod-cell.jsonl`
  against `n16c-gmod.jsonl`) and 9 KB under htslib, and it is what makes the
  `H` entries usable: every site between a fragment's entry at the cell's
  edge and the window is in hand. On chr22 that is 1 request at the median
  and at most 3; on chrY 1 at the median, 4 at p90 (stubs of long sites in
  coarser bins)
- From the rows: R = the nodes of every `R` row, deduped by offset, with
  `byStart` and `byEnd` maps; sites = every `V` row deduped by key, a stub
  recorded as a crossing; presence = every `H` entry
- Optional fetches, each one request, only when the view needs them: a
  stub's interior from `S:start-start+1`; an abridged allele from
  `S~detail:rec×16384`. Neither is needed to say which haplotypes are
  present, absent, or crossing, or to place every in-window step
- Nothing about lookbacks or sibling sequences; the header's `cell` is the
  one number a reader uses, to round the query

### Rebuilding every haplotype's path

For each fragment f, from each start point, walk until the window ends:

- Start points: f's `H` entry in the first cell it appears in (the lowest
  `shift + offset` among its entries is its earliest own coordinate), plus
  the rejoin end of every site in the window that carries f, its start
  half-site included; a walk that reaches a state another walk visited stops,
  so the union covers every run of f through the window, including a return
  after a jump out. A walk ends at f's end half-site
- At node `o` walked in direction `d`: emit the handle (flipped when `d` is
  −); leave breakpoint = `o + len` on `+`, `o` on `−`; if a site has that
  leave end and f in a carrier list, emit its allele's interior and go to the
  rejoin end: `byStart[rejoinBp]` on `+`, `byEnd[rejoinBp]` on `−`; otherwise
  step to the adjacent node. No site: the path follows R. Own coordinate =
  `shift + reference offset` at the start, plus every length walked since
- A fragment with no `H` entry and a site carrying it over the window is
  absent here by that site (a deletion, a jump, a strand switch, exactly as
  the departure record's class rules say); one with neither has nothing
  aligned here. Where `passes > 1` at an end, the site is a placement choice,
  as today
- `scripts/verify.py` implements this reader in 120 lines of Python and
  checks it against format 6 decoded by `scripts/decode6.py` (an independent
  decoder of every format 6 rule, including `@k`, `:k`, abridged rows and
  detail records): whole paths of 6 haplotypes end to end, and every
  fragment's runs through 60 random windows rebuilt from the window's rows
  alone. Results in [Measurements](#measurements)

### Container

- Tabix stays. Once every row is inside a leaf bin, Tabix does exactly what
  the index promises, in htslib and in @gmod/tabix, from any static host, and
  `tabix` itself becomes a correct tool on the file. What was wrong was the
  rows, not the index
- Alternatives considered: a bigBed-style R-tree or Parquet row groups would
  give the same 16 kb resolution with less per-row text, at the price of a
  binary writer, a new reader and losing `tabix`, `zcat`, `awk` on the file;
  a GBWT-like structure is sublinear in haplotypes but has no reference
  coordinates without its own index (gbz-comparison.md: 18-43 round trips per
  window). None removes the one cost that matters here, the per-cell presence
  row, and none is worth a second reader stack now
- The node/link index (`.graph.bed.gz`) and this file: the `R` and `V` rows
  are a node and link index of the haplotype-carried subgraph in path graphs
  (every node a path visits is on R or in an allele; every link a path
  traverses is implied), so for path graphs the graph track could read this
  file alone, which open-problems.md already asks. For rGFA the index stays.
  Merge later, as ADR 0002 did: when another change forces it

## Measurements

### Method

- Fixed random windows, seed 42, 200 per size at 1 kb, 10 kb, 100 kb and
  1 Mb over chr22:10.5-50.8 Mb (`windows.jsonl`) and chrY:2.8-56.8 Mb
  (`windowsY.jsonl`)
- Format 6 read as graph-walks 5 reads it: the walk read from the chunk before
  `start − 1000` (or before a `#long` pass overlapping the window) to
  `end + 1000`, plus the `~departure` read over the same extent ±1024
  (`measure.mjs f6`). The prototype read as one plain range query
  (`measure.mjs plain`)
- Bytes and requests: `scripts/measure.mjs` wraps the data file in a
  counting filehandle under @gmod/tabix 3.13.1's real `getLines` (bins,
  linear-index floor, 128 kb floor, chunk merging, early stop, read-ahead); a
  request is one merged chunk. `scripts/htslib_bytes.py` runs `tabix` under
  `strace` and sums its reads of the data file; its "requests" are syscalls,
  not HTTP ranges
- Prototype: `scripts/emit_native.py` decodes the format 6 file and writes
  the layout above; `bgzip` and `tabix -p bed`. `native16c` is the final 16 kb
  layout (`native16b` the same without fragment end markers, byte-identical
  in the tables), `native64` the same rows at 64 kb cells with format 6's
  chunk budgets, `native16` an earlier variant without stubs

### MC chr22, bytes per window (KB, median / p90 / p99 / max) and requests

| reader | layout | 1 kb | 10 kb | 100 kb | 1 Mb | requests med / max |
|---|---|---|---|---|---|---|
| @gmod/tabix | format 6 (graph-walks read) | 98 / 152 / 261 / 299 | 98 / 146 / 302 / 376 | 140 / 205 / 420 / 544 | 573 / 784 / 1455 / 1523 | 2 / 2 |
| @gmod/tabix | format 6, plain `tabix` query | 0 rows at the median | 0 rows at the median | 2,088 rows (whole chunks or none) | | 0-1 |
| @gmod/tabix | **native16c**, window or cell-rounded query | **25 / 96 / 265 / 344** | **27 / 117 / 344 / 344** | **79 / 161 / 399 / 1328** | 634 / 986 / 3018 / 3047 | **1 / 3** |
| @gmod/tabix | native64 | 95 / 193 / 518 / 518 | 98 / 254 / 453 / 518 | 136 / 352 / 697 / 1504 | 605 / 1182 / 3211 / 3235 | 1 / 4 |
| htslib | format 6 (graph-walks read) | 81 / 126 / 233 / 238 | 81 / 120 / 288 / 311 | 126 / 188 / 419 / 503 | 558 / 769 / 1441 / 1476 | |
| htslib | native16c, window query | 19 / 39 / 177 / 213 | 29 / 52 / 201 / 225 | 80 / 131 / 329 / 1267 | 630 / 919 / 3021 / 3050 | |
| htslib | native16c, cell-rounded query | 28 / 52 / 202 / 213 | 30 / 54 / 201 / 225 | 82 / 146 / 330 / 1277 | 630 / 925 / 3022 / 3051 | |
| htslib | native64 | 30 / 71 / 323 / 323 | 36 / 90 / 332 / 343 | 75 / 174 / 441 / 1430 | 535 / 1049 / 3215 / 3242 | |

- Small windows: 3.9× fewer bytes and half the requests under @gmod/tabix,
  4× fewer under htslib. The gain comes entirely from rows that fit the leaf
  bin: `native64` under @gmod/tabix is format 6's cost again
- 1 Mb windows: 11% more at the median, twice at p99. The median is the
  denser self-describing rows (25.7 MB window-read against 17.3 MB); the p99
  is LCR22A (18.0-18.9 Mb), where the prototype's text budget keeps alleles
  inline that format 6's compressed-byte budget abridges (native detail tier
  21.1 MB against format 6's 37.8 MB). A budget on compressed size, as the
  writer has, brings that tail back; it is a knob, not the layout
- Rows returned per 1 kb window: 20 for the window, 281 for its cell
  (native16c), against 3,440 (format 6)

### pggb chrY (136 haplotypes, 107,467 revisited nodes, 37 `#long` passes)

| reader | layout | 1 kb | 10 kb | 100 kb | 1 Mb | requests med / p90 |
|---|---|---|---|---|---|---|
| @gmod/tabix | format 6 (graph-walks read) | 51 / 442 / 804 / 841 | 51 / 459 / 909 / 1819 | 51 / 612 / 2105 / 2105 | 47 / 2044 / 4980 / 4993 | 2 / 4 |
| @gmod/tabix | **native16** | **15 / 274 / 346 / 346** | **15 / 277 / 441 / 761** | **17 / 319 / 581 / 605** | **15 / 791 / 2512 / 2529** | **1 / 4** |
| htslib | format 6 | 26 / 248 / 571 / 572 | 26 / 284 / 780 / 1520 | 38 / 426 / 1960 / 1960 | 23 / 1769 / 4859 / 4872 | |
| htslib | native16 | 19 / 122 / 182 / 187 | 19 / 149 / 280 / 575 | 21 / 178 / 375 / 400 | 19 / 690 / 2466 / 2466 | |

- Half of chrY's windows lie in N runs and cost a block either way; the
  other half halve, and the worst 1 Mb window halves from 5.0 to 2.5 MB. The
  format 6 rows a 1 kb window returns are 116 at the median and 17,076 at
  p90, nearly all departure records; the native rows are 3 and 669

### File sizes and what a window reads

| | format 6 | native16 final | native64 |
|---|---|---|---|
| MC chr22 file | 59.2 MB | 47.3 MB (native16c) | 42.4 MB |
| of which window-read rows | 17.3 MB (ref 1.2, nodes 0.6, route 2.6, walk 12.9, departure 0.4) | 25.7 MB (R 1.3, H 5.6, V 18.8) | |
| of which detail tier | 37.8 MB | 21.1 MB (14,805 alleles) | |
| index | 41 KB | 170 KB (one leaf bin per detail record) | 23 KB |
| sites / rows | 786,690 routes, 250,281 walks, 31,239 departure rows | 886,876 sites, 888,287 V rows (415 cut, 1,411 stubs), 2,229 H, 3,102 R | |
| pggb chrY file | 192 MB | 144 MB (V 5.9, H 3.8, R 1.1, detail 101.7) | |
| chrY sites | 130,039 routes + 853,629 detail routes, 1,224,004 departure rows | 228,396 sites: 183,446 under 1 kb, 15,929 over 16 kb, 466 over 8 Mb; 98,169 stubs; 30,799 abridged alleles | |

- V row bytes on chr22, gzipped: heads 5.2 MB, alleles 3.7, lengths 1.1,
  carriers 7.0. The delta-coded head is a fifth of the row; a binary container
  would shave that, nothing else
- The `H` rows are the price of 16 kb cells: 1.24 M entries, 5.6 MB, 12% of
  the file, 4.5 bytes per fragment per cell. At 64 kb cells they are a
  quarter of that, but then @gmod/tabix reads the cell pair again

### Correctness

- Whole paths, MC chr22: 6 haplotypes (CHM13#0, HG00097#1, HG002#1,
  NA19240#1, HG01175#1, HG03239#1), 22 fragments, 8,315,497 steps, rebuilt
  from the native rows alone and compared step by step with format 6's
  decode: **22 of 22 fragments identical** (`verify-n16c.log`). An earlier
  prototype without fragment end markers walked on past a fragment's last
  step on R; the half-sites fixed it
- Windows, MC chr22: 60 random windows, every fragment's runs through the
  window rebuilt from the cell-rounded query alone and compared with the
  whole walk's runs restricted to the window: **60 of 60 windows exact for
  every fragment** (145 stub fetches across them). A window
  query not rounded to cells rebuilt 46 of 60: a presence entry at the
  cell's edge walks through rows the narrower query never returned, which is
  why the procedure rounds
- pggb chrY, 8 haplotypes including the ones with the most departure records
  (HG03098#1, HG01099#1, HG03688#1, NA20762#1, HG02602#1), 41 fragments,
  34,483,618 steps: **whole paths 11 of 41 identical, windows 49 of 60
  exact** (5,193 stub fetches over the 60 windows). Every failure is in the
  collapsed ampliconic repeats and has one cause, the visit ambiguity under
  [Tradeoffs](#tradeoffs-and-failure-modes): the native walk takes a site at
  a pass where the truth follows R, because the same fragment departs there
  on another pass. Outside those regions the copy-naming by position works:
  the 11 whole paths and 49 windows include haplotypes with thousands of
  departure records
- The decoder also reproduced the whole chr22 file: 252,853 pieces,
  628,622,576 steps, every row decoded with the spec's rules and the
  encoder's invariants asserted

## Tradeoffs and failure modes

- **A carrier list cannot say which pass departs.** Where a fragment walks
  the same reference positions twice (pggb's collapsed repeats, where a
  haplotype has more copies than the reference, and any tandem duplication
  of reference sequence), it visits a site's leave end twice and may depart
  on one visit and follow R on the other. Format 6's walk row is a sequence
  of choices, so it states this; a set of carriers does not, and the chrY
  verification shows it. Counted with `scripts/visits.py` (`visits.log` on
  ada): on pggb chrY 1,336,835 of the departing ends are ambiguous, holding
  4,896,022 of 8,111,782 departures (60%), in 457 of 524 fragments; on MC
  chr22 46,082 ends holding 48,734 of 25,988,597 departures (0.19%), in 88 of
  1,094 fragments, so Minigraph-Cactus needs it too, rarely. The fix is a visit index on exactly those
  tokens: a carrier is `f` when the fragment takes the allele on every visit
  of the leave end and `f:k` for the k-th visit otherwise, counted from 0 in
  walk order; the reader counts its visits of each leave end as it walks,
  which it does anyway. The writer has every walk in order and the
  prototype's emitter does not, which is why this review reports the count
  and the rule rather than a verified pggb file. Cost: a suffix on the
  ambiguous tokens only
- **Large windows cost more**, 10-25% at 1 Mb on chr22, because a site row
  repeats what a chunk's delta chains share. Views at 1 Mb read 0.6-1 MB
  either way; the budget-tuned tail is the part worth fixing
- **pggb's hops are not fixed by layout.** chrY has 15,929 sites longer than
  16 kb and 466 over 8 Mb, from haplotypes hopping between collapsed copies;
  a window under them reads every stub (p90 4 requests, 274 KB). Format 6
  pays the same in departure rows (17,076 at p90). Only placement cuts it:
  ADR 0009's aligned filing took chrY's p95 departure rows from 18,034 to
  265, and would shrink this layout the same way
- **Satellites and segmental duplications** stay in a detail tier. One chrY
  site has 5,156 alleles; LCR22A's alleles are 6,000 steps each. The site
  layout makes the tier per allele, which is finer than per path, and a
  compressed-byte budget is needed to match format 6's tails
- **Haplotype coordinates at a crossing:** a stub gives own bp, not the
  carrier's own offset at the leave; format 6's record gives `hapStart` per
  path. Add per-carrier offsets to stubs if a viewer needs them (chr22 has
  1,411 stubs; cheap), or fetch the start block
- **Carriers are fragments, not haplotypes**, so two contigs of one haplotype
  at one locus stay distinct; the header lists every fragment (1,094 on
  chr22, 524 on chrY). Genome-wide that is one line per W line per file
- **A reader must dedup** nodes across R rows and sites across cut blocks,
  as it dedups departure records today
- **Writer:** sites are routes keyed by breakpoints, so the format 6 writer's
  route table, placement, stay and abridging carry over; the per-cell H rows
  and the site carrier lists are new and were a 300-line prototype here. The
  external sort key becomes the site's start rather than the chunk
- **@gmod/tabix specifics:** it reads to the end of a chunk's last BGZF block
  (`clampChunkEnds`) and merges chunks within 65 KB, so a window's bytes are
  whole blocks; the floor logic is harmless once rows are leaf-contained
  (`n16-gmod-nofloor.jsonl` equals `n16-gmod.jsonl`)
- **Index size** grows with detail records at one leaf bin each (170 KB on
  chr22); packing records 16 kb apart only when they are large would halve it

## Verdict

- Format 6's one-base filing is a workaround for one reader heuristic,
  adopted without measurement, and it costs every reader the same 100 KB
  chunk pair for any window, a second read, four extra mechanisms (`skip`
  then `departure` records, `#long`, `#hole`, lookback) and the ability to
  use `tabix` on the file at all. The sentence in the spec is true of
  @gmod/tabix and false of htslib, and either way the remedy was to shrink
  the rows, not to lie about their span
- The walks file should be interval-native: per-cell `R` and `H` rows inside
  the 16 kb leaf bin, and one `V` row per site at its breakpoints, cut and
  stubbed as departure records are today, with abridged alleles in the
  detail tier. On MC chr22 that is a 20% smaller file, a 1 kb window at 25 KB
  in one request instead of 98 KB in two, the same at 10 kb, 79 against
  140 KB at 100 kb, and 11% more at 1 Mb; on pggb chrY every quantile halves.
  The query is one plain Tabix region rounded to 16 kb cells, the reader has
  no lookback, no sibling read and no `@k`/`:k` (copies are named by
  position; a visit index marks only the carriers that pass a site twice),
  and the layout was checked step by step against format 6: exact on MC
  chr22, exact on pggb chrY outside its collapsed repeats, where the visit
  index is still to be built
- Keep Tabix. Keep the one file per reference. Keep placement, stay and the
  detail tier. Leave the node/link index alone for now. Carry the visit
  index on carriers from day one: 0.19% of Minigraph-Cactus chr22's
  departures need it, 60% of pggb chrY's, and the verification above is
  exact everywhere else
- **Smallest first step:** write an ADR for the filing span with the tables
  above, and add `--layout sites` to `--walks` as format 7 beside format 6,
  writing from the same placed pieces: the three row kinds, the stub rule
  and the detail tier, with the writer's existing compressed-byte budget per
  cell. Check it with `scripts/verify.py`'s procedure against the format 6
  build of the same graph. Then a graph-walks reader branch of one query, and
  rebuild the hosted chr22 before the genome
