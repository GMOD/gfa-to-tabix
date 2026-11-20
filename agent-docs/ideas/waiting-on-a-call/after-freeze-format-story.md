---
name: after-freeze-format-story
description: What the 2026-11-18 concept inventory left for after the freeze: one abridge budget as one writer option, dropping --format 1 from the story, and bandage-core strings that show users the format's words.
metadata:
  repo: gfa-to-tabix, bandage-core
---

# After the freeze: fewer concepts shown

The inventory (a Fable 5.2 read of format 8 against a minimal design derived
from the requirements) found no byte-level change to the walk file that beats
shipping unchanged. The final green round ruled on its format candidates: C43's
bin sizes stay format, with a note on ADR 0010; writer policy stays where it is
fenced; no vocabulary merge; the index's doubled `SB:H:` is a separate
index-format change (`docs/open-problems.md`, "Format 2's carrier tags").
Left:

- **One abridge budget:** C202 says budgets bind no row, and ADR 0004 has no
  measurement separating the byte budget from the step budget. Merge them into
  one writer option, or measure a case where they differ
- **`--format 1`:** back-compat only; drop it from the README and docs
- **Reader strings (bandage-core):** "placement choice" and its legend line,
  "departure(s)" as in "N departures outside the row", "nodes not shown",
  "off the reference not loaded", "own sequence not drawn", "left out of
  graph", "no step on the reference". Say what the user sees, not the format's
  word
- **One event, one mark:** a haplotype leaving the reference is encoded four
  ways (a route inside a tile, a departure inside a piece, a departure record
  between pieces, `d` and runs in a blocks list). A reader should draw one mark
  for all four
