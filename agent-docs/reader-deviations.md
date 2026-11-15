# Reader deviations from core, audited 2026-11-15

The owner's rule: no unnecessary deviation between ggbandage, BandageJS, the
JBrowse graph plugin, jb2hubs, sequenceTubeMap and ggtubemap; every deviation
is moved into a shared library or reported here with its reason. Audited at
bandage-core release-fixes 71ab29e, graph-walks c6457d3, BandageJS format8
6564a9db, plugin release-fixes 3bad160, ggbandage format8 bdf959c, jb2hubs
format8 9fe89efb2220, sequenceTubeMap format8 fe32331, ggtubemap format8
f03fc4d. Lines are the auditor's reading; verify before acting on one.

Licences decide where a shared rule can live: bandage-core is GPL-3.0, the
two tube maps are MIT, so anything they share goes into graph-walks or
tubemap-core (marked "graph-walks" below).

## Rules a reader re-implements, most visible first

- **The graph key is assembled four times.** Plugin `legendSections.ts`
  (ramp :227, off-reference :233, exon :444, depth and link-width rows);
  BandageJS `overlays.ts:348-426` (no short-skip, depth or link-width rows);
  ggbandage `autoplot.R:124-182` ("X position, Mb", "off the X path", a
  revisits caption no other reader has); core's `figureSvg` a fourth
  (`figure.ts:530-575`). Move to core: `graphKey(graph, layout, opts)`
  returning key entries, rendered by figureSvg, figureData.meta, the plugin
  and BandageJS.
- **The reference's name is missing from figures.** ggbandage
  (`scripts/figure.mjs`) and jb2hubs (`pangenomeGraphLayout.worker.ts:22`)
  never pass `referenceName`, so their keys say "the reference" where the
  others say "GRCh38 chr6". Move to core: figureSvg and figureData default
  it to `referenceLabel(graph, region)`.
- **Walk-file cut rules differ, so one region draws a different graph.**
  Context 1000 in BandageJS (`walkFiles.ts:49`), jb2hubs
  (`pangenomeWalkCut.ts:17`), ggbandage (`engine.R:180`) and the plugin;
  100 in sequenceTubeMap (`WalkFiles.ts:8`); 0 in ggtubemap (`data.R:65`).
  `contained: true` only in jb2hubs. nodeLimit 100k in BandageJS, 30k in
  jb2hubs, none elsewhere. `attachBp` 0 in ggtubemap, unlimited in
  ggbandage. Move to graph-walks: named cut presets (`browser`, `figure`)
  and the context constant. The R readers lifting byte and step budgets must
  differ, since R waits for one region with no window to protect.
- **Hovering a placeholder in BandageJS** (`describe.ts:81`) prints name, bp
  and depth; the plugin calls `placeholderHoverText`. Move: BandageJS calls
  it.
- **Node hover text built twice** with different lines (BandageJS
  `describe.ts:81-101`, plugin `HoverTooltip.tsx:66-95`); the edge hover's
  text copied in both. Move to core: `nodeHoverText(node, ctx)`, and
  `edgeHoverText` returning whole strings.
- **Not-loaded steps and bp counted four times** (BandageJS
  `derived.ts:70-111`, jb2hubs `pangenomeWalkCut.ts:64-111`, sequenceTubeMap
  `WalkFiles.ts:239-258` without departures, plugin `unloadedWalks.ts:12`)
  with four formatters. Move to graph-walks: `abridgedWalks(tables)` and
  `abridgedText()`, re-exported by bandage-core.
- **An abridged walk in a tube map** is left out by sequenceTubeMap
  (`WalkFiles.ts:68`) and drawn as a "nodes not shown" box by the plugin.
  Move to graph-walks/tubemap-core: tracks that keep a placeholder step and
  a box kind for it.
- **Tube-map tracks built twice**: sequenceTubeMap joins fragments through
  departure own steps (`WalkFiles.ts:133-205`); ggtubemap uses bare
  fragments (`tools/walks.js:13-28`). Move to graph-walks: `walkTracks`.
- **ggtubemap's departure wording** (`walks.R:51-75`) differs from core's
  `departureText`. Move to graph-walks (licence).
- **ggbandage node labels** (`geoms.R:220-253`) are GFA names with
  `check_overlap`; core labels lengths with placeholders always. Move to
  core: a `labels` table in figureData from `layoutLabels`.
