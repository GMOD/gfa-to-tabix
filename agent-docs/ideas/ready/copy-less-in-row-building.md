---
name: copy-less-in-row-building
description: Since 5.0.1 the static musl release binary allocates with jemalloc, which closed nearly all of its gap to a glibc build on --walks but only about a quarter on pggb chrY's index (94.7 s against glibc's 76.7 s). The rest is musl's memcpy under row building; copy less there, or ship a glibc Linux binary beside the static one, if the gap matters.
metadata:
  repo: gfa-to-tabix
---

# The release binary's remaining gap on pggb chrY

- The Linux binary the README's quick start downloads is built for
  `x86_64-unknown-linux-musl`, static. Up to 5.0.0 it used musl's
  allocator: pggb chrY indexed in 99-105 s where the same code built with
  cargo against glibc took 65-68 s
  ([pggb-chrY-build.txt](../../../docs/placement/pggb-chrY-build.txt)),
  and the paper's 1.7 minutes is that binary's. On `--walks`, MC chr22
  took 105-107 s against 46-49 s
  ([mc22-walks-build.txt](../../../docs/placement/mc22-walks-build.txt))
- 5.0.1 (8621207, ae8d58a) allocates with jemalloc in the musl build only
  (`src/main.rs`); it writes the same bytes. Measured 2026-11-20:
  - on `--walks`, MC chr22: 42.8 s against 106.0 s with musl's allocator
    and 38.5 s with glibc's, for 0.16-0.25 GB more peak memory
    ([musl-alloc-mc22-walks.txt](../../../docs/placement/musl-alloc-mc22-walks.txt))
  - on pggb chrY's index: 94.7 s against 101.6 s and glibc's 76.7 s,
    0.2 GB lower peak
    ([musl-alloc-pggb-chrY.txt](../../../docs/placement/musl-alloc-pggb-chrY.txt))
  - mimalloc was slower on both inputs and peaked higher
- The rest of chrY's gap is user time in musl's own `memcpy`, called from
  row building (`index_rows`, `Row::write_line`, `bed::write`), which no
  allocator replaces. In the profile memcmp is as common under glibc, and
  jemalloc replaces `free`, so memcpy is the remainder

## Options

- Copy less in row building, which speeds every build
- Ship a glibc Linux binary beside the static one
