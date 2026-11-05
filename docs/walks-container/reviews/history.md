# Walk file design review: history and container mechanics

Reviewer: history. Lead angle: why format 6 files chunks the way it does,
and what the container really fetches. Everything here was measured on the
shipped 3.0.0 files (`~/work/rel3/mc22.GRCh38.walks.bed.gz`, 59.2 MB, and
`pggbY.GRCh38.walks.bed.gz`, 192 MB), re-filed row for row. Where a number
is an estimate, the text says so.

## Short answer

- The 1 bp interval is not where the bytes go. Re-filing the same rows at
  their chunk's real span, under every index tried, never fetches fewer
  bytes than 1 bp filing once the reader reads the same chunks
- The bytes go to three things the format and its readers do around the
  interval:
  - **The reader always reads the chunk before the window.** That's one
    extra whole chunk per window on Minigraph-Cactus (MC), which only
    needs `maxnode` = 1,024 bp of lookback
  - **@gmod/tabix reads a BGZF block past the data.** It fetches beyond
    each chunk's last block, so about 30 KB per read holds no row
  - **BGZF blocks ignore chunk boundaries.** Each read starts and ends
    mid-block
- Fixing those three cuts a 1 kb window on MC chr22 from 96 KB to 36 KB at
  the median (−62%), and 10 kb from 101 to 40 KB. The fixes are a graph-walks
  query rule, a one-line @gmod/tabix change and a writer change to where
  BGZF blocks end. The rows don't change, and the file shrinks by 0.1%
- On pggb chrY the walk read is small (25 KB median) and the filing barely
  matters. The departure read dominates there: 1 MB median for a 1 kb
  window, and 30% of random windows exceed graph-walks' 2 MB departure
  budget, so the reader refuses them

## What drove the current design (history)

- **2026-10-08, 10d3ae1:** the first `--walks` filed every row at its
  chunk's whole span, `cs cs+chunk`
- **Same day, 3953bb1:** changed that to `cs cs+1`. The commit message is
  the whole rationale: "A full-chunk interval shares a 128 kb Tabix bin
  with the neighbouring chunk, so a query pulled both." No measurement was
  recorded. 842a19b copied the sentence into the README, and the format 6
  spec still carries it today
- **Also 842a19b:** "A reader fetching a window therefore queries from the
  start of the chunk before the window." So the one-chunk lookback started
  as a consequence of the 1 bp key (round down to a chunk start), plus a
  guard for pieces that reach past their chunk
- **The lookback then grew roles:**
  - ADR 0001/0003: the stay guard admitted reference nodes "in the piece's
    chunk or the next" (21f498e, 1cffbd8), so a window had to read the
    chunk before
  - ADR 0003 added `#long` lines so pggb's 1 Mb N nodes would not force
    16-31 chunks of lookback
  - graph-walks documents it as "the chunk before carries the detour a
    haplotype takes into the window's first reference node"
  - 3d9889a (graph-walks 5.0.1) moved it to the drawn stretch's start
- **Format 6 (ADR 0009) removed the reason the guard needed it:** a stay
  can no longer absorb a node the reference passes once, so a piece's steps
  on R lie in its own chunk. The spec's own invariant puts a chunk's
  content inside `[cs, cs + chunk + maxnode)` plus `#long` passes. The
  one-chunk lookback stayed anyway
- **ADR 0009 tied departure-record blocks to TBI's bin sizes**
  (2^26/2^23/2^20/2^17), so the departure filing assumes a TBI-shaped index
- **Alternatives tried before:** whole-chunk span (10d3ae1, replaced the
  same day without numbers), chunk sizes (none recorded), CSI (only for
  contigs over 512 Mb), and 16 kb against 64 kb departure blocks
  (`docs/departures/results/blocks-and-index.txt`). None measured the
  lookback itself or what the client actually fetches

## Diagnosis, with measurements

Method (scripts in `scripts/`; all on the same 300 windows per size,
uniform over MC chr22 10.51-50.79 Mb, seeded):

- `refile.py`: re-files the shipped rows under another interval, with
  optional BGZF blocks ending at chunk ends, and re-cuts departure blocks
  at other bin sizes. At TBI sizes it reproduces the writer's departure
  rows exactly (31,239 rows, same set)
