# Next session: walk format 8 release, state on 2026-11-16 and what to do, in order

Written by session b7daa067 (gfa-to-tabix-97) as its context ran out. It took
over both lanes of 2026-11-15 (`2026-11-15-next-session.md` is the earlier
plan and still holds the settled format and release facts; this file
supersedes its "Do, in order"). Nothing is pushed, tagged, published or
uploaded. The owner asked for no new subagents from that session, so the work
below is either landed, on a named branch, or in an agent that was still
running and reports into a transcript on disk.

## What the owner decided on 2026-11-15 and 16 (also in memory)

- **Aim for the ideal; nothing is cut for time.** The paper freeze moved back
  "a couple days" (about 2026-11-20; ask for the date). Anything can still
  change, the walk file format included if needed, and separate side files
  beside the walk file are welcome. A format change still raises the alarm and
  gets three fresh Fable reviews. Memory: `not-conservative-prerelease`,
  `paper-freeze-window`, `aim-for-ideal`.
- **A picture that is correct but not informative is a release-level fault.**
  Serious issues get a Fable review and go to the owner on an artifact page.
  Memory: `surface-serious-issues`.
- **The force layout (fmmm) is the default in every host, the plugin track
  included.** No forced-straight or ruler-locked reference; the rainbow is the
  only bridge to the linear view. Read memory `graph-not-linearized` whole
  before any layout question.
- **Graph views are for structure.** Small SNP-scale sites are not drawn at
  overview (no ticks, no per-site marks, no key scale); they return as nodes
  on zoom-in. Memory: `structure-over-small-variants`.
- **Threading as in ggbandage's gallery is the way to show complex walks**, and
  every reader must have it. Memory: `threading-for-clarity`.
- **"We are just a visualizer."** State what the graph holds (N of M
  haplotypes step this node), never what a haplotype has or lacks, in reports
  as well as on the drawing. Memory: `graph-not-linearized`.
- **Key wording:** "short skip" replaced "a skip too short to dash". The owner
  found "haplotypes on a route, of 9" incomprehensible (dropped).
- **Waiting on the owner's look:** the "direct join" candidate (below), and in
  the end the final BEFORE/AFTER page, which is the last gate before the
  release order.

## Heads (all local, unpushed)

- gfa-to-tabix main: this file's commit. Writer experiments for the format
  study: branch `format-additions` (~/src/gfa-to-tabix-additions, b3d9d1c when
  written; may have moved).
- graph-walks main b7b9349, still the release candidate and the vendored
  tarball (sha256 65917c45...). Branch `cohort-counts`
  (~/src/graph-walks-counts, d76aac2 plus uncommitted review fixes in flight).
- bandage-core `release-fixes` **a72f5dd** (~/src/bandage-core-rel): the six
  side branches, the placeholder label ration, gene names past a reserved box,
  `fitBesideKey`, the final graph-walks lockfile, "short skip", threading by
  pass with direction heads, and no spread of data-sized arrays into calls.
  Vendored tarball `walks8-pack/jbrowse-bandage-core-14.0.0.tgz` is from
  c09819a (sha256 57199761...), so it is **stale** and needs one repack at the
  final head.
- plugin `release-fixes` **46f92cf**
  (~/src/jb2plugins/jbrowse-plugin-graphgenomeviewer-rel; hand-linked
  `node_modules`, never `pnpm <script>` there, never `git stash` in that
  repository): hover-fix, graph-key, host-fit, switch, the unlabelled key
  line, `fitBesideKey`, and as commit 923612c the track's default layout fmmm
  (089e5b8 is the same tree with the old default). It does not typecheck
  against core a72f5dd: `legendSections.ts:191` lacks the key's new `heads`
  swatch kind (wiring owed).
- ggbandage: branch `integrated` 36c2c23 (~/src/ggbandage-integrated) and
  `pass-threading` fe973b8 (~/src/ggbandage-threading), by session
  ggbandage-7a; see its section in `2026-11-15-next-session.md`. Use those, do
  not redo the merge.
