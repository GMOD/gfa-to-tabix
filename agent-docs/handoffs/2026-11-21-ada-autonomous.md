---
name: 2026-11-21-ada-autonomous
description: The walks stack's work after the 2026-11-20 session, handed to a Claude session running on ada while the laptop is off: what is released, what is on branches, and the work left, in order, with the rules that hold.
---

# Handoff to a session on ada, 2026-11-21

You are continuing the 2026-11-20 session's work on the walks stack, running
on ada itself, with no one to ask. The owner is away. Work through the
queue below, in order, and leave everything pushed and written down.

## Rules that hold

- **Tests run here on ada,** never anywhere else. Keep jobs at `nice -n 10`,
  with modest vitest workers; other people's jobs share the machine.
- **Repositories:** clone from GitHub into `~/work/handoff-1121/<repo>`.
  - Do not use the old checkouts under `~/src` (some are bundle clones);
    the one exception is `~/src/jbrowse-plugin-list`, below.
  - Work on short-lived branches that land on main as a fast-forward.
  - Never `git commit -a`, never force-push.
- **Pushes and releases need no one's OK** when every check is green. Stop
  a line of work on red, or on any risk to pushed work, and write down why.
- **Hard questions go to Fable 5.2,** read-only, before you act on them:
  formats, naming rules, invariants, release verdicts, visual calls you're
  unsure of.
  - Run it as
    `CLAUDE_CONFIG_DIR=~/.claude claude -p --model claude-fable-5-2 --add-dir ~/work ...`
    with `--allowedTools "Read" "Grep" "Glob" "Bash(git:*)" "Bash(python3:*)"`.
  - Brief it as a peer: criteria first, the code and the data, not your
    conclusion.
  - Use Opus subagents for the rest.
- **Every check must fail when broken.** Show a new check failing on a
  planted fault before trusting it.
- **Look at every picture of a drawing change** before you land it.
  - ggbandage's gallery figures must not be redrawn on ada: ada's R graphics
    seam gradients.
  - R is at `~/micromamba/envs/r/bin`, for tests and `R CMD check` only.
- **The walk format is frozen.** Make no change to the bytes of a walk file
  or index file, or to a sentence of `docs/walks-format.md` or
  `docs/index-format.md`.
  - If you find a reason for one, get three fresh Fable reviews (is it
    needed? the alternatives, including no change? what else does it touch?).
  - Then write it up for the owner, and do not make it.
