---
name: drawing-gate-after-holes
description: What the 2026-11-20 fixes to the drawing gate left: two jobs to give a heap and prove passing, a pin to retake for four re-picked windows, two more windows to re-pick, an allele count in vcffacts.py, and the checker's own growing run time.
metadata:
  repo: walks8-evidence (fab8f323/drawcheck-merged)
---

# The drawing gate after its three holes were closed

The labels probe, the wrong-allele windows and the faceted track were closed
on 2026-11-20, each shown failing on the broken case. Record and originals:
`~/src/walks8-evidence/followup-20261120/gate-holes/`.

- **links-stress fails every run now.** Its pggb drawing and four planted
  pggb faults have drawn nothing since 8df4c07, running out of memory near
  2 GB under a 7G cap, and `run.sh` now fails a job with an undrawn window.
  Give it a heap in `caps.tsv`'s third column, as labels-probe has, and prove
  it with a passing run
- **labels-probe's passing run is owed:** 6,500 MB heap under an 8G cap, about
  2.3 hours, on a quiet ada
- **Retake the pin** (`release-20261118/pin-6ae5b1b.json`) for sv-9, sv-14,
  sv-23 and sv-48. Now that they draw their named allele, they show new
  findings: sv-14 5 false crossings, and sv-48 1 false crossing and 6
  wrong-order findings
- **Re-pick sv-32 and sv-49,** which draw an allele 118 and 225 bp off the
  named size
- **`vcffacts.py` counts the carriers of one allele.** Nine tandem-repeat
  windows draw the named change through other alleles of the same record
  and show 0 drawn. Count every allele of the record with the named change
- **The checker's time on Y-9.3M** grew from about 80 s to about 1,000 s
  under checker stages that redraw the whole every-site drawing per piece and
  climb up to 64 doubling scales per piece. Measure only each piece's own
  links and share redraws by scale
- **The faceted shot is statistical:** 10.0.0's blank panels are a race, so
  it loads each window up to 10 times. It needs puppeteer's Chrome, since
  Chrome 136 never shows the race; the other shots still use 136
