---
name: vg-phase-block-counters
description: For haplotypes from a VCF-phased GBWT, vg writes a phase-block counter where gfa-to-tabix reads a start, in a P line name's fourth field and a W line's start column; blocks that collide are refused, others are placed at their counter. Find what in vg's graph tells a counted block from a clipped fragment, when someone brings a VCF-phased graph.
metadata:
  repo: gfa-to-tabix
---

# vg's phase-block counters read as starts

ADR 0014 decided how a P line's name is read, and the writer page states
this limit
([A limit: phase blocks](../../../docs/walks-writer.md#path-names),
[ADR 0014](../../../docs/adr/0014-p-line-names.md)).

- For haplotypes from a VCF-phased GBWT, vg numbers a contig's phase
  blocks 0, 1, 2 and writes that counter in the fourth field of a P line's
  name and in a W line's start column, and the tool reads both as starts
- Blocks whose stretches then overlap are refused, with a message that
  names the cause
  ([vg-vcf-phased-p.gfa](../../../docs/walks-container/dialect/vg-vcf-phased-p.gfa),
  [vg-vcf-phased-w.gfa](../../../docs/walks-container/dialect/vg-vcf-phased-w.gfa))
- A block alone, or blocks that don't collide, are placed at their
  counter: `S1#0#chr1#2` of 70 bp is written from 2 where it lies at 50
- The same field is a start for a haplotype clipped out of a
  Minigraph-Cactus GBZ, and no line says which it is

The other name and column readings the same section listed (a 1-based
range, a `:a-b` cut past its bracket, a W line's `*` start, GFA 1.2's `;`
jumps) are tested behaviour: rows of
`docs/walks-container/dialect/expected.tsv` and sentences of
[Path names](../../../docs/walks-writer.md#path-names).

## Next

When someone brings a VCF-phased graph, find what, if anything, in vg's
graph tells a counted block from a clipped fragment, since its P and W
lines don't. The reading can accept more later, and can't re-mean what it
reads today.
