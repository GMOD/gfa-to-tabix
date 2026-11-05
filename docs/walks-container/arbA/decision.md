# Decision: the walks file's container (arbiter A)

## Decision

The walks file is one BGZF text file with a `.fai`-style table beside it.
Every entry in the table gives a real reference extent and a byte range. A
reader fetches every entry whose extent overlaps its window, in one round
trip. Departure records are listed in the same file under the same rule.

The reasons, in short:

- **Every coordinate is true.** No fake intervals, no sibling sequences, no
  lookback rule and no reach rule.
- **It reads exactly the bytes a window needs**, which Tabix can't do with
  true extents.
- **It fetches less than every Tabix variant measured.** On pggb chrY a 1 kb
  window is 69 KB in one round trip, against 292 KB in three for patched
  format 6. On Minigraph-Cactus (MC) chr22 it is 28 KB against 36 KB.
- **The rows inside a tile stay format 6's.** Measured, that dictionary
  encoding earns its cross-row dependencies: self-contained lines cost 2.4×
  to 3.1× the bytes per window on MC.

### The design (S), in full

- **Files:** `<prefix>.<sample>.walks.gz` (BGZF) and
  `<prefix>.<sample>.walks.gz.idx` (gzip text, read whole when the file is
  opened).
- **Table lines:** `seq start end kind name offset length`.
  - `kind` is one of `header`, `tile`, `departures` or `detail`.
  - `offset` and `length` are compressed bytes. Every entry starts on a BGZF
    block boundary, so stock tools can pull one entry out:
    `tail -c +$((offset+1)) f.walks.gz | head -c $length | gzip -dc`.
  - Rows are sorted by sequence, then by offset.
- **`tile` entries:** the rows of one 64 kb tile of the reference.
  - `start` and `end` are the tile's true extent: from the first base to the
    last base of every step its rows place on the reference.
  - So a node straddling the tile's edge, or a 1 Mb `#long` pass, is inside
    the extent, and no reader rule has to supply it.
  - `name` is the tile's nominal start.
  - The rows are format 6's `ref`, `nodes`, `route`, `walk` and `abridged`
    rows, unchanged except that the leading `seq cs cs+1` columns are dropped.
  - The route token chain and the `@k`/`:k` occurrence tokens stay.
- **`departures` entries:** one per block of an aligned pyramid of tile ×
  8^L, for L = 0 to 3 (64 kb, 512 kb, 4 Mb and 32 Mb).
  - Each line is a whole format 6 record with real coordinates:
    `seq start end departure path hapStart ownBp missingBp leavePos leaveStrand leavePasses rejoinPos rejoinStrand rejoinPasses`.
  - `start`/`end` run from the first base of its first end node to the last
    base of its other end node.
  - A record appears, as an identical line, in every block of the aligned
    cover of its extent (the rule `departures.rs::blocks` already uses).
    Readers dedup identical lines.
- **`detail` entries:** one per abridged path per tile, named `cs:d` with
  the number the `abridged` row already carries, and holding format 6's
  self-contained detail record. They are fetched when a viewer expands a
  piece.
- **Header:**
  - `#walks format:i:7 tile:i:65536 revisited:i: stay:i: abridge:i: abridgebytes:i:`
  - `#reference`, `#haplotype` and `#hole` lines.
  - No `#long`, `chunk` or `maxnode` lines.
- **A reader's window [s, e):**
  - Take D = [s − 1000, e + 1000).
  - Select the `tile` and `departures` entries with `start < D.end` and
    `end > D.start`.
  - Merge byte ranges that touch, and fetch them in parallel.
  - Decode tiles with format 6's rules and dedup departure lines.
  - That is all of it.

## Measurement table

### Method

- **One harness for every candidate** (`scripts/measure.mjs`). A static
  HTTP server logs every range it serves. Each candidate's query procedure
  runs over `fetch`: @gmod/tabix 3.13.1 for the Tabix candidates (patched
  `chunk.js` except A0), and a 60-line table reader for O and S.
- **Index and header are fetched once, at open, and reported separately.**
  The chunk cache is cleared between windows.
- **Windows:** 300 per size at 1 kb, 10 kb, 100 kb and 1 Mb, seeded, with
  1 kb of context.
  - MC chr22: uniform over 10.51–50.79 Mb, using the shipped 3.0.0
    `mc22.GRCh38.walks.bed.gz`.
  - pggb chrY: uniform over 2.78–26.67 Mb, the euchromatin and centromere,
    using `pggbY.GRCh38.walks.bed.gz`.
- **Round trips:** the longest chain of requests where each starts after
  the one before it finished.
- **How every candidate was built:** rewritten row for row from the shipped
  format 6 file (`scripts/build.mjs`, `sfinal.mjs`, `tnode.mjs`).
  - Each rewrite was BGZF-written with a block boundary at every chunk,
    tile or entry start.
  - The S rewrites were decoded back step for step on every piece: 252,853
    on MC and 471,098 on pggb.
- **Correctness:** 96 windows per dataset per candidate. I rebuilt every
  piece's steps over D (node, strand, reference position) and checked them
  against graph-walks' `decodeChunk` of the shipped file over a generous
  range. I also checked every departure record over the window.
- **Departure reach on pggb:** 50,008 bp, the longest node not listed in
  `#long`, for F6p, T and O. A0 uses graph-walks 5's real rule, the header's
  `maxnode` (1 Mb).

### Candidates

