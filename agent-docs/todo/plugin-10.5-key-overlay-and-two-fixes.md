---
name: plugin-10.5-key-overlay-and-two-fixes
description: Plugin 10.5.0 is to carry what the paper's graph figures need: a graph track key that can lie over the drawing, bandage-core's speed fixes for dense windows, and stress layout 1.1.0, which draws a deletion nested in a deletion as two detours. The key and the first speed fix sit on an unpushed plugin branch; the second speed fix is being made.
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
- **Nested bars:** `@jbrowse/graph-stress-layout` 1.1.0 is released
  (tag v1.1.0, Push and Publish green). A bar hung under a gap clears its
  own links, sliding off the gap's centre where only that clears them, so
  the outer deletion's link no longer runs through the inner allele's node.
  - On twelve other cuts no drawing has more links through a node, and of
    the seven other screenshots that use the stress layout six are unchanged
    and one moves a bar a few pixels.
  - The layout is about 1.4 times slower on 16,000 bubbles side by side and
    2.3 times when they nest ten deep.
  - The release also pushed that repo's lint commit of 8 November (oxlint,
    oxfmt, tsrs), which had sat unpushed on local main.
  - bandage-core takes `^1.0.0`; its bump to 1.1.0 rides on branch
    `runs-along-speed`.

## Before the release

- Dense windows freeze the tab for over a minute while drawing, since
  10.0.0: `todo/paper-graph-figures-and-timings.md`, "Timings". The fix, on
  bandage-core branch `runs-along-speed`, goes in this release.

- Release bandage-core with the speed fix and the stress layout at 1.1.0,
  then the plugin, by the usual gates, with `scripts/shoot-figures.mjs
  --compare` over every spec against 10.4.4 looked at.
- Re-pin BandageJS and ggbandage to the same bandage-core.
- The store publish stays with the laptop.

## After it

`todo/paper-graph-figures-and-timings.md`.
