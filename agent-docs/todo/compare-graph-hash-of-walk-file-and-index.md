---
name: compare-graph-hash-of-walk-file-and-index
description: A reader that opens a walk file beside a node and link index of the same graph should compare their graph:Z: values and say when they differ; no host or viewer does, so a walk file beside an index of another graph is drawn without a word.
metadata:
  repo: graph-walks, jbrowse-plugin-graphgenomeviewer
---

# Compare a walk file's graph hash with its index's

- A walk file names its graph in `graph:Z:`, the hash the node and link
  index states on its header line, and counts the lines it leaves out in
  `leftout:i:`
  ([ADR 0015](../../docs/adr/0015-walk-files-name-their-graph.md)).
  ADR 0015 expects a host or viewer that opens both to compare the two
  and say when they came from different graphs
- None does. graph-walks reads the walk file's `graph` into its header
  (`src/walkRows.ts`, 7592122); a grep of the plugin (e8be6f6d) and
  bandage-core (eef96c9) on 2026-11-25 finds no comparison with an index's
- A directory from another build is already refused where its line 1
  differs from the data's `#walks` line or its `bytes:i:` from the data's
  length ([The directory](../../docs/walks-format.md#the-directory)); a
  reader that can't learn the length, behind a server that hides
  Content-Range, falls back on its `#unit` check of the first unit it
  reads

## The change

Once a consumer reads a walk file beside an index of the same graph,
compare the two `graph:Z:` values and say so when they differ.

The file names no writer on purpose: a version stamp would change every
file's bytes at each writer release and force every hosted file to be
uploaded again (ADR 0015, "Rejects").
