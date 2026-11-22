---
name: paper-graph-figures-and-timings
description: Once plugin 10.5.0 is out, the paper's Figures 2, 5 and S7 are re-rendered on it, the pggb chrY windows re-timed, and four waiting text cards filled with the version and the numbers; the dense pggb windows measured 2.3 times slower on 10.4.3 than the paper says, before bandage-core 14.3.4.
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

- jb2bench e1e038c holds the 22 November rerun on ada with plugin 10.4.3 and
  jbrowse-web 5.0.0-beta.22. The hosted HPRC numbers are unchanged. The
  drawn pggb chrY windows took 0.4–3.4 s (median 2.6 s) where the paper says
  0.4–1.3 s (median 1.1 s).
- The cause was bandage-core's `closedStretches`, fixed in 14.3.4. In Node
  the 14,142-node window seeds its layout in about 0.5 s where it took 5 s.
  The browser re-measure was cut off: run jb2bench's pggb trace on ada
  (`~/work/scratch/graph-repro-2026-11-22`) with the plugin's `cut-speed`
  build, then with the release.
- `scripts/pggb/trace.sh` no longer writes a store reference, since
  beta.22 resolves one to the store's latest and ignores the pinned URL.

## Text cards waiting on the release

In `approve/cards.js` and `approve/index.html`:

- C6, Code availability: one plugin version for every graph figure and
  measurement.
- C10, Figure S7's caption: the upper track draws the rows of Figure 5.
- C12c, the response letter's "Graph plugin" item.
- C17b, the Results' pggb chrY timings, and C17c, the letter's "Plain GFA"
  line for Reviewer 1's comment 3. C17a, the hosted graph timing, does not
  wait on the release.
