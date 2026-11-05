# A clean sheet for the walks file, and what it says about format 6

Reviewer: cleansheet. Lead angle: design the static-hosted, region-addressable
haplotype-path store from scratch, then weigh it against Tabix. Data: the
3.0.0 format 6 files for HPRC v2.1 Minigraph-Cactus chr22 (59.2 MB, 463
haplotypes) and HPRC release 2 pggb chrY (192 MB), plus eleven rebuilds of
chr22 at other chunk sizes. Scripts and raw outputs are under `scripts/` and
`data/` beside this file.

## Summary

- Filing every row at `cs cs+1` is a workaround for one fact: TBI's leaf bin
  is 16 kb and the chunk is 64 kb. The bin-sharing claim is true and measured
  (+33% bytes on 1 kb windows if rows span their chunk under TBI), but the
  right fix was never tried: a CSI index whose leaf is the chunk
  (`min_shift 16`). With it, rows can state their real span, `tabix
  chr22:15-35` returns the chunk's rows, and a window costs the same bytes
  or fewer (83 KB against 87 KB median at 1 kb)
- Two reader and container effects cost more than the format does on small
  windows: the unconditional lookback chunk (about a third of the bytes of a
  1 kb window; graph-walks' cut is identical without it whenever the drawn
  extent starts 2 × the longest sub-chunk reference node past its chunk's
  start, 2,048 bp on MC) and the chunk after the
  window, which @gmod/tabix fetches whole because no chunk starts on a BGZF
  block boundary and its end clamp finds the next boundary only at the chunk
  after next. The fetch is exactly chunks c − 1 to c_end + 1: 87 KB for a 1 kb
  window whose own chunk is 27 KB
- The biggest size problem is not the index but the detail tier: abridging
  grows MC chr22 from 32.3 MB to 59.2 MB and pggb chrY from 137.8 MB to
  192 MB, because every abridged path's record repeats the routes and nodes
  it shares with the chunk's other paths
- A clean-sheet tile archive (binary columnar tiles, zstd, flat directory,
  departure pyramid, shared detail section) would weigh about 0.3 × format 6
  on chr22 and fetch about half the bytes per window. That gain does not
  pay for leaving htslib, `tabix`, the audit scripts and JBrowse's Tabix
  stack. The verdict is Tabix with five changes, below

## Diagnosis

### What format 6 gets right

- Fixed reference chunks as the unit of storage. The sweep below shows 64 kb
  is at the knee: file size flattens past it (32.3, 30.1, 29.8 MB at 64, 128,
  256 kb without abridging) while small-window bytes grow in proportion to
  chunk size above it (56, 100, 196 KB at 1 kb). Every alternative unit
  measured by the project pays more: bubble-wide filing reads 1.5 MB for a
  1 kb window on a base-level graph (ADR 0002), node-level storage is a cost
  per step (630 M on chr22), and per-haplotype pieces filed by their own span
  are the bubble problem again times 463
- The route dictionary. Routes are near constant across chunk sizes
  (968,217 to 968,524 at 16 kb to 1 Mb without abridging): a route is written
  once wherever a chunk cuts it, and what grows with smaller chunks is walk
  and ref rows, not routes
- Departure records cut at bin sizes under a sibling sequence. This is a
  tile pyramid, and it is the same structure bigBed's R-tree, UCSC bins and
  CSI all use. A clean sheet keeps it
- Sibling sequences as layers in one file (`~departure`, `~cs`): one index,
  one host object, layers a window query never touches unless asked

### What is wrong, with evidence

- **The 1 bp interval is a misuse.** Through htslib's `tabix`, 98 of 100
  plain 1 kb region queries and 80 of 100 at 10 kb return no rows, each
  after reading 80 KB at the median (up to 153 KB): the linear index points
  it at the chunk's rows, it reads them and filters every one out. Through
  @gmod/tabix 98 of 100 return no rows, 72 reading nothing and 26 reading
  the whole chunk for nothing, depending on whether the window shares the
  chunk's first 16 kb tile. Any BED consumer (bedtools, IGV, UCSC) would
  place every piece at one base. The
  history: commit 3953bb1 (2026-10-08) says "A full-chunk interval shares a
  128 kb Tabix bin with the neighbouring chunk, so a query pulled both". The
  observation was right, no number was taken, and CSI, which lets a file pick
  its leaf size, was not considered. The 64 kb chunk was chosen with no
  reference to TBI's 16 kb leaf
- **The bin-sharing cost is real under TBI and zero under CSI.** Filing rows
  as `cs cs+65536` with a TBI puts two chunks in each 128 kb bin and a 1 kb
  window fetches 116 KB against 87 KB (median, +33%; +50 KB at p90). The same
  rows indexed with `tabix -C -m 16` fetch 83 KB and return the right rows to
  a plain query (1,640 rows median at 1 kb). At 1 Mb windows all three are
  within 5%
