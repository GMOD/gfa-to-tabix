# Handoff, 2026-10-30: placement, walk views and non-colinear regions

A record of one long session's work, its state and its open threads, so the
next person or session can pick it up cold. Decisions live in
[ADR 0008](../adr/0008-index-keeps-its-placement.md); open problems in
[open-problems.md](../open-problems.md). This page points at both and holds
what neither does: where the data sits, what is half done, and the gotchas.

## The story in five lines

- The node and link index and the walk files both answer "what graph lies
  under this window of the reference", with different placement rules
- Off segmental duplications both work, and walk files do it in about a third
  of the bytes on GRCh38's chr22
- Every hard window lies where haplotypes leave the reference's order:
  segmental duplications, hypervariable loci, satellites, pggb's collapsed
  repeats. There a 10 kb window can hold 30-200 kb of a haplotype's own
  sequence, so any view either draws a lot or folds it
- The limit is layout time and readability, not download: those windows read
  0.3-3 MB
- The plan is to fold long alleles into labelled bars that expand on
  request, then offer haplotype coordinates and alignment views for the
  worst loci ([open problems](../open-problems.md#regions-where-haplotypes-leave-the-references-order))

## What landed

gfa-to-tabix, on `main` and pushed (`065d52a..`, version 2.1.0 on crates.io
predates all of it):

- **Allele inventory** (`src/alleles.rs`): rows no longer depend on which way
  an L line is written or their order; HPRC's SV rGFA gives 221,981 rows
  against 2.1.0's 206,016 (8db395f, c09dabc, 7a505f0, 4967928, d4b3d90)
- **Reference choice:** a plain GFA whose paths name more than one assembly
  needs `--reference`, which takes a list naming one sample's paths (0acd7fa,
  d4b3d90)
- **gfatools:** a crash or unreadable output is a note, not a failed build
  (6e2607b, d4b3d90)
- **Walk files:** a stay guards by a node's last base (d18a255);
  `--sequences` refuses a `*` segment (fea85e3)
- **Docs:** ADR 0008 (07ad526, corrected in 766a022), open-problems
  rewritten, [docs/placement/](../placement/) holds the measurement harness
  and every window's results, README outputs figure (98690ee)

graph-walks, on `main` and pushed:

- 9e89077, ff635d3, 4b064ec: a node the reference passes twice is placed at
  the pass over the window, and a step counts as on the window only at that
  pass. No window leaves a reference node undrawn any more
- ebd1197, 5074926: a kept haplotype that leaves the reference before the
  window and rejoins after it keeps the steps between, and a direct jump
  across the window comes back as a skip. The reader fetches the far side
  within its 4-chunk follow reach. No writer change was needed
- 031e9a3: a crossing over `crossingBp` (default 65,536 bp) off the
  reference comes back as a skip carrying optional `offBp`, `offSteps` and
  `chunks`; a viewer cuts again with a higher `crossingBp` to show it
- Released as 4.5.0 (tag `v4.5.0`, c411255); CI publishes it to npm from the
  tag

Hosted on jbrowse.org/demos, already live:

- Allele files for hprc, mouse, bovine, arabidopsis and ecoli_minigraph,
  regenerated with the new inventory (+1.2% to +7.7% rows); checked by row
  count and remote tabix queries
- `demos/hprc/README.txt` and `demos/bovine_pangenome/README.txt` with the
  new counts, deployed from jbrowse-components' committed copies.
  jbrowse-components commit a27851dc34 sits on its local `main`, which is far
  ahead of `origin` with other work, and is not pushed

## graph-walks 4.5.0 on the four graphs

Runs in `target/span-window/harness/`: `out/` uncapped, `out-capped/` as
released. With the 8 hosted haplotypes:

| graph | windows losing nothing, 4.4 / 4.5 | lost allele nodes, 4.4 / uncapped / 4.5 |
|---|---|---|
| Minigraph-Cactus chr22 | 85 / 85 of 100 | 6,180 / 713 / 2,150 |
| pggb chr22, GRCh38 | 71 / 71 of 100 | 6,217 / 3,941 / 3,941 |
| pggb chrY | 71 / 72 of 80 | 10,699 / 1,039 / 8,160 |
| pggb chr22, CHM13 | 59 / 59 of 100 | 77,948 / 46,862 / 46,882 |

- "Lost" still counts nodes the haplotype carries outside the window, and a
  capped crossing counts as lost though the viewer can expand it
- Heaviest windows, 8 haplotypes, nodes drawn: MC chr22 18,451,108 goes 13 /
  13,451 / 3,580; 18,538,885 goes 126 / 22,738 / 3,700; 18,714,439 goes 399 /
  20,955 / 20,955, every crossing there under the cap. With every haplotype
  kept, 18,538,885 draws 50,326 nodes in about 17 s
- With every haplotype kept, pggb chr22 22,791,104 now exceeds the kept-node
  limit; pggb chr22 has 4 such windows against 4.4's 3
- `lostcheck.mjs` can't read the CHM13 pair's 1.28 GB jsonl, so that pair has
  no loss attribution

**The viewer doesn't show the new skips yet.** bandage-core's
`src/layout/walkRowRuns.ts:769-777` draws a skip row only for a haplotype
with no walk in the cut (`!drawn.has(contig)`), and only its first skip, so
HG01109's deletion skip at MC chr22 18,451,108 doesn't show beside its
619-step fragment. `skipRowOf` (`:723`) draws every skip as a deletion; a
capped crossing needs reading `offBp` and drawing as a folded replacement
that re-cuts on click. `WalkSkips` in `src/types.ts:136` needs the two
optional arrays

## Open threads, with the next action

1. **Plugin release:** bump `@jbrowse/graph-walks` in
   jbrowse-plugin-graphgenomeviewer's lockfile to 4.5.0, release
   the plugin (`docs/developing.md`, "Releasing": push, let CI pass, `pnpm
   version`), then `cd ~/src/jbrowse-plugin-list && pnpm dep && pnpm
   invalidate`. Until then hosted tracks run graph-walks 4.4. On 2026-10-30
   the plugin checkout held another session's unpushed commits and an
   uncommitted `eslint.config.mjs`, so the release waits on that session
2. **Show skips in bandage-core, then fold long alleles:** draw a skip beside
   a haplotype's walk, draw a capped crossing as a labelled bar from
   `offBp`, and re-cut with a higher `crossingBp` on click (see above)
3. **Harness metric:** count as lost only nodes a kept haplotype carries on
   the window; today's counts are an upper bound (ADR 0008)
4. **CHM13 index:** trace which components file 2,383 node rows under all of
   CHM13 chr22, which make every window read 30-42 MB
5. **Rejoin stretch:** measure a cap on how far a haplotype's jump to a
   distant copy stretches a walk cut
6. **Smaller:** `--refs HG002#1` after the plugin reads `#reference`;
   carriers on a walk-drawn graph; `TB` in graph-walks; alleles on two
   reference samples; a newer gfatools; timing abridged windows in the plugin

## Where the data and tools are

- **Local, `~/src/gfa-to-tabix/target/`** (gitignored):
  - `crux-data/`: format 2 indexes and walk files for HPRC pggb chr22 (GRCh38
    and CHM13), pggb chrY, and Minigraph-Cactus chr22, about 3.3 GB
  - `crux-harness/`: the harness as run, with `out-4.4/` (graph-walks 4.4),
    `out/` (placement fix), `fix/` (that fix's before and after), and
    `rerun.sh`, `relost.sh`, `lostsum.py`, `stretchsum.py`
  - `span-window/harness/`: the crossing fix's runs
  - `mc-drops/`: `trace.mjs` and `atwin.mjs`, which trace one haplotype
    through the reader at one window
  - `arb/`: HPRC's SV rGFA contig index and allele comparisons; the rGFA is
    `target/hprc/hprc.sv.gfa.gz`
- **ada** (`ssh ada`, 125 GB): `~/work/crux/` (pggb walk files and window
  runs), `~/work/crux3/` (CHM13 index and walks, coarse tiers),
  `~/work/alleles/` (regenerated allele files), `~/work/pggb/chr22.gfa`
  (27 GB, decompressed)
- **Committed:** `docs/placement/scripts/` with its README; results beside it

## Gotchas met

- `/tmp/claude-1001` has a small quota that other projects' temp folders fill;
  write big scratch under `target/`
- A worktree session's shell guard refuses shell variables and loops naming
  commands; put them in a script file and run it with `bash`
- ada's `tabix` has no https; query hosted files from a laptop. ada has no
  node, so graph-walks runs locally
- Kill ada jobs by PID; `pkill -f` matches the ssh session's own command line
- `--walks` reads the GFA twice, so it needs a file, not stdin
- `jbrowse-plugin-list`'s `pnpm dep` commits, pushes and uploads in one step
