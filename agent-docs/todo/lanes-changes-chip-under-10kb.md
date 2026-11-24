---
name: lanes-changes-chip-under-10kb
description: The lanes' changes chip lists only gaps of 10 kb or more, so smaller drawn deletions have no chip; at F2-chr3, 6.2 kb and 4.2 kb deletions are drawn and unlisted.
metadata:
  repo: jbrowse-components
---

# Lanes chips skip changes under 10 kb

Found 2026-11-24 in the lanes truth check of `after-lanes/pairs-v5` (hostedaudit).

- At F2-chr3 the lanes draw 6.2 kb and 4.2 kb deletions, and the changes chip names neither. The chip lists gaps of 10 kb or more only.
- Nothing shown is false. The chip omits changes the lanes draw, so a reader can take the chip for the whole list.
- Decide whether the chip should name every drawn change, or say that it lists those of 10 kb or more.