| | what it is |
|---|---|
| A0 | 3.0.0 as shipped, read the graph-walks 5 way, stock @gmod/tabix |
| F6p | format 6 rows, 1 bp key, TBI. Blocks aligned to chunks, patched @gmod/tabix, read from the chunk holding `D.start − reach` (and `#long` passes), departures over D ± reach |
| T | the same rows at `cs cs+65536`, CSI with `min_shift` 16, departures recut at the CSI's sizes. Same reads as F6p. T16 is the 16 kb build under TBI, for bytes only |
| Tn | T with S's departure filing (end-node extents), departures queried over D only |
| O | offset table over format 6 tiles with true extents, departures in a separate real-sequence BED + TBI (cut as format 6 cuts them). Ou is the same with uncut departures |
| N | native's prototype files (`native16c` for MC, `native16` for chrY, no visit index), one cell-rounded query |
| S | the decision above |
| S2 | S with the route chain removed (each route row's tokens start from 0) |
| Oabs | O with absolute ids everywhere (no deltas) |
| Srel / Sabs | self-contained lines: each piece as a GAF-style path of reference intervals and off-reference node ids, deltas within the line or fully absolute, so no route dictionary |

### MC chr22: KB per window (median / p90 / p99), requests, round trips, file

| | open KB | 1 kb | 10 kb | 100 kb | 1 Mb | req med/max | trips | file MB | check (pieces / wrong / departures missing) |
|---|---|---|---|---|---|---|---|---|---|
| A0 | 106 | 95 / 145 / 416 | 98 / 147 / 312 | 146 / 210 / 465 | 570 / 758 / 1466 | 2 / 2 | 1 | 59.2* | 105,400 / 0 / 0 |
| F6p | 105 | 36 / 65 / 164 | 38 / 71 / 203 | 83 / 133 / 271 | 498 / 684 / 1395 | 2 / 2 | 1 | 58.8 | 105,400 / 0 / 0 |
| T | 102 | 37 / 65 / 190 | 38 / 71 / 252 | 83 / 133 / 310 | 503 / 681 / 1428 | 2 / 2 | 1 | 58.8 | 105,400 / 0 / 0 |
| Tn | 102 | 36 / 68 / 197 | 37 / 75 / 260 | 83 / 134 / 317 | 504 / 694 / 1426 | 2 / 2 | 1 | 59.0 | 105,400 / 0 / 0 |
| T16 | 129 | 24 / 66 / 109 | 36 / 69 / 365 | 120 / 161 / 281 | 978 / 1188 / 2137 | 2 / 2 | 1 | 70.4 | n/a (another build) |
| O | 122 | 33 / 63 / 169 | 36 / 67 / 203 | 81 / 129 / 264 | 487 / 665 / 1369 | 2 / 2 | 1 | 57.4 | 105,400 / 0 / 0 |
| Ou | 122 | 35 / 108 / 221 | 37 / 102 / 260 | 89 / 166 / 313 | 488 / 678 / 1384 | 2 / 2 | 1 | 57.3 | 105,400 / 0 / 0 |
| N | 236 | 26 / 121 / 296 | 28 / 128 / 357 | 83 / 189 / 357 | 625 / 885 / 2999 | 1 / 3 | 2 | 47.3 | native: 60/60 windows |
| **S** | **58** | **28 / 51 / 163** | **29 / 61 / 188** | **73 / 123 / 261** | **490 / 671 / 1399** | **1 / 3** | **1** | **57.9** | **105,400 / 0 / 0** |
| S2 | 58 | 31 / 58 / 172 | 32 / 68 / 195 | 81 / 134 / 269 | 542 / 738 / 1466 | 1 / 3 | 1 | 61.5 | 105,400 / 0 / 0 |
| Oabs | 124 | 50 / 118 / 1237 | 53 / 117 / 1157 | 128 / 270 / 1622 | 833 / 2430 / 8205 | 2 / 2 | 1 | 214.4 | |
| Srel | 122 | 87 / 201 / 641 | 91 / 242 / 511 | 221 / 489 / 996 | 1491 / 2445 / 4782 | 2 / 2 | 1 | 101.6 | 105,400 / 0 / 0 |
| Sabs | 124 | 125 / 415 / 1900 | 134 / 430 / 1900 | 336 / 980 / 3074 | 2451 / 5144 / 14964 | 2 / 2 | 1 | 281.9 | 105,400 / 0 / 0 |

\* written by bgzip. Every other file was written by my BGZF writer at
deflate level 6, so compare those with each other: F6p at 58.8 MB is the
format 6 baseline.

### pggb chrY

| | open KB | 1 kb | 10 kb | 100 kb | 1 Mb | req med/max | trips | file MB | check |
|---|---|---|---|---|---|---|---|---|---|
| A0 | 81 | 1545 / 2850 / 3342 | 1118 / 2806 / 3470 | 1422 / 3049 / 4112 | 2425 / 4674 / 5781 | 3 / 6 | 3 | 192.2* | 107,819 / 0 / 0 |
| F6p | 81 | 292 / 789 / 1855 | 286 / 749 / 2671 | 349 / 1024 / 3419 | 813 / 3497 / 4887 | 3 / 6 | 3 | 183.7 | 107,819 / 0 / 0 |
| T | 80 | 226 / 643 / 1915 | 236 / 692 / 2903 | 296 / 866 / 4323 | 910 / 3336 / 5581 | 3 / 6 | 3 | 186.3 | 107,819 / 0 / 0 |
| Tn | 80 | 187 / 471 / 1609 | 187 / 505 / 2508 | 259 / 785 / 3397 | 877 / 3316 / 5579 | 3 / 6 | 3 | 186.3 | 107,819 / 0 / 0 |
| T16 | 95 | 244 / 892 / 4140 | 212 / 865 / 4928 | 356 / 1366 / 7645 | 1139 / 9635 / 10472 | 4 / 8 | 3 | 211.1 | n/a |
| O | 88 | 281 / 761 / 1641 | 280 / 768 / 2404 | 325 / 993 / 2781 | 773 / 3379 / 4454 | 3 / 7 | 3 | 181.6 | 107,819 / 0 / 0 |
| Ou | 89 | 986 / 1553 / 2637 | 640 / 1457 / 2637 | 988 / 2042 / 2982 | 1323 / 2994 / 4457 | 4 / 8 | 3 | 173.7 | 107,819 / 0 / 0 |
| N | 371 | 155 / 327 / 581 | 155 / 329 / 599 | 192 / 421 / 1013 | 461 / 1675 / 2529 | 3 / 6 | 3 | 144.5 | native: 49/60 windows, no visit index |
| **S** | **25** | **69 / 237 / 1460** | **69 / 265 / 1650** | **118 / 462 / 2329** | **720 / 3185 / 5083** | **2 / 4** | **1** | **184.5** | **107,819 / 0 / 0** |
| S2 | 25 | 69 / 238 / 1459 | 69 / 266 / 1649 | 118 / 465 / 2330 | 735 / 3194 / 5088 | 2 / 4 | 1 | 185.0 | 107,819 / 0 / 0 |
| Srel | 88 | 283 / 765 / 2172 | 281 / 797 / 2957 | 344 / 1027 / 3747 | 930 / 4370 / 7540 | 3 / 7 | 3 | 207.4 + 11.7 | 107,819 / 0 / 0 |

### Where the bytes go (median / p90 KB, 1 kb windows)

- MC:
  - O: walk 27/48, departures 11/37. The separate BED rounds to whole
    blocks.
  - S: tiles 27/48, departures 1/6.
  - S's tile bytes are the floor for 64 kb tiles of format 6 rows, because
    the table selects exactly the tiles with a step in D. F6p and T also
    read the tile before whenever `D.start − reach` crosses a tile edge:
    1.6% of MC windows, and about 76% on pggb, where the reach is 50 kb.
- pggb:
  - O: walk 6/45, departures 275/648.
  - S: tiles 6/45, departures 55/192.
  - On pggb the departure read is the whole cost of a small window. It
    falls in two steps:
    - Filing each record over its end nodes, so no reach widening is
      needed: F6p 292 → Tn 187.
    - Exact pyramid groups in the table instead of Tabix bins: Tn 187 → S
      69, with the same records.

### Correctness

- **0 wrong pieces and 0 missing departure records** for every candidate
  that holds format 6's pieces: A0, F6p, T, Tn, O, Ou, S, S2, Srel and Sabs,
  105,400 pieces on MC and 107,819 on pggb.
- **S and Tn read departures over D itself,** so they return only records
  whose end nodes or stretch touch D:
  - 8,446 records against 8,614 on MC, and 811,437 against 895,031 on pggb.
  - The ones dropped lie in the reach band with no node in D.
  - None of the records they return falls outside the widened truth set.
- **My first S prototype misplaced the stub extent** of abridged pieces
  read backwards (5,009 pieces in one pggb 1 Mb window). That was the
  prototype's bug, not the design's; it is fixed and rechecked.

### Lens counts (Heng Li's habits)

| | row kinds | header/table kinds | sibling seqs / files | fake coordinates | read rules | cross-row dependencies |
|---|---|---|---|---|---|---|
| F6p | 6 | 5 header (`#walks #reference #haplotype #long #hole`) | `~departure`, `~cs`; 2 files | every tile row `cs cs+1`; detail `d×16384` | lookback by reach and `#long`; departures ± reach and `#long`; rows cut per bin | route chain, walk→route index, walk→R, →nodes, pieces joined across chunks |
| T | 6 | 5 | same; 2 files | tile rows claim `cs cs+C` (content overhangs by up to reach); detail `d×C` | same as F6p | same |
| O | 6 | 4 header + table | 4 files (data, table, BED, TBI) | none | departures ± reach and `#long` | same |
| N | R, H, V + stubs, detail | `#fragment` per W line | 2 files, `~detail` | detail `rec×16384` | round to cells; stubs; half-sites; visit index (needed, not built) | a path is rebuilt by chaining V rows by breakpoint across rows and cells; presence from H |
| **S** | **6** | **4 header + 4 table kinds** | **2 files, no siblings** | **none** | **one: fetch entries overlapping D** | **route chain, walk→route index, walk→R, →nodes, pieces joined across tiles** |

What each cross-row dependency earns, measured on MC (median KB at 1 kb /
1 Mb):

- **Walk rows naming routes by tile-local index:** removing it (Srel) costs
  87 against 28 KB, and 1,491 against 490 KB: 3.1×. It also costs 1.75× the
  file. It earns its keep.
- **Delta tokens:** removing them (Oabs) costs 50 against 33 KB, and 833
  against 487 KB, with p99 7×. They earn their keep.
- **The route chain across rows:** removing it (S2) costs 31 against 28 KB
  and 542 against 490 KB, +6 to 11%, and on pggb about 0. That is marginal.
  S keeps it: route rows are a dictionary read only by index, never alone,
  and keeping it changes no reader or writer.
- **Pieces joined across tiles:** a piece ends at a tile edge so that a
  tile is self-contained. A plain join by `piece` number is the cheapest
  form this can take.

## Why each other candidate loses

- **F6p:**
  - It keeps the fake `cs cs+1` key, two sibling sequences, the reach and
    `#long` lookbacks, and a @gmod/tabix patch.
  - A 1 kb window costs 36 KB against S's 28 on MC, and 292 KB in 3 round
    trips against 69 KB in 1 on pggb.
- **T:**
  - The honest-looking `cs cs+C` key still understates rows by up to reach,
    so a reach rule and `#long` stay, and detail keeps a fake coordinate.
  - Bytes on MC equal F6p's (37 KB). On pggb a 1 kb window costs 226 KB,
    and 187 KB even with S's departure filing (Tn): 2.7× S's, in 3 round
    trips.
  - True extents in Tabix are the trap the reviews measured: 3.3× the bytes
    under TBI and 2 to 4× under CSI.
- **T16:**
  - It wins only at 1 kb on MC (24 KB).
  - It costs 120 against 73 KB at 100 kb and 978 against 490 KB at 1 Mb,
    with a file 20% larger. On pggb its p90 at 1 Mb is 9.6 MB.
- **O:**
  - Its tiles are right, which is why S keeps them. Its departures still
    need the reach and `#long` widening, plus a second index file.
  - A 1 kb window costs 281 against 69 KB on pggb and 33 against 28 KB on
    MC, in 4 files against 2.
- **Ou (O with uncut departures):** filing a record once at its full
  stretch costs 3.5× on pggb (986 against 281 KB at 1 kb) and 1.7× the p90
  on MC (108 against 63 KB). The pyramid earns its keep.
- **N:**
  - It wins pggb's 1 Mb median (461 against 720 KB) and has the smallest
    file (47 MB).
  - It loses MC's tail: 121 against 51 KB at the p90 for 1 kb, and 2,999
    against 1,399 KB at the p99 for 1 Mb.
  - It needs a visit index on 60% of pggb's departures (native's own count:
    4.9 M of 8.1 M). That index is not built, so its pggb bytes are
    understated and 11 of 60 windows were wrong.
  - It replaces the reader's whole decode with site-chaining across rows,
    which is the opposite of self-contained lines.
