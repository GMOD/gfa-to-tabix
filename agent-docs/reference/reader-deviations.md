---
name: reader-deviations
description: How BandageJS, the JBrowse graph plugin, ggbandage, jb2hubs, the tube map and ggtubemap differ from one another and from the shared libraries, read at each repository's remote head on 2026-11-20.
---

# Reader deviations from core, audited 2026-11-20

The rule: no unnecessary deviation between ggbandage, BandageJS, the JBrowse
graph plugin, jb2hubs, sequenceTubeMap and ggtubemap. Every deviation is moved
into a shared library or recorded here with its reason, and a capability one
reader has and another lacks counts as one. Each entry is the auditor's
reading of the code at the heads below; check the lines before acting on one.
The rows this page is written from are in
`~/src/walks8-evidence/followup-20261120/audit/deviations.jsonl`.

Licences decide where a shared rule can live: bandage-core is GPL-3.0 and the
two tube maps are MIT, so what the tube maps share goes into graph-walks or
tubemap-core.

## Read at

- graph-walks `origin/main` 3c324d0 (8.0.1 + 2 commits)
- bandage-core `origin/main` 0a0964b (14.1.0 + 5 commits (renderer only))
- tubemap-core `origin/main` 1140aba (2.0.1 + 2 commits)
- BandageJS `origin/main` c304b31 (pins bandage-core ^14.1.0, graph-walks ^8.0.1)
- jbrowse-plugin-graphgenomeviewer `origin/main` b842bb7 (10.1.1)
- ggbandage `origin/main` 370f69d (bundle is bandage-core 14.1.0)
- jb2hubs `origin/main` 67af56e (website pins bandage-core ^14.1.0, graph-walks ^8.0.1)
- sequenceTubeMap `origin/master` b5f1bda (pins graph-walks ^8.0.1, tubemap-core ^2.0.1)
- ggtubemap `origin/main` a6bb28f (pins graph-walks ^8.0.1, tubemap-core 2.0.1)

## Rules a reader re-implements

### A user sees it at once

- **BandageJS, jbrowse-plugin-graphgenomeviewer, jb2hubs, sequenceTubeMap,
  ggbandage, ggtubemap:** One region is drawn by one reader and refused by
  another: the node cap is 100,000 at the cut in BandageJS, 20,000 after the
  cut in the plugin (settable 5,000 to 100,000), 30,000 on the website, 50,000
  in sequenceTubeMap and none in the R readers. Changed since the last audit.
  Home: graph-walks: a nodeLimit in CUT_PRESETS.browser (the presets carry
  context, contained, attachBp and budgets but no node limit). The R readers
  lifting it must differ: a figure waits for one region. At
  `BandageJS:src/walkFiles.ts:48`;
  `jbrowse-plugin-graphgenomeviewer:src/GraphGenomeView/pane/paneBase.ts:177`;
  `jbrowse-plugin-graphgenomeviewer:src/GraphGenomeView/pane/loadActions.ts:126-135`
- **jb2hubs, BandageJS, jbrowse-plugin-graphgenomeviewer, sequenceTubeMap,
  ggbandage, ggtubemap:** The website cuts each walk to the window (contained:
  true) and restates the 1000 bp context, so a copy-number locus shows fewer
  nodes there than in the five readers that spread a graph-walks cut preset.
  Changed since the last audit. Home: graph-walks: jb2hubs spreads
  CUT_PRESETS.browser and imports WALK_CONTEXT; if the page keeps contained
  cuts, a named preset for it. Context and attachBp now agree in the other
  five (sequenceTubeMap was 100, ggtubemap 0). At
  `jb2hubs:website/src/pangenome/pangenomeWalkCut.ts:17`;
  `jb2hubs:website/src/pangenome/pangenomeWalkCut.ts:40-49`;
  `BandageJS:src/walkFiles.ts:43-50`
