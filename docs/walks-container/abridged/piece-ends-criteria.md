# Criteria for a piece's own bp outside its blocks, written 2026-11-11 before any decider ran

A `blocks` row, as built, states an abridged piece from its first step on
R to its last. The graph-walks reader built on it matches a loaded piece
on everything the row states, and differs where the loaded piece has own
bp before its first step on R or after its last. The row as built, with
the acceptance test restated as "equal on what the row states", is the
baseline. Every candidate is judged on these, in this order:

- **Truth and the acceptance test.** A piece drawn from its `blocks` row
  states nothing its loaded piece contradicts, and leaves out nothing the
  loaded piece shows in the window. ADR 0012's acceptance test, rows
  built from blocks equal to loaded rows with each run of off-reference
  steps collapsed to its bp, passes, or the candidate says which
  differences remain, how many on the hosted graphs, and why they are
  acceptable.
- **One rule for a reader.** What a row could state, a reader doesn't
  infer from neighbouring rows, departure records or which tiles a
  window happened to read.
- **A row that reads alone.** Fixed columns with one meaning each, few
  mechanisms, and agreement with what the `abridged` row's `hapOffset`
  and `bp` already mean.
- **Bytes.** Added to the `blocks` units of the hosted files.
- **Cost of the change.** No file with `blocks` units is released or
  hosted. A change means rebuilding both genome files on ada (about two
  hours), and following it in the writer, its tests, the file checkers,
  the spec and the reader branch.
- **Burden.** A candidate must beat the baseline on the criteria above.
  When the evidence is mixed, the row stays as built.
