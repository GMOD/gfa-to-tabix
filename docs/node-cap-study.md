# A node cap for the browser readers

How long BandageJS and the JBrowse graph plugin take to lay out and draw a
walk-file cut as its node count grows, for the owner deciding on a node cap
for the browser preset. graph-walks' held `node-limit-preset` branch caps a
browser cut at 30,000 nodes; this page gives the numbers that cap would act
on. It decides nothing.

Measured on ada (24 cores, no GPU), 2026-11-21, from the hosted HPRC v2.1 MC
GRCh38 format 8 walk file (a local copy with the same bytes and `.idx`, served
over local http). Every number below is printed by
[summarize.py](node-cap/scripts/summarize.py) into
[summary.txt](node-cap/summary.txt) from the runs beside this page, unless it
says it was read from code or is an estimate.

## Takeaways

TAKEAWAYS

## What the released readers do today

Read from code, not measured:

- **BandageJS** (`bfa3c0e0`): a walk-file cut keeps at most 100,000 nodes
  (`GBZ_CUT_DEFAULTS.limit`, `src/walkFiles.ts`) and refuses past it with a
  zoom-in notice. Past 20,000 (`MAX_NODES`, `src/sources.ts`, or `maxNodes=` in
  the address) it draws nothing and offers **Draw anyway**, saying "A layout
  that size can take minutes". So the warning-and-button option already exists
  there, between 20,000 and 100,000
- **The plugin** (10.4.0): the graph genome view refuses a graph over 20,000
  nodes after the cut (`DEFAULT_MAX_GRAPH_NODES`), naming Layout → Walk rows,
  zooming in, or raising the limit in Graph settings (5,000, 20,000, 50,000 or
  100,000), and refuses a window over 5 Mb before it (`MAX_GRAPH_REGION_BP`).
  The linear view's graph track shares `maxGraphNodes`
- **graph-walks' browser preset** (9.0.0): with 4 haplotypes only the step
  budget, 4,000,000 steps, bites in this ladder, at the 30 and 32 Mb windows
  (4.2 and 5.2 million steps, [cut-points.tsv](node-cap/cut-points.tsv)). The
  held branch would add 30,000 nodes

So at each window of the ladder below, by those rules: BandageJS draws up to
8,656 nodes at once, asks first from 29,912 to 54,096, and refuses from
106,634; the plugin draws up to 8,656 and refuses from 29,912.

## Windows

Four haplotypes, HG002#1, HG00733#1, NA19240#1 and HG00097#1 (the scale
study's four), plus the GRCh38 reference walk; widths chosen to land near
1,000 to 300,000 nodes, and one past a million on each chromosome. chr22 is
grown from 30.0 Mb, a typical stretch of its q arm; chr6 from 31.0 Mb, into
the MHC, whose nodes lay out more slowly and whose walks are partly abridged
(placeholders, the "nodes not shown" loops).

The cut is graph-walks 9.0.0's `cutRegion` in Node from local disk, with the
browser preset's context and links, the budgets and node limit lifted, median
of three runs ([cut.tsv](node-cap/cut.tsv)):

WINDOWS

## Time to the first drawing

"To paint" runs from the end of the reader's cut to the first frame painted
after its layout: building the graph from the tables, the layout, the
geometry and the draw. It leaves out the cut, which the table above gives
and which the readers' own cuts match (below), and the page's start. Median
of three runs; a run that drew nothing ran once, and a wider window on that
chromosome was not run.

PAINT

## Thresholds

The windows between which the median time to paint passes 1 s, 5 s and 30 s,
with an estimate in brackets from a straight line through those two windows
in log nodes and log time:

THRESHOLDS

- chr6's MHC windows cross each threshold at about half chr22's node count or
  less: the cap a reader can afford depends on where the window is, not only
  on how many nodes it has
- FMMM's own time is most of it past 30,000 nodes; the rest is the geometry
  and the draw on the main thread

## After the drawing: zoom, pan and memory

The longest main-thread task before the first paint is how long the tab
could not answer a click; the zoom and the drag are timed from the input to
the next painted frame; memory is the renderer's peak resident size, workers
and wasm included. "dies" is BandageJS's hover crash ([below](#found-on-the-way)).

MAINTABLES

- **FMMM keeps the tab answering while it lays out**, since it runs in a
  worker: the longest block at chr22 3.6 Mb is 3.0 s in BandageJS and 4.3 s in
  the plugin, against 9.6 s and 11.0 s to paint. The stress engine, the tube
  map and the ordered layout hold the main thread for nearly all of their time
- **A zoom stays under about a quarter of a second up to 30,000 nodes in
  FMMM**, except the plugin's 0.66 s at chr22 1.1 Mb, and passes a second
  between 54,096 and 106,634; in the stress and ordered layouts BandageJS
  rebuilds the geometry on a zoom and takes 9 s at 106,634 and 80-103 s at
  321,044
