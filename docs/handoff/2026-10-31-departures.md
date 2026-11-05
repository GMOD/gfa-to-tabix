# Handoff, 2026-10-31: departure records and the "deletion" label

Picks up from [the 2026-10-30 handoff](2026-10-30-placement.md). The format
decision is [ADR 0009](../adr/0009-departure-records.md); pggb placement is in
[open-problems.md](../open-problems.md#placement-of-steps-on-nodes-the-reference-passes-more-than-once).
This page holds what neither does: the state, the order of work and where
things are.

## Decisions the user made

- The tools make no "deletion" or "insertion" call. Where a haplotype leaves
  the reference and rejoins it, they state the facts: the reference stretch,
  each end, and the haplotype's own sequence between ("no step on GRCh38
  across 54 kb · 120 kb of its own"). Typing stays in the Forms track
- No backwards compatibility: formats, graph-walks, bandage-core and the
  plugin may break, and hosted data may be rebuilt
- Walk format 6 per ADR 0009: one `departure` record per place a path's
  consecutive steps on a reference sequence are not adjacent there, filed as
  bin-aligned blocks under `seq~departure`, with no chunk cap and no type
  column
- Format 6 walk rows carry no neighbour tags (`pv`, `nx`, `pg`, `pr`, `ng`,
  `nr`) and detail records have no pages (2026-11-04, after a vibe check
  and two independent reviews)
- The minimal record (2026-11-04, see below): `departure path hapStart
  ownBp missingBp leavePos leaveStrand rejoinPos rejoinStrand`, no
  one-ended records, no `kinds:Z:` or `#placement` in the header. Made
  under the user's "getting a good 'minimal' design will be very valuable"
  while they were away. On 2026-11-05, told these cuts waited on them,
  the user answered "i am open to minimizing the format and whatever else
  seems good to you": a go-ahead, not a review of each cut. The format
  arbitration the same day put the pass counts back: the record is now
  `departure path hapStart ownBp missingBp leavePos leaveStrand
  leavePasses rejoinPos rejoinStrand rejoinPasses`, `ref` rows carry
  `passes` and the header `revisited:i:`, and an `abridged` row stands
  for one piece (item 2)
- The projection onto one reference is exact where haplotypes keep its order
  (Minigraph-Cactus: no jump ends on a node GRCh38 passes twice) and a
  placement choice in repeats (pggb). Viewers say so where it is a choice
- pggb repeats: show one copy by alignment-guided placement as the working
  plan, never written up as ruling out every copy; the user may meet the
  pggb team

## State

- **Released 2026-11-05:** graph-walks 4.6.1 (from branch `v4`: refuses a
  format 6 file by asking for a newer reader), gfa-to-tabix 3.0.0 (walk
  format 6, crates.io and GitHub binaries) and graph-walks 5.0.0 (reads
  format 6 only; "Changes in 5" in its README). Checked before release
  on ada: MC chr22 and pggb chrY built by the release writer and audited
  clean, abridged nets equal expanded on seven MC chr22 windows
  ([results](../departures/results/release-3.0/README.md)). Nothing
  hosted changed: users still read format 5 through plugin 8.6.0 and
  graph-walks 4. Next: the hs1 genome-wide build from
  `hprc-v2.1-mc-chm13` (`vg convert -f` of its GBZ, at
  `~/work/arb-format-opus/in/chm13.gbz` on ada) and the GRCh38 one,
  hosted under new names beside the format 5 files; bandage-core 13 and
  plugin 9 on graph-walks 5 (`*` drawn as no genotype, `@place` keys,
  pass counts for "placement choice"); then BandageJS, ggbandage, the
  tube map and jb2hubs
- Released before: graph-walks 4.6.0 (a crossing fragment carries `crossing`) and
  jbrowse-plugin-graphgenomeviewer 8.6.0, rehosted. 8.6.0's synteny
  `crossingFeature` has two flaws: its mate span depends on which haplotypes
  are kept, and it takes strand from order along the reference
- Committed and pushed: ADR 0009 with its evidence in
  [docs/departures/](../departures/) (29b5eba), the placement section of
  open-problems (a4d51ee)
- Nothing hosted has changed: users still read format 5 files through plugin
  8.6.0
- A superseded `bypass` prototype was reverted from `src/walks.rs` and
  `tests/walks.rs`; it is saved as
  `~/notes/handoffs/2026-10-31-bypass-prototype.patch`
- The writer to port is the spike, saved as
  `~/notes/handoffs/2026-10-31-departures-spike.patch` (applies to a4d51ee;
  `write_departures`, `--fold`, `--alignments`, `--chain`). Its live copy is
  `target/plan-review/final/confidence/spike/tree`, which `cargo clean`
  deletes

## Next, in order

[docs/issues-log.md](../issues-log.md) holds every finding so far with its
source, fix and guard; append to it before committing a fix.

Format 6 is not urgent for Minigraph-Cactus users: format 5 mostly works
there. The urgent part is the word on screen

1. **Drop the word now, with no format change.** The false claim users see
   is the label, not the format:
   - bandage-core: `GAP_CAUSE_TEXT.deleted` ("deleted in this haplotype",
     `src/gfa/walkStops.ts`), "inside a X deletion"
     (`src/layout/walkRowDraw.ts:150`), `skipRowOf`'s hard-coded
     `offReferenceBp: 0` (`src/layout/walkRowRuns.ts:723-777`)
   - plugin: `type: 'deletion'` and the `windowDeletion` helper in
     `src/WalkTabixSyntenyAdapter/walkLanes.ts`, the legend's deletion rows
   - BandageJS `src/view.ts` (5c229dd3) and ggbandage `R/walkrows.R` (73bb0c6,
     bundling bandage-core 12.6.2, tests green) carry the new text; both keep
     their own copy of it, so a later wording change needs both
   - Done in bandage-core 1f53c24 (12.6.0): the walk-row text now reads "no
     step on the reference across 150 kb" and the key "no step on the
     reference". `skipRowOf`'s `offReferenceBp: 0` (`walkRowRuns.ts:747`) is
     still to do
   - Graph-view deletion edges, 2026-11-02. A measurement and five reviews
     found pggb index cuts draw hundreds of false Mb-scale deletions per
     segmental-duplication window: index cuts carry no path visits, so the
     repeat checks never run. In bandage-core 12.6.0 to 12.6.2:
     - a69b585 (12.6.0): each reference visit is judged by its own strand,
       so an inverted repeat copy read backwards no longer draws a false
       deletion. This stays in 12.6.2
     - 57d99c4 (12.6.0) routed a deletion the layout must keep through a route
       node, within a budget. 0c34456 (12.6.1) arched the deletions the layout
       had left out, and fffaf40 (12.6.2) lays deletions out as bubbles again:
       the layout is 12.5.1's, with a69b585 and the route budget kept
     - On a pggb LCR22A window, FMMM goes from 114 s to 7 s in 12.6.2 (stress
       55 s to 14 s was measured on 12.6.0). MC windows render as in 12.5.1
   - jbrowse-components cfbebd84cf: the lane header reads "no step on the
     reference across 150 kb", and the HPRC haplotypes tutorial follows. Its
     header still lists CIGAR-derived changes as "30 kb deletion" (a different
     path, `layoutMultiWay.ts`), not touched
   - Plugin: a00b1af takes bandage-core 12.6.2 and types the synteny record
     `skip`. `formRows.ts` keeps `deletion`, since typing stays in the Forms
     track. The arc label, legend and hover below wait on the drawing
   - **Parked: the graph-view arc label** ("94.2 kb del", the legend's "(a
     deletion)", the plugin's "Deletion" hover). Four wordings were rendered
     side by side on real windows, published as the artifact "Deletion arc
     wording". The user found none clear, because the picture doesn't show
     what is skipped. Under a force layout the arc leaves the reference for
     a stub and nothing marks the skipped stretch, often mostly outside the
     window. Labels tried and rejected: "−94.2 kb", "skips 94.2 kb", "skips
     94.2 kb of reference", "no GRCh38 step · 94.2 kb", "jumps 94.2 kb of
     GRCh38", a bare reference range. Before choosing words, make the
     drawing show the skipped stretch, for example by marking or dimming
     the bypassed reference and saying when most of it lies outside the
     window. Or drop the arc label and leave the facts to the hover
2. **Format 6, Minigraph-Cactus first.** Ported on 2026-11-04 into
   `src/` (gfa-to-tabix 3.0, not released): the writer, `tests/walks.rs`
   and `docs/walks-format.md` are format 6, and the port's rows equal the
   prototype's on MC chr22 and pggb chrY and chr22, the cuts aside
   ([results](../departures/results/port/README.md)). ADR 0009's History
   says how the format got here. Three Opus reviews of the port found the
   code sound and corrected the docs; their open design questions are
   below. Next:
   - **Done, 2026-11-04 afternoon: graph-walks 5** at `~/src/graph-walks`
     commit 43910ec, unreleased and unpushed, `version` still 4.6.0 (the
     bump is `pnpm version major`, which pushes). Against the port3 format
     6 files of MC chr22 and pggb chrY and the fixtures rebuilt in format 6
     from their GFAs, now kept in `test_data/` with `build.sh`. It reads
     format 6 only; makes two reads per cut, the walk chunks and the
     `~departure` blocks over the drawn stretch; returns `departures`,
     every departure over the stretch once, those inside one piece
     computed from its steps and the rest from the records; cuts each
     fragment from the walk's first step on the drawn stretch to its last,
     with `trimmedBefore`/`trimmedAfter`, so no follow rounds, run-on,
     crossings, skips or stop kinds; attaches a departure's own steps
     under `attachBp` (65,536), fetching the leave chunk when the read
     lacks it, at most `attachFetches` (8) chunks; exports `departureKind`
     (`switch`, `back`, `adjacent`, `forward`); and refuses a departure
     read over `departureByteBudget` (2 MB in `WALK_BUDGETS`) with a
     `DepartureReadError`, not a zoom-in notice. `GraphTables.departures`
     is required, `before`/`after`/`skips` are gone. 159 tests pass.
     Timings on the port3 files: MC chr22 64 kb LCR22A window, every
     haplotype, 2.4 s with 67,144 departures; a 10 kb window at 30 Mb 0.3
     s; pggb chrY 64 kb at 12 Mb for HG002 1.3 s, mostly parsing the
     100,000 departure rows of the TSPY array before the keep filter.
     **Done, 2026-11-05: the structural-forms cut**, graph-walks commits
     1132859, 73f2e6b and 3574904 (unpushed; three reviews of the first
     found the defects the other two fix, each logged with its source in
     [docs/issues-log.md](../issues-log.md)): `formsCut` and
     `walkDepartures` read each
     haplotype's departures off `cut.departures` and the fragments' end
     steps. A fragment with the departures at its ends and inside it is
     a chain read in its own orientation, as the old chains were; a
     departure touching no fragment, such as a contig jumping over the
     window or rejoining far outside it, is a chain of its own; R that
     two chains reach has no call; sequence between a contig's W lines
     counts as its own; an abridged fragment stays a net.
     `DepartureSource` is `{ fragments, departures, nodes }` and
     `HaplotypeDepartures` has no `open`; `WalkFragment` carries
     `refStarts` and `against`. Checked against 4.6.0 on the format 5
     file: every old departure is reproduced on 28 chr22 windows, the
     forms are identical on 16 of them and differ on the 12 where jumps
     over the window appear
     ([results](../departures/results/minimal/README.md#the-forms-cut-on-mc-chr22)).
     **Decided 2026-11-05**, under the user's go-ahead ("whatever else
     seems good to you"): the forms keep the chain model's reading. In
     LCR22A, LCR22B and IGL they group on jumps over the window ("624 kb
     replaced by 130 kb", 114 haplotypes at LCR22A) that the old cut
     never saw, and at 12.3 and 15.0 Mb a jump over the window is one
     shared site; on MC's GRCh38 the projection is exact, so those are
     facts of the walks. Sites now come from marks `minCarriers`
     haplotypes share (be081a5, with a logic review's fixes in
     edf4acd), so one haplotype's rare departure no longer merges the
     sites it crosses (chr22:20.3 Mb, [issues log](../issues-log.md)).
     **Arbitrated 2026-11-05** by two independent agents (Fable and
     Opus), after the user asked for the design to be fixed rather than
     handed back: both found the forms had no rule for what a row may
     say of its members, and fold rules tuned on loci but never checked
     against the output. graph-walks 7601e9e (Opus's branch) is landed:
     one tolerance, `agrees`, that every fold must pass; a no call never
     folds; a rare state that agrees with no common one is `~`, a member
     that fits no common form goes to `other` (key `*`), which states
     nothing; a site is shared only if every form but `other` has one
     state there; at a site over 1 kb a change keys on its place as well
     as its size; no site widening. `formContradictions` checks any
     result against the members' own departures: 315 contradicted
     members on the 28 chr22 windows at the auto floor and 417 on the
     jb2hubs gate before, none after, at every floor, folded or not.
     Fable's branch (no folding at all) was not landed: it still drew 4
     haplotypes' 13.7 kb insertion at 42,134,095 at another carrier's
     42,125,923, which its size-only checker could not see. HG00126#1
     at 21.4 Mb is now in `other`, reversing the earlier reading.
     Plugin 9 must map `*` to no genotype in `formVariants`' `genotypeOf`
     and read state keys carrying `@place`
     **Format contract arbitrated 2026-11-05** by two more independent
     agents (Fable and Opus), who agreed on all but one point; landed
     from `arb-format-opus` of both repos (ADR 0009's History): records
     carry `leavePasses` and `rejoinPasses` as columns, `ref` rows a
     `passes` column and the header `revisited:i:`; graph-walks exports
     `placementChoice`, and plugin 9's Forms track says "placement
     choice" for a departure where it is true. graph-walks' budgets
     default to `WALK_BUDGETS`, so plugin 9 and BandageJS need pass
     nothing. Where they differed, abridged rows: one row per moved
     piece (Opus) was taken over a row stating the contig end of the
     last piece (Fable), since a per-piece row spans no other chunk's
     pieces and so leaves the reader nothing to absorb, the logic that
     went wrong twice; it costs pggb chrY +0.93% against +0.26% and its
     densest walk read 1.72 MB against 1.31, under the 8 MB budget
     Plugin 9 will need `formRows.test.ts` without `open` and the
     `^4.6.0` pin raised. Not done: bandage-core 13 and plugin 9
     (below)
   - **Done, 2026-11-04 evening: the genome-wide build**, on ada by
     `~/work/rebuild/genome.sh` from
     `~/hprc-gbz/walks/hprc-v2.1-mc-grch38.W.gfa.gz` with the port3 binary
     (76c9223), into `~/work/rebuild/genome/`: 1 h 22 m at 13.1 GB; the
     GRCh38 file 1.55 GB as format 5's, the CHM13 file 1.99 GB against
     1.46 GB, with 5.5 M departure records in 42.7 M rows, since CHM13
     passes 209,578 nodes more than once and nearest-pass placement files
     a departure at each hop between copies, as on pggb
     ([results](../departures/results/minimal/README.md)). Only 65 walk
     rows name a copy. `genome-audit.sh` then audits chr22 of each file
     with `audit6.py --seq`, CHM13 first, into `genome/CHM13.chr22.audit.txt`
     and `genome/GRCh38.chr22.audit.txt`. **Both audits are clean**
     (2026-11-05): every record matches a recomputed departure (the 9
     and 28 over a W line the file holds no row of in all but the
     missing bp the audit cannot see), no base of any stretch is
     uncovered, and a 64 kb window's departure read is at most 117 KB
     on chr22 of either file. **The CHM13 file's extra rows are on
     chr9**: 32.4 M of its 42.7 M, from 2.2 M records that hop between
     copies 1 to 100 Mb apart, three quarters of them 10 to 100 Mb, 96%
     with no own bp and 81% switching strand, so a 64 kb window between
     38 and 80 Mb of CHM13 chr9 reads up to 1.7 M rows (22 MB
     compressed; 473 k rows and 5.3 MB at 39 Mb) and graph-walks 5
     refuses it with its DepartureReadError; chr14 has 4.2 M rows in
     one Mb, and a window at 13.5 Mb reads 2.0 M (25 MB). chr2, chr16,
     chr8, chr21, chr4
     and chr5 hold 0.3 to 2.0 M rows each, not measured by window; the
     other sequences read as the GRCh38 file does
     ([results](../departures/results/minimal/README.md#where-the-chm13-files-rows-are),
     and a bullet in open-problems). **Decided 2026-11-05 by the
     format arbitration, replacing the interim below:** the hs1 files
     come from HPRC v2.1's CHM13-referenced Minigraph-Cactus graph,
     `hprc-v2.1-mc-chm13.gfa.gz` on HPRC's S3, built with `--refs
     CHM13`; this graph's CHM13 file is not hosted
     ([results](../departures/results/arbitration/README.md): on chr9
     70,960 records in 84,745 rows against 2.2 M in 32.4 M; a 64 kb
     window's departure read at most 848 rows on chr9, 1,328 on chr14
     and 902 on chr22 over the audits' windows; `revisited:i:0` on
     chr9, chr14 and chr22). Not yet done: the genome-wide build of that graph; the
     66 GB `gfa.gz` download from S3 stalled at 57 GB on ada, and `vg
     convert -f` of its 6.2 GB GBZ is the other way to a GFA. The
     interim it replaces: host the
     CHM13 file as it is, with those windows refused. graph-walks 5's
     `cut` refuses a window whose departure read the index estimates
     past `departureByteBudget`, after reading the header and index and
     before fetching any of the window's blocks, with a message naming
     a collapsed repeat; the budget was then off by default, and since
     ec8ecd9 `WALK_BUDGETS` is the reader's default. That these CHM13 windows are over it is inferred
     from their gzipped sizes, not run. A design review argues against
     this as the end state: the refused windows are chr9's
     pericentromeric duplications, where CHM13 adds most over GRCh38
     and which the hosted format 5 file draws today, and the hops look
     like a placement artefact (every haplotype hops, 96% with no own
     bp). Its proposal: build the hs1 files from a CHM13-referenced
     Minigraph-Cactus graph, where CHM13 would pass no node twice, if
     HPRC v2.1 publishes one (not checked; ada holds only the GRCh38
     one). That costs a genome-wide build and gives the hs1 tracks
     other node ids than the hg38 ones. For the user to decide; before
     hosting, a refusal map of every CHM13 sequence from the index
     alone
   - graph-walks 4.6.1 (a51b7bf, which asks for a newer viewer on a format
     6 file), bundled by the plugin, BandageJS, ggbandage and the tube map,
     before gfa-to-tabix 3.0 is released. Releasing is bumping `version`
     on main, so push main with the bump, not before
   - Then the hosted MC walk files rebuilt under new names, keeping the
     format 5 files; bandage-core 13 (its "filed near" label and "not in
     the graph" gap from the record's `rejoinPos` and `missingBp`, and the
     hand-off from graph-walks a required type, so a mismatched bump fails
     to compile); plugin 9, which per ADR 0009 bundles graph-walks 4 beside
     5 for format 5 files (synteny strand per end, mate span from
     `hapStart` and `ownBp`, `EXPAND_NAMED_MAX` replaced by a per-row
     threshold); jbrowse-components' lane-side bp; then BandageJS,
     ggbandage, the tube map and jb2hubs
3. **pggb, when it comes up.** Check that every path rebuilds from its rows
   under alignment-guided placement (checked for the chaining spike, not this
   one); then `--alignments` as an optional input in its own ADR. Questions
   for the pggb authors are in open-problems

## Minimal design, decided 2026-11-04

The user wants a minimal format 6 ("getting a good 'minimal' design will be
very valuable"). Five Fable reviews in the morning of 2026-11-04 (four per
question, one deriving the minimal format from the requirements alone) and
measurements on the port's files on ada (`~/work/rebuild/port2/`) proposed
the cuts; the next session, that afternoon, made them, since the user was
away; on 2026-11-05 the user gave a go-ahead to minimizing the format
without reviewing each cut. What ADR 0009 now says, and why:

- **Cut from the record:** `fragStart`, `ownSteps`, `leaveNode`,
  `leavePasses`, `leaveChunk`, `rejoinNode`, `rejoinPasses`,
  `rejoinChunk` and the `xb` tag. The chunks equalled the chunk of the
  end's pass start on every end measured (49,425 on MC chr22, 850,876 on
  pggb chrY), which the walk read of any window over the end holds; the
  nodes are the ones R holds at the breakpoints; the pass counts marked
  3% of departures and the `mp` tag will mark every `ref` row; the rest
  no reader needs. The record is `departure path hapStart ownBp missingBp
  leavePos leaveStrand rejoinPos rejoinStrand`
- **Cut: one-ended records** (MC chr22 129, 26 with bp between W lines
  and 103 repeating what the first or last piece's route shows; pggb chrY
  796; pggb chr22 10,578, 9,338 with own bp on another sequence). A
  contig's sequence before its first step on S or after its last is not a
  departure, and the piece's route with no entry or exit shows it
- **Adjacency is by bp:** with `ownSteps` gone, a step on a 0 bp node
  between two adjacent steps is no departure. The port had recorded it;
  the writer, the audit and the tests now agree the other way
- **Cut from the header:** `kinds:Z:` (`format:i:` refuses what a reader
  can't read, and a new kind is a new format) and `#placement` (one rule,
  which the format fixes; a later rule is a header tag or a new format)
- **Kept: `S~departure` blocks** rather than departure rows in every
  chunk of the stretch. Departure text is 1.2% of MC chr22's file and
  would be 1.8% per chunk; 11.5% of pggb chrY's and would be 34%
- **Checked:** `cargo test`, `audit6.py` over every walk fixture and five
  hand-made graphs at `--chunk 10` in five option modes (65 files), and
  `fuzz6.sh 1 300` (1,800 builds), no failures, for each of the two
  commits; then MC chr22 and pggb chrY built on ada at 76c9223 and
  audited clean ([results](../departures/results/minimal/README.md)):
  59.17 MB, +0.04% over format 5, and 190.4 MB, +5.9%, against the port's
  +0.48% and +9.3%
- **Walk rows, one copy mechanism:** a choice token is `t[:k][@k]`, `:k`
  the occurrence of the entry's node the walk leaves R from and `@k` the
  one its exit lands on, each written only where the default decodes
  wrongly; step counts on every token and the `end` column went, since
  `nsteps` bounds the last stretch. `routes.rs`, the test decoder and
  `audit6.py` changed together, with the same checks as above
- **Read back by graph-walks 5** (item 2 above), which decodes the rows,
  the copies and the records as the spec says; nothing in the format
  needed changing for the reader

Earlier, on 2026-11-04, three Opus reviews found the port's code sound (see
ADR 0009 History); their doc and number fixes are committed.

## Where things are

- `docs/departures/`: the scripts and compact results ADR 0009 cites
- `target/plan-review/` (gitignored, deleted by `cargo clean`): every review
  of this round. `plan*.md` and `naming/` lead to `final/converged.md`;
  `final/confidence/report.md` is the spike's report, with `filing/`,
  `reader/`, `pggb/` and `untangle/` beside it. Its texts and scripts are
  copied to `~/notes/handoffs/2026-10-31-departures-reviews/`, with a README
  giving the reading order
- ada: `~/work/rebuild/` (the 2026-11-03 rebuild: `out6/` the simplified
  format, `out/` the amended Decision's filing variants, `run*.sh`), and the
  prototype's sources in `~/src/gfa-to-tabix-rebuild-simple/`
- ada, the port (2026-11-04): `~/work/rebuild/port2/` its builds of MC
  chr22 and pggb chrY and chr22, with `compare2.sh` against `out6/`;
  `f5/` format 5 builds of the same graphs from 552b9c1; `noab/` MC chr22
  with abridging off in both formats. `run6.sh` audits the port's pggb
  chr22 file in four shards, each waiting for 80 GB free, into
  `port2/pggb22.shardN.audit.txt` (`port2/audit.done` when finished); shard
  0 finished on 2026-11-04 (4,497 s, 39 GB) with every record matched and
  nothing missing, and its window costs are in ADR 0009's rebuild table;
  shards 1 to 3 were still waiting for memory that afternoon. Sources:
  `~/src/gfa-to-tabix-port/` (rsync of the working tree of 2026-11-04) and
  `~/src/gfa-to-tabix-f5/`
- ada, the minimal record (2026-11-04, afternoon): `~/work/rebuild/port3/` builds
  and audits of MC chr22 and pggb chrY by `port3.sh`, from
  `~/src/gfa-to-tabix-port3/` (rsync of the working tree at 76c9223),
  with `port3/sizes.txt` against `port2/` and `f5/`; `~/work/rebuild/genome/`
  the genome-wide build (item 2 above), its chr22 audits, and the chr9
  and chr14 breakdown by `genome/chr9.sh`, the repo's
  `docs/departures/scripts/chm13-chr9-departures.sh`; its
  `chr9.records.txt`, the 2.2 M distinct records at 100 MB, stays on ada,
  and the repo's `CHM13.chr9.records.txt` is that file's summary. ada's
  disk was at 99% with 44 GB free during that build
- Local, gitignored: `target/forms-check/` holds `f5/` and `port3/`'s MC
  chr22 files, the inputs of the forms comparison, and `arb/` the format
  arbitration's MC chr22 build with its forms cuts and checks
- graph-walks: `~/src/graph-walks` at dd6986c, unpushed (43910ec the
  format 6 reader; 1132859, 73f2e6b, 3574904, be081a5 and edf4acd the
  forms cut; 7601e9e the forms arbitration; ec8ecd9 the format
  arbitration; 277fa44 to dd6986c the review of the landed work). Its
  `test_data/` holds each fixture's GFA and `build.sh`, which rebuilds them with a
  gfa-to-tabix binary; the chrM fixture's GFA was recovered from the
  format 5 file with the old decoder, bases included
- The arbitration of 2026-11-05: worktrees `~/src/arb-forms-{fable,opus}`
  and `~/src/arb-format-{fable,opus}`, their branches kept; the Fable
  branches were not landed (`arb-forms-fable` 47ecef3, no folding;
  `arb-format-fable` db3699f and 15659ac, `hapEnd` abridged rows, with
  chr9 hop scripts `hop-ends.py` and `chr9-dwell.py` and a `fuzz6.sh`
  path fix not carried over). ada: `~/work/arb-format-opus/` (65 GB,
  inputs re-cut from S3 into `in/`, builds in `out/`) and
  `~/work/arb-format-fable/`
- ada: `~/work/f6/` (the `bypass` prototype builds of MC chr22 and pggb
  chrY), `~/work/spike/` (spike builds, MC chrY cut for the agreement
  scores, alignments in `align/`)

## Gotchas

- On 2026-11-05 ada no longer held `~/work/mc/`, `~/work/pggb/` or
  `~/hprc-gbz/`; `docs/departures/scripts/arbitration-inputs.sh`, run in
  `~/work/arb-format-opus/`, recuts MC chr22 and pggb chrY from HPRC's S3,
  and chr9, chr14 and chr22 of the CHM13 graph, into its `in/`

- Local disk is at 97%; keep large builds on ada
- ada's 125 GB are shared with other heavy jobs on the same account; on
  2026-11-03 they filled it, the kernel killed audits well under their
  `systemd-run` caps, and sshd refused connections for a while. Check
  `free -g` before starting anything over 30 GB, and run `audit6.py` on
  pggb chr22 nearest pass with `--shard`, one shard at a time
- ada's login shell is zsh: `$pids` does not word-split, so kill a list of
  PIDs through `xargs`. The local shell is zsh too: run a loop over a
  string of options or seeds under `bash -c`
- `pgrep -f PATTERN | xargs kill` over ssh also matches the ssh session's
  own command line, which holds the pattern, and kills it; kill by PID
- graph-walks 4.x throws on any format but 5 (`walkReader.ts:198`), so every
  consumer still pinned to 4.x breaks on format 6 files under old names
- The `order` column of the `bypass` prototype was the reference's order, not
  the haplotype's: MC chr22's 685 "backward" jumps included
  reverse-strand contigs going forward. The breakdown in the notes (604,
  406, 8) sums to 1,018, so don't cite it. ADR 0009 derives direction from
  the ends
- `tests/build.rs`'s `gfatools_reads_the_graph_and_its_bubbles_are_sorted`
  failed once and passed on rerun: its fake gfatools reads stdin and races
- The laptop's `/tmp` is a tmpfs with a per-user quota, and
  `/tmp/claude-1001` held 8 GB of earlier sessions' scratch files on
  2026-11-05 (bender 2.8 GB, jbrowse-components 2.9 GB, notes 1.2 GB), so
  Claude Code's tool output hit "Disk quota exceeded" and one command's
  output was lost. Nothing was deleted; clear those directories when
  convenient
