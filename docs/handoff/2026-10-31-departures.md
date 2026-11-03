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
2. **Format 6, Minigraph-Cactus first. Stop before starting: ask the
   user.** A review on 2026-11-01 found gaps in the evidence behind ADR
   0009, listed under its "Review after acceptance". Six more reviews on
   2026-11-03 and eleven more that day amended it in three rounds; walk
   rows now name the copy (`@k`), a walk-row change the user agreed to
   write up. The ADR's "Open before the port" is the current list, chiefly
   a rebuild on ada with the amended record, filing and positions. Do that
   first, and confirm the format with the user before porting anything.
   The spike's writer is not a plain port: it has no `@k`, `mp`, `crowd`
   rows or pages, its blocks follow the chunk size and cover whole
   stretches, and its stay is unbounded. Port the spike's writer and its
   tests, with ADR 0009's field names (`leavePos`/`rejoinPos`), into
   gfa-to-tabix 3.0; rebuild the hosted MC walk files on ada under new names
   (keep the format 5 files: graph-walks 4.x refuses format 6); then
   graph-walks 5 (`WalkDeparture`, two reads per window, no follow rounds, a
   departure-read budget beside the 8 MB cut budget), bandage-core 13, plugin
   9 (synteny strand per end, mate span from `hapStart` and `ownBp`,
   `EXPAND_NAMED_MAX` replaced by a per-row threshold), jbrowse-components'
   lane-side bp, then BandageJS, ggbandage, the tube map and jb2hubs. ADR
   0009's Consequences list each
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
  the haplotype's: MC chr22's 685 "backward" jumps included
  reverse-strand contigs going forward. The breakdown in the notes (604,
  406, 8) sums to 1,018, so don't cite it. ADR 0009 derives direction from
  the ends
- `tests/build.rs`'s `gfatools_reads_the_graph_and_its_bubbles_are_sorted`
  failed once and passed on rerun: its fake gfatools reads stdin and races