- BandageJS `switch-f8` 0819934d, tube map `switch-f8` 61fbd24 (reader wording
  and BandageJS's two fixes); not merged onto their format8 branches.
- jb2hubs, core-next, ggtubemap, the gallery rebase, the paper patch: untouched
  since the earlier plan.

## Branches not landed, and what each is waiting for

bandage-core, each in its own worktree:

- `node-order` 45c0e43 (~/src/bandage-core-nodeorder, on a72f5dd): the layout
  no longer depends on the order of segments and links (numeric-aware node
  sort, seven other leaks). Suite green on ada (1280). **Under review** with
  the next item.
- `perf-fix` db44ade (scratch `perf/core-fix`, on a72f5dd) and plugin
  `perf-fix` e628be0: the label search that hung CFH and took 89 s at amylase
  (a grid walked cell by cell at 0.05 px cells). Measured in the real page:
  amylase 90 s to 11 s, CFH hang to 20 s. Suite green on ada (1234). **Under
  review**; the reviewer was also asked whether `orientToReference` misreads
  ids ending in `-`.
- `gene-labels` (core bc0e2f0 when written, plugin 5b9f8c2; both moving), built
  on the two perf-fix branches: a gene is named once, on the reference; a
  haplotype's own copy only when lifted; genes without a symbol not labelled;
  labels laid out once per settled view. **Agent running.** CFH today is a
  wall of forty chips.
- `level-of-detail` 0deab74 plus uncommitted rework
  (~/src/bandage-core-lod): being reworked to `smallSites: 'hidden' | 'nodes'`,
  default hidden, ticks removed, threshold in bp at the reference's scale,
  small placeholders folded, one key line `N nodes too small to draw`, a
  `sites` table in figure data. **Agent running**; then it needs a short
  review and the checker's restated gate.
- `follow-placement` 542d2b9 plus rework (~/src/bandage-core-follow) and plugin
  `snap-cut` 5938ac5 plus rework (~/src/jb2plugins/...-snap): the track holds
  a cut snapped to a grid and slides the drawing between snaps (2 re-layouts
  per 20-step pan, was 20; every held pan step a pure slide). **Agent running**
  on making a zoom inside a level magnify continuously (scale from the view's
  width, never its position). Needs review after.
- `strand-flip-links` cd3da03 (~/src/bandage-core-strandflip, on a72f5dd): a
  mark and course for a same-end link. On the force layout the two marks
  overlap at one junction, and the gate found the marks hide neighbouring
  links at amylase. **Held**; only matters much for the straight layout.
- `shortcut-small` (~/src/bandage-core-shortcut-small, uncommitted prototype):
  "direct join", a far strand-flipping link drawn as a thin dotted line with
  room in the layout. Opens the amylase star at 8 and 16 haplotypes; 18 other
  cases byte-identical. **Held for the owner's look** (page below), and may be
  superseded by the engine session's work.
- `freq-encodings`, `layout-investigation`, `stiff-reference`,
  `shortcut-review`, `threading-review`, `lod-review`: prototypes and review
  scratch, not for landing. Width by haplotype count worked at forks in the
  prototype and is unbuilt; it needs the counting call below.

graph-walks:

- `cohort-counts`: `reader.counts` gives, for a window, how many of all the
  file's haplotypes step each node and link, each count exact or a flagged
  lower bound; same bytes as a cut, about 0.4 s. Reviewed: land with named
  changes (a truth sweep test, two fixtures, README wording without
  "frequency", two small code fixes). **Agent running** on those. Landing it
  changes the graph-walks tarball, so the CI pin, every consumer checksum and
  the hosted release-check follow.

## Agents still running when this was written

Each reports as the last assistant message of its transcript under
`/tmp/claude-1001/-home-cdiesh-src-gfa-to-tabix/b7daa067-b398-4a98-ad1e-976984ecca2b/tasks/`
(JSONL: extract the final message with a script, do not read whole). Their
scratch is under `.../b7daa067-.../scratchpad/<name>/`. /tmp may be cleared by
a reboot: read these first.

- `a4e49cdaf98555e98.output`: level-of-detail rework (scratch `lod2/`).
- `a8854096a9d4aafc3.output`: gene labels and one label pass (`genelabels/`).
- `adefd38ac1f47b213.output`: the format additions study (`format-additions/`;
  heavy runs on ada). It states each candidate (complete adjacency, a bubble
  decomposition, per-node counts, stored layout coordinates, and promoting the
  writer rule "no route interior holds a node the reference passes once" to a
  stated guarantee) both inside the walk file and as a side file, with
  measured cost, and recommends nothing. **When it reports, run the three
  fresh Fable reviews** (is it needed, which alternatives, what else), neutral
  briefs, different lenses.
- `a0236db9317db564a.output`: checker repair (`checker-heads/`): teach both
  checkers the lane heads (they crash today, so windows with backward lifted
  lanes are not drawn and silently dropped), fail a gate when a window does
  not draw, check head direction, and restate the visibility gate for folded
  sites. It asked to be resumed when the reworked level-of-detail branch is
  ready.
- `a35373ca96c0fb974.output`: review of `node-order` and both `perf-fix`
  branches, with the landing order.
- `ac617ef27d6e0c377.output`: snapped cut, zoom refinement (`snap-cut/`).
- `a04fa2dfe999af7d3.output`: the counts review's named changes
  (`counts-fix/`).
- `adb54a7daa63376d8.output`: blind count of the engine session's lift grids
  (`lift-blind/`): FINISHED, summarised under the engine session below.

## The engine session (graph-fmmm-layout-5f, another account): finished

It studied why the force layout lands different drawings from one graph, and
has wrapped up. Its handoff, kept outside /tmp:
`~/src/graph-fmmm-layout/agent-docs/handoffs/2026-11-16-fmmm-drawing-stability.md`,
with `code/` (`lifted.ts` and its test, `gentleSeeds.mjs`, `starts.ts`),
`tables/` and `sheets/` beside it. Read it before any layout work. Its numbers
are its own counts by eye unless a blind count here is named.

- **Closed with no change:** node ordering as a way to stabilise the picture
  (no order makes the picture a function of the graph; the numeric node sort
  was taken only so the layout does not depend on file order), a different
  random seed, quality 3 or 4, a different seed stretch, best-of-K, limiting
  how far the coarse levels relax, a two-phase layout, OGDF's swappable
  coarsening, and two deterministic prototypes (point forces; curve energy).
- **`lifted.ts`** (no engine change): a stretch that walks take reversed is
  started on an arch, on the side away from the off-reference seeds. At the
  chr1 inversion it removes the false figure-of-eight under every link order;
  it does not reduce stars, gives no gain on a clean inversion with no bubbles
  inside (that is one merged node), and does not fix amylase. An earlier form
  (`liftOnly`) had a strand bug and is not to be used. The side rule is
  confirmed by a control: the sharp corner at amylase follows whether the arch
  is on the seeds' side, not the absolute side.
- **Blind count of the lift grids by this session (done; 6,240 cells sealed
  before the key was opened; files in scratch `lift-blind/`,
  `phase1-counts.md`):**
  - Confirms the engine session's eye-scored cases: at the chr1 inversion the
    arch removes the figure-of-eight under every link order (baseline 6, 5, 6
    clear; arched 0 of 32 in all nine rows). Stars are not reduced and rise
    slightly (8/12/15 to 10/13/17); link order moves the star count more than
    the arch does.
  - Does NOT confirm its metric-scored counts on the synthetic cases, nor its
    note that the metric runs "about one low per row": the metric flags clean
    cells at the junction, duplication and nested cases and misses some clear
    crossings; its 35 degree star threshold passes visibly bent drawings as
    good. Any count of its from a metric needs a count by eye before use.
  - **The arch makes nested inversions clearly worse:** strict good falls from
    16 to 20 of 32 to 0 to 2, full stars rise from 0 to 1 to 5 to 14 (its
    "ruleStack" variant 24 to 27). At a duplication it turns good cells into
    mild stars under one link order.
  - The side of the arch matters a great deal at amylase (same side as the
    off-reference loops: sharp corners in 24 to 29 of 32; opposite side: 2 to
    5); the rewritten rule takes the opposite side, which is its only real gain
    over the first arch.
  - No setup draws a clean inversion (nothing inside it) well: a straight
    reference in 0 to 2 of 32 cells in every row, baseline included.
  - Not reviewed: the side-control and clean-inversion grids (codes in the key,
    no grids in `blind/`), anything drawn with the fixed `lifted.ts`, the final
    candidate's grids.
  - What the reader says must be drawn before the rule is a default: several
    real inversions of different sizes including one with nothing inside,
    real nested, adjacent and inverted-duplication loci, quiet loci and a ring
    with the fixed rule, a pggb window where it fires, and a nested variant
    that keeps the reference straight.
- **Its candidate, "Q":** `lifted.ts` plus the engine option `galaxyChoice:
  'uniform'` plus selective ring seeds (the reference seeded bowed where a
  skip spans at least 0.15 of it; needs per-point seeds) plus fan placement of
  off-reference pieces. Its counts at 32 seeds, three link orders: inversion
  32 of 32 (baseline 13 to 19), C4 syng 32 (29), C4 32 (30), the 571 bp gap 32,
  AMY2A 32, KIV-2 27 to 29 (27). Not rerun for those rows: CFH, GSTM1, sv49,
  KIV-2 loaded, amylase loaded. `uniform` without ring seeds and fan ships a
  worse KIV-2 at the default seed, so it must not be taken alone.
- **What Q needs:** the engine branch `point-seeds-galaxy-choice`
  (~/src/graph-fmmm-layout-point-seeds, uncommitted, on main 29c8011; adds
  `points` on a node and `galaxyChoice`; all 117 digest lines on main identical
  with the rebuilt wasm, 24 added), a port of the ring builder and fan
  placement into bandage-core's seeding, and a wasm rebuild. Landing the engine
  branch is the owner's call.
- **Owed here before any of it is taken:** a blind Fable read of
  `/tmp/claude-1001/-home-cdiesh-src-graph-fmmm-layout/2fc9745e-b28b-40c9-9774-909b2c23edca/scratchpad/sweep/final2/blind/`
  and of the new rows in `.../sweep/lift/blind/` (each has READ-FIRST.md; the
  key stays away from the reader; tables at `.../final2/table.md` and
  `.../lift/table.md`); the rows not rerun; the wider inversion cases the
  first blind reader listed; and BEFORE/AFTER pairs in JBrowse for the owner.
  Those grids are under /tmp and may be cleared by a reboot.
- If Q lands, the "direct join" rule and the strand-flip mark should be judged
  again against it; neither it nor `lifted.ts` fixes the amylase star.

## Gates, where they stand

- One command from the laptop runs everything on ada in about 12 minutes:
  `~/src/walks8-evidence/fab8f323/drawcheck-merged/ada-gates.sh <bandage-core
  commit> <baseline under runs/>` (`JOBS="suite"` for the suite alone). It
  needs the shared SSH connection (`ssh -O check ada` says "Master running");
  one invocation at a time across all agents. `ada/README.txt` beside it.
- At a72f5dd: ink-bound passes; visibility fails by one variant in each file
  (a 4 bp skip under other skips, a 1 bp node under reference nodes), which
  the level-of-detail rework should turn into folded sites; the link gate
  finds 20 links hidden on the force layout (14 inside larger off-reference
  pieces made of many tiny nodes: a following step, the gate keeps failing
  them) and far more on the straight layout; lifted lanes 0.02 px wide at
  Y-9.3M (the lane floor in level-of-detail fixes it). Run directories under
  `drawcheck-merged/runs/`.
- The gates at a72f5dd are partly blind until the checker repair lands (lane
  heads). Do not quote "nothing newly hidden" from that run.
- bandage-core's fold-parity test needs gfa-to-tabix 5.0.0; CI pins v0.12.0, so
  its CI fails until 5.0.0 is published (release-order item).
- bandage-core c09819a and later do not load in R's V8 without a shim:
  `graphLabels.ts:163` calls `new Intl.Collator` at module scope. ggbandage
  shims it; the right fix is in core (the numeric-aware comparison from
  `node-order`'s `canonicalOrder.ts` needs no Intl).

## Do, in order

- Read the running agents' reports. For each branch: apply its review's named
  changes, then land on `release-fixes` as a linear history. Proposed order
  (the node-order/perf review may correct it): `perf-fix`, `node-order`,
  `gene-labels`, `level-of-detail`, `follow-placement`; plugin: `perf-fix`,
  `gene-labels`, `snap-cut`, then the `heads` swatch and threading wiring
  (pass labels through `layoutLabels`, the pass bar, the hit-test argument).
  Remove the module-scope `Intl.Collator` in core.
- Land `cohort-counts` on graph-walks after its fixes; repack graph-walks;
  re-point the CI pin (`ci-pin-graph-walks-7`), retake consumer checksums.
- Resume the checker agent (or its successor) on the reworked level-of-detail
  branch; then run `ada-gates.sh` at the final bandage-core head. The gates
  must pass, or each failure must be a named, accepted item.
- Format: run the three reviews on the study's output; build what they accept
  (as side files where the study shows that suffices), with the hosted files
  left as they are unless a review requires otherwise.
- Readers, once the library head is final: BandageJS (adopt core's `graphKey`
  for its legend, `fitBesideKey`, the hit-test arguments, threading, the
  `sites` key line), the plugin (above), ggbandage (rebundle `integrated` and
  `pass-threading`), the tube map, ggtubemap, jb2hubs, core-next, the gallery.
  Repack bandage-core once.
- One reshoot in a real JBrowse at the final heads with the tooling in scratch
  `reshoot/tools/` (`rerun.sh <bundle> <plugin> <core> <graph-walks dir>`;
  "released" means the hosted plugin 9.1.0 on the plain-named file, not
  427d3fa), one change per pair, on one page for the owner. Then a blind Fable
  read of the AFTER pictures.
- Then the release order in `docs/handoff/2026-11-14-format-8-release.md`.

## Pages the owner has been reading (this session's artifact account)

- Findings: https://claude.ai/artifact/SPghLBjivYpssJWxn3wSd4
- Encodings, with "small sites not drawn": https://claude.ai/artifact/XjdAZktXVFDVmWb8EG42DM
- Layout candidates: https://claude.ai/artifact/SNUfpP9Tph9tP8DVE9mpoA
- Threading: https://claude.ai/artifact/MDoCmdjRvPowmimn4L999x
- Force layout and "direct join": https://claude.ai/artifact/2Ka7BRPjBEtJhytTzrbuGN
- Track pan continuity: https://claude.ai/artifact/PwF5kFHYiSuEBAYVPyYQZ5
- JBrowse layout pairs and the CFH hang: https://claude.ai/artifact/P9vXDFxLZByC83hokkUoCM

Page sources are under scratch `findings/`, `encodings/`, `layoutpage/`,
`threadpage/`, `forcepage/`, `contpage/`, `pairspage/`. A session under another
config directory cannot update them and must publish anew.

## Machine

- **Every agent runs its tests, suites, typechecks and renders on ada, not the
  laptop** (the owner said so three times; this session briefed most agents to
  run locally under a cap and had to redirect them mid-task). Put it in the
  first lines of every brief. `ada:~/work/walks8-gates/` holds a bandage-core
  clone with `node_modules` installed and the vendored graph-walks tarball in
  the same relative layout; agents work under
  `~/work/walks8-gates/agents/<name>/`. Rules: `ssh -O check ada` before every
  command, one command at a time, niced, check `free -g` and `uptime` first,
  no retry loops. Only headless-browser shots stay on the laptop.
- The laptop's disk is nearly full (about 5 GB free) and memory is tight. The engine session's scratch holds 12 GB. Old
  session folders under `/tmp/claude-1001/-home-cdiesh-src-gfa-to-tabix/`:
  7a96682c (6.9 GB) and fab8f323 (3.7 GB) are closed sessions whose gate
  inputs and reshoot tooling are hard-linked at
  `~/src/walks8-evidence/gate-inputs/`; 8d998258 (1.3 GB, 12 to 13 November,
  no evidence copy, has a HANDOFF.md) was inspected and held. None may be
  deleted without the owner's named go-ahead.
