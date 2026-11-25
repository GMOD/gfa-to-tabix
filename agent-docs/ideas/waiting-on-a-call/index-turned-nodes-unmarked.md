---
name: index-turned-nodes-unmarked
description: On a plain GFA the node and link index turns a node to read forward along the first path that places it and its rows don't say which nodes it turned, while walk files keep the GFA's strands. Before any reader draws walks over index nodes, either mark a turned node on its row (an index-format change) or have the reader orient by the walk file's ref rows.
metadata:
  repo: gfa-to-tabix, graph-walks
---

# The index and walk files disagree on a node's strand

- On a plain GFA the index turns a node to read forward along the first
  path that places it (`flip` in `src/place.rs`, called from
  `src/main.rs`), and its rows don't say which nodes it turned;
  `docs/index-format.md` has no word on it (checked 2026-11-25)
- Walk files keep the GFA's strands
- The plugin draws the fine tier from one or the other, never both, so
  nothing shows it yet

## The choice

Before any reader draws walks over index nodes, either:

- mark a turned node on its row, an index-format change, or
- have the reader orient by the walk file's `ref` rows

The revisited-reference study reads the index against walk files more
widely (`../../handoffs/2026-11-22-revisited-reference-study.md`).
