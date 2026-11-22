---
name: lanes-coarse-table
description: Haplotype lanes read from a walk file stop near 1 Mb with tens of lanes and have no way in from a haplotype's own coordinates; a small table of each haplotype's blocks against the reference, beside the walk file, would give a zoomed-out tier and that way in. Decided 2026-11-22: it waits on the walk-file overview-tier study and is judged there as one of its candidates.
metadata:
  repo: jbrowse-plugin-graphgenomeviewer
---

# A coarse table for lanes read from walk files

Measured 2026-11-22 on the hosted HPRC format 8 walk file with the plugin at
10.4.3, in Node on ada (`~/work/synteny-extract-1122/time.jsonl`).

## What lanes do today

- Eight lanes answer every window to 5 Mb, a 1 Mb window in under a second.
- Forty lanes answer to 1 Mb and are refused at 5 Mb; all 463 answer to
  about 100 kb and are refused at 1 Mb. The step budget refuses them.
- `WalkTabixSyntenyAdapter` reports `hasCoarseTier: false`, so JBrowse asks
  it for the whole window at any zoom.
- It answers only regions on the reference. A stacked `LinearSyntenyView`
  gets records only on a level whose upper row is the reference, and a lane
  cannot be re-anchored.

## The idea

- The hosted `hprc_multiway` PIF's coarse tier holds a few hundred rows per
  haplotype for the whole genome: each haplotype's blocks against GRCh38,
  with indels over 5 kb kept.
- A table like it beside the walk file, for every haplotype, is the
  zoomed-out tier. The walk file stays the fine tier: it already holds every
  haplotype, where a PIF's fine tier grows with each one.
- Read from the haplotype's side, the same table says which reference window
  a stretch of a haplotype lies in, so the adapter can answer a region on a
  haplotype by cutting the walk file there.
- It is a side file, not a change to the walk file. It falls under
  `docs/open-problems.md`, "Pairing a side file with a walk file", as
  `haplotype-coordinate-lookup.md` does, and the two may be one file.

## Why it waits

- The overview-tier study in `handoffs/2026-11-21-ada-next.md` already
  weighs per-haplotype runs at a coarser tile, which may hold the same
  blocks.
- The table adds a side file, which `docs/open-problems.md` has not yet said
  how to pair with a walk file.
- It inherits the lanes' limit at loci like amylase, where identical
  sequence sits on separate nodes.

## Not known

- Who writes it. `gfa_to_pairwise_paf.py` has been run for eight haplotypes,
  not 463. gfa-to-tabix places every walk against the reference while it
  writes a walk file and could write the table in the same pass.
- Whether the walk-file overview tier the ada session's second queue studies
  would hold the same blocks.
- How lanes between two haplotypes should draw from a table that only states
  each against the reference.