- **BandageJS, jbrowse-plugin-graphgenomeviewer:** The same switch has a
  different name in the two canvas readers: 'Deletion edges' against 'Show
  links that skip reference', 'Bubbles' against 'Show bubble halos', 'Genes'
  against 'Show genes on the backbone', 'Bars under the graph' against 'Show
  walk rows under the graph', 'Colour every haplotype' against 'Draw paths'.
  New since the last audit. Home: bandage-core: one table of drawing layers
  with their labels and defaults, as LAYOUT_MODES and NODE_WIDTHS already are;
  BandageJS's 'Deletion edges' also breaks the links-are-data wording. At
  `BandageJS:src/menuItems.ts:175-201`; `BandageJS:src/menuItems.ts:321-326`;
  `jbrowse-plugin-graphgenomeviewer:src/GraphGenomeView/pane/launchActions.ts:386-407`
- **ggtubemap, sequenceTubeMap, jbrowse-plugin-graphgenomeviewer, BandageJS:**
  Read strand colours are swapped: ggtubemap paints forward reads red and
  reverse blue, sequenceTubeMap and bandage-core's tube map paint forward blue
  and reverse red. New since the last audit. Home: tubemap-core: exported
  forward and reverse read palettes (bandage-core restates sequenceTubeMap's
  blues and reds by hand too). At `ggtubemap:R/geoms.R:130-131`;
  `sequenceTubeMap:src/util/visOptions.ts:113-118`;
  `sequenceTubeMap:src/util/palettes.ts:27-41`
- **sequenceTubeMap, ggtubemap, BandageJS, jbrowse-plugin-graphgenomeviewer:**
  A walk's tube differs by reader: sequenceTubeMap joins a walk's pieces
  through a departure's own steps, ggtubemap draws bare pieces and drops
  departures, and the tube map mode of BandageJS and the plugin builds tracks
  from the graph's paths. Home: graph-walks (MIT, so both tube maps and
  bandage-core can import it): walkTracks(tables) returning tracks with joined
  pieces. At `sequenceTubeMap:src/api/walks/WalkFiles.ts:135-215`;
  `ggtubemap:tools/walks.js:13-28`; `ggtubemap:tools/walks.js:63`
- **sequenceTubeMap, BandageJS, jbrowse-plugin-graphgenomeviewer:** A walk the
  file abridged has no tube at all in sequenceTubeMap (it is listed in a panel
  beside the map), where the plugin's and BandageJS's tube map draw a box
  marked 'nodes not shown' in its place. Home: graph-walks walkTracks keeping
  a placeholder step, and tubemap-core a box kind for it (both MIT). At
  `sequenceTubeMap:src/api/walks/WalkFiles.ts:123-127`;
  `sequenceTubeMap:src/api/walks/WalkFiles.ts:163-178`;
  `sequenceTubeMap:src/components/AbridgedWalksPanel.tsx:64-79`

### A user sees it on a second look

