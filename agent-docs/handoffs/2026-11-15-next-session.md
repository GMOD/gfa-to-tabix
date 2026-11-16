# Next session: walk format 8 release, where it stands and what to do, in order

Written at the end of session 7a96682c (2026-11-15, evening) as its context ran
out. The long running log of this session is
`2026-11-15-format-8-release.md` ("Fourth session"), one bullet per event;
this file is the ordered plan. Nothing is pushed, tagged, published or
uploaded except the hosted `-f8` walk files. A second session
(`gfa-to-tabix-c1`, cross-session address `uds:/run/user/1001/cc-socks/620472.sock`
while it lives) holds the reviews, the CI pin, core-next, jb2hubs, the
gallery repair and the paper patch; its index is
`~/src/walks8-evidence/fab8f323/INDEX.txt`. Evidence of this session is in
`~/src/walks8-evidence/22a29087/`.

## Update from session b7daa067 (gfa-to-tabix-97), which took over both lanes

Read this section first; it supersedes the lists below where they differ. The
second session (fab8f323) has closed; its last results are the final entries of
`~/src/walks8-evidence/fab8f323/FOR-NEXT-SESSION.txt`. Its gate inputs and the
reshoot tooling are hard-linked at `~/src/walks8-evidence/gate-inputs/`.
Nothing is pushed, tagged, published or uploaded.

- **The release is held on three serious readability findings** from a blind
  read of 50 pictures (Fable; notes in this session's scratch `blind-read/`).
  The owner's rule, now in memory as `surface-serious-issues`: a picture that
  is correct but not informative is a release-level fault, gets a Fable review
  and goes to the owner. Their page:
  https://claude.ai/artifact/SPghLBjivYpssJWxn3wSd4 (source in scratch
  `findings/`).
  - The plugin track at KIV-2, amylase and sv49 is buried under stacked "1 bp"
    placeholder labels. Decided rule: leader labels spend the existing label
    budget, largest bp first, and the key states the rest. Being implemented on
    `release-fixes`.
  - An inversion every shown haplotype carries is a flat line on the stress
    layout: the two strand-flipping links are plain links drawn under the
    nodes. Candidate fix on bandage-core branch `strand-links`
    (~/src/bandage-core-strandlinks, on dea6def, 82887f8 and 2cdcafa), not
    landed, not yet read blind. No gate drew the stress layout or tested
    whether a link is covered; the checker is being extended.
  - "Compress lengths" drew HG00133's 99.8 kb stretch as the smallest loop in
    the plugin's force_kiv2_overlay figure. `compress-rank` is landed; the
    plugin figure has not been retaken.
