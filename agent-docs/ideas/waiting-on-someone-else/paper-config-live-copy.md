---
name: paper-config-live-copy
description: jbrowse-components main (c78014a9e0) loads plugin 10.0.1 and the -f8 file in paper_hprc.json, but the live copy on jbrowse.org still loads plugin 9.0.0 on the plain GRCh38 name (format 8) until main's four unrelated CI failures clear and the website upload runs.
metadata:
  repo: jbrowse-components
---

# The paper config's live copy is still plugin 9.0.0

- `format8-main` landed on jbrowse-components main as c78014a9e0: the paper
  configs load plugin 10.0.1 and `hprc-v2.1-mc-grch38-f8.GRCh38`
- `https://jbrowse.org/code/jb2/main/test_data/graphgenomeview/paper_hprc.json`
  still loads `graphgenomeviewer/9.0.0` with `walksUri`
  `https://jbrowse.org/demos/hprc/hprc-v2.1-mc-grch38.GRCh38`, whose bytes are
  format 8 since the 2026-11-19 cutover. Plugin 9 reads format 7
- The website upload is skipped while main is red on four failures that came
  from elsewhere (a README block, an unindexable `agent-docs/ideas` doc, a
  snapshot and the tutorial). When it runs, fetch the URL above and check it
  names 10.0.1 and `-f8`, then delete this file