- **Srel / Sabs (self-contained lines):**
  - 3.1× and 4.5× the bytes on MC at the 1 kb median, 1.75× and 4.9× the
    file. Gzip's 32 KB window can't recover the dictionary.
  - Simplicity at several times the bytes loses at HPRC scale.
- **S2:** 6 to 11% more bytes on MC for one fewer cross-row rule that no
  reader uses alone. That doesn't pay for changing the writer and reader.

## The detail tier

- **A second tier is needed.** Without abridging, MC chr22's largest 64 kb
  tile is 4.5 MB, and pggb chrY's satellite tiles are about 10 MB of rows
  (cleansheet's no-abridge builds). A window there would cost megabytes,
  over graph-walks' 8 MB budget on pggb. The tier is what holds the p99
  under 0.2 MB at 1 kb on MC.
- **Duplication is the simpler cost.** It is paid on disk, not per window:
  - Detail entries are 39 MB of MC's 57 MB, and 159 MB of pggb's 184 MB.
    No window read touches them.
  - A record expands in one fetch and decodes alone.
- **Cross-referencing shared routes** (cleansheet) would save up to 27 MB
  on chr22. In exchange it adds a dependent second fetch and a
  cross-record dependency.
- **Self-contained lines would not shrink it:** the Srel detail tier is
  43.8 MB against 39.1 MB.
- **Keep the tier as format 6 has it, addressed by name in the table.**

## Consequences

- **Format 7** (gfa-to-tabix 4.0.0, graph-walks 6.0.0). The row encoding
  inside tiles and detail records is format 6's, so the encoder, its build
  check, placement, stay and abridging don't change.
- **gfa-to-tabix:**
  - Write entries block-aligned. `parallel_bgzf.rs` flushes at each entry,
    and the table needs each entry's offset and length.
  - Drop the three key columns.
  - Compute each tile's true extent; the encoder already decodes every row.
  - File departure records over their end nodes, listed in the tile
    pyramid's blocks. This replaces the bin-size cut.
  - Name detail entries `cs:d`.
  - Drop `#long`, `chunk:i:`, `maxnode:i:`, the `~departure` and `~cs`
    siblings, the CSI fallback and the TBI.
  - Rough size: 200 to 300 lines changed in `walks.rs`, `departures.rs`
    and `parallel_bgzf.rs`. My converter (`build.mjs` + `sfinal.mjs`) is
    about 400 lines of JavaScript.
- **Spec (`docs/walks-format.md`):**
  - Chunks become tiles.
  - The "Header" lookback paragraph, the `#long` section, the bin-size cut
    and "Reading a window" collapse into the one overlap rule.
  - Add the table's columns and the extraction one-liner.
  - ADR 0010 records this table and why each loser loses.
- **What the old mechanisms compensated for,** each carried over:
  - `cs cs+1` compensated for TBI bin sharing: the table gives exact byte
    ranges.
  - The chunk-before lookback compensated for straddling nodes and stays:
    true tile extents.
  - `#long` compensated for 1 Mb nodes: true tile extents.
  - The departure reach of `maxnode`, and later reach, compensated for end
    nodes straddling the window's edge: records filed over their end nodes.
  - The bin-size cut compensated for wide records in big bins: pyramid
    blocks as table entries.
  - `seq~cs` at `d×16384` compensated for detail lookup: named table
    entries.
  - CSI for over 32,768 records compensated for TBI's 512 Mb limit: the
    table has no coordinate limit.
- **graph-walks:**
  - `cut`'s return shape (fragments, departures, tables) is unchanged.
  - What changes is the source `WalkReader` is built on: a table-and-ranges
    source in place of `TabixSource`. graph-walks should export one opener
    from the prefix URL.
  - `walkQueryStart`, `lookbackChunks`, the `~departure` read, the reach
    and `#long` logic and the attach-fetch lookback all go. An attach fetch
    becomes the leave tile's entry, which is exact.
  - `bytesForRegions` becomes the sum of the selected entries' lengths,
    which is exact.
  - `decodeChunk` reads rows without the key columns.
- **The five consumers** (plugin 9, BandageJS, ggbandage, tube map,
  jb2hubs):
  - The API they use doesn't change. Each changes the one line that opens
    the walk file, plus the pin bump; there is no re-port of `cut` users.
  - The plugin's `walksUri` prefix config is unchanged. The files behind it
    become `.walks.gz` and `.walks.gz.idx`, and the plugin no longer needs
    `@gmod/tabix` for walks.
- **Hosted data:**
  - Rebuild GRCh38 and CHM13 genome-wide from the writer, about 70 minutes
    each. The 3.0.0 files in `~/work/genome3/` are superseded, and the
    cutover stays on hold until format 7 is built.
  - A converter could repackage the 3.0.0 files without re-placing.
    Rebuilding is the cleaner gate, since the release check audits the
    writer's own output.
  - Estimated open cost genome-wide: about 1.25 MB of gzip table (chr22's
    48 KB with numeric detail names, × 26). Today's TBI is 1.75 MB.
- **Release gates:**
  - Consumers green on the exact graph-walks 6 before any release.
  - gfa-to-tabix's full CI job locally before the tag.
  - `pnpm release-check WALKS=<prefix>` on the hosted pair.
  - One-pass swap of data, plugin and configs.

## Found along the way (for the issues log)

- **graph-walks 5 sizes the departure read from the header's `maxnode`**
  (1 Mb on pggb). On chrY a 1 kb window costs 1,545 KB median, 3 round
  trips and up to 6 requests (A0), against 292 KB with the 50 kb reach.
  The reader review found the cause; this harness reproduces the cost.
  - Fix: format 7 removes the widening.
  - Guard: S's departure rule, checked on 96 windows.
- **@gmod/tabix reads a whole extra block past a chunk** whose end virtual
  offset is a block start (`Chunk.endPosition`). History found it. It is
  part of A0 → F6p (95 → 36 KB on MC, with the narrower read and block
  alignment).
  - Fix: upstream the one-line `chunk.js` change in @gmod/tabix, which
    other Tabix users benefit from.
- **The same departure records cost 2.7× through CSI bins (Tn, 187 KB)
  than as exact table groups (S, 69 KB)** on pggb 1 kb windows. The likely
  causes are @gmod/tabix merging chunks across bins within 65 KB and block
  rounding. I didn't confirm which.
- **Filing departures uncut costs 3.5× on pggb** (Ou). Guard: the pyramid
  stays in format 7.
- **The 3.0.0 files start no chunk on a BGZF block** (history: 0 of 776),
  so every read spills into its neighbours. Fixed in format 7 by
  construction.
- **The format 6 spec's rationale for `cs cs+1`** ("would share a Tabix
  bin") was never measured. ADR 0010 replaces it with this table.

## Files

The paths below are under
`/tmp/claude-1001/-home-cdiesh-src-gfa-to-tabix/95217c34-cd76-4f06-8705-ae30877df61b/scratchpad/format-review/arbA/`:

- **Scripts:** `scripts/measure.mjs` (harness), `build.mjs` (all
  rewrites), `sfinal.mjs` (S), `tnode.mjs` (Tn), `scodec.mjs` (self-contained
  lines), `bgzf.mjs`, `summarize.py`.
- **Results:** `data/res/*.jsonl` (one line per window per candidate,
  with per-file bytes and checks), `data/res/summary.md`,
  `data/sizes.txt`.
- **ada:** `~/work/arb-arbA/out/{mc22,pggbY}/` holds every candidate file
  and index, with `build.sh` and `run.sh` to rerun.

## Cross-examination

arbB decided on T64: format 6 rows at `seq cs cs+65536`, a CSI with
`min_shift` 16, chunks block-aligned, `reach:i:`, departures cut at
512 kb × 8^L, detail records at `d × chunk`, and the @gmod/tabix chunk-end
fix. I measured its own files (`arbB/data/*/t64d19.bed.gz` + `.csi`, copied
unchanged) in my harness, with its query rules:

- walk read `[D.start − reach, D.end)`, widened to any `#long` pass;
- departure read `[D.start − reach, D.end + reach)`;
- attach fetch `[base − reach, base + 1)`.

### Attach fetches added

My first table left out graph-walks' attach fetches; arbB counted them, and
on pggb they dominate. The harness now runs them for every candidate
(`ATTACH=1`) with graph-walks' rule:

- **Which records:** own bp greater than missing bp, own bp at most
  65,536, and the leave chunk not in the read.
- **How many:** one fetch per chunk, at most 8, as a second round trip.
- **What S fetches:** the one table entry whose extent holds the leave
  base, which is exact.

### Same windows, KB median / p90 / p99, read · read + attach fetches

| | MC 1 kb | MC 100 kb | MC 1 Mb | pggb 1 kb | pggb 100 kb | pggb 1 Mb | whole-chrY 1 kb (arbB's range) | trips max |
|---|---|---|---|---|---|---|---|---|
| F6p | 36/65/164 · 37/144/272 | 83/133/271 · 87/210/452 | 498/684/1395 · 499/729/1395 | 288/789/1855 · 604/1432/2336 | 343/1024/3419 · 669/1709/3652 | 795/3497/4887 · 1526/3737/5121 | 8/449/2433 · 275/1205/2667 | 4 |
| **T64 (arbB, exact)** | **39/68/186 · 42/269/518** | **88/138/284 · 96/287/705** | **514/699/1426 · 523/787/1521** | **249/662/2129 · 801/1996/2994** | **267/818/3425 · 809/2139/4481** | **705/3544/4261 · 1737/4585/4850** | **8/393/2464 · 284/1561/2961** | 3 |
| Tn (T + S's departure filing) | 36/68/197 · 37/263/530 | 83/134/317 · 92/277/722 | 504/694/1426 · 516/781/1518 | 187/471/1609 · 696/1881/2115 | 259/785/3397 · 786/2101/3884 | 877/3316/5579 · 1824/3802/6066 | 8/394/1609 · 275/1006/2163 | 4 |
| Tl (Tn, departures in 4 per-level siblings) | 37/62/170 · 37/255/476 | 85/132/278 · 92/270/655 | 507/694/1432 · 514/775/1525 | 177/400/1642 · 675/1910/4810 | 208/682/3326 · 733/1974/5536 | 835/3371/5540 · 1729/4416/6110 | 8/296/1642 · 276/1225/2682 | 2 |
| Tlb (Tl, each pyramid block block-aligned) | 29/55/166 · 30/242/467 | 77/128/269 · 85/263/649 | 504/690/1429 · 513/769/1521 | 73/263/1523 · 591/1788/4753 | 129/543/3209 · 620/1883/5419 | 732/3301/5485 · 1621/4344/6032 | n/a | 2 |
| **S** | **28/51/163 · 30/236/455** | **73/123/261 · 83/257/633** | **490/671/1399 · 496/745/1489** | **69/237/1460 · 364/1235/1690** | **118/462/2329 · 504/1349/2559** | **720/3185/5083 · 1409/3415/5313** | **2/164/951 · 261/592/1338** | 2 |
| S512 (S, pyramid from 512 kb, arbB's unit) | 32/55/159 · 34/243/474 | 76/127/254 · 84/264/652 | 482/658/1341 · 489/736/1431 | 123/577/1650 · 513/1349/2438 | 143/801/2064 · 588/1476/2477 | 601/3174/3673 · 1402/3760/4245 | 2/245/1449 · 261/1238/1678 | 2 |

Notes on the table:

- **Windows:** 300 per size and dataset. "pggb" is my euchromatic range,
  2.78–26.67 Mb; "whole-chrY" is arbB's 2.8–56.8 Mb. On the whole of chrY
  half of the windows fall in N runs, so the medians there only show the
  attach floor.
- **Correctness:** 96 checked windows per row, 0 wrong pieces and 0
  missing departure records in all of them. Full tables, with 10 kb, are in
  `data/res2/summary.md`.
- **arbB's own numbers match mine.** Its T64 pggb median (284 KB) was the
  whole-chrY range with attach fetches; mine gives 284 there too.

### The 2.7×: what it is

Same records, same CSI, pggb 1 kb read median, one change at a time:

- **F6p → Tn, filing each record over its end nodes,** so no reach
  widening: 288 → 187 KB (−35%).
- **Tn → Tl, splitting the departure rows into one sibling per pyramid
  level,** so each level's rows are contiguous instead of interleaved by
  position: 187 → 177 KB (−5%). This is the interleaving and the
  @gmod/tabix chunk merging across bins, and it is small.
- **Tl → Tlb, starting every pyramid block on a BGZF block:** 177 → 73 KB
  (−59%). This is the cause. A departure bin's rows are a few hundred
  bytes at each of four levels, but each read pays the whole 64 KB
  uncompressed BGZF blocks around them.
- **Tlb → S, the table instead of the CSI:** 73 → 69 KB (−5%).

So the 2.7× was block alignment of the departure groups, first, plus
filing over end nodes. It was not the index.

A Tabix design can close S's pggb read advantage to 5% (Tlb: 73 against
69 KB at 1 kb, 29 against 28 KB on MC). To do that, it must:

- file records over their end nodes;
- split departures into four sibling sequences (`~departure0` to
  `~departure3`) and issue four queries per window;
- flush a block at every pyramid block.

It doesn't close the attach difference, because T's attach rule reads
`[base − reach, base + 1)`, two chunks in about 76% of cases on pggb:

- attach median at pggb 1 kb: 486 KB for Tn, Tl and Tlb, 497 for T64,
  against 230 for S;
- read plus attach: Tlb 591 KB against S 364.

A T reader could query `[base, base + 1)` and refetch when the leave node
straddles. That is one more reader rule I haven't measured.

**Against arbB's exact T64, S fetches:**

- **pggb:** 3.6× fewer bytes in the read at 1 kb (69 against 249 KB) and
  2.2× fewer with attach fetches (364 against 801 KB). At the p90,
  1,235 against 1,996 KB.
- **Whole chrY:** p90 592 against 1,561 KB.
- **MC:** 28 against 39 KB at 1 kb.

**arbB's "offset table, zero gain" holds for tiles, not for departures.**
Its O, like mine, gives tiles exactly what a CSI with the chunk as leaf
gives. The gain is in departures and attach fetches, where the table can
address the groups and exact tiles that a bin index can't.

### S's own weak points

- **Duplicated departure lines.** S lists 54,050 lines for 24,648 MC
  records (2.2×) and 1.56 M for 425 k pggb records (3.7×):
  - Format 6 has 31,239 rows and 1.22 M; arbB has 26,903 and 0.80 M.
  - Cost on disk: S's departure groups are 0.87 MB on MC and 14.5 MB on
    pggb. S512 (arbB's 512 kb unit) halves that, to 0.43 and 7.3 MB.
  - S512 also has a lower 1 Mb tail on pggb (p99 3,673 against 5,083 KB).
    But it costs 1.8× at pggb 1 to 10 kb (123 against 69 KB) and 1.4× with
    attach fetches (513 against 364 KB).
  - Views are mostly small, so the 64 kb unit stays. The duplication is
    disk, 1.5% of MC's file and 8% of pggb's.
  - The dedup rule is "drop exact duplicate lines". It can't merge two
    real records, because two records of one path differ in `hapStart`.
    It held on every window checked.
- **The table read whole at open,** bounded rather than measured on the
  genome-wide files. I didn't open `~/work/genome3`.
  - Per entry, gzipped, on chr22: 18.0 B per tile, 14.7 B per departure
    group, 10.1 B per detail entry with numeric `cs:d` names.
  - GRCh38's 3.1 Gb has at most 47.3 k tiles and 54.1 k departure groups
    (the sum of the pyramid's levels), which bounds those at 1.65 MB.
  - Detail entries scale with abridging: 0.65 MB if like chr22 (× 26 by
    file size).
  - Estimate: up to about 2.3 MB at open, against today's measured
    1.75 MB TBI and arbB's estimated 0.6 MB CSI. **This is where T64 wins.**
  - Mitigation if it matters: put detail entries in a second table read on
    the first expansion (≤ 1.65 MB at open), or give each sequence its own
    section (chr1's share is about 8%). S as decided reads one table.
- **A custom index instead of a CSI:**
  - `tabix f region` and htslib's region API don't work on the walks file.
    pysam, noodles and JBrowse's `TabixIndexedFile` don't apply.
  - graph-walks carries its own reader: about 60 lines plus
    `@gmod/bgzf-filehandle`'s `unzip`. My `sCand` is 55.
  - Stock tools still work by offset: `awk` on the table, then
    `tail -c +$((off+1)) | head -c len | gzip -dc`. `zcat | grep` works on
    the data file.
  - What a stock `tabix` returns on T64 is a chunk of format 6 rows that
    still needs graph-walks to decode. So no tool reads a path from either
    file. It is a debugging convenience, not a capability the readers need.
- **Correctness on harder windows:** 365 targeted windows per dataset
  (`win/*.targets.jsonl`, `data/res3/`), every piece and departure record
  checked:
  - MC: LCR22A (18.0–19.0 Mb), LCR22B–D (20.3–21.6 Mb), 22q11 IGL
    (22.5–23.0 Mb), and 80 windows on randomly sampled strand-switch
    (inversion) records.
  - pggb: the AZFc ampliconic palindromes (23.0–26.6 Mb), the centromere's
    `#long` passes (10.25–10.65 Mb), TSPY and the X-transposed region
    (6.0–7.5 Mb), and 80 strand-switch records.
  - Result: S, Tlb and T64 all had 0 wrong pieces among 183,131 (MC) and
    148,647 (pggb), and 0 missing departure records.
  - In bytes, S beats T64 in every region: pggb ampliconic 190 against
    370 KB read and 470 against 968 KB with attach fetches; MC LCR22A 110
    against 155 KB.
- **A correction to my first write-up:** the detail tier's duplication is
  not 27 MB of repeated routes. arbB measured that repeated routes compress
  to 3.5 MB of chr22's 40 MB tier; the bulk is `nodes` rows. The conclusion
  stands: keep the duplication, which is disk and not window bytes.

### Restated decision

**Keep S.** The numbers that decide it:

- **Against T64 as arbB built it,** S fetches less on every dataset and
  window size except two 1 Mb quantiles on pggb (median 720 against
  705 KB, p99 5,083 against 4,261):
  - pggb 1 kb: 69 against 249 KB read, 364 against 801 KB with attach
    fetches.
  - MC 1 kb: 28 against 39 KB, p90 236 against 269 KB with attach.
  - Targeted repeats: 2× less.
- **The only Tabix design that reaches S's bytes is Tlb,** 5% behind on the
  read and 1.6× behind with attach fetches on pggb. It gets there by
  rebuilding S's table inside Tabix: four extra sibling sequences, each
  departure group block-aligned, plus the tile-span key's reach rule,
  `#long`, and detail at fake coordinates. That is the "fake refname"
  pattern multiplied.
- **What S costs:** a custom table and a 55-line reader in place of CSI and
  @gmod/tabix, `tabix` on the walks file, and up to about 2.3 MB at open
  genome-wide (estimated) against about 0.6 MB for a CSI. That is real, but
  it is read once per session, and it is no larger than today's measured
  1.75 MB TBI plus a third.
- **Taken from arbB:**
  - the @gmod/tabix chunk-end fix, upstream, whatever the walks format;
  - fixing graph-walks' attach-decode bug before release (merge attach
    fetches by tile, with the union of names);
  - its correction to the detail-tier accounting.
- **What S doesn't fix, and ADR 0010 should say so:** on pggb, attach
  fetches (230 KB median, 582 p90 at 1 kb) are now most of a window. That
  is the record design, not the container, as both arbiters found.
- **Consumers:** as before. `cut`'s return shape is unchanged; each
  consumer changes the line that opens the walk file, plus a pin bump.

Files: `scripts/measure.mjs` (with `ATTACH=1` and `WINDOWS=`),
`tnode.mjs` (`LEVELS=1`, `FLUSH=1` for Tl and Tlb), `sfinal.mjs`
(`UNIT=8` for S512), `targets.py`, `summarize2.py`; results in
`data/res2/` (300 windows per size, attach included) and `data/res3/`
(the targeted windows).

## S7

The coordinator's decision: S, amended (S7). Every data line starts
`seq start end`, the unit table is split per sequence, and the independent
prior-art and failure-mode review's changes are folded in. This section
gives the measurements, then the spec.

### Review changes: all taken

- **Dictionary rows take the tile's extent.** That covers `ref`, `nodes`
  and `route`. Measured: per-row route spans (entry to exit) cost 68.7
  against 59.3 MB on MC and 191.7 against 187.9 MB on pggb. They also cost
  +27% at a 1 Mb MC window (623 against 505 KB median) and +24% at 1 kb (36
  against 29), for nothing a reader uses. On a revisited reference a route's
  ends also have several passes, and the walk row's `:k`/`@k` picks one, so
  a route has no single span to state.
- **The departure cover is stated precisely,** as the writer already did
  it. The reader rule doesn't depend on it.
- **An in-stream `#unit` line at the start of every unit.** `verify7.mjs`
  rebuilds the unit list by scanning gzip members and checks it against the
  tables.
- **The directory is bound and versioned.** Its line 1 is the data's
  `#walks` line plus `bytes:i:<file length>`. The harness reader refuses a
  directory whose line 1 differs from the header unit's, or whose `bytes`
  differs from the Content-Range total.
- **Empty rules, name checks, file order, temp-then-rename, hosting and
  release checks** are taken into the spec below.
  - `s7.mjs` refuses bad names and writes both files under temporary names
    before renaming.
  - The prototype lists the sequences that hold rows. A format 6 input
    doesn't name the empty ones; the writer must list every reference
    sequence.
  - `verify7.mjs` runs the release checks. It passed on both files: 3,837
    units and 1,958,554 lines on MC; 1,492 units and 3,126,030 lines on pggb.

### Measurements

Same harness and windows as before (`data/res4/`). Every row checked 96
windows at the piece level: 0 wrong pieces and 0 missing departures. Cells
are KB median / p90, read · read plus attach fetches. T64b is arbB's own
`t64b.bed.gz` and `t64b.exact.csi`, with its rules:

- walk read `[D.start − reach, D.end)`;
- departures over D, keeping rows whose trailing extent touches D;
- attach `[base − reach, base + 1)`, with reach 50,008 on pggb.

| | MC 1 kb | MC 100 kb | MC 1 Mb | pggb 1 kb | pggb 100 kb | pggb 1 Mb | whole chrY 1 kb | whole chrY 1 Mb | trips max |
|---|---|---|---|---|---|---|---|---|---|
| T64b | 30/57 · 32/255 | 80/132 · 88/272 | 519/715 · 527/794 | 121/285 · 618/1301 | 149/604 · 644/1981 | 772/3451 · 1774/3947 | 2/206 · 278/828 | 6/2138 · 282/2658 | 3 |
| S | 28/51 · 30/236 | 73/123 · 83/257 | 490/671 · 496/745 | 69/237 · 364/1235 | 118/462 · 504/1349 | 720/3185 · 1409/3415 | 2/164 · 261/592 | 6/1945 · 264/2205 | 2 |
| **S7** | **29/53 · 30/243** | **76/128 · 85/263** | **505/692 · 514/772** | **70/246 · 389/1358** | **120/485 · 543/1471** | **738/3562 · 1512/3815** | **2/164 · 272/632** | **6/2008 · 276/2295** | **2** |

- **The p99s at pggb 1 Mb** (read · read plus attach): T64b 5,849 · 6,346;
  S 5,083 · 5,313; S7 5,978 · 6,231. That is the one quantile where S7's
  read is not the lowest.
- **Requests, median:**
  - MC: 1 for S7, 2 for T64b.
  - pggb, with attach fetches: about 10 for S7, 11 for T64b.
- **What S7's columns cost over S:** +2.6% file on MC and +1.9% on pggb.
  Per window, +1 KB at MC 1 kb, +3% at 100 kb, and +3% at 1 Mb. Attach
  fetches cost +7% at pggb 1 kb, because a whole tile carries the prefixes.
- **arbB's own reach-4 kb variant of T64b,** measured in its harness: 444
  against S's 384 KB with attach fetches at pggb 1 kb. Mine wasn't run.

| | MC chr22 | pggb chrY |
|---|---|---|
| data file | S7 59.31 MB, S 57.82, T64b 60.39, shipped 59.17 | S7 187.92 MB, S 184.47, T64b 192.73, shipped 192.15 |
| index read at open | S7 48.6 KB in 2 round trips: directory 159 B, header 1.4 KB, chr22's table 47.1 KB | S7 22.1 KB: directory 210 B, header 0.8 KB, chrY's table about 21 KB |
| for comparison | T64b 87 KB in 1 round trip (CSI 20 KB plus @gmod/tabix's 64 KB header probe); S 58 KB | T64b 76 KB; S 25 KB |

**Open cost genome-wide (an estimate; I didn't read `~/work/genome3`):**

- A reader fetches the directory (one line per reference sequence, a few
  KB), the header, and one sequence's table.
- chr22's table is 47 KB for 50.8 Mb, dense with LCR22 detail records. On
  that density chr1's would be about 230 KB, and the whole set about
  1.2–2.9 MB, never read at once.
- A CSI is read whole: about 0.6–1.5 MB by arbB's estimate. Today's TBI is
  1.75 MB.

### Correctness through graph-walks' `cut`

`scripts/cutcheck.mjs` runs graph-walks 5.0.2's `WalkReader.cut` with
budgets lifted, comparing fragments, departures and kept nodes. The source
addresses tiles, attach fetches and detail by the unit table. My scratch
copy on ada carries the attach-decode fix (decode a chunk again for names
not yet decoded); without it, adjacent attach fetches drop records' own
steps, as cleansheet and arbB found.

- **Against the same reads of the shipped rows** (`BASELINE=units`): the
  shipped file's own format 6 rows, read for exactly the units S7 selects,
  with the same departure lines. Any difference would be in S7's rows.
  - MC: 90 of 90 random windows and 365 of 365 targeted, identical.
  - pggb: 90 of 90 random windows and 365 of 365 targeted, identical.
  - The targeted windows cover LCR22A–D, 22q11, the chrY ampliconic
    palindromes, the `#long` centromere, the X-transposed region, and 160
    strand-switch (inversion) records.
  - Windows of 1–100 kb. graph-walks' 1 Mb cuts with budgets lifted ran
    out of Node's heap and string limits in the comparison, as arbB's did;
    1 Mb windows are covered by the piece-level check.
- **Against the shipped reader** (graph-walks 5's rule: the chunk before,
  departures ± `maxnode`). This run used the unpatched graph-walks for both
  sides:
  - MC random windows: 88 of 90 identical. The other 2 differ by one kept
    node, from the chunk before the window, which the shipped rule reads by
    habit (checked on chr22:45,417,755).
  - MC targeted windows: 328 of 365 identical, 12 identical in fragments,
    and 25 differing. All 25 are in LCR22A, LCR22B–D and on strand-switch
    records. There the shipped reader has more departures and nodes, never
    fewer, and joins fragments across the chunk before: the LCR22A
    excursion arbB and cleansheet documented.
  - pggb: no window is identical, because the shipped reader reads
    departures ±1 Mb (`maxnode`) and keeps tens of thousands more nodes.
    Six windows showed records or nodes only in the S7 cut. Rerun with the
    attach-decode fix on both sides, those six had none: the shipped cut
    holds everything the S7 cut holds, and more.
  - These are the shipped rule's differences, not S7's. The `units`
    baseline above isolates S7's rows, and they match.

### Spec (walk format 7)

**Files.** `<prefix>.<sample>.walks.gz`, the data, and
`<prefix>.<sample>.walks.gz.idx`, the directory.

**The data file** is a series of units, each a whole run of gzip (BGZF)
members, then a BGZF EOF block:

- **The header unit,** first, from byte 0:
  - `#walks format:i:7 tile:i:65536 revisited:i: stay:i: abridge:i: abridgebytes:i:`
  - `#reference`, `#haplotype` and `#hole` lines.
  - No `#long`, `chunk` or `maxnode`.
- **Per reference sequence,** in file order:
  - its `tile`, `departures` and `detail` units;
  - then its `table` unit, which lists them.
- **Every unit except the header** starts with
  `#unit seq start end kind name`. That line makes the file self-delimiting:
  the tables can be rebuilt by walking the gzip members.

**Data lines.** Every line not starting with `#` begins `seq start end`:
the reference sequence and the stretch of it the line is about. These are
data, not a key, so `zcat | grep` places any line. Format 6's columns
follow from `kind` on, unchanged.

| kind | `start end` is | where |
|---|---|---|
| `walk` | the piece's span on R: from the first base of its first placed step to the last base of its last | tile, detail |
| `abridged` | the moved piece's span on R, its stretch | tile |
| `ref`, `nodes`, `route` | the unit's extent: these are the tile's dictionary rows, with no span of their own | tile, detail |
| `departure` | from the first base of its first end node to the last base of its other end node, or the breakpoint stretch if wider | departures |

**Units:**

- **`tile`:** the rows of one tile of `tile:i:` bp, as format 6 writes a
  chunk.
  - `start end` are the union of its `ref` rows' spans and its pieces'
    spans: the tile's true extent, which may begin after the nominal start
    and run past the tile.
  - `name` is the nominal start, a multiple of the tile size.
  - Readers address tiles by extent, never by `floor(base / tile)`.
- **`departures`:** the records of one block of the departure pyramid.
  - `start end` are the block; `name` is its size (64 kb × 8^L).
  - Each record goes in the largest aligned blocks inside its tile-rounded
    extent: walk from `floor(start / T) × T` to `ceil(end / T) × T`, taking
    at each point the largest of 32 Mb, 4 Mb, 512 kb and 64 kb that is
    aligned there and fits.
  - A record's lines in different blocks are identical.
- **`detail`:** one abridged path's moved pieces in one tile, format 6's
  detail record.
  - `name` is `cs:d`: the tile's nominal start and the `abridged` row's
    `detail` number.
  - `start end` are the union of its pieces' spans.
- **`table`:** after the `#unit` line, one line per unit of the sequence,
  in file order: `#entry seq start end kind name offset length`.
  - `offset` and `length` are compressed bytes in the data file, as decimal
    text. Readers scan the table; they don't bisect it.

**The directory** is plain text:

- line 1: the data file's `#walks` line, plus `bytes:i:<data file length>`;
- `#header 0 <length>`;
- one `seq <offset> <length>` line per reference sequence, giving its table
  unit.

Every reference sequence is listed. A sequence with no units has a table
holding only its `#unit` line.

**Reading a window [s, e)** with context c, D = [s − c, e + c):

- **At open:**
  - GET the directory and refuse a format other than 7.
  - GET the header unit and the sequence's table in parallel.
  - Refuse when line 1 differs from the header's `#walks` line, or when
    `bytes` differs from the Content-Range total.
- **The read:**
  - Select the `tile` and `departures` units with `start < D.end` and
    `end > D.start`, skipping any of length 0.
  - Merge byte ranges that touch, and GET each as a single range (never a
    multi-range request).
  - gunzip each unit. In a tile, decode the rows from `kind` on with
    format 6's rules.
  - From departure units, keep lines with `start < D.end` and
    `end > D.start`, and drop exact duplicate lines.
- **Rebuilding paths, as graph-walks does now:**
  - R from the `ref` rows; routes chained through the tile's route rows;
    each walk row decoded against them.
  - Pieces joined across tiles by `path, fragStart, piece`.
  - Departures computed inside a piece; the rest from the records.
- **Attach fetches:** the `tile` unit whose extent holds the leave base.
- **Expanding an abridged piece:** the `detail` unit named `cs:d`.

**Stock tools:**

```
# a sequence's table
read off len < <(awk -F'\t' -v s="GRCh38#0#chr22" '$1==s {print $2, $3}' f.walks.gz.idx)
tail -c +$((off+1)) f.walks.gz | head -c $len | gzip -dc
# one unit
tail -c +$((uoff+1)) f.walks.gz | head -c $ulen | gzip -dc
# every line touching a region, by a full scan
zcat f.walks.gz | awk -F'\t' '$1=="GRCh38#0#chr22" && $2<20001000 && $3>20000000'
```

**What a writer guarantees:**

- Every unit starts a gzip member, with its `#unit` line, and ends one.
- The header, the units, the tables and the EOF block partition the file.
- Each table lists every unit of its sequence, before it, in file order,
  with lengths greater than 0. A length-0 entry may exist and is never
  fetched.
- A tile's extent is the union of its rows' extents, and every line lies
  within its unit's `start end`.
- Every step placed on R in [a, b) is in a tile whose extent overlaps
  [a, b).
- Every departure record is in every block of its cover; each departure
  line overlaps its block.
- Names hold no tab or newline and don't start with `#`. The build refuses
  any that do.
- Offsets and lengths are exact integers below 2^53.
- The data file is written, then the directory, each under a temporary name
  and renamed.
- Format 6's encode-decode check runs on every row.

**Hosting:**

- Versioned file names, so the data and directory can never mismatch
  across a deploy.
- Single-range requests only: CloudFront answers a multi-range request with
  the whole object.

**Release checks** (`scripts/verify7.mjs`):

- the partition of the file by header, units, tables and EOF;
- a gzip member at each unit;
- every unit listed as it is;
- tile lines within the tile's extent, and the extent their union;
- each departure line's cover containing its block;
- `bytes` and the `#walks` line matching the directory.

### For the genome-wide build

- **Scripts on ada,** `~/work/arb-arbA/scripts/` (sha256 prefixes):
  - `bgzf.mjs` 2556cb1f18fd23df
  - `scodec.mjs` 89a19a3991c7c38e
  - `build.mjs` 6784f0500e274ea0
  - `sfinal.mjs` d7f73e7313982229
  - `s7.mjs` 60bac3ba464dc904
  - `verify7.mjs` 63d7d85207c63024
  - They import graph-walks 5.0.2's `src/` from `../gw/src` (a copy; the
    attach-decode fix there is in `walkReader.ts` only, which the build
    doesn't import).
- **Pipeline,** from a 3.0.0 format 6 file, `<f>` in `<dir>`:
  - `node build.mjs <f> <dir> 65536 o` writes `o.walks.gz`/`.idx`,
    `dep.bed.gz` and `depu.bed.gz`.
  - `node sfinal.mjs <dir>` writes `s.walks.gz`/`.idx`. Its node lookup was
    rewritten to per-sequence sorted arrays, because one Map per node would
    pass V8's Map size limit on a genome. The output is byte-identical on
    MC and pggb.
  - `node s7.mjs <dir>` writes `s7.walks.gz`/`.idx`.
  - `node verify7.mjs <dir>/s7.walks.gz` runs the release checks.
- **Memory:** these scripts hold the O file and one sequence's records in
  memory, about 3 GB for 1.5 GB of input. Run them under `systemd-run`
  with `MemoryMax`.
- **This is a converter.** The ADR's writer change belongs in gfa-to-tabix;
  a writer-built file must pass the same `verify7.mjs`.