- **Memory** passes 1 GB between 30,000 and 54,000 nodes in FMMM and reaches
  3.6 GB at 321,044 on chr22 and 3.9 GB at 277,560 on chr6. Nothing came
  near the 16 GB scope: FMMM's failures are the engine aborting, BandageJS's
  hover crash is Chrome's 4 GB JS heap, and the tube map's crashes were not
  looked into

## Is 30,000 a sensible cap?

At 29,912 nodes (chr22 1.1 Mb), medians:

- **FMMM, the default:** paints in 2.7 s in BandageJS and 3.0 s in the
  plugin, zooms in 0.15 and 0.66 s, at 0.66 and 0.82 GB. In the MHC the next
  window, 36,182 nodes, paints in 6.1 and 6.4 s
- **Stress:** 3.5 and 3.8 s, with the tab unanswering for 2.7 and 3.1 s of
  it; 12.0 and 11.8 s at the MHC's 36,182
- **Tube map:** 1.4 and 1.2 s; 3.8 s at the MHC's 36,182
- **Ordered:** 2.6 and 2.0 s; 6.6 and 9.8 s at the MHC's 36,182
- **Walk rows:** WALKROWS30K

So 30,000 holds the first drawing to a few seconds in every layout on chr22
and to about 6-12 s in the MHC. As a cap for FMMM it sits near the estimated
5 s point of the MHC (about 30,000) and well under chr22's (about 60,000);
for stress it is above the MHC's (about 21,000). It is lower than what
BandageJS draws today after **Draw anyway** (up to 100,000) and higher than
the plugin's default (20,000).

Node count is a proxy, and an uneven one: the same 5 s falls at about half
the node count in the MHC that it does on chr22 in every layout but the tube
map.

## Options

OPTIONS

## Showing something instead of refusing

What a reader could draw past the cap in place of a refusal, with no change
made here:

