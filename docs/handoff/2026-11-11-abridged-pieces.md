# Handoff, 2026-11-11: abridged pieces mislead the walk view

The format review of 2026-11-11 found that graph-walks drops some abridged
pieces from windows they step in. Two blinded Fable reviews then traced
abridged pieces from file to screen and found the drop is one of several
ways the walk view states something false about a haplotype whose piece is
unloaded. This page is the brief for the session that fixes them. The
session that found the problem doesn't accept its own change, so none is
made here, and the fix needs graph-walks, bandage-core and plugin releases,
which wait for the user.

## Decision

- **Cause:** an `abridged` row summarises a moved piece by its first and
  last steps on R, its `bp` and its `nsteps`. Readers and viewers treat
  that summary as the piece's geometry: where it is (the stretch between
  its end steps), how long it is there (`bp`), which way it runs (its end
  steps' strands). A piece that doubles back, jumps or runs against R has
  none of those, so the view drops it where it steps, draws it where it
  doesn't, and misstates its size
- **Fix, reader and viewer, no format change:** an unloaded piece states
  only that this haplotype has `nsteps` steps not loaded within its detail
  unit's extent.
  - graph-walks keeps an abridged piece wherever that extent, which the
    table it already holds lists, overlaps the drawn stretch, and hands
    the extent to the consumer
  - bandage-core draws it as a "not loaded" block over the extent's part
    of the bar, with no size, strand or departure claims, and never
    labels a row "no step on the reference" while it holds an unloaded
    piece reaching the bar
  - every such row offers the load action
  - walks-format.md's "What a cut returns" names the detail extent
- **Not a format change:** an exact unloaded drawing would need each
  piece's covered stretches in its row, a format 8. ADR 0011 has no
  trigger for it, and the "not loaded" meaning removes every false
  statement below without it. Revisit only if users ask to see unloaded
  pieces' shape without loading them
- **Why the extent is sound:** every detail unit's `start end` equals the
  span of its one piece (61,056 of 61,056 on GRCh38, 56,801 of 56,801 on
  CHM13) or the hull of its several (5,925 and 3,981), by
  `detail-extent.py` on both hosted files. A multi-piece unit's extent is
  per line, not per piece; the stretch of it no piece of the line covers
  is 137 kb of GRCh38 and 271 kb of CHM13, which "not loaded" claims
  nothing about
- **The reader change can't ship alone:** with it, today's bandage-core
  draws 342 of 369 abridged rows longer than the 1,019 bp reference bar
  at chr2:91,409,000-91,410,000 (median 22 kb, max 1.87 Mb), because it
  places the block from the end steps. Release graph-walks as a major
  version so no `^6` consumer picks it up before bandage-core follows

## What the view gets wrong today

Hosted files, every haplotype kept unless named. "Verified twice" means a
reviewer ran it and this session reran it; "verified" means a reviewer ran
it, with the output in [cuts.txt](../walks-container/abridged/cuts.txt)
and [draws.txt](../walks-container/abridged/draws.txt).

- **F1, absent where it steps** (verified twice). A window over the part
  of a piece outside its end steps' stretch gets no fragment, only
  departure records, and the row reads "no step on GRCh38 across …". At
  chr2:91,409,000-91,410,000, 336 of 463 haplotypes; NA18565#2 has 98
  steps there once expanded. 1,279 rows on GRCh38 and 469 on CHM13, the
  union of their missed stretches 297 kb and 395 kb
  ([exposure.py](../walks-container/abridged/exposure.py)). On GRCh38
  they are exactly the rows whose end steps differ in strand
- **F3, no load action** (code read): the plugin offers "Load the N
  abridged steps" only on rows with `abridgedSteps`
  (`PaneContextMenu.tsx`), which an F1 row lacks
- **F4, forms report no cover** (verified): `formsCut` chooses what to
  expand from the unexpanded cut, so at chr16:14,932,000-14,933,000 60 of
  463 haplotypes come back `covered: []`, every one covering the window
  once expanded
- **F5, a block where it has no step** (verified twice): inside the end
  steps' stretch, where the piece jumps over, HG00140#1 at
  chr4:49,290,000-49,295,000 reads "≈ 45 kb (+40 kb) · 12 k steps, 45 kb
  not loaded"; expanded it has no step there and "rejoins GRCh38 on the
  other strand, 2.6 Mb away". In 11 scanned tiles 650 of 3,546 pieces
  have a hole of 1 kb or more inside that stretch
- **F6, size off by orders of magnitude** (verified twice): the row
  charges the piece's whole `bp` to the window. NA19443#2 at CHM13
  chr22:9,450,000-9,451,000 reads "≈ 27 kb (+26 kb)" against 2.0 kb
  expanded; others read 275 kb against 1.0 kb
- **F7, a hairpin on one node** (verified): 936 GRCh38 rows and 99 CHM13
  start and end on one node. At chr2:91,422,000-91,422,722 such a row
  reads "≥ 100 kb · does not rejoin the reference" and 1,851 kb, against
  0.7 kb expanded
- **F8, strand from the ends** (code read): `walkDepartures.ts` takes a
  piece as against R only when every end is, so one with 865 of 876
  reference steps against R reads as along it
- **F9, contained cuts** (verified): at chr16:14,942,147-14,942,211 a
  contained cut returns one 164,181 bp fragment where the expanded one
  returns two of 64 bp
- **F10, departures inside a piece** (verified): none come back
  unexpanded; the block stands for them, as the spec intends
- **F11, records beside an abridged piece** (verified): an attach fetch
  that lands on a tile abridging the path returns stepless records, 218
  at chr4:49,270,000-49,271,000; the 40 checked gain steps on expand
- **F12, auto-expand** (code read): the plugin expands abridged walks
  only in the walk-rows layout with 64 or fewer named haplotypes
  (`EXPAND_NAMED_MAX`). The hosted files have 463, so the four-haplotype
  default is safe and every-haplotype views are not

Checked and fine: no abridged rows on the reference's own lines; every
row's end steps decode; multi-piece units' rows find their detail rows
with matching `nsteps`; both-ends-against pieces pass the overlap test;
no record is duplicated at an abridged end.

## Tests the fix must pass

Each on the hosted file, or a fixture cut from it; the expected result is
the expanded cut over the same window unless a line says otherwise.

- **Hairpin on one node,** chr2 HG03050#1#JBJKOK010000055.1 (end steps at
  91,422,718-722, steps from 91,413,194): windows 91,415,000-91,416,000
  and 91,413,000-91,413,400, context 0, return the piece and its row is
  never stepless; at 91,422,718-91,422,722 the row claims no 29.6 kb
