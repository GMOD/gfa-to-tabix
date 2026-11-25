---
name: gfatools-bubble-segfault
description: gfatools 0.5-r296 segfaults in gfatools bubble on tests/data/alleles.gfa and on most tiny random rGFAs, so build writes no bubble file for them and says so. Find whether a newer gfatools fixes it, and report it upstream if not.
metadata:
  repo: gfa-to-tabix
---

# gfatools crashes on small rGFAs

- `gfatools bubble tests/data/alleles.gfa` with gfatools 0.5-r296 exits
  on signal 11 (rerun on 2026-11-25, exit 139). The earlier text found the
  same on most tiny random rGFAs
- `build` notes why and writes no bubble file when gfatools is missing,
  fails or crashes (`src/cli.rs`,
  [subcommands.md](../../../docs/subcommands.md))

## Next

Find whether a newer gfatools fixes it, and report it upstream with
`tests/data/alleles.gfa` if not.