- **The lookback chunk is read when it cannot matter.** The reader reads from
  the chunk before the window's first, always. By the filing rules, the chunk
  before can hold something a window needs only through a reference node
  straddling the boundary or a route whose interior sits at the boundary,
  and both lie within 2 × maxnode of the chunk's start. graph-walks' own
  `cut` run with and without the lookback keeps the same on-window nodes on
  300 of 300 windows at 1 kb to 100 kb and is byte-identical on 281; the
  rest differ off the window only ([The lookback](#the-lookback)). The
  lookback is half of the two chunks the reader asks for on a 1 kb window (a
  median 25 KB each) and a third of the 88 KB it fetches
- **Block rounding and the chunk after.** No chunk starts on a BGZF block
  boundary (0 of 776), so a chunk's first and last rows share blocks with its
  neighbours. The index tells a reader where a chunk's rows end (its bin's
  `maxv`) but not where that block ends, so @gmod/tabix extends the fetch to
  the next block boundary it knows from the linear index, and with one
  distinct entry per chunk that is the chunk after next's first block: the
  fetch is exactly chunks c − 1 to c_end + 1 (ratio 1.000 at p10, median and
  p90 on every window size, `data/fetch-vs-chunks.txt`). A 1 kb window fetches
  88 KB for 57 KB of the two chunks the reader asked for and 27 KB of its
  own chunk. htslib reads 113 KB for the same window. Starting every chunk on
  a fresh block gives the clamp its boundary and removes both the rounding
  (33.7 against 25.1 KB a chunk) and the extra chunk
- **The detail tier duplicates shared routes per path.** MC chr22's file is
  18.7 MB of walk chunks, 0.5 MB of departures and 40.0 MB of detail
  records: 2,468 records over 18 chunks, each record encoding one path's
  pieces with its own `nodes` and `route` rows, though the paths of an LCR22
  chunk share most routes. Built with abridging off the whole file is
  32.3 MB. pggb chrY: 11.4 MB walk chunks, 12.1 MB departures, 168.6 MB
  detail records (669 records over 11 chunks); without abridging the file is
  137.8 MB, so the repetition costs 54 MB there and the satellite paths
  themselves, each haplotype's own, are the rest. ADR 0004 recorded the growth
  (745 to 1,409 MB on pggb chr22) and attributed it to holding the records,
  not to the repetition inside them
- **The index at open.** A reader downloads the whole `.tbi` before its
  first window: 41 KB for chr22, 1.33 MB for the hosted genome-wide GRCh38
  file. The departure bins and the detail siblings are most of it; the CSI
  with 64 kb leaves is 18.7 KB for chr22
- **On pggb the departure content dominates, and no container fixes it.** A
  chrY window's walk read is 12 KB median but its departure read is 2.2 MB
  at p90 and 3.1 MB at p99, in up to 5 requests, and the exact bytes of the
  bins hit are the same (2.0 MB p90): the rows are the hops between copies
  that ADR 0009 and the open problems already attribute to nearest-pass
  placement. A tile pyramid transfers the same rows

## Prior art, and what each would do here

| system | the idea | what it would do for the walks store | what to take |
|---|---|---|---|
| GBWT / GBZ (Sirén) | the haplotypes as a BWT over node ids: one record per node, each listing its out-edges and a run-length coded sequence of which edge each path takes; path identity from sparse samples; GBZ adds the graph, sequences and metadata, with byte offsets per node record | compact in N, since haplotypes sharing a route share runs, but a region is a traversal: fetch R's node records, extend every path one node at a time, and name paths by walking to a sample. gbz-base pays 18 to 43 round trips a window for this. Made local it becomes a route dictionary plus per-path choices, which is format 6 | run-length coding of choices across haplotypes when N grows past a few thousand; nothing for region access |
| vg indexes (xg, distance index, snarls) | xg: a path position index, O(1) position to node; snarl tree: the bubble hierarchy | the site as a storage unit. A top-level snarl in LCR22 spans megabases, so filing a haplotype's traversal under its site is the bubble-wide filing ADR 0002 measured at 1.5 MB per 1 kb window | the position index as a header fact, not a unit of storage |
| odgi | every node holds its list of path steps; a path position index on the side | node-centric tiles: fetch the window's nodes and their steps, stitch by rank. Cost is per step, 630 M on chr22, where a haplotype that follows R costs format 6 nothing | nothing |
| bigBed / bigWig | one file; R-tree over (chrom, start, end) pointing at compressed blocks; zoom levels | blocks per chunk with true extents, no bin sharing, index read lazily by R-tree descent (two or three dependent fetches, cached). @gmod/bbi reads it today. Items would be the same text rows with extra fields | a self-contained file with a lazily read index |
| BAM / CRAM / CSI | BGZF plus bins (TBI, BAI); CSI generalises the leaf size; CRAM slices cover a reference range and the `.crai` is a flat list of (ref, start, span, offset, size) | CSI is the missing piece for Tabix here: `min_shift 16` makes a 64 kb chunk one leaf bin. The `.crai` is the simplest tile directory there is | CSI now; the flat slice index as the model for a directory |
| Parquet / Arrow | columnar; row groups with a footer of per-column stats and page offsets; dictionary, RLE and bit-packing per column | one row group per chunk; a reader fetches only the columns it needs. Footers for 47 k row groups genome-wide run to tens of MB, so row groups would be 1 Mb with page-level pruning. Browser readers exist but are heavy | column-wise coding inside a tile: measured 0.57 × gzip text |
| Zarr v3 sharding, HTSget | fixed chunks at computable keys; a shard packs chunks into one object with a 16-byte (offset, nbytes) per chunk at its end | the tile address is a function of (sequence, chunk index); the directory is one offset per tile, read per sequence. No overlap query, which fixed chunks do not need | the computable address and the 8-byte directory entry |
| PMTiles | single-file tile archive for static hosts: 127-byte header, root directory, leaf directories, tiles; Hilbert-ordered tile ids; run-length dedup of identical tiles; readers do 1 to 3 range requests | the closest fit to the requirement list as written: levels are chunk sizes, tiles are chunks, departure levels are the pyramid. Its z/x/y addressing would be bent to (level, sequence, index) | the directory layout, lazy leaf directories, and ordering a pyramid so a window's tiles at every level sit close together |

## The clean-sheet design

If nothing had to stay Tabix, the file would be a tile archive. Call it a
walks archive, one file per reference sample.

### Layout

- **Header**, first 16 KB: magic, format, chunk size C, reference sample, the
  reference sequences with lengths, `maxnode`, `revisited`, the `#long` and
  `#hole` facts, the haplotype list, and for each sequence the byte range of
  its directory. 9.8 KB of that is the haplotype list on chr22, as today
- **Directory per sequence**: for each tier, one varint-delta offset per tile
  plus a final end offset. Tiers: `W` walk tiles at C, departure tiles `D0`
  to `D4` at C × 8^L, and `X` detail sections. chr22: about 800 entries, a few
  KB; a reader fetches the root and one sequence's directory, never the whole
  index. Genome-wide that is under 10 KB at open against 1.33 MB
- **Walk tile**: the same logical rows as format 6 (ref, nodes, route, walk,
  abridged), stored column-wise as zigzag varints with path names as header
  indexes, one zstd frame per tile. Measured on chr22's 776 chunks: 10.1 MB
  against 17.7 MB as gzipped text, 0.57 ×. Every tile is self-contained: its
  R lists every reference node overlapping the tile's span, so a node that
  straddles a boundary appears in both tiles and the `#long` lookback goes
- **Departure tiles**: the record rows cut as today at the pyramid's sizes,
  one tile per (level, index), tiles of all levels interleaved in position
  order so a window's tiles at every level are adjacent in the file and one
  or two range requests cover them
- **Detail section** of an abridged tile: the full route dictionary once,
  ordered by first-using path, then the moved paths' walk rows, then a table
  giving each moved path its walk row's offset, its own routes' byte run and
  the ids of the shared routes it also uses. Expanding one path fetches its
  run and a few shared routes; nothing is written per path that another path
  also needs
- **Sequences** (`--sequences`): a sibling `S` tier of 2-bit packed bases per
  tile, fetched only by viewers that draw bases

### Query procedure for a window [s, e) on sequence S

- Open: GET header; GET S's directory
- Drawn extent [s − ctx, e + ctx); walk tiles t0 = floor(drawn.start / C) to
  t1 = floor((drawn.end − 1) / C); one range request for [off(t0), off(t1 + 1))
- Departure tiles: for each level L, the tiles covering
  [drawn.start − reach, drawn.end + reach); merge adjacent ranges; one or two
  requests
- Decode each walk tile's columns back into format 6's rows and run format
  6's decoding rules unchanged: R from the ref rows, routes chained, each walk
  row's start and choices into steps with positions; compute departures
  inside pieces, take the rest from the departure tiles, dedup records on
  their columns. graph-walks above its row parser is unchanged
- Expanding an abridged path: read the tile's detail table, fetch the path's
  walk row and route run, decode against the tile's R

### What it would weigh and fetch (chr22, estimates from the measurements)

- File: walk tiles 10.1 MB, detail sections as the no-abridge content of the
  18 chunks at the same coding, about 7.5 MB, departures about 0.3 MB: about
  18 MB against 59.2 MB, 0.3 ×. On chrY the detail tier falls from 168.6 MB to
  the no-abridge content of its 11 chunks, 114 MB as gzipped text and about
  70 MB at the binary coding if chrY's rows compress like chr22's (an
  estimate; satellite interiors are long runs of tiny-node tokens), and the
  departures stay 12 MB until placement changes: about 90 MB against 192
- Bytes per window, walk tiles fetched exactly, binary coding, lookback only
  when the rule says: 1 kb about 16 KB (31 KB for two tiles, half that
  for one), 10 kb about 20 KB, 100 kb 55 KB, 1 Mb 292 KB, medians; against
  87, 92, 128 and 564 KB fetched through @gmod/tabix today
- Requests: 2 per window (walk range, departure range), as today; open costs
  2 small requests instead of a whole index

## What leaving Tabix costs

- Tooling: `tabix`, `bgzip`, htslib, pysam and noodles stop applying; every
  audit in `docs/departures/scripts` and `docs/format-2/scripts` reads rows
  as text through gzip or `tabix`, and `walks-truth.py` too. A `walks dump`
  CLI and a Python reader would have to exist before the first build
- Readers: @gmod/tabix and JBrowse's TabixIndexedFile adapters go; a new
  reader package, a writer in Rust, and a spec for a binary layout with its
  own versioning. Four consumers (graph-walks, bandage-core, the plugin,
  jb2hubs) move together, which the project already does on a format bump,
  but the plugin would also lose Tabix's byte estimate (`bytesForRegions`)
  until the directory gives it
- Debuggability: `zcat | grep HG002` finds a haplotype's rows today;
  `tabix -H` prints the header; a row is readable in an editor. Format 6's
  tokens already need a decoder to mean anything, but structure and names are
  visible, and every finding in the issues log was made on text rows
- What it buys, measured: about 2 × fewer bytes per window on MC at every
  window size, 0.3 × the file, a 100 × smaller open cost genome-wide. None of
  these is the bottleneck a user feels: a 100 KB fetch is a few tens of
  milliseconds on an ordinary connection, and the decode and layout time
  graph-walks and bandage-core spend dominate (ADR 0004's 0.7 s ordinary cut)

## The Tabix design that captures most of it

Keep BGZF, Tabix rows and sibling sequences; change five things. Rows'
columns and decoding rules stay format 6's, so the change is a header
number, a column value, an index type and a reader rule.

- **Rows state their span.** A chunk's rows are `seq cs cs+chunk`, departure
  rows and detail rows as they are. A plain `tabix` query returns the chunk's
  rows for any window inside it
- **The index's leaf is the chunk.** The writer emits a `.csi` with
  `min_shift = log2(chunk)` and depth 5 (2^31 per sequence at 64 kb), so a
  chunk's rows fill one leaf bin and share it with nothing. `--chunk` must be
  a power of two. Departure rows are cut at the CSI's bin sizes, chunk × 8^L,
  in place of TBI's 2^17 to 2^26, and detail records go to `detail × chunk`.
  The writer already builds a CSI for long contigs; it becomes the only
  index. Measured: 83 KB against 87 KB for a 1 kb window, 540 against 564 KB
  at 1 Mb, and a 2.2 × smaller index
- **Each chunk starts a BGZF block.** The writer flushes its block at every
  chunk start, so a chunk's byte range is whole blocks: a one-chunk fetch is
  25 KB, not 34 KB, and @gmod/tabix's end clamp finds the next chunk's first
  block at once instead of reading the chunk after. BGZF allows blocks of
  any size; the cost is one block header per chunk
- **The lookback is a rule, not a habit.** A reader reads the chunk before the
  window's first only when the drawn extent starts within 2 × straddle of
  that chunk's start, or for a `#long` pass overlapping the window, where
  `straddle:i:` is a new header tag, the longest reference node pass not
  listed in `#long` (1,024 on MC; on pggb the nodes over a chunk are `#long`
  and `maxnode` is 1 Mb, so `maxnode` cannot serve). On MC that is 1.6% of
  1 kb windows. The spec states the rule and the writer's guarantee behind
  it: a piece's steps on reference nodes lie in the chunk holding each node's
  start, and a route interior lies in the chunk of the reference step before
  it, so nothing filed under chunk c − 1 overlaps a base past cs + 2 ×
  straddle
- **The detail tier shares routes.** An abridged chunk's detail sibling holds
  its route rows once, each filed at its own position (`route id × chunk`),
  and each moved path's walk row at `(routeCount + path index) × chunk`,
  listing the route ids it takes. Expanding a path reads its walk row, then
  its routes by position, merged into a few range requests. Measured upper
  bound on the saving: 27 MB of chr22's 59 MB and 54 MB of chrY's 192

Together, a 1 kb window on MC chr22 goes from 87 KB to about 27 KB of walk
read (one block-aligned chunk, median 25 KB) plus the departure read, with no
change to rows or decoding; a 1 Mb window from 564 KB to about 500 KB. The
clean sheet's remaining advantage is the binary coding (0.57 ×) and the lazy
directory.

### Should the walk file and the node/link index merge?

- No. They serve different graphs: the index is the only representation of
  an rGFA or minigraph SV graph, which has no paths, and carries the coarse
  tiers and carriers. For a path graph the walk file already holds R, the
  routes' nodes and, with `--sequences`, the bases, and the open problem
  "walk files in place of the index for path graphs" measured a third of the
  bytes with nothing a user needs lost off segmental duplications
- Merging would save one index fetch at open and nothing per window, as ADR
  0002 found for nodes and links. Sibling sequences already give the walk
  file layers; a clean-sheet archive would give them tiers in one directory,
  which is the same thing

## Measurements

### Method

- Windows: 100 fixed random windows at each of 1 kb, 10 kb, 100 kb and 1 Mb,
  uniform over chr22 10.5 to 50.8 Mb (seed 22; `data/windows.json`) and over
  chrY 0 to 57 Mb (seed 24; `data/windowsY.json`)
- Variants of the 3.0.0 chr22 file: `orig` as released; `span-tbi`, the same
  rows with `cs cs+65536` and `tabix -p bed`; `span-csi`, the same rows with
  `tabix -C -m 16 -p bed` (departure cuts left at TBI's sizes, so its
  departure read is pessimistic). `scripts/tbi.py` parses either index
- `scripts/fetch.mjs`: @gmod/tabix 3.13.1 (graph-walks' copy) with a
  byte-counting file handle, a fresh `TabixIndexedFile` per read so no cache
  helps. For each window: the graph-walks walk read (from
  `chunkQueryStart(start − 1000)` to `end + 1000`), its departure read
  (`~departure` over the extent ± `maxnode`), and a plain region query.
  `bytesForRegions` agreed with bytes actually read on every window
- `scripts/htslib.sh`: htslib 1.24's `tabix` under `strace`, summing reads on
  the data file, same windows and reads
- `scripts/compress.py`: each chunk's text under gzip 6, zstd 19, zstd with a
  trained dictionary, column-wise zstd, and a binary varint column coding
- `scripts/bgzf_blocks.py`: block sizes and per-chunk rounding;
  `scripts/blocks.mjs` prints the byte ranges @gmod/tabix fetches for a
  window under TBI and CSI, and `data/fetch-vs-chunks.txt` compares every
  window's fetch with the byte extents of its chunks from the index
- `scripts/cutdiff.mjs`: graph-walks 5.0.2's `cut` on each window twice, as
  released and with the lookback skipped under the 2 × maxnode rule, comparing
  kept nodes, fragments (order-independent, bookkeeping counts aside) and
  departures, and the bytes each read
- `scripts/chunk-sweep.sh`, `chunk-sweep-noabridge.sh` on ada: the 3.0.0
  binary on `mc22.gfa` at chunks of 16 kb to 1 Mb, with the release's
  abridging and with it off; `scripts/pyramid.py`: the exact bytes of the
  departure bins a window hits
- `scripts/summarize.py` writes `data/summary.md`, from which the tables
  below are taken

### Bytes per window through @gmod/tabix, KB, median / p90 / p99

| variant | window | walk read | departure read | total | requests | plain query rows (median / p90 / max) |
|---|---|---|---|---|---|---|
| orig | 1 kb | 87 / 128 / 356 | 7.7 / 21 / 60 | 98 / 136 / 416 | 2 | 0 / 0 / 1910 |
| orig | 10 kb | 92 / 148 / 356 | 8.1 / 37 / 60 | 100 / 178 / 416 | 2 | 0 / 1597 / 2608 |
| orig | 100 kb | 128 / 229 / 541 | 8.1 / 26 / 60 | 142 / 247 / 602 | 2 | 2040 / 3956 / 20485 |
| orig | 1 Mb | 564 / 737 / 1421 | 16 / 37 / 76 | 573 / 768 / 1490 | 2 | 26389 / 33740 / 60425 |
| span-tbi | 1 kb | 116 / 177 / 558 | 7.1 / 20 / 56 | 122 / 190 / 614 | 2 | 1640 / 2535 / 10331 |
| span-tbi | 10 kb | 113 / 190 / 529 | 7.5 / 35 / 56 | 118 / 202 / 560 | 2 | 1610 / 3612 / 14613 |
| span-tbi | 100 kb | 146 / 261 / 697 | 7.5 / 22 / 56 | 158 / 269 / 737 | 2 | 3909 / 6044 / 22865 |
| span-tbi | 1 Mb | 573 / 773 / 1536 | 15 / 35 / 71 | 587 / 788 / 1599 | 2 | 27917 / 35950 / 60426 |
| span-csi | 1 kb | 83 / 126 / 346 | 14 / 113 / 113 | 109 / 186 / 402 | 2 | 1640 / 2535 / 10331 |
| span-csi | 10 kb | 88 / 146 / 346 | 15 / 113 / 113 | 115 / 217 / 417 | 2 | 1610 / 3612 / 14613 |
| span-csi | 100 kb | 126 / 231 / 514 | 14 / 113 / 154 | 144 / 331 / 599 | 2 | 3909 / 6044 / 22865 |
| span-csi | 1 Mb | 540 / 714 / 1420 | 21 / 113 / 159 | 572 / 793 / 1528 | 2 | 27917 / 35950 / 60426 |
| chrY orig | 1 kb | 12 / 73 / 692 | 7.7 / 2219 / 3119 | 47 / 2219 / 3218 | 2 / 4 / 5 | 0 / 0 / 317 |
| chrY orig | 10 kb | 11 / 96 / 957 | 19 / 2649 / 3111 | 51 / 2752 / 3222 | 2 / 4 / 5 | 0 / 320 / 2760 |
| chrY orig | 100 kb | 28 / 90 / 973 | 61 / 2506 / 3080 | 100 / 2541 / 3193 | 2 / 4 / 5 | 1 / 1390 / 20381 |
| chrY orig | 1 Mb | 43 / 931 / 2861 | 61 / 3288 / 4234 | 104 / 4223 / 5647 | 2 / 4 / 5 | 582 / 33122 / 121246 |

- The `span-csi` departure read is larger because its departure rows were
  not recut at the CSI's bin sizes; a writer that cuts them at chunk × 8^L
  gets TBI's numbers back

### Bytes read by htslib's `tabix`, KB, median / p90 / p99

| variant | window | walk read | plain query bytes | plain query rows (median / max) |
|---|---|---|---|---|
| orig | 1 kb | 113 / 129 / 317 | 80 / 123 / 153 | 0 / 1910 |
| orig | 10 kb | 117 / 135 / 317 | 80 / 119 / 180 | 0 / 2608 |
| orig | 100 kb | 132 / 161 / 425 | 113 / 140 / 317 | 2040 / 20483 |
| orig | 1 Mb | 313 / 409 / 574 | 297 / 391 / 560 | 26387 / 60421 |
| span-tbi | 1 kb | 106 / 125 / 227 | 94 / 102 / 114 | 1638 / 10331 |
| span-csi | 1 kb | 89 / 105 / 210 | 77 / 84 / 97 | 1638 / 10331 |
| span-csi | 1 Mb | 273 / 358 / 536 | 257 / 341 / 519 | 27917 / 60419 |

- htslib reads less than @gmod/tabix on 1 Mb windows (313 against 564 KB)
  because it stops at the first row past the query, and more on 1 kb windows
  because of its read buffer; on the current file a plain query reads 80 KB
  to print nothing

### What a window's chunks actually weigh (exact, no rounding), KB, median / p90 / p99

Chunks c − 1 to c_end of the drawn extent, each coded on its own:

| window | gzip 6 (today's codec) | zstd 19 | columnar zstd | binary columnar zstd |
|---|---|---|---|---|
| 1 kb | 54 / 85 / 335 | 42 / 66 / 164 | 38 / 59 / 157 | 31 / 49 / 134 |
| 10 kb | 56 / 104 / 335 | 45 / 80 / 164 | 41 / 75 / 157 | 33 / 64 / 134 |
| 100 kb | 95 / 178 / 506 | 76 / 119 / 311 | 68 / 111 / 294 | 55 / 96 / 256 |
| 1 Mb | 500 / 663 / 1268 | 391 / 474 / 713 | 353 / 432 / 683 | 292 / 370 / 594 |

- Whole main sequence: 162.7 MB raw, 17.7 MB gzip, 13.3 MB zstd, 12.1 MB
  columnar, 10.1 MB binary columnar. A trained dictionary did not help (14.2
  MB): chunks are large enough to carry their own statistics
- 6,606 BGZF blocks, median 9.3 KB compressed; a one-chunk fetch is 33.7 KB
  block-rounded against 25.1 KB exact; 0 of 776 chunks start on a block
  boundary

### Chunk size, abridging off (every row in the main sequence)

Index-only estimate of a window's walk bytes, chunks c − 1 to c_end:

| chunk | file MB | walk chunks MB | largest chunk MB | pieces | records | 1 kb | 10 kb | 100 kb | 1 Mb |
|---|---|---|---|---|---|---|---|---|---|
| 16 kb | 49.4 | 47.9 | 4.47 | 1,005,259 | 93,166 | 31 / 42 / 541 | 37 / 50 / 334 | 120 / 143 / 6553 | 955 / 1513 / 12252 |
| 32 kb | 37.8 | 37.0 | 4.47 | 504,431 | 46,889 | 37 / 62 / 4492 | 42 / 66 / 4492 | 98 / 178 / 6914 | 659 / 1240 / 12209 |
| 64 kb | 32.3 | 31.8 | 4.47 | 253,629 | 24,648 | 56 / 86 / 4515 | 60 / 111 / 4515 | 100 / 251 / 7910 | 535 / 1165 / 12216 |
| 128 kb | 30.1 | 29.8 | 7.18 | 127,722 | 13,945 | 100 / 175 / 12144 | 97 / 231 / 7241 | 140 / 345 / 12208 | 543 / 1147 / 12319 |
| 256 kb | 29.8 | 29.6 | 12.20 | 64,470 | 7,906 | 196 / 357 / 12299 | 181 / 349 / 12256 | 249 / 569 / 12353 | 646 / 1356 / 12367 |
| 1 Mb | 32.0 | 31.9 | 12.39 | 16,893 | 1,786 | 1084 / 2608 / 12397 | 1017 / 2689 / 12397 | 1084 / 2193 / 12397 | 1429 / 3173 / 12397 |

- With the release's abridging on, the files are 70.7, 62.3, 59.2, 63.4,
  90.5 and 141.0 MB: the per-chunk budget abridges more paths as chunks grow
  (1,448 at 16 kb, 2,468 at 64 kb, 13,101 at 1 Mb) and each abridged path
  costs its own record
- Routes: 968,217 to 968,524 at every chunk size; pieces and records scale
  with the chunk count

### The lookback

graph-walks 5.0.2's `cut` on each window, as released and with the lookback
skipped when the drawn extent starts at least 2 × 1,024 bp past its chunk's
start, both with the attach-fetch cap lifted so the comparison is about the
data. Bytes are everything the cut read: walk chunks, the departure read and
the on-demand fetches of leave chunks for records' own steps.

| window | windows | lookback skipped | cuts identical | identical in on-window nodes, fragments and records | bytes read, released (median / p90) | bytes read, skipped (median / p90) |
|---|---|---|---|---|---|---|
| 1 kb | 100 | 96 | 93 | 100 | 164 / 578 KB | 135 / 556 KB |
| 10 kb | 100 | 96 | 93 | 98 | 167 / 684 KB | 141 / 737 KB |
| 100 kb | 100 | 95 | 95 | 99 | 210 / 562 KB | 179 / 531 KB |

- The on-window kept node set is the same in all 300 windows
- 16 windows differ only in whether some departure records carry their own
  steps, with the same records, fragments and nodes otherwise; the decode
  bug below is the cause
- 3 windows, all in LCR22A (chr22:18.39-18.51 Mb, beside the abridged chunks
  at 18.35 and 18.48 Mb), differ off the window: four haplotypes leave the
  window, run about 125 kb through the previous chunk's reference, a paralog
  copy, and return. With that chunk at hand the released reader draws the
  excursion as one fragment and keeps 6,469 of its reference nodes and 3,286
  records touching it; without it the same haplotypes are two fragments and
  the departure record between them, which is what the reader gives an
  excursion into any other chunk today. The lookback made that chunk's
  content visible by accident of adjacency
- A cut's real cost today is well above the walk and departure reads: at 1 kb
  164 KB median and 578 KB p90, because each on-demand fetch of a leave chunk
  reads that chunk and the one before. The lookback rule applies to those
  fetches too (the leave piece is filed under the chunk of the leave node's
  start, and the chunk before is needed only when the base beside the
  breakpoint lies within `straddle` of it), which is where the p90 at 10 kb
  rises without it (684 to 737 KB)
- Skipping the lookback moves one kind of read: a departure record's own
  steps come from its leave piece, and where that piece was in the lookback
  chunk the reader now fetches it on demand, as it already does for leave
  chunks farther off (`ATTACH_FETCHES`, 8 a cut). The bytes in the table
  include those fetches
- The comparison found a reader bug that is not the lookback's: graph-walks'
  `decode` (walkReader.ts) returns as soon as a chunk is in `decoded`,
  whatever name filter the call carries, and each on-demand fetch reads its
  chunk and the one before. Two records whose leave chunks are adjacent and
  outside the main read therefore fetch overlapping ranges, and whichever
  decodes the shared chunk first drops the other's path: its own steps are
  never attached (window chr22:22865052-22866052, record NA18608#2 with
  leave at 22,687,062, 53 own nodes missing). It is reachable in the released
  reader whenever two such records exist; skipping the lookback reaches it
  more often. The fix is to decode a chunk again for names not yet decoded,
  or to merge adjacent attach fetches into one read with the union of names.
  This belongs in `docs/issues-log.md` with a test of two records whose
  leave chunks are adjacent

### The departure pyramid, exact bytes of the bins a window hits

| file | window | exact KB median / p90 / p99 | bins hit median / max |
|---|---|---|---|
| MC chr22 | 1 kb | 0.1 / 10.6 / 51.7 | 1 / 2 |
| MC chr22 | 1 Mb | 10.0 / 33.8 / 66.3 | 15 / 22 |
| pggb chrY | 1 kb | 4.0 / 2020 / 2894 | 3 / 32 |
| pggb chrY | 1 Mb | 7.9 / 3115 / 4133 | 5 / 41 |

- On MC a departure read fetches 7.7 KB to get 100 bytes of rows: block
  rounding, one block. On chrY the fetched and exact bytes agree: the content
  is the cost

### Sizes at open

- Header: 9.8 KB (chr22, 464 haplotype lines), 4.4 KB (chrY)
- Index: 40.9 KB (chr22 TBI), 36.0 KB (span TBI), 18.7 KB (span CSI), 15.9 KB
  (chrY TBI), 1.33 MB (hosted genome-wide GRCh38 format 5 TBI, file 1.55 GB)

## Tradeoffs and failure modes

- **Repeats and collapsed nodes (pggb):** the departure rows are the cost,
  2 to 3 MB a window at p90 on chrY, and every container transfers them.
  The fix is placement, as the open problems say, or a per-path summary of
  hops that ADR 0009 measured and rejected as crowds. The pyramid itself is
  right: a window inside a 30 Mb jump finds its record in one bin
- **Long nodes:** the `#long` lookback stays in the Tabix design; the tile
  archive lists a straddling node in every tile it overlaps and needs none
- **Inversions and strand:** per-step strand in handles and per-end strand
  on records; nothing here changes it
- **Huge chunks:** without abridging MC chr22's largest 64 kb chunk is
  4.5 MB and its largest two-chunk window 7.9 MB at p99 for 100 kb windows,
  under graph-walks' 8 MB budget but over its step budget; abridging keeps
  those windows small (345 KB p99 at 1 kb) at the price of the detail tier.
  Sharing routes in the detail tier removes the price without changing what a
  window reads. On pggb chrY the largest chunk is 0.9 MB with abridging and
  the satellites move to detail either way
- **CSI instead of TBI:** htslib, @gmod/tabix and JBrowse read CSI; the plugin
  must look for `.csi` beside `walksUri`, and `--chunk` must be a power of
  two. A user who runs `tabix -p bed` by hand on a rebuilt file gets a TBI
  with bin sharing, which is harmless, so the writer should warn in the
  header, not fail
- **The lookback rule:** it is a reader promise backed by a writer guarantee.
  The audit (`audit6.py`) should check it: no row of chunk c − 1 decodes to a
  position past cs + 2 × straddle. It is also where a stay run on a revisited
  reference could bite, so the check runs on pggb too. Records whose own
  steps lived in the lookback chunk become on-demand attach fetches, so the
  attach path has to be right first: see the decode bug under Measurements
- **Block-aligned chunks:** a sequence with thousands of near-empty chunks
  (chr22's 10.5 Mb of N) pays a block header each; 26 bytes a chunk
- **The clean-sheet archive:** everything above plus a reader and writer to
  write, a spec to keep, and a text dump tool before the first audit. Its
  one advantage no Tabix change reaches is the binary coding, 0.57 × bytes,
  and the lazy directory

## Verdict

- Stay on Tabix. Measured, a custom tile archive would fetch about half the
  bytes a window needs today and weigh a third of the file on chr22, and
  that does not pay for losing `tabix`, htslib, the audit scripts and
  JBrowse's Tabix stack. The requirement list, static hosting with range
  requests and bounded reads per window, is met by Tabix once the index's
  leaf matches the chunk
- Fix the misuse, not the chunking: rows state their span `cs cs+chunk`, and
  the writer emits a CSI with `min_shift = log2(chunk)` so a chunk is one leaf
  bin. The bin-sharing claim that drove `cs cs+1` was true for TBI and is
  false for CSI, at no cost (83 against 87 KB for a 1 kb window) and with
  plain `tabix` queries returning the right rows
- Then take the two reader-and-container savings that dwarf the index
  question: start every chunk on a BGZF block, so a fetch stops at the
  chunk's end instead of running through the chunk after (a 1 kb window
  fetches chunks c − 1 to c + 1 today, 88 KB for 27 KB of its own chunk), and
  read the chunk before only when the drawn extent starts within 2 × straddle
  of the chunk's start, which graph-walks' own cut shows changes no
  on-window content in 300 of 300 windows (byte-identical in 281; the rest
  differ in own steps the reader attaches, a reader bug, or in an excursion
  into the chunk before that the released reader drew only because it had
  read that chunk). A 1 kb window then reads about 27 KB of walk rows
  against 87
- Fix the detail tier's duplication: file an abridged chunk's routes once at
  their own positions and let each moved path's row name them. That is 27 of
  chr22's 59 MB and 54 of chrY's 192 MB
- Keep the walk file and the node/link index separate, and keep 64 kb chunks
- Call it format 7, since the row span, the index type and the lookback rule
  change what a reader does, and the stack has no back-compatibility to keep.
  Record this in an ADR with the tables above, which is what commit 3953bb1
  did not do
- **Smallest first step:** in the writer, set the row end to `cs + chunk`,
  index with `Indexer::new(log2(chunk), 5)` and drop the TBI, cut departure
  rows at `chunk × 8^L`, file detail records at `detail × chunk`, and flush
  the BGZF block at each chunk start; in graph-walks, open the `.csi` and
  apply the lookback rule. Rows, decoding and the audit's row checks are
  untouched, so the port is a day's work, and `tabix chr22:15-35` on the new
  file is the test
