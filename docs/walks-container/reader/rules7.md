# Walk format 7's reader rules against graph-walks 6

The reader rules of [walks-format.md](../../walks-format.md) at `af005be`,
each against graph-walks 6 at `7f9fcc6` (branch `format7-reader`): the code
that implements it, the test that fails when it breaks, and a status.

- **Spec lines** are line numbers in `docs/walks-format.md` at `af005be`
- **Code** is `src/<file>:<line>` in graph-walks `7f9fcc6`
- **Test** is a test in `src/walkReader.test.ts` unless named otherwise,
  found by breaking the code (`scripts/rules7-mutate.py`, output in
  `results-rules7/mutants.txt`): a test listed fails on the mutant; "none"
  means every test passed with the rule broken
- **Status:** tested, implemented only (no test fails when it breaks),
  different (the code does something else), missing

## The rules

| Rule | Spec | Code | Test | Status |
|---|---|---|---|---|
| Refuse a directory whose line 1 is not `#walks`, or states a format other than 7 | 257, 286, 539 | walkFile.ts:71-82 | "a walk file whose directory states …", "a format %i walk file is refused", "a file that is not a directory is refused" | tested |
| Refuse when the directory's line 1 differs from the header's `#walks` line | 257-258, 540-541 | walkFile.ts:187-190 | "a directory and data that disagree are refused" | tested |
| Refuse when `bytes` differs from the data's length | 258-259, 541-542 | walkFile.ts:191 | same | different: skipped when the length is unknown (`stat()` gives 0 where CORS hides Content-Range) |
| GET the header unit and the sequence's table in parallel, after the directory | 540 | walkReader.ts:370-373 | none | implemented only |
| Select `tile` and `departures` units by `start < D.end`, `end > D.start` | 543-544, 224-225 | walkReader.ts:157-158, 375-379 | "a node longer than a tile is read from the tile whose extent holds it", "a cut reads the tiles and departure blocks its window overlaps …" | tested |
| D is the window widened by context on both sides | 536 | walkReader.ts:164-170, 375 | "a cut reads the chunks under its context, not only under its window" | tested |
| Skip units of length 0 | 544 | walkReader.ts:158, walkFile.ts:255 | "a table entry of length 0 is never read" (holds through either guard) | tested |
| Merge byte ranges that touch; one single-range GET each | 545-546 | walkFile.ts:253-266 | "a cut reads the tiles and departure blocks … in one read where they touch" | tested |
| Gunzip each unit alone; every unit starts with `#unit` | 199, 207-208, 547 | walkFile.ts:274-284 | none for the `#unit` refusal | implemented only |
| Readers scan a table; a sequence with no units has only its `#unit` line | 242-244 | walkFile.ts:217-246 | none for the empty table | implemented only |
| Keep the departure lines overlapping D | 548 | walkReader.ts:193-197 | none (walkCut's later filter hides the mutant) | different: walkCut filters again (below) |
| Drop exact duplicate departure lines | 522-523, 548 | walkReader.ts:191 | "a cut lists each departure over the window …" and 8 others | tested |
| The read gives every departure over D, each once | 556-561 | walkRows.ts:515-587, 641-679 | "a departure between the pieces of one run comes from the records, not the steps" (walkRows.test.ts) | different: drops records over D where no reference node lies on D; adds computed departures far outside D |
| Compute departures only between consecutive steps of one piece | 559-561 | walkRows.ts:527-529 | 13 tests | tested |
| Attach fetch: for a record whose own steps the window holds no piece of, read the tiles `ownTiles` names | 524-526, 549-550, 85-87 | walkReader.ts:173-177, 572-594; walkRows.ts:641-675 | "a cut reads the tiles … and fetches the tile holding a leave base", "a jump back whose own steps lie in the rejoin piece …" | tested, but see the next three rows |
| …and take the own steps those tiles hold | 525-527, 550 | walkReader.ts:589-593 decodes the fetched tile for the record's walk | none | different: every piece of the walk in the fetched tile joins the fragments |
| …a 0 bp own step is an own step, so a record with `ownBp` 0 can name a tile | 527-528 | walkRows.ts:643 `d.ownBp > d.missingBp` | none (mutant m31 survives) | missing |
| …within limits the spec doesn't give | — | walkReader.ts:52, 583; walkDeparture.ts:43 | "a leave piece the read lacks is fetched …, within the fetch cap", "a record over the attach threshold carries no steps" | unstated (see below) |
| Skip an attach fetch of a tile already decoded for the record's walk | 86-87 | walkReader.ts:411-413, 578 | "a cut reads the tiles … fetches the tile holding a leave base", "a walk leaving the window is cut there …" | tested |
| An abridged piece in an attach-fetched tile stays abridged | 528-532, 550 | walkReader.ts:479 | "an attach fetch reads an abridged piece's own steps where the cut expands the walk" | tested |
| An attach fetch reads no `detail` unit | 87, 627-629 | walkReader.ts:479-484 | same | different: it reads one for a walk `expand` names |
| Expand an abridged piece by reading `detail` unit `cs:d`, decoded against tile `cs`'s R | 452-454, 552-553, 630-632 | walkReader.ts:492-520; walkChunk.ts:520 | "an expanded walk is read from its detail records as the unabridged file cuts it" | tested |
| `nsteps` bounds a reader's work on a detail record | 449-451 | walkRows.ts:1010-1013 counts an abridged row as 2 steps; the detail is read and decoded before `stepBudgetError` | none | missing |
| Address tiles by extent, never `floor(base / tile)` | 224-225 | walkReader.ts:376 | "a cut lists each departure …", "a node longer than a tile …" | tested (the budget messages still step by `floor`, walkRows.ts:1143) |
| A 0 bp unit's extent is the base beside `p` | 226-231 | walkReader.ts:157-158 (generic overlap) | none (no fixture) | implemented only |
| No chunk-before rule, `maxnode`, `#long` or reach | 309-310, 554-555 | absent | "a cut reads the tiles its window overlaps, and nothing else" | tested |
| Key a piece by `path`, `fragStart`, `piece`; join consecutive pieces | 105-107 | walkRows.ts:164-194 | "continuation rows join by piece index, and a missing piece splits the walk" (walkRows.test.ts) | tested |
| Key an abridged row as a walk row | 431-433 | walkRows.ts:168-171 | "an abridged walk cuts to a fragment …" | different: an abridged piece is never joined to its neighbours and has no links to them (walkChunk.ts:876-897 takes no abridged ends) |
| Place a node from a `ref` row of a tile read: the path sorting first, at its earliest start | 142-145 | walkRows.ts:746-752 | path order: none (m18 survives); pass over the window: "a node's pass over the window wins …" (walkRows.test.ts) | different: a pass over the window outranks the earliest start |
| Never choose a pass; take each step's position from the row | 137-138 | walkChunk.ts:359-408 | indirect | tested |
| Lists the haplotypes from the header without reading a tile | 43 | walkRows.ts:100-121 | "the header names the format, the reference, the haplotypes and the tile size" | tested |
| Ignore `stay`, `abridge`, `abridgebytes`, unknown tags | 293-300 | walkRows.ts:100-121; walkChunk.ts:446-463 | none | implemented only |
| A row or unit kind the page doesn't give is another format | 286-288 | decodeChunk and `cut` ignore unknown kinds | none | different, and the spec contradicts itself: 299-300 says later additions are unit kinds |
| `#hole`s removed before comparing breakpoints | 304-308, 484-486, 496 | walkDeparture.ts:47-79; walkReader.ts:568 | `squeezer` alone: "steps either side of a hole in the reference are adjacent" (walkDeparture.test.ts); the cut's wiring: none (m20 survives) | implemented, wiring untested |
| A departure with an end passed more than once is a placement choice | 186-189 | walkDeparture.ts:121-125 | "a departure is a placement choice …" (walkDeparture.test.ts) | tested |
| Split a token by rounding down (`-5` is −3, reverse) | 334-336 | walkChunk.ts:39-61 | 18 tests | tested |
| R is the `ref` rows joined in `hapOffset` order | 354-358 | walkChunk.ts:526-527 | none (m11 survives) | implemented only |
| `passes` `.` is every step 1; a count per step | 350-353 | walkChunk.ts:74-87 | "a ref row whose passes do not count its steps is refused", 41 tests | tested |
| Route tokens chain across columns and rows from 0 | 385-387 | walkChunk.ts:576, 643-647 | 4 tests | tested |
| A route's flip | 389-391, 637 | walkChunk.ts:206-216 | 19 tests | tested |
| A first route with no entry emits its interior first | 641 | walkChunk.ts:280-289 | "a jump back whose own steps lie in the rejoin piece …" | tested |
| `start@k` | 409-411, 642-643 | walkChunk.ts:291 | none (m14 survives) | implemented only |
| `:k`, else the first position from the current one holding the entry | 411-414, 645-647 | walkChunk.ts:167-186, 299-316 | default: 8 tests; `:k`: none (m12 survives) | default tested, `:k` implemented only |
| `@k`, else the occurrence nearest the entry's position, the later on a tie | 414-416, 650-652 | walkChunk.ts:142-163, 335-339 | none for `@k` (m13) or the tie (m9) | implemented only |
| After the last route, follow R the way the step reads it until `nsteps` | 420-422, 653 | walkChunk.ts:343-354 | "a cut's drawn stretch takes every pass over the window …" | tested |
| An abridged row's `end@k`, else nearest `start`, the later on a tie | 434-437 | walkChunk.ts:488-496 | none (m15 survives) | implemented only |
| An abridged row's stretch is `hapOffset` to `hapOffset + bp` | 439-443 | walkRows.ts:448-466 | "an abridged walk cuts to a fragment …" | tested |
| `WalkReader.fromFilehandles({ data, table })` | 724 (and ADR 0010 line 284) | walkReader.ts:242-250 takes `{ data, directory }` | "a format 6 file …", every `reader()` | different (being fixed on `format7-tidy`; ADR 0010 line 284 names `table` too) |
| graph-walks 5 refuses a format 7 file | 724-725 | 5.0.2 opens a `TabixIndexedFile`, so a format 7 file fails on its missing `.tbi`, before any format check | — | different: it fails, not refuses |

The `:k`, `@k` and `start@k` rows have no unit test, though pggb chrY's
GRCh38 file uses them on 47,017, 109,697 and 86,274 of its 471,098 walk
rows, and `end@k` on 42,301 of its 110,886 abridged rows. Only the
real-data cut check on ada (`cut7check.mjs`, `results-r1/`) would catch a
break.

## Failing inputs

`scripts/rules7-probe.test.ts` runs each in graph-walks' test tree. The
output is in `results-rules7/probe.txt`.

- **An attach fetch adds a walk's whole piece to its fragment.** Tiles of
  16 bp, H `>5>6>7>11>13>12>14>6>7>8` with pieces in tiles 16, 32 and 16. A
  cut of 20-28 reads tile 16. The record 48→20 names tile 32, so the cut
  fetches it, decodes H there, joins pieces 0, 1 and 2 into one run, and
  returns one fragment `>6>7>11>13>12>14>6>7` and a computed departure at
  44, outside D. With `attachFetches: 0` the cut returns two fragments and
  no departure at 44
- **A walk's fragment depends on the other walks the cut keeps.** In the
  same file, G's record names tile 0 and comes first in the block. With
  `attachFetches: 1`, a cut keeping every walk fetches tile 0 and returns
  H as two fragments. A cut keeping R and H fetches tile 32 and returns H
  as one. The graph-walks README says a fragment "does not depend on which
  other walks the cut keeps"
- **A 0 bp own step is never attached.** G `>5>6>9>1>2`, node 9 of 0 bp,
  whose record has `ownBp` 0 and `ownTiles` 16. Cuts of 0-8 and 0-32,
  which read tile 16, both return the record with no steps
- **A window inside a hole loses the record over it.** R's lines are
  0-8 and 40-48, with `#hole R#0#chr 8 40`, and H `>1>4` has the record
  0-48. A cut of 16-24 reads block 16, which holds the line, and returns no
  departure. No reference node lies on D, so `windowStart` is Infinity and
  walkRows.ts:676 drops every record
- **`referenceNodes` gives one pass per node.** On `loop.R`, 0-36 gives
  `2@6-12` and `3@12-18` and leaves out their passes at 18-24 and 24-30.
  The JBrowse plugin calls it (RgfaTabixAdapter.ts:151). This is R1's
  pattern, in a function the R1 fix didn't touch

## On real data

From `scripts/rules7-attach-cap.mjs` on ada, 100 windows each (outputs in
`results-rules7/attach-cap.tar.gz`), and `scripts/rules7-far.py` over the
p3 harness outputs, which lift the fetch cap (`results-rules7/far-fromsteps.txt`):

- MC chr22 100 kb at 18,159,911: HG01175#1's fragment runs 18.17 to
  20.36 Mb, 5,398 steps, through tile 20,316,160, which the attach fetch
  read for its record leaving at 20,355,358. The cut returns 452 computed
  departures at 20.32 Mb, and none of the records between pieces there,
  which the departure read over D never fetched
- pggb chrY, cap lifted: fragments hold 183,381 steps more than a tile
  outside D in 100 kb windows, and the cut returns 10,089 computed
  departures there in 9 windows. With the default cap of 8, or no attach
  fetch, the far steps are 62 and the far departures 0
- pggb chrY: the fragments differ between the default cap of 8 and no cap
  in 10 of 100 windows at 100 kb and 1 of 100 at 1 kb. MC chr22 1 kb: no
  difference
- Most windows have computed departures up to 1 kb outside D: 69 of 100
  at MC 1 kb, 73 of 100 at MC 100 kb. `walkCut` takes the drawn stretch
  from whole reference nodes over D, not from D

## Links

`canonicalLink` (walkChunk.ts:91-93, from c4ff08d on 2026-10-12, format 1's
links file) writes every link the way round whose first handle, compared
with the second flipped, is smaller. `>7>3` becomes `L 3 - 7 -`, and `>8>6`
becomes `L 6 - 8 -`. bandage-core draws an arrow the way a link is
written, so the figure cuts in `gfa-to-tabix-fig7-r1/docs/figures/*-cut.gfa`
point backwards. The orientation comes from the reader's link building,
not from the writer's route rule (placeAndLink canonicalises a route's
links whichever way the row stores it) or from `scripts/bandage-figure.mjs`,
which writes `tables.links` unchanged. Format 7 has no link rows, so the
spec has nothing to state. graph-walks states the rule in its README and
writes each link with more `+` ends than `−` ends, the smaller first id on
a tie: that is the way every walk running forward along the reference
takes it. Where walks take a link both ways, as at an inversion, no
orientation matches every walk.

