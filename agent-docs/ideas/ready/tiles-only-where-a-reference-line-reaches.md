---
name: tiles-only-where-a-reference-line-reaches
description: The walk writer holds an entry for every tile from 0 to each reference sequence's end, whether a line covers it or not, so a reference line starting near 2^46 aborts under a 4 GB memory cap at the default tile. Hold entries only for tiles a reference line reaches, if a graph with such a line turns up.
metadata:
  repo: gfa-to-tabix
---

# Tiles only where a reference line reaches

- The writer allocates an entry per tile of each reference sequence from
  0 (`Chunks::new` in `src/walks.rs` counts `end.div_ceil(size)`), so a
  reference line starting near 2^46 aborts under a 4 GB memory cap at the
  default tile
  ([big-refstart-2e46.gfa](../../../docs/walks-container/dialect/big-refstart-2e46.gfa)).
  The dialect table skips that file in tests: "its tiles from 0 take more
  memory than a test may" (`docs/walks-container/dialect/expected.tsv`)
- No real assembly has such a coordinate; a W line's start is whatever its
  writer put there
- The coordinates themselves are settled: since 5.0.0 the writer refuses a
  line that starts or ends past 2^53, and a reference whose last tile
  does ([Where a step is filed](../../../docs/walks-writer.md#where-a-step-is-filed),
  [line-end-2e53.gfa](../../../docs/walks-container/dialect/line-end-2e53.gfa),
  [line-end-past-2e53.gfa](../../../docs/walks-container/dialect/line-end-past-2e53.gfa))

## The change

Hold entries only for tiles a reference line reaches, if a graph with
such a line turns up.
