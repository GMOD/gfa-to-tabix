# Decision: the walks file's container (for ADR 0010)

Arbiter arbB. Everything below was measured with one harness
(`harness/`), the same seeded windows for every candidate, through real
HTTP range requests against a local static server that logs each one.
Data: the shipped 3.0.0 files for HPRC v2.1 Minigraph-Cactus chr22
(463 haplotypes, 59.2 MB) and HPRC pggb chrY (136 haplotypes, 192 MB).

## The decision

- **The walks file is bgzipped text with a CSI index whose leaf bin is the
  chunk, every row filed at its chunk's real span, and every chunk a whole
  run of BGZF blocks**, because that fetches exactly the chunks a window
  needs (28 KB median for a 1 kb window on MC chr22, against 84 KB today,
  the same bytes as any custom chunk table), with the smallest index of any
  candidate (20 KB against 41 KB), through the client stack that exists,
  and a plain `tabix file region` returns the chunk under the region
- Concretely, walk format 7:
  - a chunk's rows are `seq cs cs+chunk` (clipped to the sequence's end);
    rows, columns and decoding rules are format 6's, unchanged
  - the index is a `.csi` with `min_shift = log2(chunk)`, depth 5, written by
    the tool (`--chunk` must be a power of two); no `.tbi`
  - the writer ends a BGZF block at every chunk end and every detail
    record's end, so a chunk's bytes are whole blocks and a chunk read ends
    where the chunk does
  - departure records are filed over their end nodes, one row per block of
    the aligned pyramid `chunk × 8^L` (64 kb to 32 Mb) the record overlaps,
    the row's interval being the block's and the record's extent two
    trailing columns; a block's rows are contiguous and end a BGZF block
    (amended after the [Cross-examination](#cross-examination); the
    [Departure cut sizes](#departure-cut-sizes) section measured the
    earlier clipped-row cut)
  - detail records are filed at `detail × chunk`, so each keeps a leaf bin
    to itself under the new index
  - the header gains `reach:i:<bp>`: the furthest any chunk's rows place a
    step past `cs + chunk`, `#long` passes aside, and `#long` lists every
    pass over a node longer than `reach`, 4,096 by default (`--long`), so
    `reach` is 1,024 on MC and 4,096 on pggb chrY (amended after the
    cross-examination: at the old threshold of a chunk it was 50,008 there)
- A reader's window `[s, e)` with context `c`: one query
  `seq:[s − c − reach, e + c)`, widened to the start of any `#long` pass it
  overlaps; the departure query `seq~departure:[s − c, e + c)` in parallel,
  keeping the rows whose extent columns touch it; an attach fetch for a
  record's leave chunk is `seq:[base − reach, base + 1)`, widened by a
  `#long` pass holding `base`. No chunk arithmetic, no chunk-before rule,
  no `maxnode`
- @gmod/tabix needs its one-line chunk-end fix (`Chunk.endPosition =
  maxv.blockPosition` when `maxv.dataPosition === 0`), upstreamed; without it
  the stock client reads one block past every chunk (58 against 28 KB at
  1 kb). htslib needs nothing
- This is candidate T (64 kb, CSI) and it is also S, the design the Heng Li
  lens produced: the chunk is the unit of meaning, as a CRAM slice is, and
  every cross-row mechanism inside it was priced and kept
  ([Mechanisms](#mechanisms-counted-and-priced))

## Method

- Windows: 300 per size at 1 kb, 10 kb, 100 kb and 1 Mb, seeded, uniform
  over MC chr22 10.51–50.79 Mb and pggb chrY 2.8–56.8 Mb
  (`harness/windows.mjs`, seed 7; `results/windows-*.jsonl`)
- Server: `harness/server.mjs`, a static range server logging every request
  (path, byte range, bytes, start and end times); 5 ms per response so
  concurrent requests are told from sequential ones
- Client: `harness/measure.mjs`. Tabix candidates go through @gmod/tabix
  3.13.1 over `RemoteFile` (fetch), a fresh chunk cache per window, the
  header and index fetched once per candidate and reported as the open
  cost. The walk read and the departure read, then attach fetches for
  records with own steps the read lacks (graph-walks' rule, cap 8), each
  phase's requests taken from the server log. Round trips: the longest
  chain of requests each starting after the one before it finished, the
  walk and departure reads counted as concurrent. The offset-table
  candidate has its own reader in the same script
- Candidate files (`scripts/build_all.sh`, `scripts/refile.py` from the
  history review, `scripts/build_offset.py`): the shipped rows re-filed
  row for row, so every Tabix candidate decodes with graph-walks as is
- Correctness: `harness/cutcheck.mjs` runs graph-walks 5.0.2's real
  `WalkReader.cut` (budgets lifted, attach cap 64) once over the shipped
  file with its rule and once through each candidate's file and query
  procedure, comparing fragments, departures and kept nodes
- Encodings: `scripts/encode_variants.py`, `scripts/routelen.py`,
  `scripts/detail_dup.py` re-emit sampled chunks (120, seed 11) or the whole
  detail tier under alternative encodings and compress each unit alone
  (zlib 6, what BGZF does)
- htslib: `harness/htslib_bytes.py`, `tabix` under `strace`, 100 windows
  per size

## Candidates as built

| candidate | file | rows | index | query | client |
|---|---|---|---|---|---|
| F6 | shipped 3.0.0 | `cs cs+1` | TBI 41 KB | chunk before, ± `maxnode` | stock @gmod/tabix |
| F6p | F6 with blocks ending at chunk ends | `cs cs+1` | TBI 39 KB | chunk of `start − reach`, rounded to chunk starts | patched |
| T64 | same rows at real spans, blocks aligned, departures cut at 64 kb × 8^L | `cs cs+65536` | CSI min_shift 16, 20 KB | `[start − reach, end)` | patched |
| T16 | the 16 kb build re-filed the same way | `cs cs+16384` | TBI 60 KB | `[start − reach, end)` | patched |
| O | rows without coordinates in a BGZF file, a chunk table, departures in their own Tabix file | `seq cs kind …` | table 39 KB gz + TBI 5 KB | table lookup, one range | custom reader |
| N16 | native's interval-native prototype (`native16c`) | R, H, V per 16 kb cell | TBI 159 KB | cell-rounded overlap, stub fetches | patched |

File sizes, MC chr22: F6 59.17 MB, F6p 59.54, T64 59.59, T16 71.47, O 59.31
+ 0.42 (departures), N16 47.33. pggb chrY: F6 192.2 MB, F6p 188.6, T64
191.8, O 176.7 + 11.1, N16 144.5. Block alignment costs about one short
block per chunk (+0.6% in the prototype; the writer can do better)

## Measurements

### MC chr22, bytes per window, KB median / p90 / p99, requests, round trips

| candidate | window | total KB med / p90 / p99 | requests med / max | rounds med / max | walk KB med | dep KB med | attach KB med / p90 | walk rows med | open KB |
|---|---|---|---|---|---|---|---|---|---|
| F6 | 1 kb | 98 / 418 / 1064 | 2 / 8 | 1 / 2 | 84 | 8 | 0 / 240 | 3286 | 106 |
| F6 | 10 kb | 102 / 291 / 1030 | 2 / 8 | 1 / 2 | 91 | 8 | 0 / 193 | 3473 | 106 |
| F6 | 100 kb | 148 / 360 / 1090 | 2 / 8 | 1 / 2 | 134 | 8 | 0 / 193 | 6132 | 106 |
| F6 | 1000 kb | 601 / 1048 / 1710 | 2 / 8 | 1 / 3 | 552 | 23 | 0 / 193 | 30084 | 106 |
| F6-patched-client | 1 kb | 98 / 418 / 1064 | 2 / 8 | 1 / 2 | 84 | 8 | 0 / 240 | 3286 | 106 |
| F6-patched-client | 10 kb | 102 / 291 / 1030 | 2 / 8 | 1 / 2 | 91 | 8 | 0 / 193 | 3473 | 106 |
| F6-patched-client | 100 kb | 148 / 360 / 1090 | 2 / 8 | 1 / 2 | 134 | 8 | 0 / 193 | 6132 | 106 |
| F6-patched-client | 1000 kb | 601 / 1048 / 1710 | 2 / 8 | 1 / 3 | 552 | 23 | 0 / 193 | 30084 | 106 |
| F6p | 1 kb | 37 / 175 / 504 | 2 / 8 | 1 / 2 | 28 | 8 | 0 / 102 | 1630 | 106 |
| F6p | 10 kb | 38 / 133 / 584 | 2 / 8 | 1 / 2 | 30 | 8 | 0 / 48 | 1734 | 106 |
| F6p | 100 kb | 91 / 168 / 579 | 2 / 8 | 1 / 2 | 76 | 8 | 0 / 48 | 4448 | 106 |
| F6p | 1000 kb | 532 / 787 / 1537 | 2 / 8 | 1 / 2 | 495 | 16 | 0 / 71 | 28314 | 106 |
| F6p-stock-client | 1 kb | 66 / 267 / 754 | 2 / 8 | 1 / 2 | 58 | 8 | 0 / 192 | 1630 | 106 |
| F6p-stock-client | 10 kb | 69 / 206 / 846 | 2 / 8 | 1 / 2 | 61 | 8 | 0 / 114 | 1734 | 106 |
| F6p-stock-client | 100 kb | 121 / 257 / 848 | 2 / 8 | 1 / 2 | 104 | 8 | 0 / 114 | 4448 | 106 |
| F6p-stock-client | 1000 kb | 568 / 936 / 1653 | 2 / 8 | 1 / 2 | 522 | 16 | 0 / 120 | 28314 | 106 |
| T64 | 1 kb | 38 / 175 / 551 | 2 / 8 | 1 / 2 | 28 | 8 | 0 / 102 | 1630 | 87 |
| T64 | 10 kb | 40 / 128 / 643 | 2 / 8 | 1 / 2 | 30 | 8 | 0 / 48 | 1734 | 87 |
| T64 | 100 kb | 92 / 161 / 579 | 2 / 8 | 1 / 2 | 76 | 8 | 0 / 48 | 4448 | 87 |
| T64 | 1000 kb | 530 / 779 / 1564 | 2 / 8 | 1 / 2 | 495 | 23 | 0 / 71 | 28314 | 87 |
| T64-stock-client | 1 kb | 69 / 267 / 801 | 2 / 8 | 1 / 2 | 58 | 8 | 0 / 192 | 1630 | 87 |
| T64-stock-client | 10 kb | 72 / 199 / 899 | 2 / 8 | 1 / 2 | 61 | 8 | 0 / 114 | 1734 | 87 |
| T64-stock-client | 100 kb | 121 / 252 / 857 | 2 / 8 | 1 / 2 | 104 | 8 | 0 / 114 | 4448 | 87 |
| T64-stock-client | 1000 kb | 568 / 936 / 1680 | 2 / 8 | 1 / 2 | 522 | 23 | 0 / 120 | 28314 | 87 |
| T16 | 1 kb | 32 / 122 / 379 | 2 / 8 | 1 / 2 | 15 | 15 | 0 / 70 | 772 | 127 |
| T16 | 10 kb | 41 / 90 / 558 | 2 / 10 | 1 / 2 | 29 | 15 | 0 / 29 | 1476 | 127 |
| T16 | 100 kb | 126 / 206 / 472 | 2 / 10 | 1 / 2 | 106 | 15 | 0 / 29 | 5510 | 127 |
| T16 | 1000 kb | 1004 / 1266 / 2132 | 2 / 10 | 1 / 2 | 940 | 53 | 0 / 51 | 48722 | 127 |
| O | 1 kb | 36 / 176 / 500 | 2 / 8 | 1 / 2 | 28 | 8 | 0 / 102 | 1630 | 45 |
| O | 10 kb | 37 / 131 / 574 | 2 / 8 | 1 / 2 | 30 | 8 | 0 / 49 | 1734 | 45 |
| O | 100 kb | 91 / 167 / 586 | 2 / 8 | 1 / 2 | 76 | 8 | 0 / 49 | 4448 | 45 |
| O | 1000 kb | 527 / 776 / 1533 | 2 / 8 | 1 / 2 | 492 | 21 | 0 / 71 | 28314 | 45 |
| N16 | 1 kb | 26 / 355 / 645 | 1 / 6 | 1 / 3 | 26 | 0 | 0 / 240 | 289 | 236 |
| N16 | 10 kb | 27 / 123 / 657 | 1 / 5 | 1 / 3 | 27 | 0 | 0 / 2 | 485 | 236 |
| N16 | 100 kb | 82 / 181 / 639 | 1 / 5 | 1 / 3 | 82 | 0 | 0 / 0 | 2006 | 236 |
| N16 | 1000 kb | 632 / 1172 / 2941 | 1 / 7 | 1 / 4 | 631 | 0 | 0 / 296 | 18346 | 236 |

- "walk" and "dep" are the median bytes of the walk read and the departure
  read; "attach" the median and p90 of attach fetches; "rows" the median
  rows the walk read returns; "open" the header and index fetched once
  (@gmod/tabix probes 64 KB for the header, the table reader fetches the
  header's exact bytes)
- F6p, T64 and O fetch the same bytes at every size, to the kilobyte: once a
  chunk is whole blocks and the read stops at its end, every container
  fetches the chunk and nothing else. The chunk floor on MC is 28 KB (the
  median compressed chunk); the reader review's estimate of the content a
  1 kb window uses is ~4 KB, so what remains is 64 kb granularity, which
  T16 buys down to 15 KB at a cost of 1.9× at 1 Mb
- The stock @gmod/tabix on the same files: 58 KB walk read at 1 kb instead
  of 28 (`F6p-stock-client`, `T64-stock-client` in `results/mc22.jsonl`);
  on the unaligned shipped file the patch changes nothing
  (`F6-patched-client` = F6)

### pggb chrY

| candidate | window | total KB med / p90 / p99 | requests med / max | rounds med / max | walk KB med | dep KB med | attach KB med / p90 | walk rows med | open KB |
|---|---|---|---|---|---|---|---|---|---|
| F6 | 1 kb | 1375 / 6286 / 8483 | 5 / 14 | 2 / 6 | 43 | 61 | 1271 / 3370 | 1 | 81 |
| F6 | 10 kb | 629 / 6423 / 8382 | 4 / 14 | 2 / 4 | 43 | 8 | 578 / 3642 | 1 | 81 |
| F6 | 100 kb | 630 / 6378 / 8462 | 4 / 13 | 2 / 4 | 43 | 8 | 578 / 3518 | 2 | 81 |
| F6 | 1000 kb | 1253 / 7739 / 8995 | 5 / 13 | 2 / 4 | 43 | 19 | 1170 / 3370 | 3 | 81 |
| F6p | 1 kb | 284 / 1167 / 2249 | 4 / 14 | 2 / 4 | 0 | 6 | 276 / 614 | 1 | 82 |
| F6p | 10 kb | 280 / 1341 / 2536 | 4 / 14 | 2 / 4 | 0 | 5 | 276 / 605 | 1 | 82 |
| F6p | 100 kb | 284 / 1423 / 2888 | 4 / 14 | 2 / 4 | 0 | 7 | 276 / 596 | 2 | 82 |
| F6p | 1000 kb | 284 / 3078 / 4768 | 4 / 13 | 2 / 4 | 0 | 8 | 276 / 606 | 3 | 82 |
| T64 | 1 kb | 284 / 1145 / 2240 | 4 / 13 | 2 / 4 | 0 | 8 | 276 / 606 | 1 | 76 |
| T64 | 10 kb | 280 / 1251 / 2383 | 4 / 13 | 2 / 4 | 0 | 5 | 276 / 605 | 1 | 76 |
| T64 | 100 kb | 284 / 1396 / 3424 | 4 / 13 | 2 / 4 | 0 | 8 | 276 / 595 | 2 | 76 |
| T64 | 1000 kb | 284 / 3041 / 5133 | 4 / 14 | 2 / 4 | 0 | 8 | 276 / 605 | 3 | 76 |
| O | 1 kb | 315 / 1069 / 2232 | 4 / 14 | 2 / 4 | 0 | 8 | 275 / 614 | 1 | 18 |
| O | 10 kb | 283 / 1359 / 2345 | 4 / 14 | 2 / 4 | 0 | 8 | 275 / 605 | 1 | 18 |
| O | 100 kb | 283 / 1276 / 2690 | 4 / 14 | 2 / 4 | 0 | 8 | 275 / 596 | 2 | 18 |
| O | 1000 kb | 283 / 2962 / 4432 | 4 / 13 | 2 / 4 | 0 | 8 | 275 / 606 | 3 | 18 |
| N16 | 1 kb | 459 / 778 / 1806 | 2 / 12 | 2 / 5 | 15 | 0 | 451 / 630 | 4 | 371 |
| N16 | 10 kb | 459 / 745 / 1836 | 2 / 12 | 2 / 5 | 15 | 0 | 451 / 469 | 4 | 371 |
| N16 | 100 kb | 459 / 806 / 1946 | 2 / 12 | 2 / 5 | 15 | 0 | 451 / 469 | 10 | 371 |
| N16 | 1000 kb | 466 / 2108 / 2650 | 2 / 13 | 2 / 5 | 17 | 0 | 451 / 469 | 67 | 371 |

- Half of chrY's windows fall in N runs or unaligned stretches and return a
  ref row or nothing (walk 0 KB, 1 row at the median); the quantiles above
  the median carry the signal. The shipped reader's 1,375 KB median at 1 kb
  is attach fetches with a 16-chunk lookback (`ceil(maxnode / chunk)`) and a
  departure read over ±1 Mb; `reach` (50,008 bp, the longest reference node
  under a chunk) takes the departure read to 6–8 KB median and 0 of 300
  windows over the 2 MB budget at 1 kb (F6: 43 of 300)
- F6p, T64 and O are again equal to the kilobyte at the median (284 KB);
  what remains is attach fetches, 276 KB median and 606 KB p90, the same for
  all three: records whose own steps lie in chunks the read lacks, the
  record-design cost ADR 0009's open problems already name
- The T64 file as first built cut departure rows at the leaf, 64 kb × 8^L
  (1,552,996 rows against 1,219,127 for the same 420,163 records): nothing
  at the median, −10% at the 1 kb p90, +19% at the 1 Mb p90. The cut-size
  variants below settle the unit at 512 kb
- N16 on pggb is 459 KB median at 1 kb (stub interiors fetched one site at
  a time, 451 KB median), against 284 for T64, with a 371 KB open cost, and
  rebuilds 11 of 41 whole paths in the native review's own check

### Departure cut sizes

The same T64 rows and CSI, departure records cut three ways, departure read
bytes per window (KB median / p90 / p99; `results/pggbY-dep.jsonl`,
`results/mc22-dep.jsonl`):

| filing | pggb 1 kb | pggb 10 kb | pggb 100 kb | pggb 1 Mb | 1 Mb windows over 2 MB | pggb rows |
|---|---|---|---|---|---|---|
| 128 kb × 8^L under TBI (format 6, F6p) | 6 / 427 / 861 | 5 / 457 / 975 | 7 / 475 / 1099 | 8 / 1391 / 2121 | 12 / 300 | 1,219,127 |
| 64 kb × 8^L under CSI 16 (the leaf; T64 as first built) | 8 / 383 / 801 | 5 / 432 / 1221 | 8 / 477 / 1587 | 8 / 1650 / 2593 | 15 / 300 | 1,552,996 |
| 128 kb × 8^L under CSI 16 (misaligned to the leaf) | 76 / 695 / 1514 | 15 / 695 / 1514 | 16 / 755 / 2007 | 76 / 1849 / 2391 | 17 / 300 | 1,219,127 |
| **512 kb × 8^L under CSI 16 (decided)** | **8 / 306 / 729** | **6 / 369 / 995** | **8 / 397 / 1351** | **8 / 974 / 1791** | **0 / 300** | **798,581** |

| filing | MC 1 kb | MC 10 kb | MC 100 kb | MC 1 Mb | MC rows |
|---|---|---|---|---|---|
| 128 kb × 8^L under TBI (F6p) | 8 / 23 / 61 | 8 / 28 / 61 | 8 / 23 / 61 | 16 / 50 / 67 | 31,239 |
| 64 kb × 8^L under CSI 16 | 8 / 21 / 75 | 8 / 19 / 75 | 8 / 20 / 37 | 23 / 32 / 93 | 34,394 |
| **512 kb × 8^L under CSI 16 (decided)** | **8 / 21 / 42** | **11 / 20 / 42** | **11 / 21 / 42** | **23 / 32 / 50** | **26,903** |

- A block the size of the leaf fragments long records into the most rows
  and a window inside a jump reads a row per 64 kb; a block misaligned to
  the leaf (128 kb under a 64 kb leaf) lands in the 512 kb bin and every
  window in that bin reads it. The 512 kb unit is the index's second level,
  as 128 kb was TBI's: fewest rows, the lowest tail on pggb at every size
  (1 Mb p90 974 KB against 1,391 for the shipped filing, none of 300 1 Mb
  windows over the 2 MB budget against 12), and on MC the same median
  (+3 KB at 10 and 100 kb, one more block) with the lowest p99
- Records shorter than 512 kb therefore share a bin with their 512 kb
  neighbourhood; the measured over-read is the +3 KB above

### htslib (`tabix` under strace, MC chr22, median KB walk + departure)

| file, query | 1 kb | 10 kb | 100 kb | 1 Mb |
|---|---|---|---|---|
| F6, chunk before (as graph-walks 5) | 79 / 133 / 402 (walk 70) | 87 / 138 / 233 (walk 76) | 130 / 179 / 331 (walk 118) | 566 / 733 / 1449 (walk 539) |
| F6p, chunk of start − reach | 44 / 69 / 160 (walk 34) | 47 / 81 / 134 (walk 36) | 96 / 130 / 244 (walk 81) | 530 / 716 / 1357 (walk 507) |
| T64, `seq:start − reach-end` | 46 / 68 / 181 (walk 34) | 48 / 81 / 133 (walk 36) | 95 / 131 / 302 (walk 81) | 530 / 715 / 1384 (walk 507) |

- htslib reads the same chunk the browser client does (34 KB median walk
  read at 1 kb: the chunk's blocks, a 4 KB header probe and the next block's
  header), so T64 and F6p cost a stock `tabix` the same; on the shipped file
  htslib's early stop already saves it the client's over-read (70 against
  84 KB)

### Correctness (graph-walks' own `cut`, shipped read against the candidate)

`harness/cutcheck.mjs`, 60 windows at 1 kb, 60 at 10 kb, 30 at 100 kb and
4 at 1 Mb from the same seeded set, graph-walks 5.0.2's `cut` with budgets
lifted and the attach cap at 64, the shipped file read as graph-walks 5
reads it against the candidate's file read by the candidate's procedure
(for an attach fetch, `[cs − reach, cs + 1)`, a superset of the exact
`[base − reach, base + 1)`), comparing fragments (every step, strand and
placed position), departure records and kept nodes:

| candidate | identical cuts | differing |
|---|---|---|
| F6p | 153 of 155 (1 kb 59/60, 10 kb 60/60, 100 kb 34/35) | 2 |
| T64 | 155 of 157 (1 kb 59/60, 10 kb 60/60, 100 kb 36/37) | 2 |
| O | 155 of 157 (the same) | 2 |

- The same two windows differ for all three candidates, and in the same
  way; the 1 Mb windows were not reached (each cut there decodes 15–19 M
  steps with budgets lifted)
- The 100 kb window chr22:18,843,668 (LCR22A) is the excursion the
  cleansheet review documented: on-window kept nodes are identical (0
  differences), but four haplotypes leave the window, run through the
  previous chunk's reference (a paralog copy) and return. With the lookback
  chunk at hand the shipped reader draws that as one fragment with 370
  departures computed inside it; without it the candidates give two
  fragments and the departure record between them, which is what the
  reader gives an excursion into any other chunk. The lookback made that
  chunk's content visible by accident of adjacency, not by rule
- T16 was checked against the 64 kb file first, which compares two
  chunkings (different pieces and 3.8× the departure records), so half its
  cuts differ by bookkeeping; a check against the 16 kb build read by the
  shipped rule (`results/cutcheck-t16.jsonl`, `BASE=f6c16.bed.gz`) was
  queued and is not part of the decision, since T16 loses on bytes

- The 1 kb window chr22:18,991,862 (LCR22) is the attach bug the cleansheet review found:
  two records' leave chunks are adjacent, the two attach fetches share a
  chunk, and `decode` returns early for the second name filter, so one
  record's own steps are never attached (24 nodes, one departure's steps).
  It is reachable in the released reader whenever two such records exist;
  the narrower read reaches it more often because the lookback chunk no
  longer hides one of the two fetches
- N16 was not run through graph-walks (no reader exists); the native
  review's own check rebuilt 22 of 22 MC fragments and 60 of 60 windows,
  and on pggb chrY 11 of 41 whole paths and 49 of 60 windows: the carrier
  set cannot say which visit of a collapsed repeat departs. The fix it
  proposes (`f:k` visit tokens) is unbuilt

## Mechanisms counted and priced

Row kinds, sibling sequences, header kinds, lookback rules, occurrence
tokens and cross-row dependencies per candidate:

| | F6 / F6p | T64 (decided) | O | N16 |
|---|---|---|---|---|
| row kinds | 6 (ref, nodes, route, walk, abridged, departure) | 6, same | 6, same | 3 (R, H, V) + stub V rows, half-site V rows, D records |
| sibling sequences | 2 (`~departure`, `~cs`) | 2 | 1 in the table + a second file | 1 (`~detail`) |
| header line kinds | 5 (`#walks #reference #haplotype #long #hole`) | 5 + `reach` tag | 5 + `reach` | 4, but `#fragment` is a 1,094-line table a reader must hold |
| lookback rules | 2 (chunk before; `#long`), plus `maxnode` for departures and attach | 1 (`reach`; `#long` widens) | 1 | 1 (round to cells) |
| occurrence tokens | 2 (`@k`, `:k`), pggb only | 2 | 2 | 1 proposed (`f:k`), unbuilt |
| cross-row dependencies | 7 | 7 | 7 | 6 + a traversal per fragment |
| index / container | TBI, 1 bp key, chunk-rounded query | CSI leaf = chunk, overlap query | new table format, BGZF offsets | TBI, honest |
| plain `tabix` on a window | 0 rows | the chunk (3,562 rows) | n/a (`tail | head | bgzip -d` by the table) | 30 rows, but not a path without the traversal |

The seven cross-row dependencies of the format 6 rows, each priced on 120
sampled MC chunks (walk-read rows, zlib 6; `results/encode-variants-mc22.txt`,
`results/routelen-mc22.txt`):

- walk choices index the chunk's route rows (the route dictionary): without
  it, departures written inline per walk row, 4.58×; as plain GAF step
  lists per piece, 24.5×. Keeps its place
- route tokens chained across route rows: deltas restarting on each row
  cost 1.10×; absolute GAF handles (`>12345`) 2.11×. The chain is worth 10%
  and one line of reader code; kept, since the row is not the unit of
  meaning anyway (a route row needs the chunk's R and nodes to mean
  anything)
- the `nodes` row gives interior lengths: lengths on each route row instead
  cost 1.146× on chunk rows and would shrink the detail tier by 33%
  (40.4 → 26.9 MB on chr22). Window bytes win; kept
- walk rows decode against R from the `ref` rows: that is what makes a walk
  row 20 bytes instead of a 10 KB step list (the 24.5× above)
- pieces joined across chunks by `path, fragStart, piece`: the chunking
  itself; 64 kb against 1 Mb chunks is 56 KB against 1,084 KB for a 1 kb
  window (cleansheet's sweep), and against 16 kb it is 1.9× cheaper at 1 Mb
  here
- departure rows deduped across cut blocks: ADR 0009's filing took chrY's
  p95 departure rows from 18,034 to 265
- abridged rows naming a detail record: ADR 0004's bound on a window
  (chunks of 4.5 MB otherwise)

### The detail tier

- Is a second tier needed? Yes: without abridging chr22's largest 64 kb
  chunk is 4.5 MB and the p99 100 kb window 7.9 MB, over any browser budget
  (cleansheet's no-abridge sweep); the tier is what bounds a window
- Does its duplication matter? Measured (`scripts/detail_dup.py`): of the
  2,468 records' 858,580 routes, 50.8% also appear in the chunk's own route
  rows and 28.0% in an earlier record of the chunk, but those duplicate
  route rows compress to 3.5 MB of the tier's 40.4 MB. The tier's bulk is
  its `nodes` rows, 23.2 MB: a satellite path's record lists each of its
  ~100 k tiny nodes once in `nodes` and again in its route interiors. So
  the cleansheet claim that 27 of 59 MB is routes repeated per path is not
  what the bytes show
- Duplication or cross-reference? Duplication: a record that decodes alone
  against its chunk's R is one fetch and no new mechanism; sharing routes
  by position would add a second dependent fetch per expanded path to save
  3.5 MB of file that no window reads. The 23 MB of `nodes` rows could be
  halved by the route-length change above, at +15% on every window; not
  taken. File size is the only cost here, and it is hosting, not windows

## Why each other candidate loses

- **F6, format 6 as shipped (98 KB median at 1 kb on MC, 1,375 KB on pggb chrY):**
  the 1 bp key makes every reader round to chunk starts and read the chunk
  before (two chunks for a 1 kb window), no chunk starts on a BGZF block so
  the client fetches its neighbours' blocks, and `maxnode` sizes the
  departure read and attach lookback (±1 Mb and 16 chunks on pggb: 43 of 300
  1 kb windows over the 2 MB departure budget). A plain `tabix` query on a
  window returns 0 rows. Loses on bytes (2.6× T64 at 1 kb on MC, 4.8× on
  pggb) and on honesty
- **F6p, format 6 patched (37 KB at 1 kb; the same bytes as T64 at every
  size and quantile):** every byte T64 saves, F6p saves too, which is the
  proof that the 1 bp key was never where the bytes went. It loses because
  it keeps the lie at equal cost: rows say `cs cs+1`, the reader still
  rounds queries to chunk starts, `tabix file region` still returns 0 rows,
  and the index is twice the size (39 KB against 20 KB; 1.33 MB genome-wide
  against an estimated 0.6 MB). Nothing measurable is bought by the key once
  the leaf bin is the chunk
- **T16, honest 16 kb chunks under TBI (32 KB at 1 kb):** 6 KB cheaper than
  T64 at 1 kb and 1 KB dearer at 10 kb, then 37% dearer at 100 kb (126 against
  92 KB) and 90% dearer at 1 Mb (1,004 against 530 KB), with a 20% larger
  file (71.5 MB) and 3.8× the departure records (dep 15 KB against 8 KB per
  window). The reader review's lean heads would recover some file size but
  not the 1 Mb cost, which is heads × tiles. A view that pans at 100 kb to
  1 Mb pays for the 1 kb win many times over
- **O, offset table (36 KB at 1 kb; identical chunks, identical bytes):**
  the chunk table is what a CSI with `min_shift = log2(chunk)` already is,
  in a format every Tabix client reads. O's table is 39 KB gzipped against
  the CSI's 20 KB; its open is cheaper (45 KB against 87) only because
  @gmod/tabix probes 64 KB for the header, a client detail. It costs a new
  index format with no tool behind it, a second file and index for the
  departures (which are intervals and want Tabix anyway), a custom reader
  beside @gmod/tabix, and `tabix` no longer runs on the walks. "More general
  and not coordinate based" buys nothing here: chunks are keyed by reference
  position whatever the index is called. Loses on tooling at zero gain
- **N16, interval-native site rows (26 KB median at 1 kb on MC, 459 KB on
  pggb):** the only candidate under T64 at the MC median (−12 KB), and it
  loses everywhere else: p90 355 KB and up to 3 round trips at 1 kb (stub
  interiors fetched one site at a time), 632 / 1,172 / 2,941 KB at 1 Mb
  against 530 / 779 / 1,564 (p99 1.9×), 459 KB median on pggb against 284,
  an open cost of 236 KB on chr22 and 371 KB on chrY (a 159 to 306 KB index
  from one leaf bin per detail allele, and a `#fragment` table of 1,094
  lines a reader must hold), and a path it cannot yet rebuild on pggb (11
  of 41 whole paths; the `f:k` visit index that would fix it is unbuilt).
  It is not simpler: three row kinds become five forms (R, H, V, stub V,
  half-site V, plus D records), carriers are index deltas or hex bitmaps,
  and a reader rebuilds each fragment by a traversal with a visited-state
  rule in place of decoding a row. A new writer (external sort by site) and
  a reader written from scratch; the five consumer ports reopen

## Consequences

- **Format 7, not a format 6 patch.** The row interval, the index type, the
  departure cut sizes and the detail record positions change what a reader
  does. The rows' columns and decoding rules do not change
- **gfa-to-tabix:** `--walks` writes `seq cs cs+chunk` (clipped to the
  sequence's end); the CSI indexer at `min_shift = log2(chunk)`, depth 5,
  for every file (it already builds one for long contigs); `--chunk` refuses
  a size that is not a power of two; the BGZF writer flushes its block at
  every chunk end and detail record end (`parallel_bgzf.rs` cuts blocks at
  a fixed size today); departure records cut at `8 × chunk × 8^L`; detail
  records at `detail × chunk`; the header tag `reach:i:`, checked at build
  time; `format:i:7`. The spec's rationale sentence for `cs cs+1` goes, with
  the measured reason for the leaf bin in its place
- **graph-walks 6:** opens `.csi`; `walkQueryStart` becomes
  `max(0, drawn.start − reach)` widened to an overlapping `#long` pass;
  the departure extent and attach fetches use `reach`, never `maxnode`;
  attach fetches read `[base − reach, base + 1)`; detail records at
  `detail × chunk`; refuses format 6. `cut`'s return shape (fragments,
  departures, tables) is unchanged, since `walkChunk` and `walkRows` decode
  the same rows: the five consumers (graph plugin 9, BandageJS, ggbandage,
  the tube map, jb2hubs) re-roll with a version-pin bump, not a port.
  Before the release, fix the attach-decode bug (two records with adjacent
  leave chunks) by merging attach fetches that share a chunk into one read
  with the union of names, since the narrower read exposes it more often
- **@gmod/tabix:** the one-line `Chunk.endPosition` fix, as an upstream PR;
  until it lands, graph-walks can apply the same clamp to `blocksForRange`'s
  result. Without it the stock client pays 58 instead of 28 KB per small
  window
- **JBrowse plugin:** `RgfaTabixAdapter` looks for `.csi` beside `walksUri`
- **Hosted data:** rebuild the genome-wide GRCh38 and CHM13 files on ada
  (about 70 minutes each) and the demo sets; the cutover that is on hold
  proceeds on the format 7 files. The genome-wide index shrinks from
  1.33 MB to roughly half; windows read 2.6× fewer bytes on MC at 1 kb
- **Release gates stay as stated:** no library release until every consumer
  is green on exact versions; full CI locally before a tag;
  `pnpm release-check WALKS=<file>` on the hosted format 7 file; one-pass
  swap
- **What this does not fix, and the ADR should say so:** pggb's tail is
  departure records and attach fetches (276 KB median of a 284 KB window,
  p90 1.1 MB) from collapsed-repeat hops; that is placement and record
  design (ADR 0009's open problems), and every candidate pays it. On MC the
  p90 is attach fetches too (102 KB at 1 kb). The next lever is a record
  that carries small own sequence, which the reader review priced at ~0.1 MB
  of file; it is a record question, not a container one

## Broken along the way (for the issues log)

- **graph-walks sizes the departure read and attach lookback from
  `maxnode`** (1 Mb on pggb chrY): a 1 kb window reads 1.4 MB median, 6.3 MB
  p90, 43 of 300 windows over the departure budget. Fix: `reach` in the
  header and `#long`-aware reads. Guard: the harness's pggb run
- **@gmod/tabix over-reads one BGZF block past a chunk whose last row ends a
  block**, under TBI and CSI alike (`clampChunkEnds` has no boundary at
  `maxv` when `dataPosition` is 0): 58 against 28 KB at 1 kb on an aligned
  file. Fix: `endPosition = maxv.blockPosition` when `maxv.dataPosition === 0`
  (history's patch, confirmed here as `F6p-stock-client` against `F6p`)
- **No chunk starts on a BGZF block boundary** in 3.0.0's output, so a chunk
  read pays its neighbours' blocks and the client fix above cannot act:
  `F6-patched-client` equals `F6`. Fix: flush at chunk ends in the writer
- **Attach fetches that share a chunk drop one record's own steps**
  (cleansheet's finding, reproduced): chr22:18,991,862, 1 of 154 windows,
  24 nodes and one departure's steps missing. Fix: merge attach fetches by
  chunk with the union of names, or decode again for names not yet decoded.
  Guard: a test with two records whose leave chunks are adjacent
- **Detail records at `detail × 16384` would share CSI leaf bins** under
  `min_shift 16` (four per bin), so a query for one record would read four.
  Fix: `detail × chunk`
- **`tabix -C -m 16` writes a CSI of depth 7** (positions to 2^37); harmless,
  @gmod/tabix and htslib read it, but the writer should emit depth 5 and the
  spec should say so
- **The spec's rationale for `cs cs+1`** ("a row spanning the whole chunk
  would share a Tabix bin with the next chunk") is true only under TBI with
  @gmod/tabix's bin-wide fetch (+35% at 1 kb, history's B variant) and false
  under CSI with the chunk as leaf (T64 = F6p to the kilobyte); it was
  adopted in 3953bb1 without a measurement
- **The cleansheet review's "27 of 59 MB is detail records repeating
  routes"** misattributes the tier's bytes: the routes repeated across
  records compress to 3.5 MB on chr22 (14.1 MB of 129 on chrY); the tier's
  bulk is `nodes` rows (23.2 MB on chr22, 31.7 on chrY) restating each
  interior node beside its routes. Lengths on route rows would cut the tier
  33% at +15% on every window's chunk rows; not taken
- **Block alignment in the prototype costs +0.6% file size** (one short
  block per chunk and per detail record) against history's −0.09%; the
  writer's own flush should land near zero. Not a bug, a number to check at
  the port
- **`tabix` folds small bins into their parent** (`compress_binning`: a
  bin whose chunks span under 64 KB of compressed file) and merges the
  parent's adjacent chunks, so a query at a higher level fetches every
  folded leaf group under it: 296 against 118 KB for one 512 kb departure
  block on chrY. The writer's CSI (noodles) does not fold. Guard: the
  release check should compare the writer's index with a `tabix -C` one
  on a window, and the spec should say what re-indexing costs
- **@gmod/tabix merges chunks across a gap of up to 65,000 bytes** into
  one request, fetching the gap: on pggb departure reads that is about
  40 KB per 1 kb window (T64b 94 against S's 55 KB for the same rows). A
  client constant, worth exposing to the walks adapter
- **`#long` listed only passes over nodes longer than a chunk**, which put
  `reach` at 50,008 bp on pggb chrY and a second tile into 76% of windows
  and every attach fetch. Fix: `--long <bp>`, default 4,096, with `reach`
  written from it. Guard: `results/x-pggbYeu-r4k.jsonl`
- **A reader of block-filed departure rows must filter by the record's
  extent columns**: fed the rows unfiltered, graph-walks drew every record
  of the overlapping blocks (29 of 141 cuts identical, fragments identical
  in all). The spec must state the filter with the filing
- **A table of true extents must be addressed by extent everywhere**: a
  tile's extent begins at its first placed base, which can lie after its
  nominal start, and an attach read by chunk start missed the leave piece
  in 8 of 65 windows until addressed by extent. For S, or for any reader
  of a true-extent index
- **graph-walks refuses every all-haplotype 1 Mb window at default budgets**
  (step budget 4 M against 15–19 M steps); the 1 Mb rows here were measured
  with budgets lifted and are the bytes a lifted budget would pay

## Files

- `harness/`: `server.mjs`, `windows.mjs`, `measure.mjs`, `summarize.py`,
  `cutcheck.mjs`, `htslib_bytes.py`, `candidates-*.json`
- `scripts/`: `build_all.sh`, `refile.py`, `build_offset.py`,
  `encode_variants.py`, `routelen.py`, `detail_dup.py`, `decode6.py` (the
  native review's independent decoder)
- `results/`: `mc22.jsonl`, `pggbY.jsonl` (one line per window and
  candidate), `cutcheck-*.jsonl`, `htslib-*.jsonl`, `encode-variants-mc22.txt`,
  `routelen-mc22.txt`, `detail-dup-*.txt`, `build.log`
- `data/`: the candidate files (links to the shipped and native files)
- Cross-examination: `harness/depprobe.mjs`, `binprobe.mjs`, `binscan.mjs`,
  `cutdebug.mjs`, `xtable.py`; `scripts/s_departures.py`, `build_t64b.py`,
  `csi_write.py`; `data/*/s.walks.gz` and `s.walks.idx` (arbA's S files),
  `tn.bed.gz` (arbA's Tn), `t64b.bed.gz` with `t64b.exact.csi` and
  `t64b.bed.gz.csi.htslib`, `pggbY/long4k.txt`; `results/x-*.jsonl`,
  `xtable-*.md`, `cutcheck-s.jsonl`, `cutcheck-t64b.jsonl`,
  `cutcheck-t64b-unfiltered.jsonl`, `depprobe-t64b.txt`,
  `windows-pggbYeu.jsonl`

## Cross-examination

The other arbiter (arbA) decided for S: one BGZF file and a `.fai`-style
table `seq start end kind name offset length`, each 64 kb tile listed at
its true extent, departure records filed over their end nodes and listed in
every block of a tile × 8^L pyramid, no `#long`, lookback, reach,
`~departure` or `~cs`. Its numbers: MC 1 kb 28 KB against T's 37; pggb chrY
1 kb 69 KB in one round trip against T's 226 (187 with S's departure
filing) in three, the gap unexplained. This section measures S in my
harness, adversarially, and restates the decision.

### What was measured

- arbA's own S files (`s.walks.gz`, `s.walks.idx`, from ada
  `~/work/arb-arbA/out/`) and its Tn file (T with S's departure filing),
  read by an S reader added to `harness/measure.mjs` (`kind: table`: tile
  and departures entries overlapping the drawn extent, touching byte ranges
  merged, lines deduped, records kept when their extent overlaps the drawn
  stretch, attach fetches by the tile whose extent holds the leave base, as
  arbA's reader does). Every candidate runs with attach fetches on and off:
  arbA's harness has them off for every candidate (`ATTACH=1` enables
  them), so its 69 KB is a walk-plus-departure read, not a window
- Windows: my 300-per-size sets on MC chr22 and on pggb chrY 2.8–56.8 Mb,
  plus a third set over arbA's range, chrY 2.78–26.67 Mb (`windows-pggbYeu`,
  same seed), since half of my chrY windows fall in the Yq12 N run and
  return nothing, which halves every median
- A third design, **T64b**: T64 with S's two departure ideas carried into
  the Tabix file. Records are filed over their end nodes (no reach on the
  departure query), and every row of a record carries the extent of the
  pyramid block it is listed in (64 kb × 8^L, S's levels), so a block's
  rows are contiguous in start order, each block ends a BGZF block, and the
  index's bin for the block is one exact chunk. The record's own extent
  rides as two trailing columns a reader may ignore (graph-walks' parser
  reads columns by index and takes them as tags). Built by
  `scripts/build_t64b.py` from S's own departure lines, so the records are
  identical to S's
- The departure probe `harness/depprobe.mjs`: for one window, every chunk
  @gmod/tabix fetches for the `~departure` query (bin, virtual offsets,
  bytes, rows returned, rows overlapping) against S's departures entries
  for the same drawn extent

### Why S's departure read was 2.7× cheaper than Tabix's, confirmed

pggb chrY window 19,129,406 (1 kb), the `~departure` query, the same
5,026 records every way (`harness/depprobe.mjs`, `results/depprobe-t64b.txt`):

| filing and index | fetched | chunks |
|---|---|---|
| T64 (512 kb cut, rows at clipped record extents, `tabix`'s CSI, query ± reach) | 203,062 bytes | 2 |
| Tn (S's end-node extents, `tabix`'s CSI, query over drawn) | 175,651 bytes | 2 |
| T64b, `tabix`'s CSI (rows at block extents, blocks contiguous and BGZF-aligned) | 114,190 bytes | 2 |
| T64b, an exact CSI (no bin folding, as the writer's own indexer builds) | 111,044 bytes | 2 |
| S table (3 entries: 4 Mb, 512 kb, 64 kb blocks) | 51,359 bytes | 3 |

Three mechanisms, none a property of Tabix as a format, each measured:

- **The chunk-end over-read under CSI (T64 → T64b, ~130 KB here).** The
  first T64 chunk was `180523498:48402..180572834:42550`, 49,336 bytes of
  rows, fetched as 114,872: `Chunk.endPosition` defaults to
  `maxv.blockPosition + 65536`, and under CSI `clampChunkEnds` has only
  other bins' chunk boundaries to clamp against (TBI has its linear index),
  so when a bin's rows end mid-block the client reads a whole 64 KB past
  them. The tile fix (`dataPosition === 0`) cannot act because departure
  rows are not block-aligned per bin. Filing a record's rows at the extent
  of the pyramid block they are listed in makes a block's rows contiguous
  (they sort together), lets the writer end a BGZF block there, and makes
  every departure chunk end at `:0`, where the patched client stops
- **htslib's bin folding (T64b, `tabix`'s index).** `tabix` folds a bin
  whose chunks span under 64 KB of compressed file into its parent bin
  (`compress_binning`) and then merges the parent's now-adjacent chunks:
  on chrY the six small leaf groups under the 512 kb block at 21,495,808
  vanished from the index and the parent's one chunk grew to 296 KB. A
  reader at that level then fetches every folded leaf group. The writer's
  own indexer (noodles, what gfa-to-tabix uses) has no folding; a CSI
  written without it (`scripts/csi_write.py`, validated row for row
  against `tabix` on both indexes) keeps the 512 kb bin's chunk at its
  118 KB. A user who re-indexes a format 7 file with `tabix` gets the
  folded index: still correct, somewhat more bytes
- **@gmod/tabix's gap merging (T64b exact → S, the rest).** `optimizeChunks`
  joins two chunks when the gap between them is under 65,000 bytes, one
  request in place of two: on window 21,677,930 the 512 kb bin (118 KB)
  and the window's 64 kb bin (20 KB) are 52 KB apart in the file (two leaf
  groups of other windows), so the client fetches 197 KB in one request
  where S's reader, which merges only touching entries, fetches 140 KB in
  three. That is a client's trade of bytes for round trips, tunable in one
  constant, and the same knob JBrowse already turns for BAM and VCF
- S's trailing-extent columns on T64b rows (so a reader can keep only the
  records touching its window, as S's reader does on `start end`) cost 7%
  of a block (124 against 116 KB for the 12,533-row block); graph-walks
  does not need them, since its cut works from `leavePos` and `rejoinPos`

### S's weak points, measured

- **Duplicated departure lines.** S lists a record once per pyramid block
  it overlaps: 54,050 lines for 24,648 records on MC (2.2×, 0.87 MB) and
  1,558,946 lines for 425,040 records on pggb chrY (3.7×, 14.5 MB), deduped
  by the reader on the whole line. Format 6's cut rows do the same thing
  (31,239 and 1,219,127 rows, deduped on the columns after the block), so
  this is not a new cost, and T64b carries the identical 54,050 lines. The
  rule is the same in all three; the ADR should state it once
- **The table at open.** S's gzipped table is 56.8 KB on chr22 (3,838
  lines: 776 tiles, 593 departure blocks, 2,468 detail records named by
  path) against the CSI's 19 KB, and 23.8 KB against 9 KB on chrY: about
  3× a CSI, because every detail record is a table line with a path name
  and every pyramid block is a line. Genome-wide both scale with covered
  sequence, roughly 1.5 MB for the CSI and 3–4 MB for the table at chr22's
  densities (arbA estimates 1.25 MB with numeric detail names). Neither is
  prohibitive; a browser reads it once. @gmod/tabix's 64 KB header probe is
  the larger part of T64's open cost (87 KB against S's 58), and it is a
  client habit, not the format's
- **A custom index with no tools behind it.** `tabix`, htslib, pysam,
  noodles, the repo's audit scripts and `walks-truth.py` all stop at S. The
  extraction one-liner (`tail -c +offset+1 | head -c length | gzip -dc`)
  works, as it does on any block-aligned BGZF, including T64b's blocks
- **Rows that say nothing on their own.** S drops the key columns, so a
  tile row is `walk HG002#1#chr22 13696762 13696762 0 5607 …` with no
  sequence and no position: `zcat | grep HG002` finds the row and cannot
  say which chromosome or tile it came from without the table and the byte
  offset. T64's row is `GRCh38#0#chr22 15138816 15204352 walk HG002#1#chr22
  …`. Under the lens this review was asked to apply, that is the one
  property a line must have
- **Tile extents.** Checked on both files: on MC no tile's extent exceeds
  its 64 kb by more than 851 bp (the straddling node), and on chrY the 36
  tiles whose extents reach 934 kb are the `#long` N-run passes, so there
  is no inflation from paralog interiors to attack. But the extent starts
  at the first placed base, so a tile's nominal start can lie outside its
  own extent (tile 18,087,936 on chr22 begins at 18,087,958): a reader that
  keeps chunk arithmetic (graph-walks' `floor(base / chunk)` for attach
  fetches, `decoded.has(cs)`) misses the tile. My first S cut check failed
  8 of 65 windows exactly that way, until the attach read was addressed by
  extent. S's reader must address everything through the table; that is a
  port of `WalkReader`'s source layer, which arbA's Consequences also say
- **JBrowse.** The plugin loses `TabixIndexedFile` and `bytesForRegions`
  for walks and gains a table reader; the departure and detail siblings go.
  A reader exists only as arbA's 60-line harness code
- **Failure modes.** Long nodes: a tile's extent covers the pass, as `#long`
  did, so every window inside a 1 Mb N run fetches that tile (the same
  bytes as today). Repeats and inversions: the rows are format 6's, so
  nothing changes. Records with a very long end node (a 50 kb node on
  pggb): listed in every block over the node, as the reach band did

### Table

| MC chr22: candidate | window | with attach fetches, KB med / p90 / p99 | walk + departure reads only | requests med / max | round trips med / max |
|---|---|---|---|---|---|
| T64 | 1 kb | 38 / 175 / 551 | 37 / 62 / 177 | 2 / 8 | 1 / 2 |
| T64 | 10 kb | 40 / 128 / 643 | 39 / 80 / 262 | 2 / 8 | 1 / 2 |
| T64 | 100 kb | 92 / 161 / 579 | 86 / 123 / 221 | 2 / 8 | 1 / 2 |
| T64 | 1000 kb | 530 / 779 / 1564 | 509 / 692 / 1407 | 2 / 8 | 1 / 2 |
| Tn | 1 kb | 36 / 166 / 542 | 36 / 62 / 177 | 2 / 8 | 1 / 2 |
| Tn | 10 kb | 39 / 129 / 629 | 38 / 80 / 260 | 2 / 8 | 1 / 2 |
| Tn | 100 kb | 89 / 162 / 560 | 85 / 123 / 216 | 2 / 8 | 1 / 2 |
| Tn | 1000 kb | 517 / 768 / 1519 | 500 / 686 / 1367 | 2 / 8 | 1 / 2 |
| S | 1 kb | 29 / 143 / 466 | 28 / 45 / 128 | 1 / 8 | 1 / 2 |
| S | 10 kb | 30 / 86 / 541 | 29 / 66 / 197 | 1 / 7 | 1 / 2 |
| S | 100 kb | 81 / 146 / 541 | 75 / 111 / 182 | 1 / 8 | 1 / 2 |
| S | 1000 kb | 500 / 732 / 1489 | 483 / 652 / 1332 | 1 / 8 | 1 / 2 |
| T64b | 1 kb | 31 / 171 / 553 | 30 / 53 / 179 | 2 / 8 | 1 / 2 |
| T64b | 10 kb | 33 / 127 / 645 | 32 / 74 / 264 | 2 / 8 | 1 / 2 |
| T64b | 100 kb | 87 / 160 / 577 | 82 / 120 / 224 | 2 / 8 | 1 / 2 |
| T64b | 1000 kb | 533 / 796 / 1578 | 514 / 703 / 1416 | 2 / 8 | 1 / 2 |
| T64b-exact | 1 kb | 31 / 157 / 536 | 30 / 52 / 169 | 2 / 8 | 1 / 2 |
| T64b-exact | 10 kb | 32 / 97 / 574 | 32 / 73 / 206 | 2 / 8 | 1 / 3 |
| T64b-exact | 100 kb | 86 / 156 / 573 | 81 / 118 / 210 | 2 / 8 | 1 / 3 |
| T64b-exact | 1000 kb | 533 / 780 / 1576 | 514 / 694 / 1408 | 2 / 8 | 1 / 3 |

| pggb chrY 2.78–26.67 Mb: candidate | window | with attach fetches, KB med / p90 / p99 | walk + departure reads only | requests med / max | round trips med / max |
|---|---|---|---|---|---|
| T64 | 1 kb | 701 / 1983 / 2403 | 198 / 627 / 1906 | 11 / 13 | 3 / 4 |
| T64 | 10 kb | 705 / 1938 / 2461 | 202 / 648 / 1965 | 11 / 13 | 3 / 4 |
| T64 | 100 kb | 791 / 2111 / 3772 | 296 / 871 / 3276 | 11 / 13 | 3 / 4 |
| T64 | 1000 kb | 1936 / 3825 / 6336 | 942 / 3114 / 5839 | 11 / 14 | 3 / 4 |
| T64-dep512k | 1 kb | 755 / 1996 / 2837 | 241 / 542 / 1939 | 10 / 13 | 2 / 4 |
| T64-dep512k | 10 kb | 750 / 1969 / 2625 | 241 / 567 / 2129 | 10 / 12 | 2 / 3 |
| T64-dep512k | 100 kb | 794 / 2105 / 4473 | 263 / 760 / 3417 | 11 / 13 | 3 / 4 |
| T64-dep512k | 1000 kb | 1781 / 3821 / 4915 | 769 / 2855 / 4418 | 11 / 12 | 3 / 3 |
| Tn | 1 kb | 674 / 1907 / 2163 | 180 / 439 / 1616 | 10 / 13 | 3 / 4 |
| Tn | 10 kb | 684 / 1885 / 2115 | 185 / 473 / 1414 | 10 / 13 | 3 / 4 |
| Tn | 100 kb | 734 / 1930 / 3470 | 254 / 661 / 2984 | 11 / 13 | 3 / 4 |
| Tn | 1000 kb | 1798 / 3535 / 6170 | 889 / 3003 / 5683 | 11 / 14 | 3 / 4 |
| S | 1 kb | 384 / 1237 / 1341 | 68 / 221 / 1056 | 10 / 12 | 2 / 2 |
| S | 10 kb | 392 / 1233 / 1354 | 67 / 251 / 682 | 10 / 12 | 2 / 2 |
| S | 100 kb | 485 / 1281 / 2762 | 95 / 468 / 2532 | 10 / 12 | 2 / 2 |
| S | 1000 kb | 1328 / 3118 / 5366 | 685 / 2674 / 5137 | 10 / 12 | 2 / 2 |
| T64b-exact | 1 kb | 615 / 1839 / 2083 | 117 / 261 / 1587 | 11 / 12 | 3 / 3 |
| T64b-exact | 10 kb | 621 / 913 / 2003 | 119 / 281 / 1301 | 11 / 12 | 3 / 3 |
| T64b-exact | 100 kb | 640 / 1858 / 3437 | 135 / 541 / 2941 | 11 / 12 | 3 / 3 |
| T64b-exact | 1000 kb | 1743 / 3675 / 6349 | 745 / 3178 / 5853 | 11 / 12 | 3 / 3 |

| pggb chrY 2.8–56.8 Mb: candidate | window | with attach fetches, KB med / p90 / p99 | walk + departure reads only | requests med / max | round trips med / max |
|---|---|---|---|---|---|
| T64 | 1 kb | 284 / 1145 / 2240 | 8 / 465 / 885 | 4 / 13 | 2 / 4 |
| T64 | 10 kb | 280 / 1251 / 2383 | 8 / 491 / 1565 | 4 / 13 | 2 / 4 |
| T64 | 100 kb | 284 / 1396 / 3424 | 8 / 523 / 2927 | 4 / 13 | 2 / 4 |
| T64 | 1000 kb | 284 / 3041 / 5133 | 8 / 2427 / 4636 | 4 / 14 | 2 / 4 |
| Tn | 1 kb | 275 / 954 / 2094 | 8 / 371 / 778 | 4 / 13 | 2 / 4 |
| Tn | 10 kb | 275 / 1120 / 2092 | 8 / 388 / 1002 | 4 / 13 | 2 / 4 |
| Tn | 100 kb | 275 / 1203 / 2770 | 8 / 425 / 2284 | 4 / 13 | 2 / 4 |
| Tn | 1000 kb | 276 / 2765 / 4424 | 8 / 2226 / 3938 | 4 / 14 | 2 / 4 |
| S | 1 kb | 261 / 589 / 1308 | 2 / 163 / 628 | 4 / 12 | 2 / 2 |
| S | 10 kb | 261 / 631 / 1309 | 2 / 169 / 788 | 4 / 12 | 2 / 2 |
| S | 100 kb | 261 / 735 / 1861 | 2 / 260 / 1631 | 4 / 12 | 2 / 2 |
| S | 1000 kb | 264 / 2319 / 3989 | 6 / 2000 / 3759 | 4 / 12 | 2 / 2 |
| T64b-exact | 1 kb | 278 / 759 / 1996 | 2 / 203 / 645 | 4 / 12 | 2 / 3 |
| T64b-exact | 10 kb | 278 / 786 / 1944 | 2 / 200 / 855 | 4 / 12 | 2 / 3 |
| T64b-exact | 100 kb | 278 / 954 / 2725 | 2 / 313 / 2229 | 4 / 12 | 2 / 3 |
| T64b-exact | 1000 kb | 282 / 2658 / 4583 | 6 / 2219 / 4086 | 4 / 12 | 2 / 3 |

- "With attach fetches" is what graph-walks' `cut` pays for a window
  (records with own steps the read lacks, fetched by the leave piece's
  tile, cap 8); "walk + departure reads only" is what arbA's harness
  measured (attach off for every candidate). The two pggb sets: arbA's
  range, and the whole chromosome, where half the windows lie in N runs
  and return nothing. T64b-exact is T64b under the writer-style CSI; the
  T64b rows measured with `tabix`'s folded index are in `results/x-*.jsonl`
  (MC: 31 / 171 / 553 against 31 / 157 / 536 at 1 kb)
- MC: S is 2 KB under T64b at the 1 kb median (28 against 30 KB, walk and
  departure reads), 5 KB at 100 kb and 31 KB at 1 Mb: 1 KB per tile of
  dropped key columns (S's tiles total 17.9 MB against 18.9 MB for the same
  rows without key columns under my writer, so part of it is arbA's
  deflate), the tile before the window in 3 of 300 windows that T64b reads
  by `reach` and S's extents spare, and one request where T64b makes two
- pggb, arbA's range, 1 kb, reads only: S 68 KB, T64b 117, T64 198, the
  shipped filing (F6p) 292 in arbA's table. Of T64b's 49 KB over S, about
  17 KB is the second tile `reach` = 50,008 bp drags in for 76% of windows,
  and about 32 KB is @gmod/tabix's gap merging in the departure read plus
  the 7% of trailing extent columns. With attach fetches the same windows
  cost S 384 KB and T64b 615, the difference again the `reach` tile, now
  once per attach fetch. The `#long` threshold variant below removes it
- Round trips: S 1 (reads) and 2 (with attach); every Tabix candidate 1–2
  and up to 3 with attach, the extra one being @gmod/tabix's read-ahead
  (chunk 1 alone, then 2, then 4) on a departure read of several chunks

| pggb chrY 2.78–26.67 Mb, reach 4,096 with #long over nodes > 4 kb: candidate | window | with attach fetches, KB med / p90 / p99 | walk + departure reads only | requests med / max | round trips med / max |
|---|---|---|---|---|---|
| T64b-exact-reach4k | 1 kb | 444 / 1311 / 1479 | 113 / 239 / 1213 | 11 / 12 | 3 / 3 |
| T64b-exact-reach4k | 10 kb | 456 / 773 / 1475 | 116 / 271 / 742 | 11 / 12 | 3 / 3 |
| T64b-exact-reach4k | 100 kb | 539 / 1324 / 3109 | 131 / 510 / 2842 | 11 / 12 | 3 / 3 |
| T64b-exact-reach4k | 1000 kb | 1468 / 3261 / 6114 | 743 / 2994 / 5847 | 11 / 12 | 3 / 3 |
| S | 1 kb | 384 / 1237 / 1341 | 68 / 221 / 1056 | 10 / 12 | 2 / 2 |
| S | 10 kb | 392 / 1233 / 1354 | 67 / 251 / 682 | 10 / 12 | 2 / 2 |
| S | 100 kb | 485 / 1281 / 2762 | 95 / 468 / 2532 | 10 / 12 | 2 / 2 |
| S | 1000 kb | 1328 / 3118 / 5366 | 685 / 2674 / 5137 | 10 / 12 | 2 / 2 |

- `reach` on pggb chrY is 50,008 bp because `#long` lists only passes over
  nodes longer than a chunk. Listing every pass over a node longer than
  4,096 bp instead (52 lines on chrY) makes `reach` 4,096: the walk read
  drops from 12 to 7 KB median and from two tiles to one in 280 of 300
  windows (S's extents: 291 of 300), and each attach fetch reads one tile.
  What remains over S at 1 kb (113 against 68 KB reads, 444 against 384
  with attach fetches) is the departure read, 94 against about 55 KB:
  @gmod/tabix's gap merging and the 7% extent columns. On MC `reach` is
  already 1,024 and nothing changes

### Correctness

`harness/cutcheck.mjs` as before (graph-walks 5.0.2's `cut`, budgets
lifted, attach cap 64, shipped file and rule against the candidate's file
and procedure), with an S source that addresses tiles and attach fetches by
extent and keeps the departure lines overlapping the reader's extent, and a
T64b source that keeps the departure rows whose trailing extent overlaps
the reader's extent (without that filter graph-walks drew every record of
the overlapping blocks: 29 of 141 identical, the fragments identical in
all, so the filter is part of the format, not an option):

| candidate | identical cuts | differing, and why |
|---|---|---|
| S (arbA's file) | 138 of 142 (1 kb 59/60, 10 kb 58/60, 100 kb 21/22) | chr22:18,991,862 the attach-decode bug; 44,683,486, 45,707,478 and 27,329,723 one node or one record's own steps: records at the edge of the extent that S's end-node filing returns and the shipped ±`maxnode` read does not, or the reverse |
| T64b (exact index) | 176 of 180 (1 kb 59/60, 10 kb 59/60, 100 kb 54/56, 1 Mb 4/4) | the same 18,991,862, 44,683,486 and 45,707,478, plus 18,843,668 (the LCR22A excursion the lookback chunk drew by accident, as for T64) |

- Fragments (every step, strand and placed position of every haplotype)
  were identical in every window for both. S's first run failed 8 of 65
  windows because my attach reads addressed tiles by chunk start; a tile's
  extent begins at its first placed base, which can lie after the nominal
  start, so S's reader must address everything by extent. That is the one
  trap in S's table, and it bit a reader that still had chunk arithmetic

### Restated decision

- **Keep T64: bgzipped text, CSI with the chunk as leaf, rows at their
  chunk's span, block-aligned chunks. Take S's departure filing into it,
  and fix `reach` in the writer.** Format 7 as decided above, amended:
  - departure records are filed over their end nodes (the first base of
    the leave node to the last of the rejoin node, or the reverse), so the
    departure query is the drawn stretch itself, with no `reach`
  - each record has one row per block of the aligned pyramid
    `chunk × 8^L` (64 kb, 512 kb, 4 Mb, 32 Mb) its extent overlaps; the
    row's interval is the block's, so a block's rows are contiguous and
    land in one bin, and the writer ends a BGZF block after each block's
    rows; the record's own extent follows the fixed columns as two more
    columns, and a reader keeps the rows whose extent touches its stretch
    and dedups the rest on the columns after the block, as format 6 does
  - `#long` lists every pass of the reference over a node longer than
    `reach`, and the writer sets `reach` to 4,096 by default (`--long`), so
    a pggb window reads one tile, not two
  - the CSI is the writer's own (noodles), which keeps every bin's chunks
    exact; a file re-indexed with `tabix` is still correct and somewhat
    larger to read
- **Why not S.** Measured in this harness, S's advantage is 2 KB (7%) per
  1 kb window on MC and, on pggb with `reach` fixed, 45 KB of the
  departure read (113 against 68 KB, or 444 against 384 with attach
  fetches): the share @gmod/tabix's chunk merging adds to a Tabix read, a
  client constant, plus 7% of extent columns. Not several times the bytes.
  Against that, S's rows carry no sequence and no position, so a line
  means nothing on its own and `zcat | grep` cannot place a hit; its index
  is a new format with no tool behind it (`tabix`, htslib, pysam, noodles,
  the audit scripts and `walks-truth.py` all stop); it is 3× a CSI; and
  its reader must address every fetch through the table, which is the
  rewrite of `WalkReader`'s source layer and of the plugin's adapter. The
  two ideas S is right about, end-node filing and one contiguous group per
  pyramid block, fit inside Tabix unchanged in meaning, and the one rule S
  removes that T64 keeps, `reach` with `#long`, is one subtraction and a
  header list whose cost on pggb was the writer's threshold, now 4 kb
- **The numbers that decide it** (1 kb windows, walk and departure reads,
  KB median / p90 / p99): MC chr22 S 28 / 45 / 128 against T64b 30 / 52 /
  169 and the decision's T64 37 / 62 / 177; pggb chrY (arbA's range) S
  68 / 221 / 1056 against T64b with `reach` 4 kb 113 / 239 / 1213, T64b
  117 / 261 / 1587, T64 198 / 627 / 1906 and the shipped filing 292 (arbA).
  With attach fetches on pggb: S 384, T64b 4 kb 444, T64 701. Correctness
  equal: 176 of 180 and 138 of 142 identical cuts with the same edge cases
- **What changes in the Consequences above:** the writer files departure
  rows per pyramid block with the record's extent as two trailing columns
  (`departures.rs::blocks` keeps its shape, the extent needs the end
  nodes' lengths, which the encoder has), takes `--long <bp>` with 4,096
  as the default and writes `reach`, and builds the CSI itself; graph-walks
  queries `~departure` over the drawn stretch, keeps rows by their extent
  columns, and sizes attach fetches by `reach` and `#long`; `cut`'s return
  shape is unchanged, so the five consumers still re-roll on a version
  pin. The pggb figures in the Measurements section above are for the
  512 kb cut without these amendments; the cross-examination tables
  supersede them

## S7 check

The coordinator has decided for S amended (S7): every line starts
`seq start end` with the true extent of what the row describes, no fake
names or coordinates, the unit table split per sequence. An independent
prior-art review adds: dictionary rows (`ref`, `nodes`, `route`) take the
tile's extent; the departure cover is the largest aligned blocks inside the
record's tile-rounded extent; an in-stream `#unit` line at each unit's
start; the directory's first line echoes `#walks` with `bytes:i:<length>`;
empty sequences listed with length 0; single-range requests only. arbA's S7
had not landed when this was written, so S7 here is my build from arbA's S
files (`scripts/build_s7.py`): `ref` rows at their R stretch, `walk` and
`abridged` rows at their piece's stretch on R from the decoded steps,
`nodes` and `route` rows at the tile's extent, departure lines at S's
end-node extents, detail records as their tile. S's table shape, read as
S is read.

### What the extent columns cost

| MC chr22 tiles (776, 1,040,884 rows), bgzf-style zlib 6 | MB | ratio |
|---|---|---|
| S, no columns | 18.41 | 1.000 |
| S7 as built: walk rows at their own extent, dictionary rows at the tile's | 19.02 | 1.033 |
| every row at the tile's extent | 18.98 | 1.031 |
| S7 with a `#unit` line per tile | 19.03 | 1.034 |

- The columns cost 3.3% of tile bytes, the same as T64's key columns (its
  tiles are 18.9 MB of the same rows under my writer); walk rows' own
  extents against a constant tile extent cost 0.2%, since consecutive
  pieces' extents share most digits; the `#unit` line 0.1%. Files: S7
  60.3 MB against S's 57.8 on MC, 193.4 against 184.5 MB (+4.9%) on pggb chrY
- My build did not use per-row route spans (route rows already take the
  tile's extent), so the 68.7 MB figure is not reproduced here; the
  dictionary-at-tile-extent amendment is what was built

### The amendments, assessed

- **Dictionary rows at the tile's extent:** right, and it makes those rows
  say what they are, members of a tile. It also means a `route` or `nodes`
  row's `start end` is not its own extent but its container's, which is
  what T64's key columns say for every row; S7 and T64 then differ in
  honesty only on `walk` and `abridged` rows
- **Departure cover as the largest aligned blocks inside the tile-rounded
  extent:** that is what arbA's `sfinal.mjs::blocks` already computes
  (greedy largest aligned block from `floor(lo / C) × C` to
  `ceil(hi / C) × C`), and what `departures.rs::blocks` does from 2^17; the
  line counts above (54,050 on MC, 1,558,946 on chrY) are for that cover.
  Nothing to change, and the amendment should be worded as the existing
  rule
- **`#unit` lines:** 0.1% of bytes, and the file can be re-indexed by a
  scan, which is `tabix`'s job on a Tabix file. A `#` line inside a unit
  means every row consumer skips `#` lines, as they skip the header
- **`bytes:i:<length>` in the directory:** a cheap guard a CSI lacks
  (htslib only warns when the index's mtime is older than the data's, which
  this harness saw on the shipped chrY file). Worth having
- **Empty sequences at length 0, single-range requests:** no cost;
  @gmod/tabix and `RemoteFile` already issue single ranges, and the gap
  merging that cost T64b its 40 KB on pggb exists to save requests on
  exactly such hosts. S7's reader, merging only touching units, makes more
  requests for fewer bytes (MC 1 kb: 1 median, up to 8; pggb reads: 2
  median, up to 4), the same trade in the other direction

### What S7 does to a reader

- graph-walks groups the rows of a read by column 2 (`walkChunk.ts`:
  `chunkStart: +cols[1]`, `readChunks`' `cs !== at` test, `decoded.has(cs)`,
  the detail sibling name `${anchor}~${cols[1]}`). With S7's per-row
  extents, column 2 no longer names the tile, so the decoder's grouping,
  its `decoded` keys and the detail lookup must take the tile from the
  table entry the bytes came from. That is a change inside `walkChunk` and
  `walkReader`, beyond the source layer arbA's Consequences describe; my
  cut check hands graph-walks the tile's name in column 2 for that reason.
  `cut`'s return shape is still unchanged
- Rows inside a tile are not sorted by `start` (ref, nodes, routes, then
  walks by path), so S7's rows are not Tabix-indexable even in principle;
  the table is the only index

### Table

| MC chr22: candidate | window | with attach fetches, KB med / p90 / p99 | walk + departure reads only | requests med / max | round trips med / max |
|---|---|---|---|---|---|
| S7 | 1 kb | 31 / 152 / 493 | 29 / 48 / 135 | 1 / 8 | 1 / 2 |
| S7 | 10 kb | 32 / 91 / 577 | 31 / 70 / 206 | 1 / 7 | 1 / 2 |
| S7 | 100 kb | 85 / 156 / 575 | 80 / 117 / 195 | 1 / 8 | 1 / 2 |
| S7 | 1000 kb | 532 / 780 / 1577 | 511 / 695 / 1408 | 1 / 8 | 1 / 2 |
| S | 1 kb | 29 / 143 / 466 | 28 / 45 / 128 | 1 / 8 | 1 / 2 |
| S | 10 kb | 30 / 86 / 541 | 29 / 66 / 197 | 1 / 7 | 1 / 2 |
| S | 100 kb | 81 / 146 / 541 | 75 / 111 / 182 | 1 / 8 | 1 / 2 |
| S | 1000 kb | 500 / 732 / 1489 | 483 / 652 / 1332 | 1 / 8 | 1 / 2 |
| T64b | 1 kb | 31 / 157 / 536 | 30 / 52 / 169 | 2 / 8 | 1 / 2 |
| T64b | 10 kb | 32 / 97 / 574 | 32 / 73 / 206 | 2 / 8 | 1 / 3 |
| T64b | 100 kb | 86 / 156 / 573 | 81 / 118 / 210 | 2 / 8 | 1 / 3 |
| T64b | 1000 kb | 533 / 780 / 1576 | 514 / 694 / 1408 | 2 / 8 | 1 / 3 |

| pggb chrY 2.78–26.67 Mb: candidate | window | with attach fetches, KB med / p90 / p99 | walk + departure reads only | requests med / max | round trips med / max |
|---|---|---|---|---|---|
| S7 | 1 kb | 418 / 1389 / 1550 | 70 / 238 / 1292 | 10 / 12 | 2 / 2 |
| S7 | 10 kb | 425 / 1383 / 1511 | 69 / 261 / 766 | 10 / 12 | 2 / 2 |
| S7 | 100 kb | 543 / 1434 / 3224 | 100 / 496 / 2966 | 10 / 12 | 2 / 2 |
| S7 | 1000 kb | 1451 / 3457 / 6451 | 717 / 3116 / 6194 | 10 / 12 | 2 / 2 |
| S | 1 kb | 384 / 1237 / 1341 | 68 / 221 / 1056 | 10 / 12 | 2 / 2 |
| S | 10 kb | 392 / 1233 / 1354 | 67 / 251 / 682 | 10 / 12 | 2 / 2 |
| S | 100 kb | 485 / 1281 / 2762 | 95 / 468 / 2532 | 10 / 12 | 2 / 2 |
| S | 1000 kb | 1328 / 3118 / 5366 | 685 / 2674 / 5137 | 10 / 12 | 2 / 2 |
| T64b | 1 kb | 615 / 1839 / 2083 | 117 / 261 / 1587 | 11 / 12 | 3 / 3 |
| T64b | 10 kb | 621 / 913 / 2003 | 119 / 281 / 1301 | 11 / 12 | 3 / 3 |
| T64b | 100 kb | 640 / 1858 / 3437 | 135 / 541 / 2941 | 11 / 12 | 3 / 3 |
| T64b | 1000 kb | 1743 / 3675 / 6349 | 745 / 3178 / 5853 | 11 / 12 | 3 / 3 |
| T64b-reach4k | 1 kb | 444 / 1311 / 1479 | 113 / 239 / 1213 | 11 / 12 | 3 / 3 |
| T64b-reach4k | 10 kb | 456 / 773 / 1475 | 116 / 271 / 742 | 11 / 12 | 3 / 3 |
| T64b-reach4k | 100 kb | 539 / 1324 / 3109 | 131 / 510 / 2842 | 11 / 12 | 3 / 3 |
| T64b-reach4k | 1000 kb | 1468 / 3261 / 6114 | 743 / 2994 / 5847 | 11 / 12 | 3 / 3 |

| pggb chrY 2.8–56.8 Mb: candidate | window | with attach fetches, KB med / p90 / p99 | walk + departure reads only | requests med / max | round trips med / max |
|---|---|---|---|---|---|
| S7 | 1 kb | 280 / 602 / 1462 | 2 / 167 / 640 | 4 / 12 | 2 / 2 |
| S7 | 10 kb | 280 / 691 / 1469 | 2 / 173 / 873 | 4 / 12 | 2 / 2 |
| S7 | 100 kb | 280 / 794 / 2212 | 2 / 278 / 1954 | 4 / 12 | 2 / 2 |
| S7 | 1000 kb | 284 / 2468 / 4531 | 6 / 2116 / 4273 | 4 / 12 | 2 / 2 |
| S | 1 kb | 261 / 589 / 1308 | 2 / 163 / 628 | 4 / 12 | 2 / 2 |
| S | 10 kb | 261 / 631 / 1309 | 2 / 169 / 788 | 4 / 12 | 2 / 2 |
| S | 100 kb | 261 / 735 / 1861 | 2 / 260 / 1631 | 4 / 12 | 2 / 2 |
| S | 1000 kb | 264 / 2319 / 3989 | 6 / 2000 / 3759 | 4 / 12 | 2 / 2 |
| T64b-exact | 1 kb | 278 / 759 / 1996 | 2 / 203 / 645 | 4 / 12 | 2 / 3 |
| T64b-exact | 10 kb | 278 / 786 / 1944 | 2 / 200 / 855 | 4 / 12 | 2 / 3 |
| T64b-exact | 100 kb | 278 / 954 / 2725 | 2 / 313 / 2229 | 4 / 12 | 2 / 3 |
| T64b-exact | 1000 kb | 282 / 2658 / 4583 | 6 / 2219 / 4086 | 4 / 12 | 2 / 3 |

- S7 against S: the extent columns cost 1 KB per 1 kb window on MC
  (29 against 28 KB reads) and 2 KB on pggb (70 against 68), 3% of the
  tiles, as the file-size study said; with attach fetches 31 against 29 and
  418 against 384 KB (the attach tiles carry the columns too)
- S7 against T64b with `reach` 4 kb, the amended Tabix design: reads only,
  S7 is 43 KB cheaper per 1 kb window on pggb (70 against 113), which is
  @gmod/tabix's gap merging in the departure read plus T64b's extent
  columns, and 1 KB on MC. With graph-walks' attach fetches, what a window
  costs, the two are within 6% at the pggb median (418 against 444 KB) and
  T64b is lower at the p90 and p99 (1,311 against 1,389 and 1,479 against
  1,550); on MC they are equal (31 against 31; 152 against 157; 493 against
  536). Round trips: S7 2 with attach, T64b 3 (@gmod/tabix's read-ahead on
  a departure read of several chunks)
- Requests: S7 makes one request per unit (median 1 on MC, 10 on pggb with
  attach), T64b merges across gaps (2 and 11). The bytes S7 saves on reads
  are the bytes T64b's client spends to make fewer requests

### Correctness

`harness/cutcheck.mjs` with an S7 source: tiles and attach fetches
addressed by extent, departure lines kept by their own extent, and the
tile's name handed to graph-walks in column 2 because its decoder groups
rows by that column. **175 of 180 windows identical** (1 kb 59/60, 10 kb
59/60, 100 kb 57/60), the same windows as S and T64b, for the same
reasons: chr22:18,991,862 the attach-decode bug; 44,683,486, 45,707,478
and 27,329,723 one node or one record's own steps at the edge of the
extent, where end-node filing and the shipped ±`maxnode` read return
different records; 18,843,668 the LCR22A excursion the shipped lookback
chunk draws by accident of adjacency (identical on-window nodes, one
fragment against two and the record between them). Fragments identical in
every other window

### Verdict on S7

- **Accept S7.** The objection that decided my cross-examination against S,
  rows that say nothing on their own, is answered: an S7 line is
  `GRCh38#0#chr22 10510000 10551763 walk HG00235#2#CM094408.1 …`, a
  piece and where it lies, and 61% of walk rows state an extent narrower
  than their tile (18,207 of the first 30,000), so the columns carry
  information T64's key columns do not. That costs 3.3% of tile bytes and
  4–5% of the file, the same as T64's columns. Measured against the
  amended Tabix design in the same harness, S7 costs the same per window
  with attach fetches on MC, 6% less at the pggb median and 5–6% more at
  its tails, and 43 KB less on pggb reads alone. There is no measured
  reason in bytes, requests or round trips to prefer T64b over S7, and
  S7 has what T64b cannot: exact byte ranges that do not depend on a
  client's merge policy or on which indexer built the index, no `reach`
  and no `#long`, no sibling names, no detail coordinate, a `bytes:i:`
  check, and an open cost of one sequence's share
- **What accepting it costs, to put in the ADR:**
  - `tabix`, htslib's region API, pysam and noodles stop at the walks
    file; the extraction is `awk` on the table and `tail | head | gzip -dc`,
    and `zcat | grep` now places every hit. The audit scripts and
    `walks-truth.py` move to the table
  - graph-walks' decoder, not only its source layer: `walkChunk` groups
    rows by column 2 and names detail siblings from it, so the tile must
    come from the table entry; attach fetches and `decoded` are keyed by
    tile entry, never by `floor(base / chunk)` (the trap that failed 8 of
    65 windows in my first S run); `cut`'s return shape is unchanged
  - the table format is a spec of its own, with the per-sequence split
    (how a reader finds a sequence's lines), the `#unit` line, the
    `bytes:i:` check and the dedup rule written down, and a version
  - 3.7× duplicated departure lines on pggb (14.5 MB of 193), 2.2× on MC;
    disk, not window bytes
  - a reader that merges only touching units makes up to 12 requests per
    pggb window; if request count ever matters more than bytes on a host,
    merging across small gaps is the same trade @gmod/tabix makes
- **Amendments:** take all six; the departure cover is already the rule
  `sfinal.mjs` and `departures.rs` implement, so word it as such. Add two:
  the writer verifies every row's extent columns against its decoded
  steps, as it already verifies the steps; and the spec defines a walk
  row's extent as its piece's stretch on the tile's R (route interiors
  that hold another chunk's reference nodes lie outside it)
- **What stays from my case:** the @gmod/tabix chunk-end fix upstream for
  every Tabix user; the attach-decode fix before release; the `#long`
  threshold finding, which S7 does not need but any Tabix reader of a
  pggb file does; and the departure-tier numbers (htslib's bin folding,
  the client's gap merging), which explain the 2.7× and belong in the
  issues log whatever the format
