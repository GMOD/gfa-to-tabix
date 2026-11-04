# The format 6 rebuild, 2026-11-03

ADR 0009's "Open before the port": a prototype writer of the amended
Decision, built on ada on HPRC v2.1 Minigraph-Cactus chr22 (`mc22`) and
HPRC release 2 pggb chrY (`pggbY`) and chr22 (`pggb22`), on GRCh38, under
nearest-pass placement and alignment-guided placement (`pggbYa`,
`pggb22a`, from `~/work/impg/lift.*.primary.tsv`). Every file but pggb
chr22's under nearest pass was read back by
[`audit6.py`](../../scripts/audit6.py); see below.

The prototype is saved as `~/notes/handoffs/2026-11-03-format6-prototype.patch`
(the simplified format) and `-with-crowds.patch` (the amended Decision the
variants measured), both against 6e1ddf6. Its live copy is
`target/f6/tree`, which `cargo clean` deletes.

## Files

- `NAME.build.log`, `NAME.audit.txt`: the simplified format 6 that ADR 0009
  now specifies: records between pieces and at contig ends, each filed over
  its whole stretch, no crowds, no `recordbp`, no `mp`. The aligned pggb
  chr22 file was audited on 2026-11-04 (`pggb22a.audit.txt`, 35 GB). Nearest
  pass on pggb chr22 has a build log only: its audit needs `--shard` (about
  37 GB a shard), and its shards were stopped twice when other jobs filled
  ada's memory, on 2026-11-03 and 11-04. The port's file, which has the same
  rows, is the one to audit next
- `variants/NAME.VARIANT.*`: the amended Decision before the
  simplification, with records inside a piece from `recordbp` or across a
  chunk boundary, `mp` tags, and its filings:
  - `k8`, `k4`: base-level filing (the stretch less the path's own pieces,
    the whole stretch for strand switches and back jumps with both ends on
    nodes passed once) with `crowd` rows at `crowdmax` 8 and 4. pggb chr22
    under nearest pass was not built with crowds: at the sizes below it
    would have filled ada's disk
  - `k0`: base-level filing, no crowds
  - `whole`: every record over its whole stretch, no crowds
- `zero-length-nodes.txt`: S lines of 0 bp in MC chr22, where the ADR's
  former reader match key could collide. The pggb counts were lost when
  other jobs filled ada's memory; the key is gone, so they no longer
  decide anything

## What the audit checks

It decodes every walk row, detail ones included, to positions by the
documented rules, recomputes every departure from those positions, and
checks:

- each departure that needs a record has one with every field equal, and
  every record matches a departure. A W line with no step on the
  reference has no rows, so its steps are invisible to a reader; records
  over one are counted apart as "steps unseen"
- every departure the reader computes inside a piece lies where a reader
  of any window over it reads the piece's chunk (the chunk and the next,
  or a `#long` pass starting in one of them)
- every base of a record's stretch lies under a row of the record
- per 64 kb window and per 1 bp window every 1,024 bp: departure rows by
  class, text bytes, paths, distinct `leaveChunk`s outside the walk read,
  and requests and bytes from the `.tbi` as @gmod/tabix 3.10 merges chunks
- against `dep.rs`'s enumeration from the GFA where it exists (MC chr22,
  pggb chrY), on departures with both ends on nodes passed once. Its
  stretches are the gap between the nodes, the records' the breakpoints,
  so they differ wherever an end runs against S or the jump goes back

It agrees with the writer on every test fixture in five option modes and on
450 random graphs ([`fuzz6.sh`](../../scripts/fuzz6.sh) with
[`fuzz6-gen.py`](../../scripts/fuzz6-gen.py)) in six, at chunks of 8 to 64 bp.
