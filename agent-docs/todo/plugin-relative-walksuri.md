---
name: plugin-relative-walksuri
description: In the JBrowse graph plugin a relative walksUri resolves against the page, not the config, so a config served from elsewhere 404s on <walksUri>.walks.gz.idx.
metadata:
  repo: jbrowse-plugin-graphgenomeviewer
---

# A relative `walksUri` resolves against the page

The walksLocations preprocessor (`tabixSlots.ts`, around line 41) reads
`snap.baseUri`, which the shorthand string `walksUri` never gets. Absolute
URLs work. Fix with a test that serves a
config from another directory, and grep jb2hubs and jbrowse-components configs
for a relative walk URI first.
