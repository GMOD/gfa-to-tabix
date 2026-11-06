# S7 at genome scale: measured against format 6

Measured 2026-11-05 on ada, under `~/work/s7-genome/`. Inputs are the audited gfa-to-tabix 3.0.0 files in `~/work/genome3/` (GRCh38 and CHM13, read-only). In every table, KB means 1,024 bytes.

## Verdict

S7 holds at genome scale. Both genome-wide files convert, pass `verify7.mjs` in full, and read correctly:

- **Correctness:**
  - arbA's check on 800 windows found 0 wrong pieces among 600,549, and 0 missing departure records among 117,877.
  - graph-walks' own `cut`, given format 6's rows for the units S7 selects, is identical to the cut over S7 on 800 of 800 windows (300 GRCh38, 500 CHM13). That holds once graph-walks 5.0.2's attach-decode bug is fixed. Without the fix, 784 of 800 are identical, and all 16 that differ come from that bug.
- **First view is far cheaper than format 6's:**
  - S7 opens a sequence for 56–192 KB: a 0.9–7.9 KB directory, a 1.3 KB header and that sequence's table, the largest of which is 183 KB (GRCh38 chr9 and chr1).
  - Format 6 pays 1,729–1,770 KB before drawing anything: the whole `.tbi` plus a 64 KB header read.
  - Open plus a first 1 kb window costs S7 62–225 KB median against format 6's 1,782–1,935 KB: 0.03–0.12×.
  - Round trips are the same, 3–4. S7 makes one more request to open (3 against 2).
- **Window bytes are lower at every quantile measured:**
  - 1 kb reads are 0.3× format 6's, and 100 kb reads about 0.5×.
  - The former trouble spots fall too: CHM13 chr14 13–14 Mb at 1 kb is 93 against 266 KB read, and 296 against 771 KB with attach fetches.

Where S7 looks worse:

- **Its file is 1.7% (GRCh38) and 0.7% (CHM13) larger** than format 6's file plus `.tbi`.
- **All of its tables together (2.1 MB) are larger than format 6's `.tbi` (1.7 MB).** No reader reads them all at once.
- **The converter is slow:** 1 h 25 min (GRCh38) and 1 h 38 min (CHM13), single-threaded JavaScript.
- **It makes one more request at open, and more requests per window in CHM13 chr9 38–80 Mb** (median 5 against 4).
- **Its read-exactly-the-overlap rule drops a little that format 6's lookback chunk picks up by accident.** That is 6 windows' joined fragments and 4 windows' attached own steps for one record, all through steps outside the drawn stretch. See "Anything that breaks". This is a reader-rule gap for ADR 0010 to settle, not wrong data.

## Method

- **Format 6 baseline:** graph-walks 5.0.2's own `WalkReader.cut`.
  - Copy: `gw/` is graph-walks main at df676a1, whose `src/` is identical to the 5.0.2 tag 9300103.
  - It runs over @gmod/tabix 3.13.1 and generic-filehandle2 `RemoteFile`, against a local HTTP server that logs every range.
  - Budgets are lifted. "Read" is `attachFetches: 0`; "+ attach" is graph-walks' default of 8 attach fetches.
  - First view uses a fresh reader: `header()`, which fetches the whole `.tbi` and the header, then the cut.
  - Windows use one reader per sequence, with `clearChunkCache()` before each cut.
  - Script: `f6.mjs`. Outputs: `res/f6.grch38.jsonl` and `res/f6.chm13.jsonl`.
- **S7:** arbA's reader `s7Cand`, copied from `measure.mjs`, over the same server and windows (`s7win.mjs`).
  - Open: GET the directory, then the header and the sequence's table in parallel, with the bound checks.
  - Window: units overlapping D = window ± 1 kb, with touching ranges merged.
  - "+ attach" is arbA's attach rule: records with own bp > missing bp and own bp ≤ 65,536, one fetch of the tile holding the leave base, at most 8. This approximates graph-walks' `cut.unattached` rule; it isn't that rule.
  - Outputs: `res/s7.grch38.jsonl` and `res/s7.chm13.jsonl`.
