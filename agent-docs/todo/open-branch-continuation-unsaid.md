---
name: open-branch-continuation-unsaid
description: An open branch (a haplotype's sequence that leaves the window and rejoins past it) is drawn as a line that just stops; only its hover says "continues past the window". Open deletions draw nothing at all, so HLA's 189 and 26 haplotypes simply begin mid-window.
metadata:
  repo: bandage-core
---

# The drawing does not say an open branch continues

- At CFH (chr1:196,779,982-196,889,982), the 8 kb branch 11 haplotypes carry in place of 19.2 kb of GRCh38 stops past its "8 kb" label. Nothing on the drawing says it carries on; the hover does.
- Raised by the user-view Fable review of the hover fix on 26 November, and before that by the final truth review (`fold-from-runs.md`, "a mark for open deletions").
- A mark must read without the key (memory "graph track: visual, not text"). Candidates: a fade or arrow at the branch's free end, and the same mark at the reference node where an open deletion leaves.
