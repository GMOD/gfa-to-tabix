# ADR 0006: Mark a haplotype that jumps over a window in the walk files

- **Status:** accepted for the writer, 2026-10-28. graph-walks doesn't draw
  `skip` rows yet
- **Decides:** what a walk file holds for a window that a haplotype's deletion
  spans
- **Measured by:** HPRC release 2's pggb chrY
  (`20251014_hprc25272.p98-k311.chrY.gfa.zst`, 1,053 paths) on GRCh38 and
  CHM13

## Context

- A walk file files each piece of a path under the chunk of its reference
  steps. A haplotype that leaves the reference before a window and rejoins it
  after has no row in the window's chunks, as
  [gbz-comparison.md](../gbz-comparison.md#differences) lists under misses
- A viewer then draws the haplotype as absent, the same as one with no
  assembly there, though the haplotype carries a deletion
- Tested on two synthetic graphs:
  - `>1>2>9>10` against a reference `>1` to `>10` of 10 bp nodes, `--chunk 10`:
    a query over 31-60 returns only `ref` rows. The piece at chunk 10 records
    the jump as `nx:i:80`, but a window at 40 never reads chunk 10
  - a 300 kb deletion at the default chunk: graph-walks' `WalkReader.cut`
    shows nothing for the haplotype in windows from 120 to 310 kb. The reader
    follows a cut-off walk at most 4 chunks (`FOLLOW_CHUNKS`), and only one it
    has read
- The node and link index has no such gap: it files a deletion link under the
  span it jumps

## Decision

- Between two consecutive pieces of a path of another sample, the tool takes
  the reference passes of the last reference step before the jump and the
  first after it. When both lie on one sequence and leave a stretch between
  them, the tool writes a `skip` row into each chunk that stretch touches
- A path gets at most one `skip` row in a chunk, from its first jump over it,
  and none in a chunk where it has a piece
- A stretch touching more than 32 chunks (2 Mb at the default chunk) gets no
  rows, so a jump onto a distant paralog writes none. The header states the
  limit as `skip:i:32`
- Row: `seq cs cs+1 skip path fragStart piece from to refStart refEnd`.
  `piece` numbers the piece before the jump, `from` and `to` give the chunks
  the two pieces are filed under, and `refStart`-`refEnd` is the stretch
- A crossing of a reference node longer than a chunk leaves no stretch, so it
  writes no row though its pieces lie chunks apart
- graph-walks 4 skips row kinds it doesn't know, so the files stay format 5,
  as `#long` lines did in format 4

## Evidence

pggb chrY, built with `--refs GRCh38,CHM13`:

| | GRCh38 | CHM13 |
|---|---|---|
| walk rows | 246,593 | 582,942 |
| `skip` rows, one per jump and chunk | 910,123 | 2,857,477 |
| `skip` rows, one per path and chunk | 4,879 | 37,705 |
| jumps writing them | 693 | 4,306 |
| jumps going backward along the reference | 247 | 1,472 |
| median stretch | 789 kb | 803 kb |
| `skip` rows bgzipped | under 0.05 MB | 0.3 MB |
| walk file | 179.8 MB | 117.4 MB |

- Writing a row per jump put 891,275 of GRCh38's 910,123 rows in a chunk the
  same path had already skipped: in chrY's collapsed ampliconic repeats, a
  haplotype hops back and forth over the same chunks
- One row per path and chunk costs under 0.3% of the file
- No stretch is under 10 kb, since a row needs a chunk the path doesn't touch

## Alternatives rejected

- **One row under the jump's whole interval:** Tabix returns it for every
  window inside, but files it in a coarse bin, so every query there reads it,
  as with the node and link index's wide intervals
  ([ADR 0005](0005-node-link-format-2.md))
- **Follow `nx` tags further in the reader:** the window's chunks hold no row of
  the haplotype to follow from
- **A row per jump:** 76 to 186 times the rows on chrY, for the same chunks

## Still open

- The chrY numbers don't separate deletions from hops between repeat copies.
  Score the jumps against impg's alignments, as ADR 0001 scores placement
- Count the rows on HPRC v2.1's Minigraph-Cactus graph, where jumps are mostly
  real deletions
- graph-walks: draw a `skip` row as the haplotype crossing the window, and
  count it against the window's budgets
