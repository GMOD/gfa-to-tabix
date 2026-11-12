# Decision criteria: reader-implementer lens

Written before reading the reader code, the spec text, the measurements or
either side's notes. Only the brief has been read.

## What a reader must be able to do
- R1 Exactness from the spec alone. For every cut (a region query), a reader
  written from the spec alone, with no knowledge of this writer's habits,
  must decide exactly: which pieces to load, which piece holds an attached
  departure record's own steps, and which bytes it will fetch (`bytesFor`).
  "Exact" means 0 wrong picks on every row of the fixture and both genome
  files, and a statement in the spec that an independent checker can verify
  per row.
- R2 No reads to decide what to read. Deciding which detail records a cut
  needs must not itself require a read beyond the tile(s) the cut already
  fetched. If it does, that read must be bounded and counted.
- R3 Worst-case read cost. On the worst CHM13 windows the bytes and range
  requests for an unloaded cut, an expanded cut and `bytesFor` must not
  exceed what the best alternative needs. A difference under about 5% of
  bytes or under one request per cut is noise.
- R4 Reader code. Fewer branches and fewer record kinds a reader must join
  to answer one question. A design that removes a join beats one that adds
  a derived rule the reader must reimplement.

## What a format change must clear (ADR 0011 as given in the brief)
- C1 The change must beat shipping unchanged on R1 or on R2/R3 by more than
  noise. If a reader-only rule over existing fields is exact (0 failures)
  and costs no extra read, the format stays.
- C2 The added field must be true, fully determined by the walk and the
  piece boundaries, and checkable against another record in the file
  (`blocks`), so a wrong value is detectable.
- C3 Bytes: the measured growth must be stated and small against what it
  saves in reads. If it saves no read and no code, it is not justified.
- C4 Mixed evidence keeps the format.

## How I will choose between alternatives
- A1 Prefer the alternative that answers the question at the place the
  reader already is (the tile row or the record it just fetched) over one
  that needs a second unit.
- A2 Prefer a real coordinate or length on the haplotype contig over an
  index, pointer or step count that only means something relative to
  another record.
- A3 Prefer one field that serves several needs (attach, `bytesFor`, F5,
  placeholder ids) over one per need.
- A4 Redundancy with `blocks` is acceptable only if (a) it removes a read
  or a guess, and (b) the spec states the equality so a checker enforces it.

## What would make me say SHIP UNCHANGED
- A reader-only rule from the `abridged` row plus the record already in
  hand that is exact on every row tested, with a proof sketch from spec
  invariants (not writer behaviour), and read cost within noise of the
  column's.

## What would make me say ADD
- No such rule exists (a counterexample row where two candidate pieces
  cannot be told apart from the fields available), or the only exact route
  needs the `blocks` unit read on cuts that would not otherwise need it and
  that read is more than noise on the worst windows.

## What would make me pick an alternative over `bp`
- It satisfies R1 and R2 with fewer bytes or fewer reader branches than
  `bp`, and is a real coordinate (A2).