- `fetch-gmod.mjs`: graph-walks 5's two reads per window through
  @gmod/tabix 3.13.1 (`getLines`), cache cleared per window, counting every
  `read()` the filehandle sees. In a browser each one is one HTTP range
  request. It also simulates graph-walks' attach fetches from the
  departure rows
- `fetch-htslib.py`: the same reads with htslib 1.24's `tabix` under
  strace, counting reads and seeks on the data file's descriptor
- `reader-check.mjs`: graph-walks' own `WalkReader.cutRegion` on 240
  windows, as released and with the narrower read, comparing what a
  viewer gets
- `chunk-bytes.py`: the compressed bytes of each chunk

### Is the 1 bp interval a misuse, and does the bin-sharing claim hold?

Walk read only, @gmod/tabix vs htslib, MC chr22, median KB (1 kb / 10 kb /
100 kb / 1 Mb windows). Every row here reads the same chunks except D/E:

| filing, index, query | @gmod/tabix | htslib |
|---|---|---|
| A0 shipped: 1 bp, TBI, from the chunk before | 88 / 89 / 129 / 549 | 66 / 70 / 109 / 529 |
| B: chunk span, TBI, from the chunk before | 120 / 127 / 156 / 587 | 68 / 71 / 112 / 536 |
| C: chunk span, CSI min_shift 16, from the chunk before | 89 / 89 / 131 / 560 | 67 / 70 / 112 / 535 |
| D: span + maxnode (correct for any overlap query), TBI, plain overlap | 290 / 320 / 339 / 768 | 43 / 47 / 91 / 514 |
| E: same as D, CSI min_shift 16 | 346 / 339 / 361 / 796 | 186 / 175 / 216 / 629 |

- **The bin-sharing claim holds for @gmod/tabix and not for htslib.**
  Span filing under TBI costs +35% at 1 kb with @gmod/tabix (B against A0),
  because the reader fetches each 128 kb bin's whole byte range. htslib
  reads the same rows for +2%, because it starts at the linear index's
  floor and stops at the first row past the window. The claim was never
  tested against either client
- **What 1 bp buys:** with TBI, each chunk gets a 16 kb leaf bin of its own.
  A CSI index with `min_shift` = log2(chunk) = 16 gives the same to
  real-span rows (C = A0, and the index is 19 KB instead of 40 KB)
- **What 1 bp costs:**
  - Bytes: nothing measurable
  - Correctness for generic tools: `tabix file chr22:15000-16000` returns
    nothing unless the window holds a chunk start. Span filing returns the
    chunk, but still not a correct answer: that also needs the `maxnode`
    margin, the departure read and the attach fetches. So span filing
    reads better to generic tools without making them correct
  - It reads as a misuse because the interval is a key, not an extent. It's
    a legitimate use of Tabix as a sorted key index, but the spec should
    say so
- **Filing honest extents is the real trap.** Rows filed over everything
  they describe (D/E) cross bin boundaries: 3.3× the bytes on @gmod/tabix
  under TBI, and 2-4× on both clients under CSI, which has no linear
  index. The project met the same mechanism in the node/link index's wide
  intervals (9e9c369)

### Where the bytes actually go

Window total (walk + departure read), median / p90 / p99 KB:

| variant | 1 kb | 10 kb | 100 kb | 1 Mb |
|---|---|---|---|---|
| A0 shipped, graph-walks 5 rule | 96 / 146 / 324 | 101 / 158 / 324 | 142 / 212 / 411 | 564 / 758 / 1479 |
| Am: same file, read from the chunk holding drawn start − maxnode | 64 / 112 / 194 | 70 / 116 / 234 | 115 / 173 / 326 | 544 / 733 / 1486 |
| Fmp: Am + blocks end at chunk ends + @gmod/tabix stops at `maxv` | **36 / 68 / 169** | **40 / 78 / 191** | **85 / 133 / 293** | **509 / 688 / 1456** |
| Kmp: as Fmp but span filing, CSI 16, departures cut at CSI sizes | 37 / 66 / 170 | 40 / 79 / 198 | 85 / 133 / 352 | 510 / 695 / 1483 |
| Fm/Km with htslib (no client fix needed) | 35 / 68 / 163 | 38 / 77 / 191 | 85 / 133 / 296 | 510 / 688 / 1460 |

- Requests: 1 walk + 1 departure read per window in every variant (max 2
  seeks per read in E). @gmod/tabix merges chunks, and htslib needs 1 seek
  per read here
