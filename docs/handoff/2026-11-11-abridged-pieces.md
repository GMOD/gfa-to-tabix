# Handoff, 2026-11-11: abridged pieces mislead the walk view

The format review of 2026-11-11 found that graph-walks drops some abridged
pieces from windows they step in. Two blinded Fable reviews then traced
abridged pieces from file to screen and found the drop is one of several
ways the walk view states something false about a haplotype whose piece is
unloaded. [ADR 0012](../adr/0012-abridged-blocks.md) decides walk format
8: a `blocks` row gives each abridged piece's shape on the reference, and
the `abridged` row keeps only what finds and costs its detail record.
This page lists what is wrong today, the tests a fix must pass, and where
the work stands; the releases and the hosted swap wait for the user.

## Decision

- **Cause:** format 7's `abridged` row summarises a moved piece by its
  first and last steps on R, its `bp` and its `nsteps`, and readers and
  viewers treat that summary as where the piece lies, how long it is
  there and which way it runs
- **Fix:** [ADR 0012](../adr/0012-abridged-blocks.md), walk format 8.
  graph-walks builds an unloaded piece from its `blocks` row as an
  ordinary fragment, each run off R one placeholder step of known bp and
  unknown identity; bandage-core draws it in loaded geometry with those
  runs styled "not loaded"; the plugin offers the load action on every
  row with unloaded runs
- **Not to say:** two unloaded rows with equal lists may differ in the
  nodes of their runs (0.3% of piece-windows), so a view never calls
  them the same sequence; and a run off R is off the tile's reference,
  not proof of sequence the reference lacks

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
  CHM13 chr22 NA19443#2 at 9,480,000-9,482,000: unloaded, the row draws
  the departure the loaded cut shows, with no block over the jump
- **Partial overlap,** CHM13 chr22 NA19443#2 at 9,450,000-9,451,000:
  unloaded, the row states the loaded cut's 2.0 kb
- **Contained,** chr16:14,942,147-14,942,211: two 64 bp fragments,
  unloaded as loaded
- **Forms,** chr16:14,932,000-14,933,000: no haplotype with empty cover
  that covers the window expanded
- **Multi-piece unit,** CHM13 chr7 HG02698#1, three pieces: each drawn
  from its own blocks
- **Menu:** every row holding an unloaded piece offers the load action
- **Renders:** before and after at chr2:91,409,000-91,410,000 with every
  haplotype, and the four-haplotype default as a control that must not
  change, shown to the user before bandage-core is committed
- **Every row equal:** blocks-built rows equal loaded rows, in bp, gaps,
  readout and runs, on all the windows above plus 1,000 random
  abridged-tile windows per file, ADR 0012's acceptance test
- **Each test fails on graph-walks 6.2 and today's bandage-core**
- **A file in another format:** graph-walks 7 refuses a format 7 file at
  open, naming the gfa-to-tabix version to rebuild with

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

Hosting freezes the format, and the `blocks` row changed twice once a
first reader was built on it, so nothing is hosted or released until
every consumer has read it end to end. Experiments and runs go to ada,
one agent at a time. No more rulings on the row's spelling: a change
from here needs a consumer failing on a real window.

- gfa-to-tabix, done on main, not pushed and not released: the writer,
  the spec, the proof, five file checkers with 74 broken files, and the
  repo's CI steps green on ada but for the job that rebuilds every path
  with graph-walks, which needs graph-walks 7. The version is still
  4.0.0: a push to main with a new version in Cargo.toml publishes it,
  so main isn't pushed before graph-walks 7 is released
- graph-walks on its `blocks-unit` branch (`~/src/graph-walks-blocks`):
  an independent review found its first round unsafe to build on, and a
  second round is fixing that and following format 8. It is done when
  its equality harness shows no difference from the full loaded cut on
  chr22, plain and contained, the harness fails on a broken reader, its
  cost on the worst windows is measured against 6.2, and a second review
  passes it
- walks-format.md's "Reading a window" follows the reader once it is
  settled, and the departure pyramid's blocks become bins in its prose,
  since "block" now means three things
- bandage-core on a branch, linked: loaded geometry for unloaded runs,
  runs off R styled "not loaded", exact sizes; renders to the user
- the plugin's load action on every row with unloaded runs
- chr22 end to end, from the writer to rendered rows, through all three
- then both genome files rebuilt on ada (`genome-blocks.sh`) and ADR
  0012's acceptance list run on them, the parts that check the writer by
  someone other than the session that wrote it
- then, with the user's go-ahead: release gfa-to-tabix 5.0, graph-walks
  7, bandage-core, the plugin and the other consumers, each green on the
  exact versions, and swap the hosted files with them
- the paper names the gfa-to-tabix version that built the hosted walk
  file and a request count measured on it; both are rechecked after the
  swap, and [the prior-art review](../walks-container/abridged/reviews.md#prior-art)
  has three sentences that say what the file is to a reader who knows
  GFA. If the consumers aren't green in time, the paper cites 4.0.0 and
  today's hosted files, which none of this touches
