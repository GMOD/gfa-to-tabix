# Criteria for the final shape of a `blocks` row, written 2026-11-11 before any decider ran

The row has changed once since it was first built, and no reader beyond
graph-walks' branch has decoded it. This is the last look at its shape
before bandage-core and the plugin are built on it; after the paper it
can't change. The row as it stands, `seq start end blocks path fragStart
piece ownBefore ownAfter list` with `<d><+|-><len>[:<own>]`, is the
baseline. Every candidate is judged on these, in this order:

- **It still determines the piece.** The proven claim holds for the
  candidate: the row, with its tile's `ref` rows and its `abridged` row,
  gives the piece's collapsed walk and where it starts and ends on its
  contig, and holds nothing else. A candidate for which that statement
  is shorter, or needs fewer cases, is better.
- **One way to say each thing, read without a manual.** Each fact is
  stated once, by one mechanism. A token says what stands where it
  stands, and can't be read as arithmetic or as something else. Judge it
  by the habits of CIGAR, PAF and GFA W lines.
- **Names that claim no more than is true.** A run "off R" is off the
  tile's R; it can hold reference nodes of another tile where the
  reference passes a node more than once.
- **Bytes,** measured in 64 KB BGZF members on real units, not
  estimated.
- **Cost of the change.** Nothing with `blocks` units is released or
  hosted. A change is one more pass over the writer, its tests, the file
  checkers, the spec and the reader's parser, and a rebuild.
- **Burden.** A candidate must beat the row as it stands. When the
  evidence is mixed, the row stays.
