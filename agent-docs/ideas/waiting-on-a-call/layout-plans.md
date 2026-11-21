---
name: layout-plans
description: Three plans from 2026-11-18 wait on the owner's decisions: holding the layout steady between cuts, a least drawn length sized by the view, and whether the separate graph genome view stays.
metadata:
  repo: bandage-core, jbrowse-plugin-graphgenomeviewer
---

# Layout plans waiting on decisions

The plans are in `~/src/walks8-evidence/layout-next-20261118/`. Bandage-core
14.1.0 and the plugin's 10.1.x changed node lengths and the layout switch
since, so read each plan against today's heads first.

- **Cut stability** (`cut-stability/plan.md`): hold the layout within a
  drawn cut to a depth limit of 8, mirror-match replacements, rotate to level
  the reference, no seeding. To decide: path dependence in a live session,
  the cap on the turn, and the floor rule it shares with the plan below
- **Least lengths** (`min-lengths/plan.md`): a least length sized by the
  view, for the track only, in sparse cuts; and skips measured by bp in the
  draw-time fold, which amends "small means small as drawn" for skips. To
  decide: the skip clause, the 12 px mark size, leaving loop-held cuts alone.
  Under a hold, a floor fixed at the cut's zoom is magnified up to 8 times,
  so the depth limit is settled with it
- **The graph genome view** (`pit-of-success/plan.md`): the owner is open to
  removing it, since a graph reads better as a track. It is still the only
  way to open a small whole GFA, and `launchFromGraph` opens it
