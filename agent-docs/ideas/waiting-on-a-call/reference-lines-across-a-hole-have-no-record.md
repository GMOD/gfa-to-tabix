---
name: reference-lines-across-a-hole-have-no-record
description: The format page's adjacency rule, read to the letter, gives the reference's own lines a departure record across each hole, and no file has one; the page needs a sentence, which is a wording call on a frozen page.
metadata:
  repo: gfa-to-tabix
---

# The reference's own lines across a hole

Found on 2026-11-25 by a reader written from part one of
`docs/walks-format.md` alone, which derived every departure record from
the lines it decoded and compared them with the file's.

- `docs/walks-format.md` "Adjacent steps" says two steps are adjacent
  when `ownBp` is 0, the strands are equal and the breakpoints are equal,
  holes removed. Two lines of the reference either side of a hole have
  equal breakpoints with the hole removed, and the hole's length between
  them on their contig, so `ownBp` is not 0 and by that sentence they
  depart
- The header table says a hole is not a departure of any haplotype, and
  no file states such a record: `walks-sequences.gfa` built with
  `--refs R --tile 10` has 10 `#hole` lines and no departure line whose
  `path` is its own `seq`
- The files are right and the sentence under-says. A departure record
  is "for each place a path departs ... that its walk rows can't show",
  which reads as paths with `walk` rows, and nothing says the reference's
  own lines have none
- Proposed wording, for the owner: one clause under `departure`, such as
  "the reference's own lines have no records: a `#hole` line gives each
  gap between them". No byte and no rule changes
- Not done on 2026-11-25, since it states something of every file that
  the page does not state now, and format 8's page is frozen but for
  wording
