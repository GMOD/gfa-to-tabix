---
name: concepts-beyond-gfa
description: The four classes of concept walk format 8 adds to GFA (restated GFA, derived from GFA and one reference, writer policy, packaging), the 2026-11-18 inventory that found no byte-level change worth making, and the reader written from the format page alone on 2026-11-19.
---

# Concepts beyond GFA

Walk format 8 asks its readers, and through them its users, to learn
concepts a GFA doesn't have, and each one costs users, other implementers
and a paper that must explain it. As of 2026-11-19 each falls in one of
four classes:

- **Restated GFA:** node ids, lengths, bases, each line's steps.
  `walks-truth.py rebuild` shows the lines come back step for step
- **Derived from GFA and one reference, with no choice involved:**
  reference positions, `passes`, `revisited`, departures, `#hole`,
  `leftout`. Anyone can recompute them, but readers must learn what they
  mean
- **Writer policy, bytes that follow a choice or budget of the writer:**
  where a step lies on a node the reference passes more than once
  (`stay`, the nearest pass), abridging and its budgets, the tile size,
  departure bins
- **Packaging:** units, the directory, `#entry` tables, routes as runs
  shared by haplotypes. This is what lets a window take a few byte ranges
  where gfaidx takes hundreds
  ([comparison](../../docs/comparison-details.md#reading-a-64-kb-window))

The format page separates exact from chosen
([Exact and chosen](../../docs/walks-format.md#exact-and-chosen)).
gfaidx-viz, for one, shows paths, links and the reference, and none of
departures, abridged blocks or placement choices.

## The inventory of 2026-11-18

- An inventory of every concept against a minimal design derived from the
  requirements alone found no byte-level change to the walk file that
  beats shipping unchanged
- Three reviews then kept C43's bin sizes as format, the writer's policy
  where it is fenced and the vocabulary as it is, and left the index's
  doubled `SB:H:` to its own change
  (`../ideas/waiting-on-a-call/index-carrier-tag-names.md`)
- What is left is about what users are shown, not bytes: one abridge
  budget, `--format 1` out of the docs, readers' strings that use the
  format's words, and one mark for a haplotype leaving the reference
  however it is encoded (`../ideas/waiting-on-a-call/after-freeze-format-story.md`)

## A reader from the page alone, 2026-11-19

- A reader written from `docs/walks-format.md` alone, before its author
  had read the writer or another reader, rebuilt the W and P lines of the
  fixtures' files and of 2,101 files of random graphs on its first run
- `scripts/walks-brief.py` is that reader in about 150 lines. To rebuild
  the lines it reads the directory, the tables, the `ref`, `nodes`,
  `route` and `walk` rows and the `detail` units
- A reader of one window also needs the `departure` rows, for where a path
  goes outside the tiles it read, the `blocks` rows, to draw a moved piece
  without its detail unit, and `passes`, to mark a position as chosen
- The scripts and counts are in
  `~/src/walks8-evidence/doc-only-reader-20261119/`