- **Hairpin at a tile start,** chr4 HG01252#1 and chr9 NA18959#1, 20 kb
  in: the piece is present, and nothing claims chr9's two passes are all
- **Mixed strand,** CHM13 chr16 HG04228#2 at 15,031,100-15,031,400,
  context 0: present, with no along-R claim
- **Same strand, first step not lowest,** CHM13 chr2 HG02886#1 at
  91,423,100-91,424,500: present
- **Jumped-over stretch,** chr4 HG00140#1 at 49,290,000-49,295,000 and
  CHM13 chr22 NA19443#2 at 9,480,000-9,482,000: no size claim; the block
  says not loaded, and expanding shows the departure
- **Partial overlap,** CHM13 chr22 NA19443#2 at 9,450,000-9,451,000: no
  number above the piece's true 2.0 kb, or none
- **Contained,** chr16:14,942,147-14,942,211: two 64 bp fragments, or a
  marked unloaded piece
- **Forms,** chr16:14,932,000-14,933,000: no haplotype with empty cover
  that covers the window expanded
- **Multi-piece unit,** CHM13 chr7 HG02698#1, three pieces: no window
  outside the unit's extent shows them
- **Menu:** every row holding an unloaded piece offers the load action
- **Renders:** before and after at chr2:91,409,000-91,410,000 with every
  haplotype, and the four-haplotype default as a control that must not
  change, shown to the user before bandage-core is committed
- **Each test fails on graph-walks 6.2 and today's bandage-core**

## Running the evidence

- `cut.ts` runs under node 24 directly, importing graph-walks' source
- `draw.ts` imports bandage-core, whose extensionless imports node won't
  resolve: bundle it with esbuild to an `.mjs` and run that
- `census.ts` lists every abridged row of a file with its end steps and
  detail unit; `detail-extent.py` and `exposure.py` stream a whole file
  and run on ada, where the hosted files are `~/work/genome7/*.walks.gz`
- Run node under `systemd-run --user --scope -p MemoryMax=4G
  -p MemorySwapMax=0`

## Order

- graph-walks on a branch: extent on the fragment, `abridgedSpan` by
  extent, `formsCut` and contained cuts by extent, tests above that fail
  on 6.2
- bandage-core on a branch, linked to it: the "not loaded" block, no
  stepless readout beside an unloaded piece, no size or strand from the
  ends; renders to the user
- the plugin's load action on any row with an unloaded piece
- every consumer green on the exact versions, then release graph-walks
  7, bandage-core, the consumers, and the walks-format.md sentence with
  the reader
