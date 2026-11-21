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

Node counts where each reader's median time from the cut to the first
drawing passes 1, 5 and 30 s, by layout, on chr22's q arm and in the MHC,
and the first window of the ladder that drew nothing. "~" is an estimate
between the two windows measured on either side; a range is given where the
wider one drew nothing:

| layout | reader | 1 s chr22 | 1 s MHC | 5 s chr22 | 5 s MHC | 30 s chr22 | 30 s MHC | fails chr22 | fails MHC |
|---|---|---|---|---|---|---|---|---|---|
| FMMM | BandageJS | ~11,000 | ~6,300 | ~65,000 | ~30,000 | ~257,000 | ~107,000 | 1,199,754, aborts | 973,240, aborts |
| FMMM | plugin | ~10,000 | ~6,100 | ~57,000 | ~29,000 | ~236,000 | ~105,000 | 1,199,754, aborts | 973,240, aborts |
| stress | BandageJS | ~11,000 | ~7,400 | ~37,000 | ~21,000 | ~112,000 | 36,182-157,896 | 1,199,754, nothing in 300 s | 157,896, nothing in 300 s |
| stress | plugin | ~9,600 | ~6,300 | ~37,000 | ~21,000 | ~108,000 | 36,182-157,896 | 1,199,754, nothing in 300 s | 157,896, nothing in 300 s |
| tube map | BandageJS | ~24,000 | ~16,000 | ~68,000 | ~41,000 | ~158,000 | ~101,000 | 1,199,754, crashes | 277,560, crashes |
| tube map | plugin | ~26,000 | ~16,000 | ~71,000 | ~41,000 | ~150,000 | ~96,000 | 1,199,754, crashes | 277,560, crashes |
| ordered | BandageJS | ~14,000 | ~10,000 | ~50,000 | ~30,000 | ~127,000 | ~88,000 | 1,199,754, nothing in 300 s | 277,560, nothing in 300 s |
| ordered | plugin | ~12,000 | ~10,000 | ~60,000 | ~25,000 | 106,634-321,044 | ~76,000 | 321,044, view fails | 277,560, view fails |
| walk rows | BandageJS | ~71,000 | ~70,000 | ~307,000 | ~310,000 | ~1,199,000 | never | none | none |
| walk rows | plugin | ~145,000 | ~140,000 | ~515,000 | ~709,000 | never | never | none | none |

