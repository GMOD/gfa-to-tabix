# Abridged pieces on format 7: the failure windows

Taken on 2026-11-11, on the format 7 files then hosted as
`jbrowse.org/demos/hprc/hprc-v2.1-mc-grch38.GRCh38.walks.gz` and
`hprc-v2.1-mc-chm13.CHM13.walks.gz`, read with graph-walks 6.2 and the
bandage-core and JBrowse plugin of that day. It lists what the walk view
stated falsely about a haplotype whose abridged piece was not loaded, and
the windows a fix had to pass. The fix is walk format 8's `blocks` unit
([ADR 0012](../../adr/0012-abridged-blocks.md)); its acceptance runs are in
[accept-5.0.0](../accept-5.0.0/4b14ee3/README.md).

Format 7's `abridged` row summarised a moved piece by its first and last
steps on the reference, its `bp` and its `nsteps`, and the readers took
that summary as where the piece lies, how long it is there and which way
it runs.

## What the view got wrong

Every haplotype kept unless one is named. "Verified twice": a reviewer ran
it and the session reran it. "Verified": a reviewer ran it, with the
output in [cuts.txt](cuts.txt) and [draws.txt](draws.txt). "Code read":
traced in the code, not run.

- **F1, absent where it steps** (verified twice): a window over the part
  of a piece outside its end steps' stretch got no fragment, only
  departure records, and the row read "no step on GRCh38 across …". At
  chr2:91,409,000-91,410,000, 336 of 463 haplotypes; NA18565#2 has 98
  steps there once expanded. 1,279 rows on GRCh38 and 469 on CHM13, the
  union of their missed stretches 297 kb and 395 kb
  ([exposure.py](exposure.py)). On GRCh38 they are exactly the rows whose
  end steps differ in strand
- **F3, no load action** (code read): the plugin offered "Load the N
  abridged steps" only on rows with `abridgedSteps`
  (`PaneContextMenu.tsx`), which an F1 row lacks
- **F4, forms report no cover** (verified): `formsCut` chose what to
  expand from the unexpanded cut, so at chr16:14,932,000-14,933,000 60 of
  463 haplotypes came back `covered: []`, every one covering the window
  once expanded
- **F5, a block where it has no step** (verified twice): HG00140#1 at
  chr4:49,290,000-49,295,000 read "≈ 45 kb (+40 kb) · 12 k steps, 45 kb
  not loaded"; expanded it has no step there and "rejoins GRCh38 on the
  other strand, 2.6 Mb away". In 11 scanned tiles 650 of 3,546 pieces
  have a hole of 1 kb or more inside their end steps' stretch
- **F6, size off by orders of magnitude** (verified twice): the row
  charged the piece's whole `bp` to the window. NA19443#2 at CHM13
  chr22:9,450,000-9,451,000 read "≈ 27 kb (+26 kb)" against 2.0 kb
  expanded; others read 275 kb against 1.0 kb
- **F7, a hairpin on one node** (verified): 936 GRCh38 rows and 99 CHM13
  rows start and end on one node. At chr2:91,422,000-91,422,722 such a
  row read "≥ 100 kb · does not rejoin the reference" and 1,851 kb,
  against 0.7 kb expanded
- **F8, strand from the ends** (code read): `walkDepartures.ts` took a
  piece as against the reference only when every end is, so one with 865
  of 876 reference steps against it read as along it
- **F9, contained cuts** (verified): at chr16:14,942,147-14,942,211 a
  contained cut returned one 164,181 bp fragment where the expanded one
  returns two of 64 bp
- **F10, departures inside a piece** (verified): none came back
  unexpanded; the block stood for them, as the spec intended
- **F11, records beside an abridged piece** (verified): an attach fetch
  that landed on a tile abridging the path returned stepless records, 218
  at chr4:49,270,000-49,271,000; the 40 checked gained steps on expand
- **F12, auto-expand** (code read): the plugin expanded abridged walks
  only in the walk-rows layout with 64 or fewer named haplotypes
  (`EXPAND_NAMED_MAX`). The hosted files have 463, so the four-haplotype
  default was safe and every-haplotype views were not. The cap is still
  64 in the plugin's `src/GetSubgraph.ts` on 2026-11-25