## Decisions

- **What a cut returns for an attach fetch:** the record's own steps, and
  nothing else. The fetched tile's pieces must not join the fragments or
  feed the computed departures. Four reasons:
  - It is what lines 524-527 and 549-550 say
  - It keeps a fragment from depending on `attachFetches` or on the other
    walks kept
  - Line 562's two fragments are the accepted outcome
  - The excursion's records between pieces are never read, so the joined
    fragment shows the far region half-described
  
  `walkCut` already finds the own steps from the leave and rejoin pieces
  (walkRows.ts:641-675). It should take the fetched runs for that lookup
  alone. The 18.16 Mb cut is not what the spec says a cut returns, and it
  is not what a viewer wants
- **D or the nodes over D:** the spec should say the drawn stretch is the
  reference nodes over D, whole, as `walkCut` and every viewer draw it. The
  record filter should keep a line overlapping D when no node lies on D, as
  in a hole
- **Node placement:** the spec should give the code's rule, since the
  2026-10-30 fix (9e89077) was made for a real failure: a pass over the
  window, then the path sorting first, at its earliest start
- **0 bp own steps:** graph-walks should attach them, as W1 decided: gate on
  `ownTiles` or on the steps, not on `ownBp > missingBp`
- **`nsteps`:** graph-walks should check the detail rows' `nsteps` against
  `stepBudget` before reading them, or the spec should drop the sentence.
  The first, since the README already says expansion counts against the
  step budget
