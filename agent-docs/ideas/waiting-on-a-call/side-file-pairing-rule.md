---
name: side-file-pairing-rule
description: No rule says how a file beside a walk file names the walk file it was built against. graph:Z: names only the segments, the #walks line names no reference, and the prototype's bytes:i: follows the compressor; a hash of the directory was proposed by two reviews and measured by none. ADR 0016 leaves the rule to the first side file.
metadata:
  repo: gfa-to-tabix
---

# Pairing a side file with a walk file

Several proposals are side files and need this first:
`haplotype-coordinate-lookup.md`,
`../waiting-on-someone-else/lanes-coarse-table.md`,
`../waiting-on-someone-else/gfa-tags-not-kept.md`, and the side-file form
of `complete-adjacency-for-a-bubble-layer.md`.

## What the file gives to pair by

- `graph:Z:` names the GFA's segments, not the walk file: two `--refs` of
  one GFA share it, and a side file naming pieces depends on `tile`,
  `stay` and the abridging budgets as well
- A side file can copy the whole `#walks` line it was built against, and
  must also name the reference sample: two `--refs` files of one GFA and
  options can state the same `#walks` line, which names no reference
  ([Header](../../../docs/walks-format.md#header)). A hash of the paths
  could come later as a tag
- The page says the same walk file is the same bytes
  ([Header](../../../docs/walks-format.md#header)), and no rule says how a
  second file names those bytes

## What was tried

- The rule a prototype wrote copies the directory's line 1, whose
  `bytes:i:` is the one field that told two files of the same segments and
  options apart, 676 against 643. `bytes:i:` follows the compressor: the
  same rows compressed again would not pair, and other rows of the same
  length would
  ([the format study](../../../docs/walks-container/format-study/writeup.txt),
  its pairing section, and
  [the review of its text](../../../docs/walks-container/format-study/review-spec.txt))
- A hash of the directory, which holds every table's offset and length,
  was proposed by two reviews and measured by none

## What it waits on

ADR 0016's three reviews: "later, with the first side file, from all
three" ([The candidates](../../../docs/adr/0016-format-8-is-frozen.md#the-candidates)).