- **Windows** (`windows.mjs` to `win/windows.jsonl`, sha256 52eb5879…):
  - Seeded, uniform over each sequence's row extent, with the same windows for both formats.
  - 200 per size (1 kb and 100 kb) on GRCh38 chr1, chr6 and chr22, and on CHM13 chr9, chr14 and chr22.
  - Plus 200 per size in CHM13 chr9 38–80 Mb and in chr14 13–14 Mb.
  - Plus 20 first-view 1 kb windows on each of chr1, chr6, chr9, chr14, chr22 and chrX per file.
  - Because windows are uniform over the row extent, some fall in gaps, where both formats pay little.
- **Scripts from arbA**, copied from `~/work/arb-arbA/scripts/` into `scripts/` (sha256, mtime PST):
  - `bgzf.mjs` 2556cb1f18fd23df, 13:18:41
  - `scodec.mjs` 89a19a3991c7c38e, 13:18:00
  - `build.mjs` 6784f0500e274ea0, 13:41:42
  - `sfinal.mjs` d7f73e7313982229, 15:36:15
  - `s7.mjs` 60bac3ba464dc904, 15:29:53
  - `verify7.mjs` 63d7d85207c63024, 15:30:36
  - `measure.mjs` 17e7b2c68456a9e0, 15:30:12
  - `cutcheck.mjs` 73e5724dbf955397, 15:34:46
  - All full hashes are in `res/scripts.sha256.txt`. The first six match the coordinator's expected prefixes.

## First view per sequence

Open the file and draw one 1 kb window with attach fetches, 20 seeded windows per sequence. Outputs: `res/f6.*.jsonl` and `res/s7.*.jsonl`; table from `summarize.mjs` (`res/summary.md`).

| genome | seq | S7 open KB (directory + header + table) | S7 open requests, trips | S7 window KB median / max | S7 total KB median / max | S7 trips max | format 6 total KB median / max | format 6 trips max | S7 / format 6 total, median |
|---|---|---|---|---|---|---|---|---|---|
| grch38 | chr1 | 188 (7.9 + 1.3 + 179) | 3, 2 | 23 / 53 | 211 / 241 | 4 | 1841 / 1876 | 3 | 0.11 |
| grch38 | chr6 | 110 (7.9 + 1.3 + 101) | 3, 2 | 25 / 52 | 135 / 162 | 3 | 1847 / 1884 | 3 | 0.07 |
| grch38 | chr9 | 192 (7.9 + 1.3 + 183) | 3, 2 | 30 / 405 | 222 / 597 | 4 | 1846 / 2873 | 4 | 0.12 |
| grch38 | chr14 | 98 (7.9 + 1.3 + 89) | 3, 2 | 24 / 56 | 122 / 154 | 4 | 1840 / 1924 | 4 | 0.07 |
| grch38 | chr22 | 56 (7.9 + 1.3 + 46) | 3, 2 | 5.8 / 140 | 62 / 196 | 4 | 1838 / 2278 | 4 | 0.03 |
| grch38 | chrX | 91 (7.9 + 1.3 + 82) | 3, 2 | 16 / 21 | 106 / 112 | 3 | 1819 / 1878 | 3 | 0.06 |
| chm13 | chr1 | 174 (0.9 + 1.3 + 172) | 3, 2 | 25 / 93 | 199 / 266 | 4 | 1806 / 2010 | 4 | 0.11 |
| chm13 | chr6 | 95 (0.9 + 1.3 + 93) | 3, 2 | 25 / 56 | 121 / 151 | 3 | 1810 / 1833 | 3 | 0.07 |
| chm13 | chr9 | 92 (0.9 + 1.3 + 89) | 3, 2 | 26 / 71 | 118 / 163 | 4 | 1815 / 1907 | 5 | 0.06 |
| chm13 | chr14 | 116 (0.9 + 1.3 + 114) | 3, 2 | 26 / 239 | 142 / 356 | 4 | 1804 / 2328 | 4 | 0.08 |
| chm13 | chr22 | 103 (0.9 + 1.3 + 101) | 3, 2 | 122 / 659 | 225 / 762 | 4 | 1935 / 2957 | 4 | 0.12 |
| chm13 | chrX | 83 (0.9 + 1.3 + 81) | 3, 2 | 17 / 56 | 100 / 139 | 3 | 1782 / 1865 | 3 | 0.06 |

- **Format 6's open,** every sequence: 2 requests and 2 round trips. GRCh38 is 1,770 KB (`.tbi` 1,706 KB plus 64 KB of header read); CHM13 is 1,729 KB (1,665 + 64).

## Directory and table sizes

From `structure.mjs`: `res/structure.grch38.json` and `res/structure.chm13.json`. Bytes.