- **Fold before the layout, in the reader.** Cut every node as today, fold
  each bubble under a size set by the window's bp per pixel into the
  reference, and lay out what is left, each walk keeping what it carries
  there as marks. bandage-core already folds this way for tube maps
  (`tubeMapFold`, `src/tubeMap/coarsen.ts`, after svSTM) and, at draw time
  only, for the node layouts ("Small sites", `src/levelOfDetail.ts`), which
  still lay out every node first
  - For: today's files, no format change; the cut is a small share of the
    time (1.4 s of chr22's 10 Mb, against 38 s to paint with FMMM)
  - Against: the download, the decode and the memory still grow with the
    window; the force engines have no fold step yet; the drawing changes kind
    as the user zooms
- **Only the reference, bubbles as glyphs.** Draw the reference as a bar at
  its bp and each bubble as one mark sized by its bp and its routes, with no
  node layout
  - For: cost grows with bubbles, not nodes, and needs no engine
  - Against: a new drawing in both readers, and the graph's shape, which a
    force layout is for, is gone
- **Switch to walk rows.** Both readers draw them from runs, with no node
  layout, and the plugin's refusal already names them
  - For: exists today in both readers (times above)
  - Against: a different picture from the one asked for, with no topology
- **An overview tier in the file,** as `gfa-to-tabix fold` writes the coarse
  tier the plugin's graph-index track switches to past `aboveBpPerPx`
  - For: shrinks the download and the decode as well as the layout; readers
    skip unit kinds they do not know, so format 8 files keep working
  - Against: a format change, which is the owner's call, and writer work; a
    separate study on the queue

## Found on the way

- **BandageJS's tab dies on the first pointer move** over the drawing of
  chr6 31.0-31.4 Mb (36,182 nodes) and the wider MHC windows, in every run:
  the main thread's JS heap runs to Chrome's 4 GB limit within seconds and the
  renderer crashes (`V8 javascript OOM`). It is the hover's edge hit test:
  bandage-core's `findHoveredEdge` builds an `EdgeSpatialIndex`, whose
  `addToGrid` stamps each link's bounding box cell by cell, and two links
  there span 3,784 x 5,913 and 3,839 x 5,878 cells, 22 million each
  ([hover-oom.txt](node-cap/hover-oom.txt), from a debug copy). The drawing
  itself is unaffected, so its times above stand; its zoom, pan and memory
  read "dies". No chr22 window does it, and the plugin's runs, whose pointer
  sat elsewhere, did not; the plugin was not checked further
- **FMMM aborts past a million nodes** in both readers
  (`RuntimeError: Aborted(undefined)` from the wasm engine), at 1,199,754 on
  chr22 and 973,240 on chr6, with the renderer at 2.5-4.8 GB
- **The geometry is built two to four times before the first paint** in the
  stress and ordered layouts, in both readers (the marks in
  [reader-runs.jsonl](node-cap/reader-runs.jsonl)), and in the ordered layout
  it, not the layout, is the time: at chr22 10 Mb BandageJS lays it out in
  about 1 s and builds the geometry twice in 83 and 108 s. BandageJS builds it
  again on a zoom, so a zoom there takes as long as a build (the zoom table)
- **The plugin's tube map cuts and lays out twice** at chr22 10 Mb and chr6
  0.4 and 1.8 Mb, the windows of the tube-map ladder whose cuts hold
  placeholders, and once elsewhere; the first paint at chr22 10 Mb comes
  after two layouts of over two minutes each
- **The plugin's view errors out at chr22 10 Mb in the ordered layout:** after
  the main thread had been held for minutes, JBrowse's fetch of a code chunk
  timed out and the view was replaced by `ChunkLoadError: Loading chunk 71176
  failed. (timeout …)`. A long main-thread block in the plugin can take down
  the view, not just delay it
- **The tube map lays out on the main thread** in both readers, so the tab
  answers nothing until it is drawn: at chr22 3.6 Mb, 13 s and 11 s

## Method

- **Readers:** BandageJS `bfa3c0e0` (bandage-core 14.3.0, graph-walks
  9.0.0), built and served from a local clone; the plugin `0a82b467` (10.4.0)
  built from a local clone and loaded as the plugin of a jbrowse-web
  5.0.0-beta.20 build, the host its e2e suites run on, with one graph track
  reading the walk file through `RgfaTabixAdapter`. Neither clone is pushed;
  their changes are [bandagejs.diff](node-cap/scripts/bandagejs.diff) and
  [plugin.diff](node-cap/scripts/plugin.diff)
- **Changes to the readers:** performance marks around the cut, the layout,
  the geometry and each paint of the canvas, and the cut's refusals lifted:
  BandageJS spreads the figure preset and no node limit where it spreads the
  browser preset and 100,000; the plugin spreads the figure preset in place of
  the browser preset and its budget slots. The address and session lift the
  rest: `maxNodes=` in BandageJS, `maxGraphNodes` and `maxRegionBp` in the
  plugin's view. Neither change touches a layout or a draw
- **What each opens:** BandageJS `?walks=<file>&loc=…&haps=…&layout=…&engine=…&genes=0`;
  the plugin a session spec with one `GraphGenomeView` whose `loadedTrackId`,
  `loadedRegion`, `subgraphHaplotypes`, `layoutMode` and `layoutEngine` name
  the same cut ([urls.mjs](node-cap/scripts/urls.mjs)). Genes are off in both,
  so no request leaves the machine
- **Layouts:** force-directed with FMMM, each reader's default; force-directed
  with the stress engine; the tube map; ordered; walk rows. Anchored, sample
  rows and the tube map on reference are left out
- **A run** ([measure.mjs](node-cap/scripts/measure.mjs)): a fresh headless
  Chrome 154 (SwiftShader, 1400 x 1000 px), the address opened, and a wait of
  up to 300 s for the first frame painted after the last layout. Then the JS
  heap from CDP, a wheel zoom and a 60 px drag with the pointer 12 px below the
  pane's top, each timed to the next painted frame, and the renderer process's
  peak resident memory (VmHWM), which holds the page's workers and their wasm.
  The longest main-thread task before the paint, from a `longtask` observer,
  says how long the tab could not answer a click
- **Runs** ([drive.mjs](node-cap/scripts/drive.mjs)): each layout, each
  chromosome's windows smallest first, three runs alternating the readers,
  each run once the 1-minute load is under 4, under `nice -n 10` in a
  `systemd-run` scope of 16 GB with no swap. A run that drew nothing was not
  repeated, and that reader was not run on that chromosome's wider windows in
  that layout. Other jobs shared ada throughout

## What this does not measure

- **No GPU.** Chrome draws the Canvas2D on the CPU here; a laptop with GPU
  rasterization would draw faster. The layouts run on the CPU either way, and
  past 30,000 nodes they are most of the time
- **Local http.** The readers fetch from the same machine, so a hosted file's
  download time is not in these numbers; the cut's bytes are in the scale
  study ([placement/scale-past-464.md](placement/scale-past-464.md))
- **Two places on two chromosomes, four haplotypes.** More haplotypes put
  more nodes in the same window; the MHC shows how much where the graph lies
  matters
- **One zoom and one pan** right after the first paint, not a session of them
- **Chrome's own limits apply:** a renderer's JS heap stops at 4 GB, well
  under the 16 GB scope

## Reproduce

On ada, from a directory `N` set up as
[scripts/README.txt](node-cap/scripts/README.txt) says:

```bash
S=docs/node-cap/scripts
GRAPH_WALKS_DIR=$N/cut $S/run-cut.sh docs/node-cap/cut.tsv
NODECAP=$N $S/run-readers.sh docs/node-cap/reader-runs.jsonl
python3 $S/summarize.py docs/node-cap/reader-runs.jsonl docs/node-cap/cut.tsv docs/node-cap > docs/node-cap/summary.txt
```
