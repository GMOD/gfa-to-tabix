---
name: reader-deviations-first-moves
description: The deviations of the 2026-11-20 reader audit a user meets first, each with the library it should move to: node caps, switch names, the website's cut, tube-map tracks, read strand colours.
metadata:
  repo: graph-walks, bandage-core, tubemap-core, then every reader
---

# Reader deviations to move first

From [the audit](../reference/reader-deviations.md), in the order a user
would meet them. Each is one change in a library and a re-pin of its readers.

- **Node caps:** one region draws in BandageJS (100,000 nodes) and is refused
  by the plugin (20,000), the website (30,000) or the tube map (50,000). A
  node limit in graph-walks' `CUT_PRESETS.browser`; the R readers lift it
- **Switch names:** BandageJS and the plugin name the same drawing layers
  differently ("Deletion edges" against "Show links that skip reference").
  One table of layers with labels and defaults in bandage-core
- **The website's cut:** jb2hubs passes `contained: true` and restates the
  1000 bp context where the others spread a preset. It spreads the preset,
  or graph-walks names a preset for contained cuts
- **Tube-map tracks:** built three ways, and an abridged walk has no tube in
  sequenceTubeMap. `walkTracks` in graph-walks, with a placeholder step
- **Read strand colours:** ggtubemap paints forward reads red and reverse
  blue; sequenceTubeMap and bandage-core paint forward blue and reverse red
  (checked in `R/geoms.R`, `visOptions.ts` and `tubeMap/reads.ts`). JBrowse's
  alignments track paints forward red, so which way is kept is a call;
  the palettes then live in tubemap-core
- **The `links` setting's type and choice labels:** defined in each of the
  three readers, the labels capitalised differently. One definition in
  graph-walks beside `WalkCutOptions.links`
- **The website's layout:** stress engine, grey, against force-directed in
  every other host. Its reason is the 434 KB wasm download; it needs a ruling
