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
2. **Format 6, Minigraph-Cactus first.** Ported on 2026-11-04 into
   `src/` (gfa-to-tabix 3.0, not released): the writer, `tests/walks.rs`
   and `docs/walks-format.md` are format 6, and the port's rows equal the
   prototype's on MC chr22 and pggb chrY and chr22, the cuts aside
   ([results](../departures/results/port/README.md)). ADR 0009's History
   says how the format got here. Three Opus reviews of the port found the
   code sound and corrected the docs; their open design questions are
   below. Next:
   - graph-walks 5 against a local format 6 build of MC chr22 (`WalkDeparture`,
     two reads per window, no follow rounds, no neighbour tags, a
     departure-read budget beside the 8 MB cut budget), which settles the
     spec before any file is hosted
   - A format 6 build of what is hosted, the genome-wide MC graph with
     `--refs GRCh38,CHM13`: its size, time, memory and an audit by
     chromosome or `--shard`. CHM13 passes 209,578 of its nodes more than
     once, so that file is the first to need `@k`, step counts and the
     bounded stay
   - graph-walks 4.6.1 (a51b7bf, which asks for a newer viewer on a format
     6 file), bundled by the plugin, BandageJS, ggbandage and the tube map,
     before gfa-to-tabix 3.0 is released. Releasing is bumping `version`
     on main, so push main with the bump, not before
   - Then the hosted MC walk files rebuilt under new names, keeping the
     format 5 files; bandage-core 13 (its "filed near" label and "not in
     the graph" gap from the record's `rejoinChunk` and `missingBp`, and the
     hand-off from graph-walks a required type, so a mismatched bump fails
     to compile); plugin 9, which per ADR 0009 bundles graph-walks 4 beside
     5 for format 5 files (synteny strand per end, mate span from
     `hapStart` and `ownBp`, `EXPAND_NAMED_MAX` replaced by a per-row
     threshold); jbrowse-components' lane-side bp; then BandageJS,
     ggbandage, the tube map and jb2hubs
   - First decide the minimal design below, which changes the writer,
     tests, walks-format.md and ADR 0009 before graph-walks 5 is written
3. **pggb, when it comes up.** Check that every path rebuilds from its rows
   under alignment-guided placement (checked for the chaining spike, not this
   one); then `--alignments` as an optional input in its own ADR. Questions
   for the pggb authors are in open-problems

## Minimal design proposal, 2026-11-04 (not decided)

The user wants a minimal format 6 ("getting a good 'minimal' design will be
very valuable"). Five Fable reviews (four per question, one deriving the
minimal format from the requirements alone) and measurements on the port's
files on ada (`~/work/rebuild/port2/`) propose these cuts. The session ran
out before the user chose; ask them, group by group:

- **Backed by two reviews and measurement, or no consumer:**
  - `kinds:Z:`: `format:i:` already refuses unknown formats, and new kinds
    are a format change anyway. No reader reads it
  - the `#placement` line: no reader acts on it; a tag on `#walks` can
    come with a second placement rule, without a format bump
  - `leaveChunk`/`rejoinChunk`: equal to the chunk of the end node's pass
    start on every end measured (49,425 on MC chr22, 850,876 on pggb
    chrY), so derivable from `Pos`, `Strand` and the node's length; they
    differ from the chunk of the base beside the breakpoint only for a node
    straddling a chunk boundary, by one chunk. The fetch of a departure's
    own steps needed them on 0 records of three graphs. 6% of pggb chrY's
    departure bytes
  - `leavePasses`/`rejoinPasses`: only the 3% of departures that are
    records carry them, never checked by the audit (it needs `mp`); the
    deferred `mp` tag on `ref` rows is the real ambiguity mark
  - `xb`: says how much, not where; a later tag naming the other sequence's
    chunk and bp would replace it
- **One review, medium:** `ownSteps` (only the attach policy uses it,
  which `ownBp > 0` serves), `leaveNode`/`rejoinNode` (the piece edge step
  where the end's chunk is read), `fragStart` (`hapStart` keys the leave
  piece, since a contig's W lines can't overlap)
- **Split: one-ended records.** Measured: MC chr22 129, of which 26 carry
  sequence from other W lines (`missingBp` > 0) and 103 repeat what the
  first or last piece's route shows; pggb chrY 796, 240 with `xb`; pggb
  chr22 10,578, 9,338 with `xb`. Cutting them gives every record both ends
- With all of the above the record is `departure path hapStart ownBp
  missingBp leavePos leaveStrand rejoinPos rejoinStrand`, against 16
  columns and a tag now
- **Structural, one review each:**
  - file departure rows in the chunk rows, every chunk the stretch covers,
    in place of `S~departure` blocks: one read per window, no sibling
    sequence or block rule. Measured departure text: MC chr22 1.2% of the
    file's text now, 1.8% filed per chunk (47,725 rows against 31,368);
    pggb chrY 11.5% now, 34% per chunk. ADR 0009 rejected it for pggb's
    cost; the genome-wide MC number is unknown
  - fold step counts (`:n`) into `@k` on route entries and drop the walk
    row's `end`, which `nsteps` makes redundant: one copy mechanism. MC
    chr22 writes neither today; it changes the encoder, `audit6.py` and the
    test decoder

Earlier the same day three Opus reviews found the port's code sound (see
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
  0 was running at the end of 2026-11-04, and no audit of nearest pass on
  pggb chr22 had finished. Sources:
  `~/src/gfa-to-tabix-port/` (rsync of the working tree) and
  `~/src/gfa-to-tabix-f5/`
- ada: `~/work/f6/` (the `bypass` prototype builds of MC chr22 and pggb
  chrY), `~/work/spike/` (spike builds, MC chrY cut for the agreement
  scores, alignments in `align/`)

## Gotchas

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