- **`bytes` with no known length:** the spec should say a reader that
  can't learn the length skips the check, and the README should say a
  server must expose Content-Range for it to hold
- **Unknown kinds:** line 287 should say only that a row kind or placement
  rule the page doesn't give is another format. Unit kinds are an
  extension point (line 300), which readers skip
- **Abridged pieces stand alone:** the spec's line 431 should say an
  unexpanded abridged row is its own fragment, not joined to the pieces
  beside it

## Unstated behaviour and where it belongs

- **README, cut options (most already there):**
  - `context` 1000
  - `stepBudget` 4,000,000, with rows read up to 8× it before keeping
    (`READ_STEPS_PER_KEPT`, not in the README)
  - `byteBudget` 8 MB on tiles only
  - `departureByteBudget` 2 MB
  - `attachBp` 65,536
  - `attachFetches` 8
  - `nodeLimit` Infinity
  - `contained`, `links`, `sequences`, `expand`, `keep`, `budgetNames`
  - Detail reads 16 at once (`DETAIL_READS`)
- **README, wrong today:**
  - "A cut reads the tiles overlapping the drawn stretch, and nothing
    else" leaves out attach fetches
  - "its fragment ends at its last step on the stretch" and "does not
    depend on which other walks the cut keeps" are false while attach
    fetches join pieces
  - "`cut` returns every departure over the drawn stretch" leaves out the
    far computed departures
