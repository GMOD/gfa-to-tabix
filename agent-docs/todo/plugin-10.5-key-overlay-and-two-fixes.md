---
name: plugin-10.5-key-overlay-and-two-fixes
description: Plugin 10.5.0 is to carry three things the paper's graph figures need: a graph track key that can lie over the drawing, bandage-core 14.3.4's faster layout seed for dense windows, and a stress-layout fix that draws a deletion nested in a deletion as two detours. The first two sit on an unpushed branch; the third is not released.
metadata:
  repo: jbrowse-plugin-graphgenomeviewer
---

# Plugin 10.5.0: key overlay, dense-window speed, nested bars

A paper session asked for all three on 2026-11-22 and the owner agreed to the
releases ("we can certainly release new versions"). It ran out of quota
mid-way. Its transcript is `~/.claude/projects/-home-cdiesh-paper/d4df8e96…`,
and its scratch files are copied to
`~/src/walks8-evidence/sessions-20261122/paper/`.

## Where each part is

- **Key overlay:** branch `graph-key-overlay`, fa8e1f8b, in
  `~/src/jbrowse-plugin-graphgenomeviewer-keyoverlay`, on 10.4.4, not pushed.
  - A graph track takes `key`: `column` (the default, as today), `overlay`
    or `hidden`.
  - A track that follows the view draws and labels only the view; drawing
    past it was treated as a fault, so that part reaches every such track.
  - The owner has seen Figures 2 and 5 drawn with it.
- **Dense-window speed:** bandage-core 14.3.4 is released (84a78ee, tag
  v14.3.4, Push and Publish green with both consumer jobs).
  - `closedStretches` walked each like-end join's whole span, since
    `archSeeds` came in with 14.0.0. It now reads a running count.
  - The plugin's bump is branch `cut-speed`, 23943542, on top of the key
    overlay, in `~/src/jbrowse-plugin-graphgenomeviewer-cutspeed`: 1,169
    tests and the typecheck pass, not pushed.
  - BandageJS and ggbandage are still on 14.3.3.
- **Nested bars:** `@jbrowse/graph-stress-layout`, branch `nested-bubbles` in
  `~/src/graph-stress-layout-nested`. A bar's two links are not tested
  against what already hangs in its gap, so the outer deletion's link runs
  through the inner allele's node. The plan, reviewed by Fable, is
  `sessions-20261122/paper/nestedplan.txt`: link-aware bar candidates that
  may slide off the centre of their gap.

## Before the release

- The nested-bars change moves bars over gaps that hold other pieces. Shoot
  `scripts/shoot-figures.mjs --compare` over every spec against 10.4.4, look
  at each pair, and show the owner the ones a reader sees at a glance.
- Release graph-stress-layout, then whatever of bandage-core pins it, then
  the plugin, by the usual gates.
- Re-pin BandageJS and ggbandage to the same bandage-core.
- The store publish stays with the laptop.

## After it

`todo/paper-graph-figures-and-timings.md`.
