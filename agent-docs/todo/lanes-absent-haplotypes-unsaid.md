---
name: lanes-absent-haplotypes-unsaid
description: At H-TSPY six of the track's haplotypes have no lane and nothing on screen says so; true before the lanes-truth branch too.
metadata:
  repo: jbrowse-components
---

# Lanes leave absent haplotypes unsaid

Found 2026-11-24 in the lanes truth check of `after-lanes/pairs-v5` (hostedaudit).

- At H-TSPY the track declares eight haplotypes, and six of them draw no lane. No line or key entry says they are absent.
- The lanes-truth branch shows a no-haplotype line only when none of the track's haplotypes has sequence placed. A partial absence goes unsaid, on main as well as on the branch.
- The graph track's absent-haplotypes note ("N have no walk here") is the reader model to match.