- **ggbandage gene-label placement** (`geoms.R:266-283`) is its own; same
  `labels` table.
- **ggbandage exon colour and swatch**: `#e8a200` filled bar (`geoms.R:341`,
  :325) against core's `#daa520` outline. Move to core: inks in
  figureData.meta.
- **ggbandage walk-row wording and blocks**: its own run-kind names
  (`walkrows.R:67`), "no ribbons" text (:75), ribbon key (:274), block fills
  (:295) and a 1.2% block filter that renumbers letters (:101). Move to
  core: `walkRowsData()` with key entries, palette and letters.
- **ggbandage walk lookup** by name prefix (`figure.mjs:57`) and W/P
  re-parsing with pass numbering in R (`engine.R:91-118`). Move to core: a
  `steps` table in figureData; matching through `filterSamples`.
- **Node-count refusal** worded by the plugin (`loadActions.ts:110-118`) and
  BandageJS (`sources.ts:166-170`), core's text unused. Move to core:
  `nodeLimitText`.
- **Where a walk passes a node**: BandageJS `placedWalks` uses `walksThrough`
  plus departures; the plugin's `nodeAssemblySpans` (`contributors.ts:57-90`)
  reads `pathVisits` only. Move to core: `walkPlaces(graph, node)`.
- **Walk-row hover**: BandageJS `rowHtml` (`describe.ts:115-127`) against the
  plugin showing the readout only when cut (`fitViews.ts:212`). Move to
  core: `walkRowHoverText`.
- **SVG export loses node-length labels** in both canvas readers. Move to
  core: one `figureSettingsOf(host settings)`.
- **jb2hubs restates graph-walks constants** (`minCarriersFor`,
  `STRUCTURAL_BP`, `pangenomeSvStates.ts:19-29`). Move: import them.
- **jb2hubs prose for changes** (`plainName`, `pangenomePanels.ts:84-105`).
  Move to graph-walks as `markWords`.
- **Small restatements**: BandageJS `DEFAULTS` (`settings.ts:49-67`) repeats
  `ENGINE_DEFAULTS`; ggbandage `bandage_hues` (`scales.R:15`) repeats the
  ramp. Move: read core's values.
- **Plugin walk-row bars through render-core spans** (`walkRowSpans.ts`)
  copy `walkRowsTree`'s geometry. Must differ for scale (thousands of rows
  on canvas); core should export the span geometry so they cannot drift.

## Must differ, with the reason

- **jb2hubs "net +N kb" marks** (`pangenomePanels.ts:55-66`): the sidecar
  callset gives a size change with no route, a kind graph-walks lacks. Kept
  this release (second session's ruling); a `net` kind there if wanted.
- **jb2hubs uses the stress layout and the grey scheme**: a 434 KB wasm
  download on a public page. Its other claim, that FMMM tangles at that
  size, is a question for core's default.
- **Tube maps draw no deletion edges**: a tube routed round a box is the skip
  mark, by design.
- **The website draws no genes**: the page's design, one change in focus.

## Capability gaps

- **BandageJS lacks** ribbons, shared blocks and order in walk rows; link
  width by walks; depth, frequency, link-width and short-skip keys; the
  reference strip; walk-row groups; frequency widths outside a URL
  parameter. All but grouping exist in core: wire them up.
- **The plugin lacks** genes in the node hover, a node's walk list with
  places, per-walk not-loaded bp: the hover and `walkPlaces` helpers above.
  Haplotype threading: the graph half already matches ggbandage; walk rows
  on a lifted walk's own ramp, rows by haplotype and the thread key line are
  being moved into core (branch `row-ramps`).
- **ggbandage lacks** bubble halos, the walk strip, the reference strip,
  depth, not-loaded and short-skip key entries, placeholder labels:
  figureData emits them.
- **Only ggbandage reads a VCF's AT tags for node frequencies**
  (`frequencies.R:28-116`). Move to core: a JS reader, so the canvas readers
  can width nodes by a callset.
- **figureSvg cannot export** grouped walk rows or tube maps. Add both.

## Order

- `graphKey` in core with `referenceName` defaulting to `referenceLabel`.
- Cut presets in graph-walks.
- Placed labels, inks and keys in figureData.
- Not-loaded counting and text in graph-walks.
- The hover helpers.
- The rest, as listed.
