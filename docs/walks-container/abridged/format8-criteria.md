# Criteria for format 7 with a `blocks` unit against a format 8, written 2026-11-11 before any decider ran

The owner, the same day: "we literally do not care about old readers, if
format 8 is needed, we should do it", with a week before the paper
freezes the format. The declaration ruling of that morning kept
`format:i:7` mostly so that released readers would go on reading the
hosted file, which was the wrong thing to weigh. Readers and files that
exist today count for nothing here: every reader is rebuilt and every
hosted file rewritten either way.

The question is confined to the abridged tier: the `abridged` row, the
`blocks` unit and its row, the `detail` unit, and how a file says it
holds them. Nothing else in format 7 is in question. Format 7 with the
`blocks` unit, as the `blocks-unit` branch has it, is the baseline.
Every candidate is judged on these, in this order:

- **The format one would design today.** Each fact about a piece is
  stated once, in the row where a reader needs it. No field is kept
  only because an earlier format had it, and none says something
  narrower or other than what it appears to say.
- **One check tells a reader what it holds.** A reader learns at open
  whether it can read the file, and no two different row shapes share a
  format number.
- **What each read costs.** A cut of a few named haplotypes, which reads
  a tile and loads their detail units, and a cut of every haplotype,
  which reads the tile and its `blocks` unit: the bytes each reads,
  measured on real units.
- **What stays provable and checkable.** The proof of what a `blocks`
  row determines still holds, restated; and how much of a rebuilt file
  can still be compared with today's hosted files byte for byte.
- **Cost of the change.** The writer, its tests, the file checkers, the
  spec and the reader branch, with a week in hand.
- **Burden.** A candidate must beat the baseline on the criteria above.
  When the evidence is mixed, the baseline stays.