- **The lookback (A0 → Am, −33% at 1 kb):** MC's `maxnode` is 1,024, so a
  window needs the chunk before only when its drawn start lies within
  1,024 bp of a chunk start, about 3% of windows. The rule reads it
  always. Median chunks read at 1 kb: 2 → 1
- **The @gmod/tabix over-read:** `Chunk.endPosition` defaults to
  `maxv.blockPosition + 65536`, clamped to the next block boundary the
  index knows. When `maxv.dataPosition` is 0, the last row ends where that
  block begins, and the client still downloads the whole block. On a
  chunk-aligned file that's 30 KB per read with no rows in it, for example
  `14189485:0..14271821:0` fetched to 14302511. The one-line fix,
  `endPosition = maxv.dataPosition === 0 ? maxv.blockPosition : …` in
  `chunk.js`, returned identical rows on all 1,200 windows. It does
  nothing for files whose blocks straddle chunks, so it needs the writer
  change
- **The BGZF alignment:** ending a block at each chunk end changes the
  file by −0.09%, and reads become exact: 28 KB is the median compressed
  MC chunk (`chunk-bytes.py`: 776 chunks, median 25.9 KB, p90 39.6, p99
  120, max 300 KB). The main sequence's chunks total 19 MB of the 59 MB
  file. Detail records (abridged satellites) are 40 MB and departures
  0.5 MB
- **Fmp vs Kmp:** at this point the interval makes no difference on MC.
  Both are at the floor of a 64 kb-chunk design, one chunk per small window

### Is the narrower read correct? (graph-walks' own reader)

`reader-check.mjs` ran `cutRegion` with a contained cut on 240 windows:
every haplotype for 1-100 kb, five samples at 1 Mb. It compared the walks
(steps by node, strand, length and placed position) and the departures
(with their own steps):

- 232 of 240 identical
- One window failed with NodeLimitError on both reads
- The other 7 are all in 22q11 (22.60-22.84 Mb). In every one, one record
  differs: NA18945#1's 580 kb jump, 22,322,969 → 22,903,368, with 3,743 bp
  of its own. The narrower read attaches that record's own steps and the
  released read doesn't. Likely cause (not confirmed): graph-walks caps
  attach fetches at 8, and the two reads want different sets of leave
  chunks
- Separate finding: in the 240-window batch, the released reader's output
  for two of these windows (22,837,844 and 22,609,406) differed from its
  output for the same windows run alone (digests 4f7ddc/29cd23 and
  419448/9ead33). The narrow read was stable. Something in the released
  path depends on process state; I didn't run down whether @gmod/tabix's
  shared read cache or attach ordering causes it
- Real reader bytes agree with the simulation: median 103 → 69 KB at 1 kb,
  110 → 81 at 10 kb, 155 → 126 at 100 kb (unaligned file, no client fix)

### Attach fetches: the p90 driver on MC

A departure record whose leave piece lies in a chunk the walk read did not
decode triggers a second, sequential read. That covers 15-22% of MC windows
(45-66 of 300), up to 8 fetches, each 2 chunks under the released rule.
With them included (same windows, `with-attach-summary.txt`):

- A0 shipped: 98 / 439 / 1030 KB (median/p90/p99) at 1 kb, up to 9
  requests
- Fmp: 37 / 220 / 833 KB, up to 10 requests. The narrower read adds a
  second round trip on only 1-3 windows in 300
- Attachable records on MC chr22: 18,793 of 24,648, with 37.8 Mb of own
  sequence, about 5.5 M steps at 6.8 bp per off-reference node. Copying it
  into the records would be large (estimate, not built), so I leave this
  as the next lever, not part of the proposal

### Chunk size (the same writer, `--chunk`, MC chr22)

Same fixes applied (aligned blocks, narrow read, client fix). Total KB
median / p90:

| chunk | file | 1 kb | 10 kb | 100 kb | 1 Mb | departure records |
|---|---|---|---|---|---|---|
| 16 kb | 70.7 MB (+19%) | 32 / 59 | 40 / 67 | 123 / 173 | 1005 / 1171 | 93,166 |
| 32 kb | 62.3 MB (+5%) | 28 / 52 | 41 / 62 | 91 / 131 | 665 / 841 | 46,889 |
| 64 kb | 59.2 MB | 36 / 68 | 40 / 78 | 85 / 133 | 509 / 688 | 24,648 |