| | GRCh38 | CHM13 |
|---|---|---|
| directory (`.idx`) | 8,109 (197 lines) | 886 (27 lines) |
| header unit | 1,366 | 1,366 |
| all tables together (never read at once) | 2,147,161 | 2,133,185 |
| all tables, tile + departure entries only (each table gzipped without its detail entries) | 1,437,825 | 1,453,447 |
| format 6 `.tbi` (read whole at open) | 1,747,103 | 1,705,430 |
| largest table | chr9 187,287 | chr1 175,643 |
| smallest table | chrM 93 (1 unit) | chrM 92 (1 unit) |

Per sequence: table bytes; then each entry kind gzipped alone (tile / departures / detail); then the table gzipped without detail entries.

| genome | seq | table | tile / departures / detail entries | without detail |
|---|---|---|---|---|
| GRCh38 | chr1 | 183,199 | 72,542 / 51,388 / 67,817 | 114,466 |
| GRCh38 | chr6 | 103,270 | 50,847 / 37,317 / 22,273 | 80,089 |
| GRCh38 | chr9 | 187,287 | 40,100 / 26,228 / 125,599 | 61,136 |
| GRCh38 | chr14 | 90,779 | 30,106 / 19,930 / 44,019 | 46,039 |
| GRCh38 | chr22 | 47,549 | 14,074 / 8,763 / 26,032 | 21,175 |
| GRCh38 | chrX | 83,553 | 46,028 / 33,543 / 10,104 | 72,536 |
| CHM13 | chr1 | 175,643 | 72,542 / 52,615 / 59,083 | 115,264 |
| CHM13 | chr6 | 95,287 | 51,144 / 37,421 / 13,742 | 80,484 |
| CHM13 | chr9 | 91,455 | 44,128 / 30,525 / 22,147 | 68,485 |
| CHM13 | chr14 | 116,958 | 29,547 / 22,644 / 68,759 | 47,775 |
| CHM13 | chr22 | 102,926 | 15,099 / 11,697 / 78,305 | 24,628 |
| CHM13 | chrX | 82,932 | 45,553 / 33,475 / 10,184 | 71,780 |

- **arbA's estimate tested:**
  - chr1's table is 183 KB on GRCh38 and 176 KB on CHM13, against the estimated ~230 KB.
  - All tables together are 2.15 and 2.13 MB, inside the estimated 1.2–2.9 MB.
- **Detail entries dominate the dense tables:** 65% of GRCh38 chr9's and 75% of CHM13 chr22's, measured with each entry kind gzipped alone. They are the part the converter's naming bug touches (below). Without them, chr1's table falls to 114–115 KB on both genomes.

## Windows

Same windows for both formats. Read; read + attach. Outputs: `res/f6.*.jsonl` and `res/s7.*.jsonl`.