- **bandage-core `release-fixes` is 4c8451e**: the six side branches landed in
  the reviewed order (clearance-force, link-ends, compress-rank, nested-arcs,
  graph-key, host-fit) as a linear history, 42 commits on 43696f3, with the
  code review's named changes and tests. Suite 1159 passed, typecheck, lint,
  format clean (the integrator's run). Decided by a separate design review and
  landed: zero-length fallback strokes go over the nodes in the skip's ink and
  are keyed as a short skip; nested arcs kept; lifted lanes beside pushed
  alleles left as they are; no rule for the lost lens shape under FMMM; no
  re-layout on resize. The walks8-pack bandage-core tarball is stale until the
  label work lands and it is repacked.
- **Reader branches moved** (all unpushed): BandageJS `switch-f8` 0819934d,
  plugin `switch` 52c61c0, tube map `switch-f8` 61fbd24, all on graph-walks'
  own not-loaded text; their `node_modules` now resolve the final graph-walks
  tarball. Plugin `hover-fix` 1b4286b in
  ~/src/jb2plugins/jbrowse-plugin-graphgenomeviewer-hoverfix (on 95f291a):
  folded tube-map hover box and counts restored, the figure shooter on the
  `-f8` file, and a real fault fixed: hovering row "HG00133 HP1" lifted
  HG00133#2, because JBrowse now counts HP from 1.
- **BandageJS's 8 red gene tests** are not cleared by the gene rule: core
  reserves the key column against labels while BandageJS fits to the whole
  pane. Core fix under way with the label work; hosts then call one core fit
  helper.
- **Running when this was written:** the label work on `release-fixes`; the
  gates at 4c8451e plus stress windows and a link-ownership gate
  (`~/src/walks8-evidence/fab8f323/drawcheck-merged/`); a layout investigation
  (~/src/bandage-core-layouts, branch `layout-investigation`); frequency and
  level-of-detail prototypes (~/src/bandage-core-freq, branch
  `freq-encodings`). The last two were asked for by the owner and decide
  nothing until their contact sheets have been read blind.
- **Later the same session (state when this line was written):**
  - The owner's standing position, restated twice on 2026-11-15: the default
    layout is the force layout (fmmm) in every host, the plugin track
    included; no forced-straight or ruler-locked reference; haplotype
    threading as in ggbandage's gallery is the way to show complex walks and
    every reader must have it. Memory: `graph-not-linearized`,
    `threading-for-clarity`. A layout study in this session recommended a
    ruler-locked straight reference for the track; that recommendation is
    set aside.
  - bandage-core `release-fixes` c09819a: label rule landed (leader labels
    rationed to the label budget, key line "N unlabelled, X or less each"),
    gene names search past a reserved box, `fitBesideKey`, and the lockfile on
    the final graph-walks tarball. The checkout had held a stale graph-walks
    build under the same file name; it is reinstalled and the suite passes
    against the final reader (1166 passed). Tarball repacked:
    `walks8-pack/jbrowse-bandage-core-14.0.0.tgz` sha256 57199761..., the old
    one kept beside it as `.43696f3`.
  - Plugin `release-fixes` 923612c: hover-fix, graph-key, host-fit and switch
    landed, the key's unlabelled line and the fit through `fitBesideKey`
    wired, and as its last commit the track's default layout is fmmm (089e5b8
    is the same tree with the old default). A config or session naming no
    engine now draws force-directed.
  - Prototypes, uncommitted or on scratch branches, none landed:
    `strand-links` (~/src/bandage-core-strandlinks), `freq-encodings`
    (~/src/bandage-core-freq: level of detail and flow widths worked, fork
    dots and paler tones rejected, loading steps by default undecided),
    `layout-investigation` (~/src/bandage-core-layouts), `stiff-reference`
    (~/src/bandage-core-stiff, running), `threading`
    (~/src/bandage-core-threading: threading by pass being built properly on
    c09819a, plus a commit removing spread-into-call sites from core).
  - Running: the gates at 4c8451e with stress windows and a link-ownership
    gate; the stiffened force layout batch; the threading build; a JBrowse
    before/after reshoot (scratch `reshoot/`, with `manifest.jsonl`).
  - Owner's pages from this session: findings
    https://claude.ai/artifact/SPghLBjivYpssJWxn3wSd4, encodings
    https://claude.ai/artifact/XjdAZktXVFDVmWb8EG42DM, layouts
    https://claude.ai/artifact/SNUfpP9Tph9tP8DVE9mpoA, threading
    https://claude.ai/artifact/MDoCmdjRvPowmimn4L999x.
- **Still owed, in order:** repack bandage-core; blind read of the new
  pictures; land plugin `hover-fix`, `graph-key`, `host-fit`, `switch`;
  BandageJS, ggbandage, tube map and ggtubemap merges; jb2hubs; core-next
  rebases; gallery redraw; final reshoot and the owner's page; then the
  release order.

## Settled

- Format 8 is frozen as it is: two independent designs, a pangyplot-informed
  review, and the spec-sentence reviews all say no byte change. The spec text
  is true (gfa-to-tabix main through 1b4cf89 and later handoff commits);
  check-claims 178/178/0 both ways, broken.sh 132 files, cargo test green.
- Hard cutover, decided by the owner: nothing stays on format 7; the plain
  hosted names take format 8 once plugin 10 is on `latest/`; the `-f8` names
  stay canonical.
- Hosted: `hprc-v2.1-mc-grch38-f8`, `-chm13-f8` and
  `-grch38-chr6-sequences-f8` carry `graph:Z:` and `leftout:i:`, byte-checked
  against the old pair, leftout counted independently from the GBZ, release
  check 28/28 at graph-walks 4b14ee3, ADR 0015 filled.
- ADR 0012 acceptance runs all pass (`docs/walks-container/accept-5.0.0/4b14ee3/`);
  the kept-node drop at the worst window is the attach rule, not a defect.
- gfa-to-tabix's whole CI passes locally on the pin branch
  `ci-pin-graph-walks-7` (second session, ~/src/gfa-to-tabix-ciaudit; it
  points at graph-walks 4b14ee3 and must be re-pointed once more, below).
- graph-walks is fit to tag per the reader diff review, subject to the
  pre-tag branch below.
- The gate "nothing carried may be invisible" is ruled by the second session:
  no hidden carried variant whose own node is 1 px or longer or whose edit
  spans 1 px or more at the fit; the merged checker passes it at
  `nested-arcs` e9bf00b.

## Heads now (all local, unpushed)