- 64 kb is the right size once the fixes are in. 32 kb saves 8 KB at 1 kb
  and loses 31% at 1 Mb; 16 kb loses on file size and at 100 kb and up.
  Smaller chunks repeat R and the routes and split departures across
  pieces

### pggb chrY

Walk read with the released rule, median / p90 / p99 KB at 1 kb:

- Y0 shipped: 25 / 116 / 957
- YB span TBI: 39 / 170 / 1576
- YJ span CSI 16: 25 / 116 / 969

The departure read is 965 KB median at 1 kb, 1.75 MB at 1 Mb. 89 of 300
windows at 1 kb (114 at 1 Mb) exceed graph-walks' 2 MB departure budget,
from 77 k (median) to 234 k (p90) record rows. Simulated attach fetches
hit the 8-fetch cap in every window (an estimate: 11 requests, about
2.5 MB).

- **Cutting departure blocks at CSI 16 sizes costs pggb:** +10% at 1 kb,
  +34% at 1 Mb, because more blocks per record means more duplicate rows
  read. That is the one measured cost of moving to span + CSI
- `maxnode` on pggb is 1 Mb with `#long` lines, so the narrower read only
  helps pggb if the writer states how far non-`#long` nodes reach
  (proposed `reach` below). Without it, the margin is a chunk, the same as
  today

## Ideal design

Keep fixed 64 kb chunks, the row encoding and Tabix. Change how chunks sit
in BGZF, the read rule, and the spec's rationale.

### Record layout

- Rows as format 6 writes them: `ref`, `nodes`, `route`, `walk`, `abridged`
  per chunk; departures under `seq~departure`; detail records under
  `seq~cs`
- Keep the key interval `seq cs cs+1`. The spec should name it a chunk key,
  not an extent, and give the honest reason: one 16 kb TBI leaf bin per
  chunk. A full-chunk interval shares a 128 kb bin, which @gmod/tabix reads
  whole (+35% at 1 kb), and an interval over a chunk's real extent crosses
  bins (3.3×)
- New header tag `reach:i:<bp>`: the furthest any chunk's rows place a step
  past `cs + chunk`, `#long` passes aside. The writer knows this when it
  cuts. MC: ≤ 1,024; pggb: whatever its longest non-`#long` node is. A
  missing tag means a whole chunk, today's rule
