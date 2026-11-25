---
name: name-the-placement-policy
description: A walk file states stay and the abridge budgets but not the placement rule that wrote it, and claims7.md and the file checkers mix format invariants with this writer's policy in one table. Name the policy in a #walks tag (an addition to the format) and split the claims table and checkers into format and policy, when pggb placement work starts.
metadata:
  repo: gfa-to-tabix
---

# The writer's placement policy has no name in the file

- The format page lists what a reader relies on as the format, and calls
  pass choice, `stay`, the abridge budgets and the order of a tile's
  detail records this writer's policy
  ([What a reader relies on](../../../docs/walks-format.md#what-a-reader-relies-on),
  [Exact and chosen](../../../docs/walks-format.md#exact-and-chosen),
  [ADR 0013](../../../docs/adr/0013-abridged-hapbp.md)). No byte changed
  when it did
- A file doesn't say which policy wrote it: `stay`, `abridge` and
  `abridgebytes` are on the `#walks` line, the placement rule's name
  isn't
- Still mixed: `docs/departures/claims7.md` lists the format's invariants
  and this writer's choices in one table (its C202 row: claims7's B1 to B3
  stay checks of this writer's policy), and the file checkers fail a file
  for either, so a file from another placement fails checks of the policy.
  The checkers' side is `../../todo/checkers-hold-a-file-to-the-format-alone.md`
- The pyramid's bin sizes were settled on 2026-11-18: three reviews kept
  C43's bin sizes as format (`../../reference/concepts-beyond-gfa.md`)

## The proposal

When pggb placement work starts: name the policy in a `#walks` tag and
split the claims table and the checkers' claims into format and policy.
A tag is an addition a reader ignores
([Later additions](../../../docs/walks-format.md#later-additions)); on a
file already written it changes the header, every `#entry` offset, the
`.idx` and the checksum, as ADR 0016 says of a header tag
([The candidates](../../../docs/adr/0016-format-8-is-frozen.md#the-candidates)).
