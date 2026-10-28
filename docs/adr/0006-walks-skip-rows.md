# ADR 0006: Mark a haplotype that jumps over a window in the walk files

- **Status:** proposed, 2026-10-28
- **Decides:** what a walk file holds for a window that a haplotype's deletion
  spans
- **Measured by:** not yet; see [Before deciding](#before-deciding)

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

## Proposal

- When two consecutive pieces of a path lie on the same reference sequence more
  than one chunk apart, the tool writes a `skip` row into each chunk strictly
  between them, up to 32 chunks (2 Mb at the default chunk)
- A farther jump is a paralog jump and gets no `skip` rows, as today
- Row: `seq cs cs+1 skip path fragStart piece from to`, where `piece` numbers
  the piece before the jump and `from` and `to` give the starts of the two
  pieces' chunks
- A reader draws the haplotype across the window as a jump from `from` to `to`
- graph-walks 4 skips row kinds it doesn't know, so the files stay format 5,
  as `#long` lines did in format 4

## Alternatives rejected

- **One row under the jump's whole interval:** Tabix returns it for every
  window inside, but files it in a coarse bin, so every query there reads it,
  as with the node and link index's wide intervals
  ([ADR 0005](0005-node-link-format-2.md))
- **Follow `nx` tags further in the reader:** the window's chunks hold no row of
  the haplotype to follow from

## Before deciding

- Count the `skip` rows and their bytes on HPRC v2.1's Minigraph-Cactus chr22
  and on pggb chr22, where collapsed repeats make more jumps
- Choose the 32-chunk limit from the distribution of same-sequence jumps,
  against the paralog jumps ADR 0001 measured
- graph-walks: draw a `skip` row, and count it against the window's budgets