- **README, missing:**
  - An unattached record whose walk the cut fetches only partly gets the
    steps of the tiles fetched
  - Records with `ownBp` at most `missingBp` are never attached
  - The tiles chosen when the cap binds are the first in record order
  - Attach-fetched rows are not counted against the read step budget
  - Expanded detail records count against `stepBudget` only after
    decoding
- **Package docs (doc comments):**
  - `fromSteps` departures take their ends' passes from the ref rows the
    cut read: 0 for a node placed off R
  - A computed departure is kept when its stretch overlaps the nodes on
    D, lies inside a fragment's span, or starts or ends at a fragment's
    edge (walkRows.ts:552-557)
  - `trimmedBefore` and `trimmedAfter` depend on the tiles read
  - `referenceNodes` returns one pass per node
  - `sequenceLength` comes from tile extents
  - The refusals the spec doesn't list:
    - no `tile:i:`
    - no `#header` line
    - a non-integer byte range
    - a table row naming another sequence
    - a unit with no `#unit` line
    - an abridged row naming a missing detail unit
    - format 6 named by `.walks.bed.gz`
- **Spec:** the drawn stretch as whole nodes over D. A record's leave step
  is the last step on R of its piece and its rejoin step the first: line
  444 says so in passing, the reader keys own steps on it, and it belongs
  with the writer's guarantees