- gfa-to-tabix main: this file's commit. graph-walks main b7b9349, FINAL:
  `pre-tag` landed (revisited listed as breaking, tables() tolerant of
  hand-built fragments, abridgedText now `<walk>: <bp> off the reference not
  loaded` with no step count because the format states a run only as bp,
  `AbridgedWalk` is `{ name, bp }`, header keys left out when unstated,
  presets frozen, the review's three tests; suite 761). bandage-core `release-fixes` 43696f3 in
  ~/src/bandage-core-rel. Plugin `release-fixes` 95f291a in
  ~/src/jb2plugins/jbrowse-plugin-graphgenomeviewer-rel (hand-linked
  node_modules; never run `pnpm <script>` there). ggbandage `format8` 2b92eed.
  BandageJS `format8` 6564a9db. sequenceTubeMap `format8` fe32331. ggtubemap
  `format8` 83dcce6. jb2hubs `format8` 9fe89efb2220 (second session's).
- Vendored tarballs in ~/src/vendor/walks8-pack/: graph-walks 7.0.0 from
  b7b9349 (sha256 65917c45..., final unless a review forces a change),
  bandage-core 14.0.0 from 43696f3 (86187563..., goes stale with the
  landings below; the final pass repacks it).

## Agents that were still running when this session stopped

None: all reported before the session ended; their results are below.

Their branches exist with the heads listed; each may have added commits or a
reply after this file was written. Read `git log` in the worktree and the
task output under
`/tmp/claude-1001/-home-cdiesh-src-gfa-to-tabix/7a96682c-92be-45ca-9e3d-55bf7fb5184d/tasks/`
(the agent's JSONL transcript; its last assistant message is the report).


## Side branches ready, not landed (bandage-core unless said)

- `nested-arcs` e9bf00b (~/src/bandage-core-arcs, on 519f0b4): gate passes;
  two calls for the review: keep fallbacks under the nodes (my lean: yes),
  and the ring look of stacked loops on 1 to 2 px chords.
- `graph-key` 0946b2f (~/src/bandage-core-graphkey, on 519f0b4) with plugin
  `graph-key` 1d99f35, BandageJS `graph-key-f8` 85e51d88, ggbandage
  `graph-key` d3aa173: one `graphKey` from what is drawn, with a census test;
  figureData `labels`, `meta.inks`, `meta.graphKey`. BandageJS's 8 gene-label
  e2e tests were red against 519f0b4's gene rule; expect 43696f3 to clear
  them; confirm.
- `compress-rank` 0299985 (~/src/bandage-core-rank, on 43696f3): compress
  ranks loops by total bp.
- `link-ends` dea6def (~/src/bandage-core-linkends, on 43696f3): lane on the
  right link, arrows with the reference, lane joins, hit test strandedness
  required.
- `host-fit` b3054d0 (~/src/bandage-core-hostfit, on 43696f3; plugin `host-fit`
  31c1723, BandageJS `host-fit-f8` 2a9757af, ggbandage `host-fit` 76d0297):
  `forceLayout(graph, settings, engine, fit?)` sizes the clearance and the
  compress floor for the host's pane (the plugin passes width less the key
  column and track height less the strip; BandageJS its canvas; the figure
  path `figureFit(spec)`, 1200 by 800 by default); `ASSUMED_FIT` 1200 by 280
  when none; the fit is in the cache key. Tests in all four repos; core 1080.
  Pictures `*host-fit*`: KIV-2 in the plugin pixel-identical (it binds on
  height); ggbandage at 900 by 450 under compress no longer puts alleles on
  long sticks. To know: figures taller than about 0.18 of their width now
  draw a narrower, correct allele gap, so committed renders differ; on
  resize no host re-lays out, and below about 0.8 of the room the layout was
  sized for ink starts to touch (recommended: re-apply the cheap clearance
  pass on shrink, not the engine).
- `clearance-force` 9da7c22 (~/src/bandage-core-clearforce, on 43696f3):
  `clearOfReference` runs only under the stress engine (pipeline.ts:272);
  FMMM leaves the engine's positions; README 119-124; a test fails on
  43696f3. Pictures `*clearance-force*`: bandage-core's kiv2_walks figure,
  the plugin's force_kiv2_overlay and syng_c4 and the KIV-2 FMMM view are
  clean again; KIV-2 stress pixel-identical; the 571 gap FMMM loses the
  lens-shaped alleles 7351107 gave it where FMMM's reference is nearly
  straight (a real loss); force_gstm1_walk keeps its teeth because the
  plugin's track uses stress and a lifted lane steps out to each pushed
  allele and back (needs a rule for lifted lanes beside pushed alleles).
  Also seen: the KIV-2 views, stress and FMMM, are flooded with stacked
  "1 bp" placeholder labels on leaders, from 4c673cb (placeholders skip the
  drawn-length gate): the review must decide the rule for one-step
  placeholders (a floor on the label count, or lengths under some bp
  summarised).
- Readers' switch-over to graph-walks' presets and counts, each on a branch
  off its format8 head, package.json and lockfile pointing at a scratch
  tarball uncommitted: BandageJS `switch-f8` 74fd1e1d, plugin `switch`
  f3d5690 (carets ^7.0.0 and ^14.0.0, lockfile for publish time), tube map
  `switch-f8` 29e0b92, ggtubemap `switch-f8` 307f474, ggbandage `switch`
  b27dcc5. They must take `pre-tag`'s abridgedText wording.
- Second session's: ggbandage `gallery-format8` 1f9e112 (rebase and redraw on
  the final core), core-next branches (BandageJS `core-next-f8`, plugin
  `core-next`), jb2hubs `format8`, `ci-pin-graph-walks-7`, the paper branch
  ~/paper-format8-text `format8-text` and the jbrowse-components patch
  `~/src/walks8-evidence/fab8f323/paper/jbrowse-components-paper-figures-plugin10.patch`.

## Do, in order

- graph-walks is done (b7b9349, tarball 65917c45...); the second session
  re-points the pin and reruns the rebuild job at it. The readers'
  switch-over branches must take the new abridgedText (`{ name, bp }`, no
  step count): BandageJS derived.ts, the tube map's AbridgedWalksPanel, the
  plugin's abridged list and jb2hubs still read `steps`.
- One Fable review of the six bandage-core branches (nested-arcs, graph-key,
  compress-rank, link-ends, clearance-force, host-fit), plus the two
  stress-layout items clearance-force left (lifted lanes stepping to pushed
  alleles; the "1 bp" label flood at KIV-2) as the earlier batch
  reviews were run: criteria first, a mutant per branch, composition in a
  scratch merge, landing order, the two nested-arcs calls, the ring look,
  BandageJS's gene tests. Land in its order on release-fixes (core, plugin,
  BandageJS, ggbandage), with its named changes. Repack bandage-core.
