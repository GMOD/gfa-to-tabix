---
name: refuse-inputs-the-writer-misreads
description: The walk writer reads segment names 01 and 1 as one node and refuses a GFA with no paths with an empty "have:" list, and the node and link index reads no W line end column and refuses a W line with no steps that --walks skips. Refuse or name each; each refuses a GFA accepted today and changes no file it still accepts.
metadata:
  repo: gfa-to-tabix
---

# Inputs the writer accepts and shouldn't

Each has a fixture under `docs/walks-container/dialect/` and a row in its
`expected.tsv` (checked 2026-11-25):

- Segment names `01` and `002` are read by `--walks` as nodes 1 and 2, so a
  line stepping on `1` steps on `01`
  ([s-leading-zero.gfa](../../docs/walks-container/dialect/s-leading-zero.gfa)).
  The index refuses it, as a step on a segment with no S line
- A GFA with no paths is refused as `--refs R matches no path's sample;
  have: ` with nothing after it
  ([no-paths.gfa](../../docs/walks-container/dialect/no-paths.gfa))
- The node and link index doesn't read a W line's end column, so it
  builds a graph `--walks` refuses for one
  ([w-end-wrong.gfa](../../docs/walks-container/dialect/w-end-wrong.gfa)),
  and it refuses a W line with no steps, which `--walks` skips
  ([w-empty-line-first.gfa](../../docs/walks-container/dialect/w-empty-line-first.gfa))

## The change

- Refuse segment names with a leading zero, naming the line
- Say that the GFA has no paths
- Check a W line's end in the index

Each refuses a GFA accepted today and changes no file it still accepts.
The expected rows change with them.
