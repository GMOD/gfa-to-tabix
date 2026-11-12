# Criteria: `bp` on the `abridged` row (writer / whole-format lens)

Written before reading the writer, the measurements or the other reviewers' notes.
ADR 0011 frame: the change must beat shipping unchanged; mixed evidence keeps the format.

## A change is warranted only if all of these hold
- **C1 Real gap.** There is a question a reader must answer for a correct or
  bounded read (which piece holds an attached record's own steps, how many
  bytes a piece costs, whether a piece overlaps a window) that the `abridged`
  row plus the record cannot answer, and that today needs a second fetch
  (`blocks`) or a guess. If `blocks` is always fetched anyway, or the answer
  is derivable from rows already in the tile, there is no gap.
- **C2 True by construction.** The invariant the new field supports
  (own steps = record stretch ∩ piece stretch) follows from how the writer
  builds pieces and records on every graph shape, not from two HPRC files.
  One constructed counterexample (hairpin, revisit, own steps spanning two
  pieces or two tiles, crossing to another reference sequence, contig end,
  pggb P-line names) fails this unless the spec can state the exception
  exactly.
- **C3 Fully determined, real coordinate.** The field has one definition an
  independent reader can recompute from other rows (`blocks` runs, detail
  record) and check. No fake coordinates, no "narrower than it looks"
  semantics: its meaning must not depend on which reference the tile is on,
  on strand, or on a writer threshold.
- **C4 Writer has it for free.** The writer holds the value at the moment it
  emits the row, with no new pass, no new state proportional to the graph,
  and no shape where it must invent a value.
- **C5 Not a patch.** No simpler restructure (different abridging boundary,
  record naming its piece, info in `blocks`) removes the need with fewer
  bytes or fewer rules. If one does, prefer it; if the deeper issue remains
  after adding `bp`, the column is a patch and fails.
- **C6 Bytes justified.** Measured cost is small against abridged tiles and
  against what it saves (fetches avoided), on both genome files.
- **C7 Checkable.** A checker independent of the writer can verify the field
  and the invariant, and demonstrably fails on a mutated file or writer.

## What decides between alternatives
- Guarantee strength first (format invariant > reader rule > writer habit).
- Then fewest columns / record kinds and no redundancy that can disagree
  (two fields that must agree need a stated check).
- Then writer complexity, then bytes.
- A reader-only rule wins if it is exact on every shape; it loses if it is a
  heuristic that picks wrong on measured or constructed cases.

## What keeps the format (ship unchanged)
- C1 fails (no real gap), or C2 fails with no exact statement of exceptions,
  or the evidence is mixed between `bp` and an alternative with no clear
  winner.

## Disqualifiers for any option
- A field that is false or undefined on some shape (e.g. piece spanning two
  haplotype contigs, zero-step piece, piece with no own bp).
- A guarantee that only holds for this writer's abridging policy unless the
  spec makes that policy normative.