| genome | seq | set | size | n | S7 read | format 6 read | S7 + attach | format 6 + attach | S7 req | format 6 req | S7 trips | format 6 trips |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| grch38 | chr1 | all | 1 kb | 200 | 25 / 34 / 78 | 76 / 106 / 204 | 25 / 39 / 167 | 77 / 109 / 478 | 1 / 6 | 1 / 6 | 2 | 2 |
| grch38 | chr1 | all | 100 kb | 200 | 64 / 90 / 189 | 118 / 159 / 310 | 65 / 91 / 250 | 118 / 159 / 595 | 1 / 5 | 2 / 6 | 2 | 2 |
| grch38 | chr6 | all | 1 kb | 200 | 24 / 34 / 105 | 73 / 99 / 233 | 24 / 34 / 105 | 73 / 99 / 233 | 1 / 2 | 1 / 2 | 1 | 1 |
| grch38 | chr6 | all | 100 kb | 200 | 64 / 86 / 170 | 116 / 145 / 254 | 65 / 86 / 180 | 116 / 145 / 254 | 1 / 2 | 2 / 2 | 2 | 1 |
| grch38 | chr22 | all | 1 kb | 200 | 26 / 49 / 158 | 86 / 135 / 290 | 27 / 83 / 515 | 87 / 299 / 1038 | 1 / 9 | 1 / 9 | 2 | 2 |
| grch38 | chr22 | all | 100 kb | 200 | 69 / 108 / 258 | 131 / 194 / 367 | 74 / 185 / 629 | 135 / 363 / 1050 | 1 / 9 | 2 / 8 | 2 | 2 |
| chm13 | chr9 | all | 1 kb | 200 | 23 / 36 / 81 | 77 / 109 / 259 | 27 / 75 / 220 | 87 / 203 / 568 | 2 / 7 | 2 / 6 | 2 | 3 |
| chm13 | chr9 | all | 100 kb | 200 | 55 / 90 / 149 | 116 / 171 / 275 | 72 / 125 / 266 | 134 / 271 / 594 | 2 / 7 | 2 / 7 | 2 | 3 |
| chm13 | chr14 | all | 1 kb | 200 | 27 / 44 / 187 | 79 / 165 / 286 | 27 / 119 / 554 | 79 / 369 / 1318 | 1 / 8 | 2 / 7 | 2 | 2 |
| chm13 | chr14 | all | 100 kb | 200 | 72 / 110 / 380 | 128 / 255 / 531 | 73 / 209 / 747 | 128 / 509 / 1534 | 1 / 9 | 2 / 8 | 2 | 2 |
| chm13 | chr22 | all | 1 kb | 200 | 30 / 71 / 239 | 102 / 263 / 523 | 57 / 385 / 668 | 142 / 923 / 1255 | 1 / 10 | 2 / 9 | 2 | 2 |
| chm13 | chr22 | all | 100 kb | 200 | 80 / 178 / 457 | 151 / 331 / 666 | 102 / 424 / 786 | 186 / 923 / 1300 | 1 / 9 | 2 / 9 | 2 | 2 |
| chm13 | chr9 | 38-80Mb | 1 kb | 200 | 11 / 41 / 117 | 69 / 144 / 547 | 72 / 162 / 342 | 192 / 464 / 706 | 5 / 7 | 4 / 7 | 2 | 3 |
| chm13 | chr9 | 38-80Mb | 100 kb | 200 | 13 / 74 / 256 | 55 / 174 / 724 | 73 / 158 / 499 | 179 / 398 / 848 | 5 / 7 | 4 / 6 | 2 | 3 |
| chm13 | chr14 | 13-14Mb | 1 kb | 200 | 93 / 111 / 237 | 266 / 344 / 423 | 296 / 385 / 475 | 771 / 1024 / 1104 | 4 / 5 | 4 / 5 | 2 | 2 |
| chm13 | chr14 | 13-14Mb | 100 kb | 200 | 220 / 313 / 331 | 412 / 513 / 515 | 416 / 571 / 572 | 874 / 1104 / 1194 | 4 / 5 | 4 / 5 | 2 | 2 |

- **Requests:** S7's median is equal or lower everywhere except CHM13 chr9 38–80 Mb (5 against 4). S7's attach fetches are one range per tile, and there are many records to attach.
- **Round trips:** at most 2 for S7, against up to 3 for format 6.

## Correctness

### Pieces and departure records

arbA's check (copied in `s7win.mjs`): every piece's steps over D, and every departure record over D, rebuilt from S7's fetched units and compared with format 6's rows decoded by graph-walks' `decodeChunk`. Every 4th window.

| genome | set | windows | pieces | missing | differ | extra | departures | missing | outside truth |
|---|---|---|---|---|---|---|---|---|---|
| grch38 | all | 300 | 213958 | 0 | 0 | 0 | 14126 | 0 | 0 |
| chm13 | all | 300 | 217269 | 0 | 0 | 0 | 27883 | 0 | 0 |
| chm13 | 38-80Mb | 100 | 19714 | 0 | 0 | 0 | 34434 | 0 | 0 |
| chm13 | 13-14Mb | 100 | 149608 | 0 | 0 | 0 | 41434 | 0 | 0 |

### graph-walks 5.0.2's cut

arbA's `cutcheck.mjs`, copied as `cutcheck7g.mjs`; only paths and the per-window sequence changed. Budgets lifted, `attachFetches` 64, every 4th window, sizes 1 kb and 100 kb. Detail expansion is not exercised: no `expand`, so the detail-name bug can't reach these results.

| baseline | graph-walks | GRCh38 identical | CHM13 identical | the rest |
|---|---|---|---|---|
| units: format 6's rows for the units S7 selects (`BASELINE=units`) | 5.0.2 as released | 297 / 300 | 487 / 500 | identical fragments; departures differ in attached steps; extra kept nodes on the format 6 side |
| the same, rerun on the differing windows | 5.0.2 with arbA's attach-decode fix (`gwfix/`) | 300 / 300 (3/3 rerun; full run 300/300) | 500 / 500 (13/13 rerun) | none |
| shipped: format 6 read the graph-walks 5 way (lookback chunk, departures ± `maxnode`) | 5.0.2 as released | 294 / 300 | 224 / 250 (every 8th) | see below |
| shipped, differing windows rerun | with the fix | 2 of 6 become identical | 9 of 26 become identical | 4 GRCh38 and 17 CHM13 remain |

