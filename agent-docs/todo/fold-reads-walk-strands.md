---
name: fold-reads-walk-strands
description: gfa-to-tabix's fold (the coarse tier) reads SO/SR tags and not the strand the walks give, so on a tagged GFA whose reference walk steps nodes backwards it folds nothing where bandage-core's foldVariants now folds.
metadata:
  repo: gfa-to-tabix
---

# `fold` ignores the reference walk's strands

`src/fold.rs` ports bandage-core's `foldVariants`, which
takes the reference's strand from its walk (held by a test there). The port
was not updated, so the coarse tier and a fine cut fold differently on such a
GFA. Port the change with a fixture that fails today: a tagged GFA whose
reference walk is reversed over a bubble.