- **Never push to `jbrowse-components`** (the owner's repo).
- **Do not touch `jb2hubs`:** another session owns it, and has been asked to
  move it to graph-walks 9.
- **gbz-base is being removed;** rest nothing on it.
- **Writing:**
  - bullet lists, not numbered;
  - self-explanatory code with few comments;
  - TypeScript without `any` or typecasts, nested ifs rather than early
    returns;
  - commit messages one plain sentence saying what is now true (read each
    repo's `git log`), ending with `Co-Authored-By: Claude Opus 5.5
    <noreply@anthropic.com>`;
  - docs state takeaways; exact numbers in docs only where a script
    generates them.

## Where things are on ada

- **Evidence from 2026-11-20:** `~/work/followup-20261120/`, a copy of the
  laptop's folder. Each subfolder has the scripts, TSVs and pictures of one
  line of work:
  - `query-time/`: the profile of where a window's time goes
  - `early-refusal/`: its `STATE.txt` says where that branch stopped
  - `musl/`: `STATE.txt` again
  - `change-kind/`: the naming rule's evidence
  - `gate-holes/`, `core-branches/`, `gw9-tubemaps/`
  - `gw9-wave.jsonl`: where the reader wave stopped
- **The drawing gate:** `~/work/walks8-gates/`. Its harness on the laptop
  was `~/src/walks8-evidence/fab8f323/drawcheck-merged/`; ada holds the
  run copies.
  - The release tooling is described in `agent-docs/reference/release-tooling.md`
    of gfa-to-tabix.
- **The gfaidx comparison:** indexes and walk files are in
  `~/work/gfaidx-compare/`, scripts in gfa-to-tabix's
  `docs/comparison/scripts/`.
- **Tonight's reader timing runs:** `~/work/query-time-1120/`, early
  refusal `~/work/early-refusal-1121*` (find the folder), musl
  `~/work/musl-alloc/`.
- **A gfa-to-tabix release binary:**
  `~/work/gw-tablecover/g2t/target/release/gfa-to-tabix`. The window oracle
  is `scripts/check-windows.sh <binary> <graph-walks checkout>`, over an
  hour; run it detached.
- **Plugin store:** `~/src/jbrowse-plugin-list`. `git pull` it first; the
  laptop pushed to it.
  - Publish a new plugin version with `pnpm dep`, then `pnpm invalidate`
    (AWS credentials are set up here).
  - Check that
    `https://jbrowse.org/plugins/jbrowse-plugin-graphgenomeviewer/latest/package.json`
    names it.
- **Node:** `~/.local/node/bin`.

## Released on 2026-11-20

- graph-walks 8.0.2, then 9.0.0
  - 9.0.0 names a change a deletion only at 0 bp of the haplotype's own,
    else a replacement with both sizes
  - no shift
  - a sub-50 bp departure joins only another such
- bandage-core 14.2.0
- tubemap-core 2.1.0 (`readColor`: forward reads red, reverse blue)
- plugin 10.3.0, the plugin store's `latest/`
- on graph-walks 9: the plugin, sequenceTubeMap, ggtubemap, gfa-to-tabix's CI
- format 8 frozen; gfa-to-tabix 5.0.0's release notes written

## Progress on ada, 2026-11-21

Run folders for everything below: `~/work/handoff-1121/runs/`. Clones:
`~/work/handoff-1121/<repo>`.

### Landed

- **bandage-core 14.3.0** on npm. main fast-forwarded to cfaac76, Push CI
  44871362916 green with both consumer jobs; release commit 2b565f0, tag
  v14.3.0, Publish 44871775615 green (checks, npm, GitHub release).
- **Plugin 10.4.0** on npm and the store's `latest/`.
  - d5d2e3e2 pins core `^14.3.0` and recommits `img/tube_map_reads.png`
    (looked at: same layout, forward red, reverse blue, legend swapped);
    release commit 0a82b467, tag v10.4.0, Publish 44874037147 green.
  - On ada (`runs/plugin/`): build, typecheck, typecheck:tests, lint,
    format, unit 1160 passed / 6 skipped, host-names, host-compat, e2e 50
    passed / 6 skipped, typos, all 0. Push CI 44873360431 green.
  - Store: jbrowse-plugin-list b2d55fcb, `latest/package.json` names 10.4.0.
- **BandageJS** bfa3c0e0 on main: core `^14.3.0`, graph-walks `^9.0.0`.
  typecheck, lint, format, build, playwright 251 passed, README and tutorial
  shoots all 0; three PNGs rewritten at 0 px difference, left as committed.
  Build CI green. Deployed from main by `pnpm run deploy` (a fresh clone
  has no pre-push hook); the demo's `app.js` sha256 equals the local build.
- **gfa-to-tabix 5.0.1** (musl + jemalloc): 8621207 and ae8d58a on main,
  Release 44874117406 green through crates.io and the GitHub release.
  - fmt, clippy (glibc and musl target) clean; `cargo test` 168 passed;
    check-links, check-claims 193/193; the 26 outputs of the fixtures
    identical across 5.0.0 glibc, 5.0.0 musl and the new binary.
  - The new musl binary's sha256 equals the one measured as `jemalloc`.
- **early refusal's six mutants** rerun at 5ed3315 (`runs/er-mutants/`):
  each fails at least one new test.
- **5.0.1 rebuilds the hosted chr6-sequences walk file byte for byte**
  (`runs/rel501-repro/`): 6e2c7eda… and 463f5f6d…, in 149 s at 1.8 GB peak
  where 5.0.0 took 324 s at 1.3 GB.
- **ggbandage** 2038da2 on main, bundle and R-CMD-check CI green.
- **The scale study** (`docs/placement/scale-past-464.md`, 2df58fb, Push CI
  green). Its takeaways:
  - a 4-haplotype 100 kb view stays under 1 MB at 5,000 haplotypes;
  - the first view's table (14 MB) and 1 Mb windows cross it;
  - the default abridge budgets, not the format, drive growth: budgets
    scaled to the haplotype count give 539 MB against 1.89 GB;
  - "20 GB at 10,000" is not borne out with default budgets.
  
  It writes up per-group units for the owner with three Fable reads, and
  edits neither comparison doc that makes the claim. Builds and queries ran
  at load < 6, not 3, recorded per run. Files in `runs/scale/`.
- **The 8.0.2 window oracle** passed every window of all 309 files. Of its
  mutants, the twelve run so far are caught except the two whose text
  98cb1ff moved; holes-kept and the three placement mutants were still
  running.

- **graph-walks 9.1.0** on npm: early refusal (5ed3315, 00b60d0, 9bba9cf,
  README 0d30644) and the superlinear cut (seven commits to 84bd551, tests
  09baeac); release commit after 09baeac, tag v9.1.0, Publish 44947054527
  green (tests, npm, GitHub release).
  - Suite 1009 passed; lint, format, typecheck, build clean; push CI
    44946621808 green.
  - Early refusal: on 39 probe windows the error equals the finished cut's
    in every field but `fitsBp`; it fires on 27, in 20–281 ms where 9.0.0
    took 0.5–45 s (`runs/er-fix/`); 17 mutants each fail a test.
  - Superlinear: 0 differences over 20,621 fixture cases, 720 comparison
    and 19 slow-window cases; cuts 1.05–2.33× faster on the six slow windows
    at load < 3 (`runs/superlinear/times.medians.tsv`).
  - Window oracle on 84bd551 (`runs/oracle-910/`): all 309 files agree on
    every window; every mutant caught but holes-kept, which no longer hit
    live code (below).
- **gfa-to-tabix's window oracle on graph-walks 9:** fa6d09a rewrites
  step-touching and computed-across-pieces (both caught on 84bd551);
  677b07c moves holes-kept to `departingPairs`, where 98cb1ff (8.0.2)
  inlined the hole check, leaving `adjacentSteps` unused by the cut; caught
  on 9.1.0, and no reader behaviour went untested
  (`runs/holes-kept/trimmed-910.out`).
  - The 8.0.2 run (`~/work/gw-tablecover/check-windows.log`) found no real
    difference: 309 files agree; it exited 1 on the two stale mutants and
    holes-kept.
- **Node-cap study** for the owner, `docs/node-cap-study.md` (bc5bd11):
  FMMM's first drawing passes 5 s near 60,000 nodes on chr22 and 30,000 in
  the MHC; walk rows draw a million; options laid out, none decided. The
  faults it hit, BandageJS's hover crash at the MHC first, are
  `todo/reader-faults-from-node-cap.md`. Its timings ran at load < 4.

- **Every reader on graph-walks 9.1.0,** CI green on each:
  - bandage-core 129f55b, 1826 tests;
  - the plugin d4b15f35 (unit 1160, e2e 50, 27 figures unchanged), then
    **10.4.1** (92782442, tag v10.4.1, Publish green), on npm and the
    store's `latest/` (jbrowse-plugin-list a479d325);
  - BandageJS 08019d0e, playwright 251, figures 0 px; jbrowse.org's demo
    redeployed (`app.js` sha256 equals the build). Its Build workflow also
    deploys GitHub Pages on every push to main;
  - ggbandage a7cc147 and ggtubemap 48e77e2, bundles rebuilt, testthat and
    R CMD check pass, figures not redrawn on ada;
  - sequenceTubeMap c331f41, 760 tests, Pages deployed;
  - gfa-to-tabix 3a3ef84: CI's rebuild job checks out v9.1.0 and the
    claims' test list follows it.
- **The gfaidx comparison on 9.1.0** (7132d2c): interleaved at load < 3,
  three runs, with the browser preset's case. gfaidx answers most chr22
  windows faster, the median in about two thirds of the walk reader's time
  (not a tie); the reader is faster in nearly every chrY window. Sentences
  the numbers made false are rewritten. The preset's refusals on these
  one-tile windows come only after a full cut:
  `ideas/ready/early-refusal-context-tiles.md`.

- **The drawing gate's follow-ups** (`~/work/followup-20261121/drawing-gate/`,
  `README.txt`), at bandage-core 129f55b (14.3.0's source):
  - links-stress given a 6,500 MB heap under 8G in ada's `caps.tsv`, and
    passed: 18,239 s, exit 0, every window drawn;
  - labels-probe's owed run passed: 6,241 s, exit 0, every window drawn,
    the same violation counts class by class as the earlier heap runs;
  - patches 1–3 (all alleles with the named change, sv-32 and sv-49
    re-picked, run.sh's sampler following the tree) applied on the laptop,
    patch 1 changed; link-ends passes 83/83 on the new picks;
  - **patch 4 should not land:** with identical findings, the bounded
    redraws took 663 s against 692 s side by side, within noise, because a
    bounded geometry build still folds and curves the whole graph; it adds
    150 lines that must track the library's renderer. The saving has to
    come from the library (`todo/drawing-gate-after-holes.md`);
  - every flagged finding on the six re-picked or re-pinned windows was
    looked at: none is a library fault.

The first queue is done; what it leaves is filed in `agent-docs/todo/` and
`agent-docs/ideas/`.

### Decisions

- **From the laptop watcher (2026-11-21):** a laptop session released
  bandage-core 14.3.1 and plugin 10.4.2 and owns the plugin store from
  there; the ada clones are pulled to 427d1f0 and dc21ec08. The node-cap
  study's crashes are now the head of the second queue.
- **Calls the owner left with the laptop watcher (2026-11-21):** no
  per-group units; after both queues, abridge budgets that grow with the
  haplotype count and graph-walks no longer rebuilding its unit map per cut
  (both added to `2026-11-21-ada-next.md`); the gbz-base removal takes the
  plugin's `GbzBaseSyntenyAdapter` too, the store's old builds kept.
  ggbandage's gallery was redrawn on the laptop at a7cc147 and all 14
  figures and the gallery docs came out byte-identical: nothing to commit.
- **Fable's design reads for reader standardization started early,** while
  the drawing gate's long runs hold ada: they are read-only and put no load
  on it (`runs/standardize/design-verdict.md`).
- **9.1.0's early refusal promises the full cut's error on valid files,
  not on every malformed one.** Fable's second read
  (`runs/fable/r910-verdict.md`) found 9bba9cf right on every point of the
  first and the superlinear commits identical on valid files, but a
  malformed row the count does not inspect (a `ref` row's passes, a walk
  row's overstated `nsteps`, a `blocks` or detail unit at odds with its
  rows) can get the zoom-in notice where 9.0.0 threw the format error.
  Ruling every malformation out would mean decoding, which the refusal
  exists to skip; Fable named narrowing the criterion as a fix. README now
  says so (0d30644). The superlinear agent is adding unit tests for its
  commits, which touched no test file.
- **No 5.0.2 for the once-seen writer failure:** 30 rebuilds of the
  regenerated 5,000-haplotype graph (5.0.1, 5.0.0, glibc, instrumented)
  finished with one sha256, the code has no race or `unsafe`, and the
  error read two faults at once, another tile's rows plus a changed byte:
  memory corruption, allocator or hardware. Written up in
  `scale-past-464.md` (c489562); landing the instrumentation is
  `todo/writer-integrity-checks.md`.
- `tube_map_micb.png` came out changed in the plugin's shoot, without its
  hover (no tooltip, outline or crosshair). It was reshot three times alone
  and kept unchanged each time, so it was a hover flake under load, not
  committed.
- The musl branch's subagent changed a sentence of `docs/index-format.md`
  (chrY's "100 s with the release binary"). That file is frozen, so 5.0.1
  landed without it. The sentence now describes releases up to 5.0.0 and is
  left for the owner.
- `open-problems.md` puts chrY's remaining musl gap down to musl's
  `memcpy` alone, not "memcpy, memcmp and free": in the profile memcmp is
  as common under glibc (5 against 6 samples), and jemalloc replaces `free`.
- Early refusal and the superlinear cut go out together as graph-walks
  9.1.0, after one window-oracle run on the combined head, with one round of
  reader lockfile refreshes: the oracle takes hours and every refresh touches
  six repositories.
- ggbandage's `gallery.R --check` needs `codetools`, which
  `~/micromamba/envs/r` lacks; it passes under `~/work/walks8-gates/r-env`.

## The queue, in order

- **Finish the reader wave (bandage-core 14.3.0).**
  - Branch `gw9-wave` on bandage-core's origin, cfaac76: graph-walks
    `^9.0.0`, and read colours re-exported from tubemap-core 2.1.0. Read
    `gw9-wave.jsonl` for where it stopped.
  - Already done on ada, all green:
    - bandage-core's CI steps: 1825 passed;
    - the consumer gate on its packed tarball (ada `~/work/gw9-wave/rc/summary.tsv`):
      plugin 1160 unit and 50 e2e, BandageJS 251, ggbandage 130;
    - figure shoots: only the plugin's `img/tube_map_reads.png` changes,
      by read colour, which was looked at; BandageJS's figures are 0 px off.
  - Next:
    - fast-forward bandage-core main to cfaac76 and confirm Push CI green,
      consumer jobs included;
    - release 14.3.0 as 14.2.0 was (version bump, `node scripts/version.mjs`,
      commit "14.3.0", annotated tag, `git push --follow-tags`; Publish
      green; npm answers);
    - then the plugin: branch `core-14.3`, 37f3bc5e, holds a docs commit.
      Pin core `^14.3.0`, recommit `tube_map_reads.png`, run every check,
      release 10.4.0 the way 10.3.0 was cut (its git log), publish to the
      store.
  - Then the plugin 10.4.0 on it, and publish it to the store.
  - Then BandageJS on core 14.3.0 and graph-walks 9; its pre-push hook
    deploys jbrowse.org/demos/bandagejs, so check the demo serves the new
    build.
  - Then ggbandage: rebundle and test, but leave its gallery for the laptop
    and say so.
- **graph-walks early refusal.**
  - Branch `early-refusal`, commit 5ed3315 on 9.0.0, pushed. A window over
    the step budget is refused right after fetch, from the `nsteps` of rows
    inside the window, in 18–277 ms where it took 0.5–41 s, with the same
    verdict on all 39 probe windows.
  - Done: suite 956, typecheck, lint and format clean; release-check 28/28
    on both hosted `-f8` files.
  - Left:
    - rerun its six planted mutants at 5ed3315;
    - collect the window oracle, started 20:52 PST: `~/work/early-refusal-1120/oracle.log`
      and `oracle.exit`, from `run-oracle.sh`.
  - Then release a 9.x minor and refresh every reader's lockfile; rebuild
    ggbandage's and ggtubemap's bundles.
  - `fitsBp`, the zoom-in suggestion, is more than a tile off the widest
    window that draws in 5 of 32 refused windows (9.0.0's own: 13 of 32).
    Counting abridged pieces from their `blocks` rows would bring that to 4,
    at the cost of a fetch. Not needed for the release; file it.
  - Read `early-refusal/STATE.txt` first.
- **gfa-to-tabix's window oracle is stale against graph-walks 9.**
  - Two of `scripts/check-windows.sh`'s planted mutants, `step-touching` and
    `computed-across-pieces`, look for source text that graph-walks 98cb1ff
    moved, so the script exits 1 on 9.0.0 whatever the reader does.
    `~/work/early-refusal-1120/run-oracle.sh` runs a copy with both
    rewritten.
  - Fix the script in gfa-to-tabix, show each mutant is caught, push.
  - The oracle run against 8.0.2 in `~/work/gw-tablecover/check-windows.log`
    (started 17:03 on 11-20) will exit 1 for the same reason. Read its
    output for real differences, and say what it found.
- **graph-walks' superlinear cut.**
  - Departure-dense and abridged windows take 6–44 s: pggb chrY window
    20250624, and chr6:32.5M at 200 kb.
  - Suspects from the profile: `RefPath.reach`, `attachTiles` per departure,
    `linkSteps` and `placeholderId` on abridged pieces.
  - Output tables must be identical before and after. Window oracle; then
    release.
- **Regenerate the gfaidx comparison** in gfa-to-tabix
  (`docs/comparison/scripts/`, `tables.py`). Tables are generated, never
  hand-edited.
  - Add the browser preset's case, 1 kb context, beside the tile-aligned one.
  - Fix sentences the numbers make false, such as "under half the walk
    reader's time": it is about a tie now.
  - Time only at load under 3, interleaved, three runs each.
- **musl: take jemalloc** (decided 2026-11-21 from the measurements below).
  - Branch `musl-allocator`, 22bf1de, pushed. It has mimalloc and a WIP
    message; the jemalloc version is on ada in `~/work/musl-alloc/jemalloc`.
    Read `musl/STATE.txt`.
  - Set-2 means over three interleaved rounds each, with identical sha256
    of every output across all 21 runs:

    | Binary | chrY index | chr22 `--walks` |
    |---|---|---|
    | glibc | 76.7 s | 38.5 s |
    | musl as released | 101.6 s | 106.0 s |
    | musl + jemalloc | 94.7 s | 42.8 s |

    jemalloc closes about 94% of the `--walks` gap and about 28% of chrY's.
    The rest of chrY's gap is musl's own `memcpy`, `memcmp` and `free`,
    which no allocator replaces. It costs 0.16–0.25 GB more peak on
    `--walks` than the released build.
  - Do:
    - replace mimalloc with jemalloc on the branch, musl target only;
    - run clippy for the musl target and `cargo test` in full;
    - add the measurement files under `docs/placement/`, in the style of
      the ones there;
    - rewrite `docs/open-problems.md`, "The release binary is slower than a
      cargo build", to say what is now true, the chrY remainder and its
      cause included;
    - land, and release gfa-to-tabix 5.0.1 by its release workflow (it
      triggers on Cargo.toml changes; read `release.yml`);
    - confirm the released musl binary rebuilds the hosted chr6-sequences
      walk file byte for byte, as 5.0.0's did (`agents/rel5-repro/` under
      `~/work/walks8-gates`).
- **Scale past 464 haplotypes.** Nothing has been measured past HPRC's 464;
  "20 GB at 10,000" is an extrapolation.
  - Build a synthetic chr22 with about 2,000 and 5,000 haplotypes,
    recombined from the real ones so routes stay realistic.
  - Write walk files and measure: file size, bytes per window, and query
    time for 4 haplotypes and for all.
  - A tile holds every haplotype's rows, so a few-haplotype view downloads
    everyone's. If that reaches about a megabyte or more at 5,000, write up
    per-group units under the format-change rule above for the owner. Do
    not change the format.
- **The drawing gate's follow-ups:** gfa-to-tabix
  `agent-docs/todo/drawing-gate-after-holes.md`. Do the long proving runs
  only when ada is quiet.
- **Held, do not release:**
  - graph-walks `node-limit-preset`, a 30,000-node browser cap. The owner
    questioned the caps. With all haplotypes the step budget refuses first;
    with four, 1–10 Mb windows reach 26,000–440,000 nodes.
  - Measure layout and draw time against node count in the plugin and
    BandageJS, and write up the cap, or showing the zoomed-out tier instead
    of refusing, for the owner.
- **Recorded, not to do:**
  - the forms track's 20-character row labels (core JBrowse, the owner's
    call)
  - jb2hubs on graph-walks 9 (its session)
  - sequenceTubeMap's orange haplotype bands beside red reads (add it to
    `agent-docs/ideas/collections/drawing-faults.md`)

## When you finish, or stop

- Bring this file up to date: what was done, with commits, versions and
  check numbers; what is still open and why. Move finished items' leftovers
  into `agent-docs/todo/` or `agent-docs/ideas/` as `agent-docs/CLAUDE.md`
  says.
- Push gfa-to-tabix main.
- Delete this handoff only once every item above has landed or been filed.
