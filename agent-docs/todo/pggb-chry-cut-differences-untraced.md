---
name: pggb-chry-cut-differences-untraced
description: On pggb chrY a loaded and an unloaded cut still differ in one untraced window at CHM13 28.84 Mb (7,298 against 7,294 links with an end off the reference), and the 4 links over 2 windows left after graph-walks 0350375 have not been rerun since graph-walks gained its links setting. Trace the one and rerun both.
metadata:
  repo: graph-walks
---

# Loaded and unloaded cuts on pggb chrY

The record, with every probe and output, is
[pggbY/notes.md](../../docs/walks-container/pggbY/notes.md#where-a-loaded-and-an-unloaded-cut-differ),
measured 2026-11-12 and 11-13.

- **Untraced:** at CHM13 chrY 28.84 Mb the loaded cut walks links with an
  end off the reference 7,298 times and the unloaded one 7,294
- **Not rerun:** after graph-walks 0350375, pggb chrY's cuts differed in 4
  links over 2 of 24 windows, where a built piece takes a route through a
  node the reference passes elsewhere on steps the cut trims off its
  fragment. The suggestion then was a cut that lists the reference's links
  and those its returned steps walk, and no other. graph-walks now has a
  `links` setting, `walked` by default (`src/walkReader.ts`, 7592122);
  whether `walked` ends the 4 has not been run
- Rerun the equality harness on both pggb chrY files at graph-walks' head,
  on ada, and trace the 28.84 Mb window
- The 4 can't happen where `revisited` is 0, so on no hosted file; the
  28.84 Mb window's cause is not known
- The place-by-chain proposal would put more runs off the reference
  through nodes the reference passes elsewhere
  (`../handoffs/2026-11-22-pggb-place-by-chain.md`), so a trace here
  bears on it