## Assumptions the reader makes about the file

| Assumption | Code | Stated | True |
|---|---|---|---|
| Line 1 of the directory is the header's `#walks` line plus `bytes:i:` | walkFile.ts:106, 187 | 256-259 | yes, checked |
| A table's first line is its `#unit` line | walkFile.ts:221 (skipped unread) | 207, 243 | yes |
| Unit offsets are distinct | walkFile.ts:254; walkReader.ts:411 | 571-573 | yes |
| A tile's `name` is its decimal start, unique among tiles | walkReader.ts:175, 473 | 216 | yes |
| Detail names are unique among detail units (a Map, the last wins) | walkReader.ts:422-424 | 216-218, 452-454 | yes (the guarantee limited to names other than `.`) |
| Departure unit names | never read | — | they repeat (block sizes), which costs the reader nothing |
| Departure lines lie in their block | never assumed: each line is filtered by its own `start end` (walkReader.ts:195-196) | the false guarantee at 577-578 | overlap only; the reader is safe |
| A line over D lies in a block over D | walkReader.ts:377-379 | 232-238 | yes, by the cover |
| Every piece over D is in a tile whose extent overlaps D | walkReader.ts:376 | 221-225, 576-578 | yes for tile lines, checked by the writer |
| A record's text is the same in every block | walkReader.ts:191 | 237, 522 | yes |
| A record's leave is its piece's last step on R and its rejoin the first, at `hapStart` and `hapStart + ownBp` | walkRows.ts:593-664 | 444-445, in passing; not among the writer's guarantees | yes, by the placement rules; checked only through `ownTiles` |
| `hapOffset` plus node lengths gives contig positions | walkRows.ts:345-355 | 345-347, 479-480 | yes, given every route node's length in the `nodes` row (366-368) |
| Every walk piece has a step on R (`start` never `.`) | walkChunk.ts:291-294 throws | 403-404, implied | yes |
| A contig's W lines don't overlap, so contig positions identify a fragment's edges without `fragStart` | walkRows.ts:501-507 | 110-111 | yes, refused at build |
| Pieces are numbered consecutively along a W line | walkRows.ts:180-192 | 105-107 | yes |
| An abridged row's `detail` is never `.` | walkChunk.ts:520 | 452 | yes; unchecked, would read as a missing detail unit |
| `ownTiles` present | walkDeparture.ts:178 treats absence as `.` | 459 | yes in format 7; the inline test files omit it |
| The data's length is known | walkFile.ts:191 | 258-259 | not over CORS without exposed Content-Range; then unchecked |

