---
name: index-carrier-tag-names
description: The node and link index writes a link row's two carrier tags under one name, SB:H:, with values that are not SAM H hex, and renaming the second within format 2 would break graph-walks. graph-walks would first accept a TB tag beside SB, so a later index format can rename and retype them, and write the shorter of the bitmask and a list.
metadata:
  repo: gfa-to-tabix, graph-walks
---

# The index's carrier tags

- The tool writes a link row's two carrier tags under one name, `SB:H:`,
  with values that aren't SAM `H` hex
  ([What the file holds](../../../docs/index-format.md#what-the-file-holds))
- Today's readers cope. graph-walks, the only one that parses `SB`, takes
  the two tags by column (`parseGraphRow` in `src/rgfaBed.ts`), and
  bandage-core gets carriers as `SM:Z:` from graph-walks
- Renaming the target's tag within format 2 would break graph-walks, which
  rewrites only columns that start `SB:H:`, so the far ends would lose
  their carriers (still so at graph-walks 7592122, 2026-11-23)
- A list of assembly numbers, where shorter than the bitmask, saves 12% of
  node tag text and 7% of link tag text on pggb chrY's 151 assemblies, and
  nothing after gzip
- The concept inventory of 2026-11-18 left this to its own change
  (`../../reference/concepts-beyond-gfa.md`)

## The proposal

Have graph-walks accept a target tag named `TB` beside `SB`, so a later
index format can rename it, type both `Z`, and write the shorter of the
bitmask and a list, measured again at HPRC's 470 assemblies.

## What it waits on

A call on an index-format change, after graph-walks accepts `TB`.