- The writer checks the invariant at build time ("no row places a base
  past `cs + chunk + reach`, except `#long` passes and departure
  stretches"), as it already decodes every row

### Container

- Bgzipped text with a TBI index, as now
- The writer ends a BGZF block at every chunk end (and where a sibling
  sequence starts), so each chunk is a whole run of blocks. File −0.09%;
  BGZF and Tabix stay valid for every tool
- Departure blocks stay at TBI sizes
- Why not span + CSI 16 (Kmp)? Same bytes on MC, a 20 KB smaller index,
  and a generic `tabix` returns the chunk under a window. Against it:
  pggb departure reads grow 10-34%, JBrowse tracks need `"csi": true`,
  and a CSI index has no linear index, so any wide row added later costs
  2-4× on both clients (E). The 1 bp key wins on evidence. I'd switch only
  if generic-tool legibility is worth those costs to the user
- Why not another container (custom block index, bigBed R-tree, Parquet,
  GBWT)? Every variant here already makes 1 request per read and, once
  blocks are aligned, fetches exactly the chunk bytes. That's what a custom
  chunk-offset table (776 × 8 bytes) would give. bigBed and Parquet have
  the same request pattern with worse tooling. The repo's own comparison
  measured gbz-base (SQLite) at 18-43 round trips per window. The
  remaining costs, the chunk floor and the departure and attach reads, are
  in the record design, not the container
- Walks and `.graph.bed.gz`: keep them separate. They serve different
  readers (the index serves non-walk graphs, the coarse tier and carriers).
  open-problems.md measured a walk-file view at about a third of the
  index's bytes on chr22, so the walk view doesn't need the index for
  drawing. I didn't measure a merge

### Query procedure for a window [s, e) on sequence S

- drawn = [s − context, e + context), context 1,000 as graph-walks has
- Walk read: `getLines(S, from, drawn.end)`, where `from` is the start of
  the chunk holding `drawn.start − reach` (rounded down to a chunk start,
  since rows carry chunk keys). If the window overlaps a `#long` pass, read
  from the start of that pass's chunk instead. One request
- Departure read, in parallel, as now: `S~departure` over
  [s − context − maxnode, e + context + maxnode). One request
- Attach fetches as now, each for the leave chunk alone:
  `[chunk(base − reach), base + 1)`
- Rebuilding paths is unchanged: graph-walks' decode, `joinPieces`,
  `walkCut`

## Tradeoffs and failure modes

- **The read rule rests on a writer invariant** (`reach`). If a future
  placement change files a step further out, windows silently lose it. The
  build-time check guards that. Without the tag, readers keep the one-chunk
  rule, so old files stay correct
- **Attach fetches rise** from 0.47 to 0.64 per window on MC. A second
  round trip is new on 1-3 windows in 300. p99 bytes still fall, from 1030
  to 833 KB at 1 kb
- **The @gmod/tabix fix** is needed for the bytes on the browser side.
  Without it, aligned blocks plus the narrow read give 58 KB, not 28 KB,
  at 1 kb. htslib needs no change
- **Repeats and inversions:** nothing here changes placement. On pggb, a
  generous `reach` keeps today's behaviour exactly
- **Long nodes:** handled by `#long`, as today
- **Huge chunks** (satellites, up to 300 KB compressed on MC): unchanged;
  abridged detail records still keep them out of window reads
- **Generic tools:** a plain `tabix` query still returns nothing for a
  window that holds no chunk start. The spec should give the generic recipe
  (`tabix file S:cs+1-cs+1` per chunk key), and say that no plain overlap
  query is a correct walk read in any filing
- **pggb's departure read** (1 MB median, 30% of windows over budget) is
  untouched by any of this and is the largest open cost on pggb

## Verdict

- The 1 bp chunk key is not a hack that costs downloads. Filing chunks at
  their real span saves nothing in any configuration measured. The one
  filing a generic overlap query would get right (real extent) costs 3.3×
  under TBI. Keep `seq cs cs+1`, and rewrite its rationale in the spec as a
  chunk key that gives each chunk its own TBI leaf bin. That claim is true
  for @gmod/tabix (+35% for span filing) and not for htslib
- The design's real excess is the one-chunk lookback, a day-one consequence
  of the 1 bp key that format 6 no longer needs on MC. With @gmod/tabix's
  over-read past `maxv` and chunks that start mid-block, it's 60% of a
  small window's bytes. Fix all three: 96 → 36 KB at 1 kb, 101 → 40 at
  10 kb, 142 → 85 at 100 kb, 564 → 509 at 1 Mb (MC chr22, median). Same
  rows, same requests, file −0.1%
- Keep fixed 64 kb chunks (16 and 32 kb measured worse overall) and keep
  Tabix (already 1 request per read, and exact bytes once aligned). Keep
  walks and the node/link index separate
- Smallest first step: in graph-walks, read from the chunk holding
  `drawn.start − maxnode` when `maxnode` ≤ chunk and the file has no
  `#long` line, otherwise keep today's rule. It needs no format change. On
  the shipped MC files it takes a 1 kb window from 96 to 64 KB (−33%), and
  graph-walks' own reader gave the same cut on 232 of 240 windows; the 7
  differences all gain one departure's own steps. Then end BGZF blocks at
  chunk ends in the writer, fix `Chunk.endPosition` in @gmod/tabix, and add
  `reach:i:` so pggb benefits too
- Next, outside this angle's scope: on MC the p90 comes from attach
  fetches; on pggb, departure reads put 30% of chrY windows over budget.
  Those are record-design questions, not container ones

## Files

- `scripts/refile.py`, `fetch-gmod.mjs`, `fetch-htslib.py`,
  `reader-check.mjs`, `chunk-bytes.py`, `chunks-for.mjs`, `summarize.py`
- Results: `gmod*.jsonl` (@gmod/tabix; `gmod-summary.txt`,
  `gmod2-summary.txt`, `gmodY-summary.txt`, `with-attach-summary.txt`),
  `htslib*.jsonl`, `reader-check.jsonl`
- `patched/x/tabix`: @gmod/tabix 3.13.1 with the one-line `chunk.js`
  change
- ada `~/work/review-history/`: `chunks.sh` and the 16 kb and 32 kb chunk
  builds (3.0.0 binary)
- Variant files (A-K, YB, YJ) were deleted to free the shared tmpfs.
  `refile.py` rebuilds any of them from the shipped file in about a
  minute, as its usage line says