Outputs:

- `res/cut.units.{grch38,chm13}.jsonl`
- `res/cut.units-fix.grch38.jsonl`, `res/cut.units-fix.diff3.jsonl`, `res/cut.units-fix.chm13-diff13.jsonl`
- `res/cut.shipped.{grch38,chm13}.jsonl`, `res/cut.shipped-fix.grch38-diff.jsonl`, `res/cut.shipped-fix.chm13-diff.jsonl` (and `logs/cut.shipped-fix.chm13-diff.log`, which has the positions)

The 21 shipped-baseline differences left after the fix:

- **11 windows (GRCh38 3, CHM13 8): only kept nodes differ,** by 1 to 124. The shipped reader keeps nodes from its lookback chunk. Fragments and departures are identical.
- **6 windows (GRCh38 chr22 at 34.09 Mb, 100 kb; CHM13 chr14 13.48–13.57 Mb, 1 kb and 100 kb): fragments differ.**
  - The shipped reader joins some haplotypes' pieces into one fragment through steps placed 80–92 kb before the drawn stretch, which its lookback chunk happens to hold.
  - S7 reads only tiles overlapping D, so it shows the same haplotypes as two fragments with a gap: 51 bp on GRCh38, e.g. 34,090,238–34,103,036 and 34,103,087–34,192,279.
  - All the shipped-only departures there (351 on GRCh38; 36 to 8,947 per CHM13 window) lie outside the drawn stretch. None inside D is missing.
- **4 windows (CHM13 chr14 13.20–13.21 Mb): one departure record has its own steps attached only on the shipped side.**
  - The record: NA19185#2#CM087748.1, leaving at 13,472,637 and rejoining at 13,135,857, with 53,524 own bp.
  - Its own steps are filed in chunk 13,107,200, the rejoin side (`whereSteps.mjs` confirms it). That is exactly format 6's lookback chunk for this window.
  - graph-walks' attach rule, and S7's spec ("the tile unit whose extent holds the leave base"), fetch the leave tile, 13,434,880, which doesn't hold them.
  - Lifting the attach cap to Infinity changes nothing (`res/cut.shipped-fix-allattach.four.jsonl`).

## Build cost

`build.sh`: each step under `systemd-run` with `MemoryMax=28G` and `node --max-old-space-size=24000`. Both genomes ran in parallel on the shared host. Logs: `logs/build.<genome>.<step>.log`.

| step | GRCh38 time | GRCh38 peak RSS | CHM13 time | CHM13 peak RSS |
|---|---|---|---|---|
| `build.mjs` (format 6 to O tiles, `dep`, `depu`) | 32:48 | 2.6 GB | 38:59 | 3.3 GB |
| `sfinal.mjs` (departure pyramid) | 9:58 | 5.2 GB | 10:34 | 5.3 GB |
| `s7.mjs` (S7 file and directory) | 42:08 | 3.7 GB | 48:29 | 4.8 GB |
| total conversion | 1:24:54 | 5.2 GB | 1:38:02 | 5.3 GB |
| `verify7.mjs` (release checks) | 1:24, passed | 1.9 GB | 9:36, passed | 2.1 GB |

`verify7.mjs` results:

- GRCh38: 159,038 units, 195 tables, 97,164,719 lines, of which 3,813,809 are departure lines.
- CHM13: 154,936 units, 25 tables, 111,337,174 lines, of which 3,743,089 are departure lines.

| | GRCh38 | CHM13 |
|---|---|---|
| format 6 file + `.tbi` | 1,552,571,702 + 1,747,103 | 1,766,959,626 + 1,705,430 |
| S7 file + directory | 1,580,182,028 + 8,109 (+1.7%) | 1,780,802,603 + 886 (+0.7%) |
| tile units | 47,440, 1,115.9 MB | 47,579, 1,168.1 MB |
| departure units | 44,617, 57.6 MB | 46,575, 58.3 MB |
| detail units | 66,981, 404.5 MB | 60,782, 552.3 MB |