- Queued drawing fixes from the redraw audit, not started: the plugin's
  tube-map hover lost its red box and "N of M haplotypes here" counts
  (3bad160 suspect; docs/tube-maps.md); BandageJS's rows draw a not-loaded
  stretch as charcoal off-path with no marking (rows do not get the cut's
  placeholders) and its link hover still says "Deletion"; labels covering
  what they name (plugin force_kiv2_open, force_kiv2_bubbles,
  ordered_micb_link_width); the plugin's scripts/shoot-figures.mjs feeds the
  plain (format 7) name, and against hosted JBrowse main its lane-ordering
  step and tube_map_micb_row_hover throw; the tube map's .gbz.db backend
  still cuts with gbz-base's 100 bp context; ggtubemap draws no departure
  nodes (needs a shared `walkTracks` in graph-walks, after the tag).
- Final consumer pass on the final tarballs: merge each switch-over, graph-key
  and host-fit reader branch onto its format8 branch, retake checksums, full
  suites; the plugin from scratch; ggbandage rebundled; the second session's
  jb2hubs, core-next rebases, gallery redraw (kiv2_overlay with and without
  compress), merged checker rerun with the ink-per-node and link-ends gates,
  vg-slice equality through the final tarball.
- Final reshoot at the final heads (tooling under this session's scratch
  `reshoot-final/`, copied by each fix agent): every locus and view, the
  two paper figures (paper/cohort_views, paper/hprc_lanes_graph_stacked_force)
  with lengths on, KIV-2 force with lifted walks, Y-rand-10 arrows, the C4
  threading figure, pggb rows with the final wording, and say which
  haplotypes a fresh user gets by default. The second session puts the pairs
  on one page for the owner, ordered by how much each changed. The owner's
  look is the last gate.
- Release, per `docs/handoff/2026-11-14-format-8-release.md` "Order of the
  release" (updated today: both paper configs to plugin 10 with lengths on;
  the cutover upload over the plain names once plugin 10 is on `latest/`;
  the pin branch lands last before the gfa-to-tabix push, after graph-walks
  is on GitHub). bandage-core: package.json's graph-walks `file:` becomes
  ^7.0.0, CHANGELOG from the reviewed notes
  (`~/src/walks8-evidence/fab8f323/release-notes/*.reviewed.txt`), revisited
  and the hit-test arguments named as breaking.

## Standing rules learned this session (also in memory)

- No unnecessary deviation between readers; every deviation moved to core or
  reported with its reason (`agent-docs/reader-deviations.md` is the list;
  the graph key, labels, cut presets, not-loaded counts and hover list are
  done; the rest is listed there).
- Every drawing change: BEFORE/AFTER pairs, including force layouts, and a
  check that can fail (the merged checker's gates, the link-ends check, the
  ink-per-node check).
- Checks must fail when broken; a claim with no failing case is unproved.