There is no F2. Checked and fine: no abridged rows on the reference's own
lines; every row's end steps decode; multi-piece units' rows find their
detail rows with matching `nsteps`; pieces with both ends against the
reference pass the overlap test; no record is duplicated at an abridged
end.

## The windows a fix had to pass

Each on the hosted file, or a fixture cut from it. The expected result is
the expanded cut over the same window unless a line says otherwise.

- **Hairpin on one node:** chr2 HG03050#1#JBJKOK010000055.1 (end steps at
  91,422,718-722, steps from 91,413,194): windows 91,415,000-91,416,000
  and 91,413,000-91,413,400, context 0, return the piece and its row is
  never stepless; at 91,422,718-91,422,722 the row claims no 29.6 kb
- **Hairpin at a tile start:** chr4 HG01252#1 and chr9 NA18959#1, 20 kb
  in: the piece is present, and nothing claims chr9's two passes are all
- **Mixed strand:** CHM13 chr16 HG04228#2 at 15,031,100-15,031,400,
  context 0: present, with no along-the-reference claim
- **Same strand, first step not lowest:** CHM13 chr2 HG02886#1 at
  91,423,100-91,424,500: present
- **Jumped-over stretch:** chr4 HG00140#1 at 49,290,000-49,295,000 and
  CHM13 chr22 NA19443#2 at 9,480,000-9,482,000: unloaded, the row draws
  the departure the loaded cut shows, with no block over the jump
- **Partial overlap:** CHM13 chr22 NA19443#2 at 9,450,000-9,451,000:
  unloaded, the row states the loaded cut's 2.0 kb
- **Contained:** chr16:14,942,147-14,942,211: two 64 bp fragments,
  unloaded as loaded
- **Forms:** chr16:14,932,000-14,933,000: no haplotype with empty cover
  that covers the window expanded
- **Multi-piece unit:** CHM13 chr7 HG02698#1, three pieces: each drawn
  from its own blocks
- **Menu:** every row holding an unloaded piece offers the load action
- **Renders:** before and after at chr2:91,409,000-91,410,000 with every
  haplotype, and the four-haplotype default as a control that must not
  change
- **Every row equal:** rows built from blocks equal loaded rows, in bp,
  gaps, readout and runs, on all the windows above plus 1,000 random
  abridged-tile windows per file
- **Against the old readers:** each test fails on graph-walks 6.2 and the
  bandage-core of 2026-11-11
- **A file in another format:** graph-walks 7 refuses a format 7 file at
  open, naming the gfa-to-tabix version to rebuild with

## Running the scripts

- `cut.ts` runs under node 24 directly, importing graph-walks' source from
  `~/src/graph-walks/src`
- `draw.ts` also imports bandage-core, whose extensionless imports node
  won't resolve: bundle it with esbuild to an `.mjs` and run that
- `census.ts` lists every abridged row of a file with its end steps and
  detail unit
- `detail-extent.py` and `exposure.py` stream a whole file. They ran on
  ada, where copies of the format 7 files were `~/work/genome7/*.walks.gz`
- Run node under `systemd-run --user --scope -p MemoryMax=4G
  -p MemorySwapMax=0`
- `cut.ts`, `draw.ts` and `census.ts` open the hosted URLs above by name.
  All three read format 7 through graph-walks 6.2, and graph-walks from 7
  on reads format 8 only, so a rerun needs graph-walks 6.2 and a format 7
  copy. `exposure.py` reads format 7's `abridged` columns
- `blocks-check.ts` and `piece-ends.ts` read rows from before format 8 was
  final: they were last changed on 2026-11-11, before
  [ADR 0013](../../adr/0013-abridged-hapbp.md) gave the `abridged` row
  `hapBp`, and `blocks-check.ts` takes abridged rows from
  `decodeChunk(...).rows`, where graph-walks' format 8 decoder no longer
  puts them
