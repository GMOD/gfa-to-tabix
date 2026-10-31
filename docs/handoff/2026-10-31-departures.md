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
- The projection onto one reference is exact where haplotypes keep its order
  (Minigraph-Cactus: no jump ends on a node GRCh38 passes twice) and a
  placement choice in repeats (pggb). Viewers say so where it is a choice
- pggb repeats: show one copy by alignment-guided placement as the working
  plan, never written up as ruling out every copy; the user may meet the
  pggb team

## State

- Released: graph-walks 4.6.0 (a crossing fragment carries `crossing`) and
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
   - jbrowse-components: `laneHeader.ts:196`, on its next beta
   - BandageJS `src/view.ts:95` and ggbandage `R/walkrows.R:90` keep their own
     copies of the text; ggbandage's `tests/testthat/test-figure.R:647` asserts
     it, and its update-deps job stops on a failed check
2. **Format 6, Minigraph-Cactus first.** Port the spike's writer and its
   tests, with ADR 0009's field names (`leavePos`/`rejoinPos`), into
   gfa-to-tabix 3.0; rebuild the hosted MC walk files on ada under new names
   (keep the format 5 files: graph-walks 4.x refuses format 6); then
   graph-walks 5 (`WalkDeparture`, two reads per window, no follow rounds, a
   departure-read budget beside the 8 MB cut budget), bandage-core 13, plugin
   9 (synteny strand per end, mate span from `hapStart` and `ownBp`,
   `EXPAND_NAMED_MAX` replaced by a per-row threshold), jbrowse-components'
   `laneBp`, then BandageJS, ggbandage and the tube map. ADR 0009's
   Consequences list each
3. **pggb, when it comes up.** Check that every path rebuilds from its rows
   under alignment-guided placement (checked for the chaining spike, not this
   one); then `--alignments` as an optional input in its own ADR. Questions
   for the pggb authors are in open-problems

## Where things are

- `docs/departures/`: the scripts and compact results ADR 0009 cites
- `target/plan-review/` (gitignored, deleted by `cargo clean`): every review
  of this round. `plan*.md` and `naming/` lead to `final/converged.md`;
  `final/confidence/report.md` is the spike's report, with `filing/`,
  `reader/`, `pggb/` and `untangle/` beside it. Its texts and scripts are
  copied to `~/notes/handoffs/2026-10-31-departures-reviews/`, with a README
  giving the reading order
- ada: `~/work/f6/` (the `bypass` prototype builds of MC chr22 and pggb
  chrY), `~/work/spike/` (spike builds, MC chrY cut for the agreement
  scores, alignments in `align/`)

## Gotchas

- Local disk is at 97%; keep large builds on ada
- graph-walks 4.x throws on any format but 5 (`walkReader.ts:198`), so every
  consumer still pinned to 4.x breaks on format 6 files under old names
- The `order` column of the `bypass` prototype was the reference's order, not
  the haplotype's: 604 of MC chr22's 685 "backward" jumps were reverse-strand
  contigs going forward. ADR 0009 derives direction from the ends
- `tests/build.rs`'s `gfatools_reads_the_graph_and_its_bubbles_are_sorted`
  failed once and passed on rerun: its fake gfatools reads stdin and races