## How each mismatch got in

| Mismatch | Code | Spec | How |
|---|---|---|---|
| Attach fetch joins pieces | `decode` of fetched chunks into `rows`, 43910ec (2026-11-04, graph-walks 5), kept by a6269e4 | "takes the own steps those tiles hold", 99fc07e (2026-11-06) | The spec sentence was written for one question, detail units, by a reader of the fetch's purpose; neither side looked at what the decoded rows do downstream. The format 7 port's "what graph-walks 5 compensated for" list covered the read rules only |
| README's fragment independence | 43910ec | — | Written for the window read before attach fetches joined pieces, and kept through a6269e4 |
| Computed departures outside D | walkRows.ts:552-557, 43910ec | 556-561, 86d1006 (2026-11-05) | The spec was written from ADR 0010's reading rule, not from `walkCut` |
| Records dropped in a hole | `overExtent`, 43910ec | 548, 86d1006 | Same |
| Node placement | 9e89077 (2026-10-30): a pass over the window first | 9cb9317 (2026-10-19), kept through the format 6 and 7 rewrites | The code was changed for a bug and the spec never revisited |
| 0 bp own step | `ownBp > missingBp`, 43910ec | 108bab7 (2026-11-06, W1) | W1's issues-log entry says graph-walks 6 follows the steps. It does for `ownTiles`, not for the gate, and no test was added on the reader's side |
| Attach fetch reads detail units for an expanded walk | 17ed0a6, 00:28 | Terms "it reads no `detail` unit", 99fc07e, 00:30 | Written two minutes apart, by different hands, in opposite directions |
| `nsteps` bound | never implemented | 1a74b3e (2026-11-05) | Prose ahead of code |
| `bytes` skipped when unknown | a6269e4, 19:13 | 86d1006, 19:35 | The spec was written 22 minutes after the code, from the ADR |
| `{ data, table }` | a6269e4 takes `directory` | 2b0f7a5 (ADR), 86d1006 (spec) | Same: the spec copied the ADR's planned name, not the code's |
| Unknown unit kinds | ignored | 287 (86d1006) against 300 (c5d388c, 2026-11-04) | A new sentence not reconciled with an older one |
| `:k`, `@k`, `start@k` untested | 43910ec | — | No graph-walks test has ever held a walk row with `@` or `:` |