This is the converter's cost: three passes in JavaScript, each reading the whole intermediate file. It is not the cost of the gfa-to-tabix writer, which writes S7 directly; the 3.0.0 writer took about 70 min per genome.

## Anything that breaks

- **Sequences with no rows:**
  - Every reference sequence holds rows: GRCh38's graph has 195 reference paths and all 195 hold rows; CHM13 has 25 of 25 (from the 3.0.0 build logs). So the converter's gap, listing only sequences with rows, misses no sequence on these two files.
  - 145 of GRCh38's 195 sequences have no departure records. Their tables hold tiles only, and the smallest is 93 bytes.
  - The spec's empty-sequence case (a table holding only its `#unit` line) is not exercised by these files. The real writer must list every reference sequence.
- **Offsets past 4 GB:**
  - S7 uses no BGZF virtual offsets anywhere. Table offsets and lengths are plain decimal compressed bytes, and the largest unit end is 1,780,778,726 (CHM13).
  - The format has no 4 GB limit.
  - The prototype scripts do: they `readFileSync` whole files, and Node refuses anything over 2 GiB. A 2.2 GB sparse file gave `ERR_FS_FILE_TOO_LARGE`.
  - `s7.mjs` reads `o.walks.gz` and `s.walks.gz` whole (CHM13: 1.65 and 1.71 GB), and `verify7.mjs` reads `s7.walks.gz` whole (1.78 GB). That leaves 17% headroom on CHM13.
  - A larger genome-wide file would need streaming versions; the real writer and any release check must stream.
- **Largest units:**
  - Tile: CHM13 chr15 at 1,179,648, 315,444 bytes compressed (2.96 MB of text).
  - Tile: GRCh38 chr22 at 11,993,088, 295,618 bytes (1.92 MB of text).
  - Departure block: GRCh38 chr14 at 19,595,264, 35,650 bytes.
  - Detail unit: GRCh38 chr22 `11796480:0`, 116,734 bytes.
  - No tile's extent reaches more than 1,023 bp past its nominal 64 kb (max node 1,024; `extents.mjs`). So no unit is selected by windows far from it.
  - pggb satellites are not in these files.
- **Departure pyramid duplication:**
  - GRCh38: 3,813,809 lines for 1,797,769 records, 2.12×.
  - CHM13: 3,743,089 lines for 1,750,312 records, 2.14×.
  - Format 6's bin cut writes 2,066,063 and 2,033,905 rows (1.15× and 1.16×).
  - S7's departure units are 3.6% and 3.3% of the file.
