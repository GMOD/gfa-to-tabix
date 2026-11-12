# Ruling on a piece's own bp outside its blocks, 2026-11-11

A blinded Fable decider, given the question, the
[criteria](piece-ends-criteria.md), the measurements
([genome/piece-ends-grch38.json](genome/piece-ends-grch38.json),
[genome/piece-ends-chm13.json](genome/piece-ends-chm13.json)) and the
reader branch's equality harness on chr22. Its report, as returned:

**Ruling: change the row. A `blocks` row gains two fixed columns,
`ownBefore` and `ownAfter`, and ADR 0012's acceptance test stands as
written, against the full loaded cut.** This is a format change to the
unreleased `blocks` unit only; `abridged` rows and tiles keep their bytes.

**Grammar:** `seq start end blocks path fragStart piece ownBefore ownAfter list`

- `ownBefore` / `ownAfter`: the piece's bp off R before its first block
  and after its last, 0 for none. `list` is unchanged
- **Example:** R is `>1>2>3>4>5>6`, six nodes of 6 bp; a piece walks
  `>12>1>2<2<1>11>5>6>3>13>14`, nodes 11 to 14 off R with 10, 7, 20 and
  30 bp. `R#0#c 0 36 blocks H#1#c 0 0 7 50 0+12,0-12,24+12:10,-24+6`
- **Its `abridged` row:** `hapOffset` 7, `bp` 52, `nsteps` 11; the piece
  covers its contig from 0 to 109

## Candidates, by criterion

- **The row as built:** fails truth and one rule; best on bytes and cost
- **Both columns (ruled):** expected to pass truth, not yet run; passes
  one rule; `hapOffset`, `bp` and the list's sum to `bp` are untouched;
  about +0.6% of `blocks` bytes; one rebuild
- **`ownAfter` only:** the same on truth; the reader still derives the
  lead from `hapOffset − fragStart` on piece 0
- **In the list** (`0+12:7,0-12,24+12:10,-24+6,:50`): the same on truth;
  breaks the sum to `bp` and adds a token that is no block
- **Contig stretch columns:** repeat `hapOffset` and `bp`
- **Widening the `abridged` row's `hapOffset` and `bp`:** changes format
  7's tile bytes; out

## Deciding facts

- **The row as built is window-dependent.** The reader takes a piece's
  tail from the next piece only when the window read its tile, else 0
  (graph-walks branch `src/walkReader.ts:681-688`), and the harness's
  "stated" comparison trims the loaded piece by the same condition
- **It misstates, not only omits.** Of chr22's 23,275 differing gaps,
  11,589 are row ends cut short where no record reaches, such as 1,476 bp
  against 48,802; 3,112 call bp `unread` that the loaded cut calls
  `read`; 8,570 say `own` where the loaded cut has `steps` or `read`
- **A line's last piece has no neighbour to infer from:** 63 of chr22's
  2,572 abridged pieces
- **Nothing is counted twice.** Pieces partition a W line
  (`src/walks.rs`, `cut_pieces`), and only steps before a line's first
  placed step lead a piece. On chr22 all 113 leads are piece 0 and equal
  `hapOffset − fragStart`
- **The `abridged` row stays consistent:** the new columns give the bp of
  the steps `nsteps` counts and the row's stretch leaves out
- **Bytes, estimated** by recompressing chr22's 18 `blocks` units in
  64 KB members: +4,058 bytes on 670,778

## What would reverse it

The rebuilt reader still differing from the full loaded cut on chr22, or
the rebuilt units breaking a gate limit. Then the row stays as built.
