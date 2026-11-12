# Referee criteria for the `bp` column on format 8's `abridged` row

Written after reading the brief only, before reading the spec, ADR 0012, the
measurements or either reviewer's notes.

## What makes a change needed (any one suffices)
- **Undetermined:** some fact a reader must have to draw or attach correctly
  is not a function of the file's rows under the spec's stated invariants.
  Cost alone does not count here.
- **Determined only by a writer habit:** the fact is derivable today only
  because the one writer happens to behave some way the spec does not
  require and no checker enforces.
- **Determined only at a cost that breaks the format's own purpose:** the
  fact is in the file but reaching it forces reading the very unit the
  abridged row exists to avoid, on a measured, non-trivial share of real
  queries, and no rule over already-loaded rows removes that.

## What a new column must satisfy
- **True:** a real coordinate or length on a named axis (the haplotype
  contig), with stated half-open ends and strand, not a placeholder.
- **Fully determined:** one value per row, a pure function of the walk and
  the cut, independent of tiling; the spec says what it is under hairpins,
  revisits, a piece spanning tiles, zero-length pieces, a piece that is all
  own steps or none.
- **Non-redundant within its own unit:** not computable from the other
  columns of the same row or of rows a reader of that row must already
  hold. Redundancy with a unit the reader would otherwise not fetch is
  acceptable only if an equality invariant ties the two and a checker
  enforces it.
- **Minimal:** the smallest field that determines the missing fact. If two
  candidates determine the same thing, prefer the one with the plainer
  meaning, then fewer bytes.
- **Not narrower than it looks:** the spec must forbid, by statement, the
  misreadings (bp on the reference, bp of drawn sequence, span vs sum).
- **Checkable:** an independent checker recomputes it from the GFA or from
  the `blocks`/detail units and fails on a writer that gets it wrong; this
  is demonstrated with a broken writer, not by a "0 failures" count.

## What the change must beat (ADR 0011)
- Shipping unchanged, with a reader-only rule, must be shown to fail one of
  the "needed" tests above on measured data, not merely to be slower.
- Each alternative is scored on: what it determines, bytes, number of new
  concepts, and the strongest referee objection.
- Mixed evidence keeps the format.

## Numbers I will require before saying ADD
- The claimed identity (own steps = record extent ∩ piece extent) reproduced
  by me on the fixture, 0 exceptions, and I must understand why it holds
  (a proof sketch, or a counterexample search on adversarial shapes).
- The reader-only rule's failure count reproduced, and whether each failure
  is a wrong answer or only an extra read.
- Bytes: compressed delta on abridged tiles, reproduced on the fixture at
  least.
- Evidence that the column closes the hole completely: after adding it,
  list every question about an abridged piece that still needs `blocks`.

## What would make me say SHIP UNCHANGED
- `blocks` determines everything and the excess reads are removable by a
  reader rule that is provably right from spec invariants.
- Or the column is an approximation (span that does not localise own steps
  when the walk revisits) so that it is "true" but does not determine the
  attach, i.e. it buys cost only and the cost is small.

## What would make me prefer an alternative
- It determines the same fact with a strictly plainer invariant or fewer
  bytes, or puts the fact on the row that asks the question (the departure
  record) instead of on every abridged row.
