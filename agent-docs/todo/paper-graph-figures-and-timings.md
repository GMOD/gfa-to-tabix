---
name: paper-graph-figures-and-timings
description: Once plugin 10.5.0 is out, the paper's Figures 2, 5 and S7 are re-rendered on it, the pggb chrY windows re-timed, and four waiting text cards filled with the version and the numbers; the paper's pggb timing is the time to load a graph and not to draw it, and dense windows take about 85 s to draw on 10.4.3 against 2.6 s on 9.0.0.
metadata:
  repo: paper, jbrowse-components, jb2bench
---

# The paper's graph figures and timings on one plugin release

Waits on `todo/plugin-10.5-key-overlay-and-two-fixes.md`. The paper session
that started this ran out of quota on 2026-11-22; its scratch files are in
`~/src/walks8-evidence/sessions-20261122/paper/`, and its pages are private
to the `~/.claude` account, so a session under another config publishes
anew from `approve/` and `compare/` there.

## Figures

- Re-render Figures 2, 5 and S7 from their jbrowse-components specs
  (`website/scripts/specs/paper-cohort.ts`, `paper-hprc-workspace.ts` and
  `paper-hprc-minimap2.ts`) with the graph track's `key: 'overlay'`.
  `~/src/jbrowse-components-keyoverlay` holds uncommitted changes to
  `graph-fixtures.ts` and the first two specs.
- Figure 2's graph track needs 320 px, not 270, so the key clears the
  drawing.
- Figure 5's callout box is clipped at the right edge and its arrow covers
  the 2.5 kb label.
- Figure 2c: the 114 kb detour's left end sits about 55 px early, since the
  layout places nodes by length, not position. Not asked to be fixed.
- Figure S7 is reshot with the walk rows as the upper track.

## Timings

- **The paper's pggb number is the time to load the graph, not to draw it.**
  jb2bench's `cutMs` stops when the view holds a graph; layout and drawing
  come after. The sentence "a graph view drew 15 in 0.4–1.3 s" and cards
  C17b and C17c quote it as drawing. Measured on ada on 2026-11-22
  (`~/work/scratch/cut-speed-prof/out/`, copied to
  `~/src/walks8-evidence/sessions-20261122/takeover/pggb-retime/`), until
  the layout is in place and two frames have painted, the eight dense
  windows of 14,000–17,600 nodes take about 2.6 s on plugin 9.0.0.
- **On 10.4.3 those windows take about 85 s, with the tab frozen.**
  bandage-core 14.3.4 does not change that. One profile puts 73 s in
  `runsAlong` and `distanceToSegment` (`src/util/edgeCurves.ts`), which test
  every sample of a deletion edge against every skipped node.
- **bandage-core 14.3.5 fixes that:** the same windows draw in 8.5–10.5 s on
  a plugin build with it, with byte-identical screenshots. What is left
  against 9.0.0 is the FMMM layout in the worker, 5.9 s against 1.3 s for
  the 14,142-node window, and about 1.9 s of main thread against 0.5 s. A
  laptop session is finding out why.
- **Load time is back to 9.0.0's with 14.3.4:** the drawn windows load in
  0.4–1.2 s (median 1.1 s) on the plugin's `cut-speed` build, where 10.4.3
  took 0.4–3.4 s (median 2.6 s). Nodes, requests and bytes are identical in
  every window.
- **The dense pggb windows are mostly not those windows.** Of the 14,142
  nodes drawn at `chrY:17,123,157`, 114 are the window's own graph; the rest
  come from megabases away, kept because their links' stored places lie
  either side of the window: `todo/dense-pggb-chain-joints-drawn-as-skips.md`.
  The paper's "up to 17,570 nodes" counts them.
- jb2bench e1e038c holds the 22 November rerun with 10.4.3. The hosted HPRC
  numbers are unchanged.
- To redo for the paper: time to drawn, on the released plugin, with
  `drawn-local.sh` there, and reword the sentence to say which clock it is.
  `scripts/pggb/trace.sh` takes only a released version, not a local build,
  and writes no store reference since beta.22 resolves one to the store's
  latest.

## Text cards waiting on the release

In `approve/cards.js` and `approve/index.html`:

- C6, Code availability: one plugin version for every graph figure and
  measurement.
- C10, Figure S7's caption: the upper track draws the rows of Figure 5.
- C12c, the response letter's "Graph plugin" item.
- C17b, the Results' pggb chrY timings, and C17c, the letter's "Plain GFA"
  line for Reviewer 1's comment 3. C17a, the hosted graph timing, does not
  wait on the release.
