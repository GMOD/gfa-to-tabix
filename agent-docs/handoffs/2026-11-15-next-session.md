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

Their branches exist with the heads listed; each may have added commits or a
reply after this file was written. Read `git log` in the worktree and the
task output under
`/tmp/claude-1001/-home-cdiesh-src-gfa-to-tabix/7a96682c-92be-45ca-9e3d-55bf7fb5184d/tasks/`
(the agent's JSONL transcript; its last assistant message is the report).

- bandage-core `clearance-force` (~/src/bandage-core-clearforce, 9da7c22):
  the clearance only on the stress engine, which lays the reference straight;
  force pictures were still rendering. Task a5b0379ca4f063d0c.

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
- `clearance-force` above.
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
  compress-rank, link-ends, clearance-force, host-fit) as the earlier batch
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