- **ggbandage, jbrowse-plugin-graphgenomeviewer:** Shared-block colours and
  letters are written in two readers with slightly different hexes (#d4785f
  #d9a94e #c98aa3 against #d4735e #d8a94a #c98aa4), and ggbandage drops blocks
  under 1.2% of the longest row and renumbers the letters. Changed since the
  last audit. Home: bandage-core: palette, lettering and the size filter
  beside walkRowBlocks. At `ggbandage:R/walkrows.R:89-94`;
  `ggbandage:R/walkrows.R:179`; `ggbandage:R/walkrows.R:370`
- **BandageJS, jbrowse-plugin-graphgenomeviewer:** The exported SVG writes
  node lengths even when the user turned them off on screen, since neither
  reader passes its node-length setting to figureSvg; BandageJS also leaves
  out the connector thickness and colour domain the plugin passes. Changed
  since the last audit. Home: bandage-core: one figureSettingsOf(host
  settings). Changed since the old audit: the default flipped to lengths on,
  so the export now adds labels where it used to lose them. At
  `BandageJS:src/figure.ts:36-59`;
  `jbrowse-plugin-graphgenomeviewer:src/GraphGenomeView/pane/fitViews.ts:847-877`;
  `bandage-core:src/figure.ts:369-372`
- **jb2hubs:** The website counts and words abridged walks itself ('HG002#1:
  1.2 k steps, 40 kb not loaded', by haplotype with a step count), where
  BandageJS, the plugin and sequenceTubeMap now print graph-walks'
  abridgedText. Changed since the last audit. Home: graph-walks: jb2hubs
  imports abridgedWalks and abridgedText; a step count and a by-haplotype
  grouping there if the page keeps them. At
  `jb2hubs:website/src/pangenome/pangenomeWalkCut.ts:54-109`;
  `jb2hubs:website/src/pangenome/PangenomeGraph.tsx:28-29`;
  `graph-walks:src/abridgedWalks.ts:8-49`
- **BandageJS, jbrowse-plugin-graphgenomeviewer, ggbandage, jb2hubs,
  sequenceTubeMap, ggtubemap:** Which abridged walks are read in full differs:
  the R readers read every one, BandageJS reads lifted walks and falls back
  when over budget, the plugin reads up to 64 for a tube map or walk rows,
  sequenceTubeMap and the website only on a click. New since the last audit.
  Home: graph-walks: the expand policy as part of the cut presets (figure:
  all; browser: lifted walks, retried abridged when over budget, which only
  BandageJS does today). At `ggbandage:scripts/walks-cut.mjs:31`;
  `ggtubemap:tools/walks.js:58`; `BandageJS:src/walkFiles.ts:86-102`
- **BandageJS, jbrowse-plugin-graphgenomeviewer, ggbandage, jb2hubs,
  sequenceTubeMap:** One thing has three names: the graph key and hovers say
  'nodes not shown', menus and panels say 'N kb off the reference not loaded',
  and the website and sequenceTubeMap say 'abridged'. New since the last
  audit. Home: graph-walks: one phrase, which bandage-core's NOT_LOADED_TEXT
  then imports. At `bandage-core:src/gfa/departures.ts:216`;
  `graph-walks:src/abridgedWalks.ts:47-49`;
  `jb2hubs:website/src/pangenome/PangenomeGraph.tsx:28-29`
- **BandageJS, jbrowse-plugin-graphgenomeviewer, ggbandage:** Apart from
  links, one drawing setting has three spellings: BandageJS links say layout=,
  color=, width=, smallsites=; the plugin's slots are layoutMode,
  encoding.color, size and layers.smallSites; ggbandage and a figure spec say
  layout, colorScheme, nodeWidth and small_sites. New since the last audit.
  Home: bandage-core: the figure spec's names as the one vocabulary, with each
  host mapping to it in one place; the plugin's grammar-of-graphics slots may
  have to differ as JBrowse config. At `BandageJS:src/settings.ts:165-183`;
  `jbrowse-plugin-graphgenomeviewer:src/LinearGraphDisplay/configSchema.ts:29-128`;
  `jbrowse-plugin-graphgenomeviewer:src/GraphGenomeView/nodeSize.ts:23-36`
- **BandageJS, jbrowse-plugin-graphgenomeviewer:** Hovering a node prints
  different lines: BandageJS gives 'refName:pos (rank n)' and each gene with
  'intron here' or 'N exons here'; the plugin gives 'and N more' for merged
  nodes, the sample's own span, a 'Reference' line and the genes as one italic
  list. Home: bandage-core: nodeHoverText(node, ctx) returning lines, beside
  placeholderHoverText, which both now call. At
  `BandageJS:src/describe.ts:64-109`;
  `jbrowse-plugin-graphgenomeviewer:src/GraphGenomeView/components/HoverTooltip.tsx:56-119`;
  `bandage-core:src/hoverText.ts:42-47`
- **ggbandage, BandageJS, jbrowse-plugin-graphgenomeviewer:** ggbandage's walk
  rows use their own words and colours: 'on the reference's path' in charcoal
  and grey where bandage-core's key says 'on GRCh38's path' in blue and
  purple, its own ribbon entries, and a 'no ribbons' note. Home: bandage-core:
  walkRowsData() emitting walkRowsKey's entries and inks, as
  figureData.meta.graphKey does for the graph. At
  `ggbandage:R/walkrows.R:70-87`; `ggbandage:R/walkrows.R:470-473`;
  `ggbandage:R/walkrows.R:493-512`
- **BandageJS, jbrowse-plugin-graphgenomeviewer:** A walk row's hover differs:
  BandageJS shows label, length and the contig span; the plugin shows the
  readout, and only when the row is thin or its readout is cut. Home:
  bandage-core: walkRowHoverText(row, reference). At
  `BandageJS:src/describe.ts:146-156`;
  `jbrowse-plugin-graphgenomeviewer:src/GraphGenomeView/pane/fitViews.ts:279-286`
- **ggtubemap:** ggtubemap's warning words a departure its own way ('leaves
  the reference at X and rejoins it at Y, with N bp of its own between') and
  always says 'of its own', where bandage-core says 'no step on GRCh38 across
  54 kb' and says 'off the reference's path' unless the file counts no
  revisited node. Home: graph-walks (bandage-core is GPL, ggtubemap MIT):
  departureText and ownAmount move down a library. At
  `ggtubemap:R/walks.R:51-68`; `ggtubemap:R/walks.R:86-108`;
  `bandage-core:src/gfa/departures.ts:138-159`

### Seen only side by side

- **ggbandage:** The pass bar is placed again in R: the side margin, the px
  per letter and the rule for leaving a name off are restated, and the axis is
  ggplot's ('kb along <walk>') in place of bandage-core's ticks. New since the
  last audit. Home: bandage-core: figureData emits the pass bar's placed
  names, joined runs and ticks (it emits passes and passRuns only). At
  `ggbandage:R/autoplot.R:162-276`; `bandage-core:src/passBar.ts:69-70`;
  `bandage-core:src/passBar.ts:84-214`
- **ggbandage:** Label and gene inks, the head halo, swatch sizes and the
  default 1000 px width are R constants; bandage-core's figure default is 1200
  px, so a default ggbandage figure is fitted for a narrower pane than a
  default bandage-figure. New since the last audit. Home: bandage-core:
  figureData.meta.inks gains the label inks; the R default width reads
  FIGURE_DEFAULTS. Drawing swatches as grobs must differ (ggplot2 draws them).
  At `ggbandage:R/geoms.R:257-258`; `ggbandage:R/geoms.R:240`;
  `ggbandage:R/geoms.R:418`
- **jbrowse-plugin-graphgenomeviewer:** The plugin writes 'force', 'fmmm', the
  layer defaults and copies of WALK_BUDGETS and GBZ_CUT_DEFAULTS as its own
  literals (the last two held equal by a test). New since the last audit.
  Home: bandage-core and graph-walks: import ENGINE_DEFAULTS, the layer table
  above and WALK_BUDGETS; no reason for the copies is written in the files. At
  `jbrowse-plugin-graphgenomeviewer:src/LinearGraphDisplay/configSchema.ts:29-44`;
  `jbrowse-plugin-graphgenomeviewer:src/GraphGenomeView/pane/graphViews.ts:298-303`;
  `jbrowse-plugin-graphgenomeviewer:src/GraphGenomeView/graphLayers.ts:33-44`
- **BandageJS, jbrowse-plugin-graphgenomeviewer:** The engine names in the
  layout menu ('FMMM', 'stress') and the helper that strips ' layout' from a
  mode's label are the same code in both readers, beside bandage-core's own
  labels 'Bandage (FMMM)' and 'Stress' used in BandageJS's layout dialog. New
  since the last audit. Home: bandage-core: a short name on LAYOUT_ENGINES and
  a menu label on LAYOUT_MODES. At `BandageJS:src/menuItems.ts:79-82`;
  `BandageJS:src/describe.ts:24`; `BandageJS:src/layoutDialog.ts:79`
- **BandageJS, jbrowse-plugin-graphgenomeviewer, ggbandage:** The links
  setting agrees on name (links), default (walked) and label ('Links drawn'),
  but each reader defines the type and choices itself, and the choice labels
  start lower-case in the plugin and upper-case in BandageJS. New since the
  last audit. Home: graph-walks: export the choices, default and label beside
  WalkCutOptions.links (MIT, and the tube maps pass 'none' from the same
  type). At `BandageJS:src/gbz.ts:17-31`;
  `BandageJS:src/menuItems.ts:361-374`; `BandageJS:src/query.ts:21`
- **BandageJS, jbrowse-plugin-graphgenomeviewer, graph-walks:** A size is
  formatted five ways: a refusal says 'Zoom in to about 12.3Kbp', a form tag
  '12.3kb', a readout '12 kb', the key '12.3 kb', the website '12 kb'. New
  since the last audit. Home: graph-walks: one exact and one rounded
  formatter, imported by bandage-core and the readers. At
  `graph-walks:src/util.ts:198-205`;
  `graph-walks:src/structuralForms.ts:1029-1036`;
  `graph-walks:src/abridgedWalks.ts:44-45`
- **BandageJS, jbrowse-plugin-graphgenomeviewer:** The edge hover's sentence
  'skips N bp of <reference> sequence' is written out in both readers, and
  they name the reference from different calls. Home: bandage-core:
  edgeHoverText returning whole strings, given the reference label. At
  `BandageJS:src/describe.ts:120-130`;
  `jbrowse-plugin-graphgenomeviewer:src/GraphGenomeView/components/HoverTooltip.tsx:121-137`;
  `bandage-core:src/hoverText.ts:23-38`
- **ggbandage:** ggbandage matches a walk to a name by its own prefix rule
  (also accepting a ':' range suffix), the website by startsWith('hap#'), and
  bandage-core restates the PanSN helpers graph-walks exports. Home:
  graph-walks: walkNameFilter or panSNMatchesPrefix, imported by bandage-core,
  the figure script and the website's worker. At
  `ggbandage:scripts/figure.mjs:70-90`; `ggbandage:scripts/figure.mjs:154`;
  `jb2hubs:website/src/pangenome/pangenomeGraphLayout.worker.ts:113-117`
- **ggbandage:** bandage_walk_steps parses W and P lines and numbers passes in
  R, apart from the numbering bandage-core gives a lifted walk's threads.
  Home: bandage-core: a steps table in figureData. At
  `ggbandage:R/engine.R:93-121`
- **ggbandage:** scale_fill_bandage_position rebuilds the reference ramp from
  hsv arithmetic and titles it 'reference position, Mb', where the key says
  'position on GRCh38'. Home: bandage-core: read figureData.meta.inks.ramp,
  which the layout already carries. At `ggbandage:R/scales.R:9-17`;
  `bandage-core:src/figureData.ts:941-943`; `bandage-core:src/graphKey.ts:470`
- **BandageJS:** BandageJS's DEFAULTS write out engine, quality, bubble
  spread, spacing, separation and deletion edges, which bandage-core's
  ENGINE_DEFAULTS and FIGURE_DEFAULTS already state. Home: bandage-core:
  spread ENGINE_DEFAULTS and FIGURE_DEFAULTS. At
  `BandageJS:src/settings.ts:52-71`; `bandage-core:src/pipeline.ts:118-126`;
  `bandage-core:src/figureSettings.ts:29-40`
- **jb2hubs:** The website keeps its own minCarriersFor, STRUCTURAL_BP, state
  characters and a changeKind that takes a size change with rounding slack, so
  a change near 50 bp can be named differently on the page and on the plugin's
  forms track. Home: graph-walks: import minCarriersFor and STRUCTURAL_BP; the
  sidecar's state characters differ from the walk file's ('~' is other there,
  rarer in graph-walks) and stay with the sidecar reader. At
  `jb2hubs:website/src/pangenome/pangenomeSvStates.ts:19-55`;
  `graph-walks:src/structuralForms.ts:143-185`
- **jb2hubs:** The website words a change in prose ('18.4 kb deletion', '12 kb
  → 2.01 kb', '240 kb shorter') from its own table, where the forms track
  prints graph-walks' tags ('del 18kb'). Home: graph-walks: markWords beside
  markTag. At `jb2hubs:website/src/pangenome/pangenomePanels.ts:69-105`;
  `graph-walks:src/structuralForms.ts:1054-1075`
- **BandageJS, jbrowse-plugin-graphgenomeviewer:** Where a walk passes a node
  is worked out twice: BandageJS from walksThrough plus departure visits, the
  plugin from pathVisits alone, so a walk that reaches a node only on a
  departure's own steps is placed in one and not the other. Home:
  bandage-core: walkPlaces(graph, node). At
  `BandageJS:src/nodeDetails.ts:69-123`;
  `jbrowse-plugin-graphgenomeviewer:src/launchFromGraph/contributors.ts:57-90`;
  `bandage-core:src/walksThrough.ts:14`

## Capability gaps

### A user sees it on a second look

- **BandageJS, jbrowse-plugin-graphgenomeviewer, ggbandage, jb2hubs:**
  Haplotype threading (lifting a walk, colouring by progress, walk, reference
  position or pass) works in BandageJS, the plugin and ggbandage; the website
  lifts the focused haplotype in one blue scheme only, and only ggbandage
  documents naming passes or stating their spans. Changed since the last
  audit. Home: bandage-core has it all (WALK_FIELDS, passNames, passes); the
  canvas readers lack a way to name passes, and BandageJS's link carries walk
  names only. The two tube maps have no lift: a tube is the thread. At
  `BandageJS:src/highlightDialog.ts:30-66`;
  `jbrowse-plugin-graphgenomeviewer:src/GraphGenomeView/components/HighlightColorDialog.tsx:64-130`;
  `ggbandage:R/engine.R:151-160`
- **BandageJS, jbrowse-plugin-graphgenomeviewer, ggbandage:** Side-by-side
  panels on screen in BandageJS and the plugin are bare canvases with no exon
  outlines, gene names or node lengths, which ggbandage's faceted figure and
  the exported SVG draw in every panel. New since the last audit. Home:
  bandage-core: a per-panel overlay tree, which figureSvg's overlays() already
  computes, for the canvas readers to mount. At
  `BandageJS:src/view.ts:361-393`;
  `jbrowse-plugin-graphgenomeviewer:src/GraphGenomeView/components/GraphCanvas.tsx:324-352`;
  `jbrowse-plugin-graphgenomeviewer:src/GraphGenomeView/components/FacetPanels.tsx:1-17`
- **jbrowse-plugin-graphgenomeviewer:** The plugin opens a plain GFA only in
  its own graph view (file or URL in the import form); no adapter serves one
  to a graph track in the linear genome view. New since the last audit. Home:
  The plugin: an adapter that reads a whole GFA with a reference path and cuts
  it by bandage-core's region trim, as ggbandage does for a GFA with region.
  At
  `jbrowse-plugin-graphgenomeviewer:src/GraphGenomeView/components/ImportForm.tsx:138-154`;
  `jbrowse-plugin-graphgenomeviewer:src/GraphGenomeView/viewModel.ts:139-144`;
  `jbrowse-plugin-graphgenomeviewer:src/GraphAddTrackWorkflow/buildTrackConfig.ts:198-224`
- **sequenceTubeMap, ggtubemap:** ggtubemap warns and captions which
  haplotypes got no tube because they have no step on the reference in the
  window, and takes a haplotypes list at the cut; sequenceTubeMap passes no
  walk filter to the cut and says nothing of such haplotypes. New since the
  last audit. Home: graph-walks: the absent-haplotype table beside walkTracks,
  for both tube maps. At `ggtubemap:R/walks.R:16-37`;
  `ggtubemap:R/plot.R:59-73`; `ggtubemap:tools/walks.js:57`
- **BandageJS:** BandageJS still has no ribbons, shared blocks or shared order
  in walk rows, no link width by walks, no reference strip, no row grouping,
  and offers width by frequency only through a link's width= parameter. Home:
  BandageJS wiring; all but grouping are in bandage-core. Its depth, frequency
  and skip key rows now come from graphKey. At
  `BandageJS:src/layoutDialog.ts:110-141`; `BandageJS:src/settings.ts:168`;
  `BandageJS:src/view.ts:935-949`
- **ggbandage, jb2hubs, BandageJS, jbrowse-plugin-graphgenomeviewer:** No
  figure draws bubble halos: figureData and figureSvg both pass an empty halo
  list, so ggbandage, the website and both SVG exports lack what the two
  canvas readers show; ggbandage also has no walk strip under a layout and no
  reference strip. Home: bandage-core: halos and the strips in figureData and
  figureSvg. ggbandage's placeholder labels and key entries are fixed (from
  figureData). At `bandage-core:src/figureData.ts:761`;
  `bandage-core:src/figure.ts:531`; `ggbandage:R/geoms.R:540`

### Seen only side by side

- **jbrowse-plugin-graphgenomeviewer:** The old gaps in the plugin's hover
  have narrowed: it now lists genes on a hovered node, but still has no list
  of the walks through a node with their places. Changed since the last audit.
  Home: bandage-core: walkPlaces, then the plugin's hover or feature panel. At
  `jbrowse-plugin-graphgenomeviewer:src/GraphGenomeView/components/HoverTooltip.tsx:68-76`;
  `BandageJS:src/nodeDetails.ts:69-86`
- **BandageJS, jbrowse-plugin-graphgenomeviewer, ggbandage, ggtubemap,
  sequenceTubeMap, jb2hubs:** The files each reader opens differ: a
  gfa-to-tabix segment index opens in the plugin and ggbandage only, a GBZ
  database in BandageJS, the plugin and sequenceTubeMap only, and the website
  reads walk files alone. New since the last audit. Home: graph-walks already
  holds rgfaCut for the segment index; bandage-core holds the GBZ cut. Whether
  every reader should open every source is the owner's call. At
  `jbrowse-plugin-graphgenomeviewer:src/GraphAddTrackWorkflow/buildTrackConfig.ts:198-224`;
  `ggbandage:R/engine.R:37-48`; `BandageJS:src/gbz.ts:53-78`
- **ggbandage:** Only ggbandage reads a VCF's AT tags into node frequencies.
  Home: bandage-core: a JS reader feeding withFrequencies, so the canvas
  readers can width nodes by a callset. At `ggbandage:R/frequencies.R:28-116`;
  `bandage-core:src/nodeWidths.ts:88`
- **BandageJS, jbrowse-plugin-graphgenomeviewer:** Neither canvas reader can
  export a tube map as SVG, and the plugin cannot export grouped walk rows;
  each words its refusal itself. Home: bandage-core figureSvg: tube maps and
  row groups, and the refusal text. At `BandageJS:src/figure.ts:20-27`;
  `jbrowse-plugin-graphgenomeviewer:src/GraphGenomeView/pane/fitViews.ts:828-838`

## Must differ, with the reason

### A user sees it at once

- **jb2hubs:** The website's graph is laid out by the stress engine in grey at
  900 by 400 px, so the reference is forced straight where every other reader
  draws the force-directed FMMM picture in position colours. Reason: Stated
  reason is the 434 KB FMMM wasm download on a public page (graph-fmmm-layout
  1.0.2 is still wasm); it contradicts the owner's FMMM-in-every-host rule, so
  it needs a ruling rather than a library move. The engine default itself
  already lives in bandage-core ENGINE_DEFAULTS. At
  `jb2hubs:website/src/pangenome/pangenomeGraphLayout.worker.ts:22-31`;
  `bandage-core:src/pipeline.ts:118-126`;
  `bandage-core:src/figureSettings.ts:29-40`

### A user sees it on a second look

- **jbrowse-plugin-graphgenomeviewer, BandageJS, sequenceTubeMap, ggtubemap:**
  The same window's tube map has log-scaled node widths and 3 to 15 px tubes
  in the plugin and BandageJS, and every base drawn with 15 px tubes in
  sequenceTubeMap and ggtubemap; haplotype colours come from three palettes.
  New since the last audit. Reason: Partly must differ: a track among others
  has no room for a base per px. The defaults and a haplotype palette could
  still be named once in tubemap-core. At
  `bandage-core:src/layout/tubeMapLayout.ts:130-141`;
  `bandage-core:src/layout/tubeMapLayout.ts:366-370`;
  `sequenceTubeMap:src/util/tubemap.ts:236-243`

### Seen only side by side

- **jbrowse-plugin-graphgenomeviewer:** The plugin's canvas walk-row bars now
  take their run colours and merging from bandage-core, but still turn them
  into canvas spans in the plugin. Changed since the last audit. Reason:
  Thousands of rows need a canvas where bandage-core's walkRowsTree builds
  SVG; the shared geometry (runPaint, gapStyle, coalesceRuns) is now imported.
  At
  `jbrowse-plugin-graphgenomeviewer:src/GraphGenomeView/walkRowSpans.ts:1-13`;
  `bandage-core:src/layout/walkRowDraw.ts:567-637`;
  `bandage-core:src/layout/walkRowDraw.ts:1238`
- **ggbandage, ggtubemap:** The R readers cut with every byte and step budget
  lifted. Changed since the last audit. Reason: R waits for one region with no
  window to protect; now stated once as graph-walks CUT_PRESETS.figure. At
  `ggbandage:scripts/walks-cut.mjs:28`; `ggtubemap:tools/walks.js:55`;
  `graph-walks:src/walkReader.ts:94-101`
- **jb2hubs:** The website names a diffuse replacement by its size change
  alone ('net +78kb'), a kind graph-walks' marks do not have. Reason: The
  callset sidecar gives a size change with no route; a net kind in graph-walks
  only if the forms track wants it. At
  `jb2hubs:website/src/pangenome/pangenomePanels.ts:52-67`;
  `jb2hubs:website/src/pangenome/pangenomeMarks.ts:13-19`;
  `jb2hubs:website/src/pangenome/pangenomeMarks.ts:75-80`
- **sequenceTubeMap, ggtubemap:** The tube maps draw no link for a skip; a
  tube routed round a box is the mark. Reason: By design of a tube map; both
  now ask the cut for links: 'none' by graph-walks 8's name. At
  `sequenceTubeMap:src/api/walks/WalkFiles.ts:92`;
  `ggtubemap:tools/walks.js:60`
- **jb2hubs:** The website's graph draws no genes. Reason: The page's design:
  one change in focus. At
  `jb2hubs:website/src/pangenome/pangenomeGraphLayout.worker.ts:118-122`

## Fixed since the 2026-11-15 audit

- **BandageJS, jbrowse-plugin-graphgenomeviewer, ggbandage, jb2hubs:** The
  graph key is one function now: BandageJS, the plugin, ggbandage (through
  figureData.meta.graphKey) and figureSvg all render bandage-core's graphKey,
  so entries and wording match.
- **ggbandage, jb2hubs:** Figures name the reference: graphKey and the figure
  scene default referenceName to referenceLabel(graph, region), so ggbandage
  and the website no longer say 'the reference'.
- **sequenceTubeMap, ggtubemap, ggbandage, BandageJS,
  jbrowse-plugin-graphgenomeviewer:** Context and attach limits agree: five
  readers spread graph-walks' CUT_PRESETS (context 1000, attachBp 65,536),
  where sequenceTubeMap kept 100 bp, ggtubemap 0 bp and no attached steps, and
  ggbandage attached without limit.
- **BandageJS:** Hovering a placeholder in BandageJS prints bandage-core's
  placeholderHoverText, as the plugin does.
- **BandageJS, jbrowse-plugin-graphgenomeviewer, sequenceTubeMap:** Not-loaded
  bp is counted and worded once: BandageJS, the plugin and sequenceTubeMap use
  graph-walks' abridgedWalks and abridgedText.
- **ggbandage:** ggbandage's node lengths, placeholder labels, gene names and
  pass names are the ones bandage-core placed (figureData's labels table), and
  its exon colour is bandage-core's EXON_COLOR.
- **BandageJS:** BandageJS no longer words a node-count refusal itself: an
  over-large cut gets graph-walks' 'Zoom in to about N to see the graph'.

## Not settled by this audit

- Whether the plugin's `defaultHaplotypes` makes one region draw differently
  from BandageJS and the R readers, which cut every walk unless told
  otherwise: the hosted configs were not read
- Whether sequenceTubeMap filters haplotypes after its cut; it passes the cut
  no walk filter
- Why the plugin's `slotDefaults.ts` copies `WALK_BUDGETS` and
  `GBZ_CUT_DEFAULTS`, which a test holds equal, rather than importing them