- **Detail unit naming (converter bug, known; reported to the coordinator by the format 7 writer's author):**
  - Units sharing a name: 10,993 of 66,981 detail units on GRCh38 (16%), 1,592 of 60,782 on CHM13 (2.6%), and 355 of 2,468 on GRCh38 chr22 (the same count arbA's MC chr22 file shows).
  - It can affect:
    - detail unit names and counts;
    - the detail-entry share of each table, and so the table bytes above (the "without detail" column isolates it);
    - any expansion of an abridged piece.
  - It cannot affect window bytes, first-view bytes apart from the table's detail entries, the piece and departure check, or the cut checks, none of which expand detail.
  - `verify7.mjs` does not check that names are unique.
- **graph-walks 5.0.2's attach-decode bug:**
  - A chunk decoded for some names is not decoded again for others.
  - It caused all 16 units-baseline differences (GRCh38 3, CHM13 13). With arbA's fix (`gwfix/src/walkReader.ts`) every one is identical.
  - It affects format 6 and S7 alike, and must be fixed before graph-walks 6.
- **The overlap rule against format 6's lookback** (correctness section above):
  - S7 reads only what overlaps D. On 6 windows it shows a haplotype as two fragments where format 6 joins them through steps outside D.
  - On 4 windows it leaves one record's own steps unattached, because they are filed at the rejoin side and the attach rule fetches the leave tile.
  - Format 6 gets both only when the needed chunk happens to be its single lookback chunk, so it isn't a guarantee there either.
  - ADR 0010 should state where a record's own steps are filed and have the attach fetch name that tile.
- **The cut check is slow on CHM13 chr14 13–14 Mb:** up to about 15 minutes for one 1 kb window with `attachFetches` 64. graph-walks' default of 8 cuts the same window in 0.7 s (`res/f6.chm13.jsonl`).

## Reproduce

On ada, in `~/work/s7-genome/`. Every command runs in bash (`bash -c` from the zsh login shell).

```
# staging: graph-walks main at df676a1 (src = 5.0.2) as gw/, arbA's helper modules as h/
cd ~/src/graph-walks && git archive df676a1 | (mkdir -p /tmp/gw && tar -x -C /tmp/gw)   # on the laptop
rsync -a /tmp/gw/ ada:work/s7-genome/gw/
cd ~/work/s7-genome/gw && pnpm install --frozen-lockfile
cp -a ~/work/arb-arbA/h ~/work/s7-genome/h
mkdir -p ~/work/s7-genome/scripts && cp -p ~/work/arb-arbA/scripts/*.mjs ~/work/s7-genome/scripts/
cp -a gw gwfix && cp ~/work/arb-arbA/gw/src/walkReader.ts gwfix/src/walkReader.ts

# input inventory and windows
./inventory.sh ~/work/genome3/hprc-v2.1-mc-grch38.GRCh38.walks.bed.gz res/inv.grch38
./inventory.sh ~/work/genome3/hprc-v2.1-mc-chm13.CHM13.walks.bed.gz res/inv.chm13
node windows.mjs res > win/windows.jsonl
for g in grch38 chm13; do grep "\"genome\":\"$g\"" win/windows.jsonl > win/windows.$g.jsonl; done

# format 6 through graph-walks 5.0.2
for g in grch38 chm13; do systemd-run --user --scope -q -p MemoryMax=16G -p MemorySwapMax=0 node f6.mjs win/windows.$g.jsonl res/f6.$g.jsonl; done

# S7 conversion and release checks
./build.sh grch38 ~/work/genome3/hprc-v2.1-mc-grch38.GRCh38.walks.bed.gz
./build.sh chm13 ~/work/genome3/hprc-v2.1-mc-chm13.CHM13.walks.bed.gz

# S7 windows, structure, extents
for g in grch38 chm13; do
  systemd-run --user --scope -q -p MemoryMax=16G -p MemorySwapMax=0 node s7win.mjs win/windows.$g.jsonl res/s7.$g.jsonl
  node structure.mjs out/$g > res/structure.$g.json
  node extents.mjs out/$g
done

# cut checks (graph-walks 5.0.2, then the fix on the differing windows)
for g in grch38 chm13; do BASELINE=units node --max-old-space-size=16000 cutcheck7g.mjs $g win/windows.jsonl res/cut.units.$g.jsonl 4; done
BASELINE=units node --max-old-space-size=16000 cutcheck7g-fix.mjs grch38 win/windows.jsonl res/cut.units-fix.grch38.jsonl 4
node diffwindows.mjs chm13 res/cut.units.chm13.jsonl win/windows.jsonl > win/chm13-units-diff.jsonl
BASELINE=units node --max-old-space-size=16000 cutcheck7g-fix.mjs chm13 win/chm13-units-diff.jsonl res/cut.units-fix.chm13-diff13.jsonl 1
node --max-old-space-size=16000 cutcheck7g.mjs grch38 win/windows.jsonl res/cut.shipped.grch38.jsonl 4
node --max-old-space-size=16000 cutcheck7g.mjs chm13 win/windows.jsonl res/cut.shipped.chm13.jsonl 8
node diffwindows.mjs grch38 res/cut.shipped.grch38.jsonl win/windows.jsonl > win/grch38-shipped-diff.jsonl
node diffwindows.mjs chm13 res/cut.shipped.chm13.jsonl win/windows.jsonl > win/chm13-shipped-diff.jsonl
node --max-old-space-size=16000 cutcheck7g-fix.mjs grch38 win/grch38-shipped-diff.jsonl res/cut.shipped-fix.grch38-diff.jsonl 1
RANGES=1 node --max-old-space-size=16000 cutcheck7g-debug.mjs chm13 win/chm13-shipped-diff.jsonl res/cut.shipped-fix.chm13-diff.jsonl 1
node whereSteps.mjs ~/work/genome3/hprc-v2.1-mc-chm13.CHM13.walks.bed.gz 'CHM13#0#chr14' 13000000 13500000 'NA19185#2#CM087748.1' 57367106,57367108,57368286,57367129

# tables
node summarize.mjs res > res/summary.md
```

Disk: `out/` holds 9.2 GB. The intermediate `o`, `s`, `dep` and `depu` files can be deleted; the S7 pair is 3.4 GB.