- **The two readers are close in FMMM and stress,** within about 15% from
  30,000 nodes up, since both lay out with bandage-core 14.3.0. Below that the
  plugin adds about 0.2 s; it is faster in the ordered layout from 30,000
  nodes and in walk rows, and slower in the tube map where it lays out twice
  ([Found on the way](#found-on-the-way))
- **The default layout, FMMM, passes 1 s at about 10,000 nodes, 5 s at about
  60,000 and 30 s at about 250,000 on chr22, and at about half those counts
  in the MHC.** It aborts at the ladder's two largest windows, 973,240 and
  1,199,754 nodes, in both readers. It is the one
  node layout that keeps the tab answering while it works, since it runs in a
  worker
- **Stress, the tube map and the ordered layout hold the main thread** for
  nearly all their time, so the tab answers nothing until they draw: stress
  passes 5 s at about 37,000 nodes on chr22 and 21,000 in the MHC and drew
  nothing in 300 s at the MHC's 157,896; the tube map crashes the tab at the
  MHC's 277,560; the ordered layout lays out in a second at 321,044 nodes and
  then spends minutes building its geometry
- **Walk rows hold up past a million nodes:** 1 s at about 70,000 (BandageJS)
  and 140,000 (plugin), 5 s at about 300,000 and 500,000-700,000, and both drew
  chr22's 1,199,754 nodes, in 30 s and 19 s
- **After the drawing,** a FMMM zoom stays under 0.7 s up to 36,182 nodes and
  takes 1.3 s at 106,634 and 3.7-5.2 s at 321,044. BandageJS's tab dies on the
  first pointer move over its FMMM drawings of the MHC from 36,182 nodes, a
  hover bug, not a size limit ([Found on the way](#found-on-the-way))
- **30,000 nodes keeps the first FMMM drawing to about 3 s on chr22 and 6 s in
  the MHC** (2.7-3.0 s at 29,912; 6.2-6.4 s at 36,182), at about 0.7-0.8 GB.
  It is near the MHC's 5 s point for FMMM, past it for stress, and far under
  what walk rows can draw. It sits between the plugin's default refusal
  (20,000) and BandageJS's hard one (100,000)
- **Where a window lies moves these numbers as much as a factor of two,** so
  a node cap is a proxy for the time it is meant to bound

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

| window | reference bp | nodes | of them placeholders | links | steps | cut |
|---|---|---|---|---|---|---|
| chr22 37 kb | 30,000,001-30,037,000 | 971 | 0 | 1,027 | 4,594 | 10 ms |
| chr22 220 kb | 30,000,001-30,220,000 | 5,143 | 0 | 5,529 | 23,853 | 26 ms |
| chr22 370 kb | 30,000,001-30,370,000 | 8,656 | 0 | 9,325 | 40,051 | 32 ms |
| chr22 1.1 Mb | 30,000,001-31,100,000 | 29,912 | 0 | 32,653 | 135,992 | 101 ms |
| chr22 2 Mb | 30,000,001-32,000,000 | 54,096 | 0 | 57,855 | 251,824 | 164 ms |
| chr22 3.6 Mb | 30,000,001-33,600,000 | 106,634 | 0 | 115,197 | 490,414 | 375 ms |
| chr22 10 Mb | 30,000,001-40,000,000 | 321,044 | 317 | 348,617 | 1,456,828 | 1.4 s |
| chr22 32 Mb | 18,000,001-50,000,000 | 1,199,754 | 709 | 1,305,240 | 5,180,750 | 7.0 s |
| chr6 17 kb | 31,000,001-31,017,000 | 1,084 | 0 | 1,245 | 4,637 | 12 ms |
| chr6 90 kb | 31,000,001-31,090,000 | 5,095 | 0 | 5,935 | 21,068 | 24 ms |
| chr6 150 kb | 31,000,001-31,150,000 | 8,451 | 0 | 9,887 | 35,015 | 36 ms |
| chr6 400 kb | 31,000,001-31,400,000 | 36,182 | 2,438 | 44,213 | 139,224 | 136 ms |
| chr6 1.8 Mb | 31,000,001-32,800,000 | 157,896 | 19,364 | 198,574 | 548,007 | 598 ms |
| chr6 5.5 Mb | 31,000,001-36,500,000 | 277,560 | 19,364 | 329,867 | 1,086,121 | 1.1 s |
| chr6 30 Mb | 31,000,001-61,000,000 | 973,240 | 19,364 | 1,087,084 | 4,235,119 | 5.7 s |

## Time to the first drawing

"To paint" runs from the end of the reader's cut to the first frame painted
after its layout: building the graph from the tables, the layout, the
geometry and the draw. It leaves out the cut, which the table above gives
and which the readers' own cuts match (below), and the page's start. Median
of three runs; a run that drew nothing ran once, and a wider window on that
chromosome was not run.

B is BandageJS, P the plugin; "aborts" is FMMM's wasm engine aborting,
"> 300 s" a run that drew nothing in 300 s, "fails" the plugin's view
replaced by an error, and an empty cell a window not run after a narrower
one drew nothing. The readers' own cuts, fetch included, took 15-100 ms more
than the Node cut above up to 157,896 nodes and within 0.2 s of it beyond
([reader-points.tsv](node-cap/reader-points.tsv), `cut_ms`).

| window | nodes | FMMM B | FMMM P | stress B | stress P | tube map B | tube map P | ordered B | ordered P | walk rows B | walk rows P |
|---|---|---|---|---|---|---|---|---|---|---|---|
| chr22 37 kb | 971 | 199 ms | 369 ms | 176 ms | 383 ms | 54 ms | 273 ms | 134 ms | 355 ms | 75 ms | 318 ms |
| chr22 220 kb | 5,143 | 516 ms | 540 ms | 477 ms | 602 ms | 158 ms | 276 ms | 332 ms | 605 ms | 147 ms | 301 ms |
| chr22 370 kb | 8,656 | 787 ms | 847 ms | 699 ms | 887 ms | 232 ms | 258 ms | 529 ms | 758 ms | 219 ms | 278 ms |
| chr22 1.1 Mb | 29,912 | 2.7 s | 3.0 s | 3.5 s | 3.8 s | 1.4 s | 1.2 s | 2.6 s | 2.0 s | 471 ms | 298 ms |
| chr22 2 Mb | 54,096 | 4.0 s | 4.6 s | 9.2 s | 8.2 s | 3.2 s | 3.0 s | 5.6 s | 4.2 s | 785 ms | 425 ms |
| chr22 3.6 Mb | 106,634 | 9.6 s | 11.0 s | 27.5 s | 29.5 s | 12.5 s | 10.9 s | 21.2 s | 13.9 s | 1.5 s | 711 ms |
| chr22 10 Mb | 321,044 | 40.1 s | 44.1 s | 228.7 s | 244.5 s | 142.5 s | 275.7 s | 195.5 s | fails | 5.3 s | 2.4 s |
| chr22 32 Mb | 1,199,754 | aborts | aborts | > 300 s | > 300 s | crash | crash | > 300 s |  | 30.0 s | 18.8 s |
| chr6 17 kb | 1,084 | 295 ms | 384 ms | 210 ms | 391 ms | 66 ms | 295 ms | 156 ms | 358 ms | 69 ms | 281 ms |
| chr6 90 kb | 5,095 | 834 ms | 849 ms | 687 ms | 861 ms | 220 ms | 258 ms | 418 ms | 547 ms | 143 ms | 287 ms |
| chr6 150 kb | 8,451 | 1.3 s | 1.4 s | 1.1 s | 1.2 s | 370 ms | 335 ms | 734 ms | 697 ms | 201 ms | 286 ms |
| chr6 400 kb | 36,182 | 6.2 s | 6.4 s | 12.0 s | 11.8 s | 3.8 s | 3.8 s | 6.6 s | 9.8 s | 537 ms | 358 ms |
| chr6 1.8 Mb | 157,896 | 52.9 s | 54.4 s | > 300 s | > 300 s | 73.3 s | 84.3 s | 81.9 s | 90.6 s | 2.1 s | 1.1 s |
| chr6 5.5 Mb | 277,560 | 84.2 s | 73.9 s |  |  | crash | crash | > 300 s | fails | 4.4 s | 2.0 s |
| chr6 30 Mb | 973,240 | aborts | aborts |  |  |  |  |  |  | 20.6 s | 6.8 s |

## Thresholds

The windows, by node count, on either side of the point where the median
time to paint passes 1 s, 5 s and 30 s; the takeaways' table gives the
estimate between them, from a straight line through the two in log nodes and
log time:

| layout | reader | | 1 s | 5 s | 30 s |
|---|---|---|---|---|---|
| FMMM | BandageJS | chr22 | 8,656-29,912 | 54,096-106,634 | 106,634-321,044 |
| FMMM | BandageJS | MHC | 5,095-8,451 | 8,451-36,182 | 36,182-157,896 |
| FMMM | plugin | chr22 | 8,656-29,912 | 54,096-106,634 | 106,634-321,044 |
| FMMM | plugin | MHC | 5,095-8,451 | 8,451-36,182 | 36,182-157,896 |
| stress | BandageJS | chr22 | 8,656-29,912 | 29,912-54,096 | 106,634-321,044 |
| stress | BandageJS | MHC | 5,095-8,451 | 8,451-36,182 | 36,182-157,896 |
| stress | plugin | chr22 | 8,656-29,912 | 29,912-54,096 | 106,634-321,044 |
| stress | plugin | MHC | 5,095-8,451 | 8,451-36,182 | 36,182-157,896 |
| tube map | BandageJS | chr22 | 8,656-29,912 | 54,096-106,634 | 106,634-321,044 |
| tube map | BandageJS | MHC | 8,451-36,182 | 36,182-157,896 | 36,182-157,896 |
| tube map | plugin | chr22 | 8,656-29,912 | 54,096-106,634 | 106,634-321,044 |
| tube map | plugin | MHC | 8,451-36,182 | 36,182-157,896 | 36,182-157,896 |
| ordered | BandageJS | chr22 | 8,656-29,912 | 29,912-54,096 | 106,634-321,044 |
| ordered | BandageJS | MHC | 8,451-36,182 | 8,451-36,182 | 36,182-157,896 |
| ordered | plugin | chr22 | 8,656-29,912 | 54,096-106,634 | 106,634-321,044 |
| ordered | plugin | MHC | 8,451-36,182 | 8,451-36,182 | 36,182-157,896 |
| walk rows | BandageJS | chr22 | 54,096-106,634 | 106,634-321,044 | 321,044-1,199,754 |
| walk rows | BandageJS | MHC | 36,182-157,896 | 277,560-973,240 | never |
| walk rows | plugin | chr22 | 106,634-321,044 | 321,044-1,199,754 | never |
| walk rows | plugin | MHC | 36,182-157,896 | 277,560-973,240 | never |

- chr6's MHC windows cross each threshold at about half chr22's node count or
  less: the cap a reader can afford depends on where the window is, not only
  on how many nodes it has
- FMMM's engine time is most of the time to paint from 30,000 nodes (1.6 of
  2.7 s at 29,912 in BandageJS, 23 of 40 s at 321,044, in
  [reader-points.tsv](node-cap/reader-points.tsv)); the rest is the graph
  build, the geometry and the draw on the main thread

## After the drawing: zoom, pan and memory

The longest main-thread task before the first paint is how long the tab
could not answer a click; the zoom and the drag are timed from the input to
the next painted frame; memory is the renderer's peak resident size, workers
and wasm included. "dies" is BandageJS's hover crash ([below](#found-on-the-way)).

Longest main-thread task before the first paint:

| window | nodes | FMMM B | FMMM P | stress B | stress P | tube map B | tube map P | ordered B | ordered P | walk rows B | walk rows P |
|---|---|---|---|---|---|---|---|---|---|---|---|
| chr22 37 kb | 971 | 83 ms | 114 ms | 89 ms | 114 ms | 63 ms | 0 ms | 119 ms | 94 ms | 78 ms | 53 ms |
| chr22 220 kb | 5,143 | 199 ms | 234 ms | 278 ms | 328 ms | 168 ms | 104 ms | 320 ms | 226 ms | 170 ms | 68 ms |
| chr22 370 kb | 8,656 | 254 ms | 349 ms | 438 ms | 515 ms | 263 ms | 175 ms | 509 ms | 343 ms | 251 ms | 91 ms |
| chr22 1.1 Mb | 29,912 | 772 ms | 1.1 s | 2.7 s | 3.1 s | 1.5 s | 1.1 s | 2.6 s | 1.7 s | 581 ms | 145 ms |
| chr22 2 Mb | 54,096 | 1.3 s | 2.1 s | 7.9 s | 7.0 s | 3.3 s | 2.9 s | 5.7 s | 3.5 s | 968 ms | 403 ms |
| chr22 3.6 Mb | 106,634 | 3.0 s | 4.3 s | 25.0 s | 27.0 s | 12.9 s | 10.9 s | 21.4 s | 13.8 s | 1.8 s | 691 ms |
| chr22 10 Mb | 321,044 | 11.1 s | 15.8 s | 217.5 s | 235.2 s | 143.2 s | 145.8 s | 194.8 s | fails | 5.9 s | 2.4 s |
| chr22 32 Mb | 1,199,754 | aborts | aborts | > 300 s | > 300 s | crash | crash | > 300 s |  | 34.0 s | 18.9 s |
| chr6 17 kb | 1,084 | 114 ms | 131 ms | 120 ms | 122 ms | 74 ms | 0 ms | 140 ms | 107 ms | 81 ms | 58 ms |
| chr6 90 kb | 5,095 | 234 ms | 295 ms | 428 ms | 514 ms | 235 ms | 132 ms | 402 ms | 272 ms | 167 ms | 75 ms |
| chr6 150 kb | 8,451 | 319 ms | 442 ms | 803 ms | 935 ms | 397 ms | 239 ms | 709 ms | 450 ms | 239 ms | 90 ms |
| chr6 400 kb | 36,182 | 1.2 s | 1.5 s | 10.7 s | 10.7 s | 3.9 s | 1.8 s | 6.6 s | 5.7 s | 625 ms | 192 ms |
| chr6 1.8 Mb | 157,896 | 10.6 s | 18.1 s | > 300 s | > 300 s | 73.7 s | 44.4 s | 81.1 s | 90.4 s | 2.5 s | 1.1 s |
| chr6 5.5 Mb | 277,560 | 14.2 s | 20.5 s |  |  | crash | crash | > 300 s | fails | 5.0 s | 2.0 s |
| chr6 30 Mb | 973,240 | aborts | aborts |  |  |  |  |  |  | 23.6 s | 6.8 s |

A wheel zoom, to its next painted frame:

| window | nodes | FMMM B | FMMM P | stress B | stress P | tube map B | tube map P | ordered B | ordered P | walk rows B | walk rows P |
|---|---|---|---|---|---|---|---|---|---|---|---|
| chr22 37 kb | 971 | 56 ms | 55 ms | 59 ms | 53 ms | 40 ms | 52 ms | 63 ms | 52 ms | 45 ms | 48 ms |
| chr22 220 kb | 5,143 | 73 ms | 180 ms | 77 ms | 199 ms | 52 ms | 44 ms | 79 ms | 203 ms | 50 ms | 52 ms |
| chr22 370 kb | 8,656 | 79 ms | 209 ms | 81 ms | 208 ms | 53 ms | 32 ms | 71 ms | 200 ms | 42 ms | 54 ms |
| chr22 1.1 Mb | 29,912 | 146 ms | 655 ms | 155 ms | 468 ms | 167 ms | 31 ms | 1.4 s | 429 ms | 82 ms | 66 ms |
| chr22 2 Mb | 54,096 | 653 ms | 556 ms | 2.2 s | 679 ms | 230 ms | 21 ms | 2.4 s | 627 ms | 114 ms | 149 ms |
| chr22 3.6 Mb | 106,634 | 1.3 s | 1.3 s | 8.9 s | 1.4 s | 929 ms | 52 ms | 9.4 s | 36 ms | 298 ms | 31 ms |
| chr22 10 Mb | 321,044 | 5.2 s | 3.7 s | 79.9 s | 4.1 s | 8.9 s | 201 ms | 102.8 s | fails | 836 ms | 42 ms |
| chr22 32 Mb | 1,199,754 | aborts | aborts | > 300 s | > 300 s | crash | crash | > 300 s |  | 3.6 s | 747 ms |
| chr6 17 kb | 1,084 | 61 ms | 50 ms | 55 ms | 84 ms | 41 ms | 50 ms | 62 ms | 69 ms | 43 ms | 44 ms |
| chr6 90 kb | 5,095 | 80 ms | 191 ms | 100 ms | 199 ms | 62 ms | 50 ms | 80 ms | 207 ms | 47 ms | 52 ms |
| chr6 150 kb | 8,451 | 86 ms | 252 ms | 115 ms | 250 ms | 79 ms | 47 ms | 108 ms | 231 ms | 55 ms | 53 ms |
| chr6 400 kb | 36,182 | dies | 617 ms | 3.4 s | 824 ms | 912 ms | 51 ms | 3.5 s | 745 ms | 83 ms | 76 ms |
| chr6 1.8 Mb | 157,896 | dies | 10.5 s | > 300 s | > 300 s | 16.3 s | 170 ms | 43.1 s | 2.9 s | 379 ms | 26 ms |
| chr6 5.5 Mb | 277,560 | dies | 11.4 s |  |  | crash | crash | > 300 s | fails | 800 ms | 43 ms |
| chr6 30 Mb | 973,240 | aborts | aborts |  |  |  |  |  |  | 2.8 s | 52 ms |

A 60 px drag, to its next painted frame:

| window | nodes | FMMM B | FMMM P | stress B | stress P | tube map B | tube map P | ordered B | ordered P | walk rows B | walk rows P |
|---|---|---|---|---|---|---|---|---|---|---|---|
| chr22 37 kb | 971 | 66 ms | 40 ms | 52 ms | 39 ms | 45 ms | 47 ms | 67 ms | 38 ms | 43 ms | 45 ms |
| chr22 220 kb | 5,143 | 55 ms | 52 ms | 77 ms | 52 ms | 40 ms | 47 ms | 76 ms | 56 ms | 39 ms | 46 ms |
| chr22 370 kb | 8,656 | 72 ms | 57 ms | 71 ms | 91 ms | 35 ms | 46 ms | 75 ms | 99 ms | 36 ms | 44 ms |
| chr22 1.1 Mb | 29,912 | 126 ms | 106 ms | 144 ms | 128 ms | 131 ms | 45 ms | 166 ms | 136 ms | 60 ms | 44 ms |
| chr22 2 Mb | 54,096 | 197 ms | 151 ms | 210 ms | 196 ms | 209 ms | 44 ms | 207 ms | 320 ms | 91 ms | 44 ms |
| chr22 3.6 Mb | 106,634 | 301 ms | 334 ms | 795 ms | 363 ms | 811 ms | 41 ms | 346 ms | 326 ms | 151 ms | 43 ms |
| chr22 10 Mb | 321,044 | 2.2 s | 954 ms | 2.2 s | 1.0 s | 7.7 s | 58 ms | 1.9 s | fails | 353 ms | 39 ms |
| chr22 32 Mb | 1,199,754 | aborts | aborts | > 300 s | > 300 s | crash | crash | > 300 s |  | 1.3 s | 98 ms |
| chr6 17 kb | 1,084 | 61 ms | 40 ms | 56 ms | 39 ms | 44 ms | 47 ms | 61 ms | 39 ms | 43 ms | 46 ms |
| chr6 90 kb | 5,095 | 100 ms | 98 ms | 111 ms | 93 ms | 56 ms | 46 ms | 75 ms | 88 ms | 41 ms | 44 ms |
| chr6 150 kb | 8,451 | 83 ms | 107 ms | 94 ms | 96 ms | 72 ms | 46 ms | 94 ms | 99 ms | 38 ms | 45 ms |
| chr6 400 kb | 36,182 | dies | 165 ms | 269 ms | 239 ms | 705 ms | 43 ms | 319 ms | 244 ms | 58 ms | 43 ms |
| chr6 1.8 Mb | 157,896 | dies | 12.2 s | > 300 s | > 300 s | 14.4 s | 54 ms | 2.8 s | 1.1 s | 172 ms | 42 ms |
| chr6 5.5 Mb | 277,560 | dies | 2.7 s |  |  | crash | crash | > 300 s | fails | 322 ms | 37 ms |
| chr6 30 Mb | 973,240 | aborts | aborts |  |  |  |  |  |  | 1.1 s | 59 ms |

Renderer peak resident MB:

| window | nodes | FMMM B | FMMM P | stress B | stress P | tube map B | tube map P | ordered B | ordered P | walk rows B | walk rows P |
|---|---|---|---|---|---|---|---|---|---|---|---|
| chr22 37 kb | 971 | 278 | 337 | 274 | 340 | 238 | 281 | 261 | 317 | 239 | 286 |
| chr22 220 kb | 5,143 | 392 | 454 | 403 | 441 | 288 | 333 | 326 | 405 | 314 | 326 |
| chr22 370 kb | 8,656 | 446 | 497 | 455 | 515 | 315 | 366 | 355 | 407 | 329 | 341 |
| chr22 1.1 Mb | 29,912 | 659 | 822 | 683 | 785 | 618 | 604 | 457 | 615 | 435 | 433 |
| chr22 2 Mb | 54,096 | 1,020 | 1,182 | 969 | 1,151 | 642 | 734 | 603 | 752 | 481 | 518 |
| chr22 3.6 Mb | 106,634 | 1,513 | 1,938 | 1,438 | 1,590 | 1,674 | 757 | 846 | 1,054 | 589 | 689 |
| chr22 10 Mb | 321,044 | 3,638 | 3,574 | 2,725 | 3,108 | 988 | 5,186 | 2,038 | fails | 1,385 | 1,226 |
| chr22 32 Mb | 1,199,754 | aborts | aborts | > 300 s | > 300 s | crash | crash | > 300 s |  | 3,288 | 3,766 |
| chr6 17 kb | 1,084 | 310 | 347 | 300 | 351 | 249 | 287 | 265 | 327 | 246 | 288 |
| chr6 90 kb | 5,095 | 452 | 479 | 458 | 474 | 312 | 341 | 331 | 400 | 317 | 332 |
| chr6 150 kb | 8,451 | 463 | 576 | 476 | 598 | 381 | 415 | 398 | 451 | 337 | 346 |
| chr6 400 kb | 36,182 | 804 | 1,076 | 997 | 1,052 | 563 | 1,158 | 736 | 847 | 433 | 494 |
| chr6 1.8 Mb | 157,896 | 2,319 | 2,964 | > 300 s | > 300 s | 1,037 | 4,107 | 1,736 | 2,193 | 737 | 864 |
| chr6 5.5 Mb | 277,560 | 3,261 | 3,891 |  |  | crash | crash | > 300 s | fails | 1,262 | 1,187 |
| chr6 30 Mb | 973,240 | aborts | aborts |  |  |  |  |  |  | 3,115 | 3,211 |

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
  window, 36,182 nodes, paints in 6.2 and 6.4 s
- **Stress:** 3.5 and 3.8 s, with the tab unanswering for 2.7 and 3.1 s of
  it; 12.0 and 11.8 s at the MHC's 36,182
- **Tube map:** 1.4 and 1.2 s; 3.8 s at the MHC's 36,182
- **Ordered:** 2.6 and 2.0 s; 6.6 and 9.8 s at the MHC's 36,182
- **Walk rows:** 471 and 298 ms; 537 and 358 ms at the MHC's 36,182

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

Each is for the owner; nothing here picks one.

- **One cap in the browser preset, 30,000 as held.** A cut past it throws
  `RegionTooLargeError` with `fitsBp`, the zoom-in notice readers already show
  - For: one number every browser reader inherits, which the deviations audit
    asks for (`agent-docs/reference/reader-deviations.md`); the cut stops
    before the layout
  - Against: graph-walks does not know the layout, so it refuses walk rows
    windows that draw in under a second; BandageJS today draws 30,000-100,000
    after **Draw anyway**, which this would refuse
- **A cap per layout, in bandage-core's layout modes or the readers.** From
  the 5 s estimates above, taking the MHC's: about 30,000 for FMMM, 20,000 for
  stress, 40,000 for the tube map, 25,000-30,000 for ordered, and 300,000 or
  more for walk rows
  - For: each layout refused where it stops being usable, not where the
    slowest does
  - Against: a switch of layout after the cut has to check again, and may
    need a narrower cut; the preset would carry only a ceiling, or none
- **A warning with "Draw anyway",** as BandageJS has from 20,000
  - For: nothing refused that would draw; the user, who knows the wait is
    worth it, decides
  - Against: still needs a hard ceiling (FMMM aborts by a million nodes; the tube
    map crashes from 277,560 in the MHC); in the main-thread layouts the tab
    freezes with no way to cancel, and in the plugin a long freeze can make
    the view fail outright ([Found on the way](#found-on-the-way)); FMMM, in a
    worker, can be cancelled
- **Draw something instead of refusing,** below

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

- **BandageJS's tab dies on the first pointer move** over the FMMM drawing
  of chr6 31.0-31.4 Mb (36,182 nodes) and the wider MHC windows, in every run:
  the main thread's JS heap runs to Chrome's 4 GB limit within seconds and the
  renderer crashes (`V8 javascript OOM`). It is the hover's edge hit test:
  bandage-core's `findHoveredEdge` builds an `EdgeSpatialIndex`, whose
  `addToGrid` stamps each link's bounding box cell by cell, and two links
  there span 3,784 x 5,913 and 3,839 x 5,878 cells, 22 million each
  ([hover-oom.txt](node-cap/hover-oom.txt), from a debug copy). The drawing
  itself is unaffected, so its times above stand; its zoom, pan and memory
  read "dies". No chr22 window and no other layout did it. The plugin's FMMM
  runs, with the pointer at the same place on its own pane, did not; whether
  its hover shares the fault was not checked
- **FMMM aborts at the ladder's two largest windows** in both readers
  (`RuntimeError: Aborted(undefined)` from the wasm engine), 1,199,754 nodes
  on chr22 and 973,240 on chr6, with the renderer at 2.5-4.8 GB
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
- **The plugin's view errors out in the ordered layout at chr22 10 Mb and
  chr6 5.5 Mb:** after the main thread had been held for minutes, JBrowse's
  fetch of a code chunk timed out and the view was replaced by
  `ChunkLoadError: Loading chunk 71176 failed. (timeout …)` (chunk 59038 on
  chr6). A long main-thread block in the plugin can take down the view, not
  just delay it
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
  that layout
- **Other jobs shared ada throughout,** so a run's load could rise after it
  started. Two runs at chr6 5.5 Mb in FMMM whose load reached 9-10 were run
  again. BandageJS's FMMM runs at chr6 0.4, 1.8 and 5.5 Mb were run again to
  read memory before the hover crash, and the plugin's first two tube-map
  runs at chr22 10 Mb to record every mark; the runs they replace are in
  [reader-runs-superseded.jsonl](node-cap/reader-runs-superseded.jsonl).
  Load moves the numbers: the first three runs at chr6 5.5 Mb drew in
  72.9-73.4 s at a load near 3, the three kept in 83.5-86.3 s at near 4. A
  first pass with the pointer at the pane's centre was dropped when
  BandageJS's hover crash showed

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
