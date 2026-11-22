---
name: drawing-gate-after-holes
description: What the drawing gate still owes after the 2026-11-21 ada session: the pin retaken for six windows on the laptop, sv-49's sites job and recorded layout, sv-19's zero drawn, and a checker time on Y-9.3M that only the library can cut.
metadata:
  repo: walks8-evidence (fab8f323/drawcheck-merged)
---

# The drawing gate after the 2026-11-21 follow-ups

Done on ada on 2026-11-21 (record: `~/work/followup-20261121/drawing-gate/`
on ada, `README.txt` first): links-stress has a 6,500 MB heap and passed at
bandage-core 129f55b, labels-probe's owed run passed, `vcffacts.py` counts
every allele with the named change (the laptop's version), sv-32 and sv-49
are re-picked, and link-ends passes on them. The laptop applied patches
1–3; the checker is a git repo (`drawcheck-merged`, de49404).

- **Retake the pin** (`release-20261118/pin-6ae5b1b.json`, laptop only) for
  sv-9, sv-14, sv-23, sv-48 and the re-picked sv-32 and sv-49, with
  `known_failures.py` over `pin-retake/6ae5b1b/` on ada. Every finding there
  was looked at: none is a library fault; sv-48's and sv-49's false
  crossings are a placeholder's outline loop laid across the reference,
  which the gate is right to flag
- **sv-49's sites job** (`rerun-sites.sh`) was not rerun on the new pick,
  and `fixtures/site-layouts/sv-49-*.json` was not retaken
- **sv-19 still shows 0 drawn** under the new `vcffacts.py`; re-pick it or
  say why
- **The checker's time on Y-9.3M** (637 s at 129f55b, about 1,000 s before)
  goes to whole redraws at 527 distinct scales. Bounding the checker's own
  redraws saved nothing (patch 4, not landed); it needs the library:
  per-scale caching of edge curves and folded sites, a measure of one
  link's stroke at a scale, or a paint order that holds under viewport
  culling
- **The faceted shot is statistical:** 10.0.0's blank panels are a race,
  so it loads each window up to 10 times, with puppeteer's Chrome
- `rerun.sh`'s provenance line prints a git error into the log in a tree
  with no `release-fixes` branch; harmless
