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
  by the plugin (20,000), the website (30,000) or the tube map (50,000).
  Decided 2026-11-20 by a Fable read of each number's reason: 30,000 kept
  nodes, `BROWSER_NODE_LIMIT` in graph-walks' browser preset (branch
  `node-limit-preset` 2bf643c, for 9.0.0); the figure preset keeps every
  node. BandageJS's 100,000 was gbz-base's limit, counted in another unit,
  and stays for gbz-base cuts; the tube map's 50,000 backstop and 30,000-visit
  render cap stay, since a tube's cost is visits. The plugin's setting starts
  at the preset and passes it as the cut's `nodeLimit`; jb2hubs spreads the
  preset and shows `fitsBp`
- **Switch names:** BandageJS and the plugin name the same drawing layers
  differently ("Deletion edges" against "Show links that skip reference").
  One table of layers with labels and defaults in bandage-core
- **The website's cut:** jb2hubs passes `contained: true` and restates the
  1000 bp context where the others spread a preset. It spreads the preset,
  or graph-walks names a preset for contained cuts
- **Tube-map tracks:** built three ways, and an abridged walk has no tube in
  sequenceTubeMap. `walkTracks` in graph-walks, with a placeholder step
- **Read strand colours:** decided 2026-11-20 (Fable): forward red, reverse
  blue, as JBrowse's alignments track beside the plugin's tube map and vg's
  tube map before its 2023 swap to UCSC's blue-forward. tubemap-core 2.1.0
  exports `readColor`, `FORWARD_READ_COLORS` and `REVERSE_READ_COLORS`;
  bandage-core imports them in place of its copies, sequenceTubeMap swaps
  `defaultReadColorPalette` and `EXAMPLE_READS`, ggtubemap takes them in
  place of its two hexes
- **The `links` setting's type and choice labels:** defined in each of the
  three readers, the labels capitalised differently. One definition in
  graph-walks beside `WalkCutOptions.links`
- **The website's layout:** stress engine, grey, against force-directed in
  every other host. Its reason is the 434 KB wasm download; it needs a ruling
