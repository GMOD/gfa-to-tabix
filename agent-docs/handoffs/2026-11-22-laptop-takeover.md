---
name: 2026-11-22-laptop-takeover
description: A laptop session took over two stalled sessions on 2026-11-22 and worked through subagents all day; what it released, what sits on branches unlanded, what waits on the owner, what it owes two other sessions, and which worktrees and agents it left behind.
---

# Laptop takeover, 2026-11-22

Pointers to where each thread stands. Delete this when the owed items below
are paid and the unlanded branches are landed, parked as ideas or deleted.
The evidence for everything is in
`~/src/walks8-evidence/sessions-20261122/` (`takeover/` is this session's:
plans, reviews, pictures; `paper/` and `lanes/` the two stalled sessions').

## Read first

- The owner's page with before and after pictures and ticks:
  `https://claude.ai/artifact/LkmWkosnehMQwKyQ9EHjtN`, private to the
  account of the `~/.claude3` config. Its source is
  `takeover/page/index.html`; ticks are read with the artifact's data tool,
  collection `approvals`.
- A review of this session's conduct, `takeover/reviews/vibe-check-2.txt`.
  Its point: land and release nothing a user would see change, and flip no
  default, before the owner has seen it; and do not hand back a call the
  owner has already made.

## Released

- bandage-core 14.3.4 and 14.3.5: dense windows no longer freeze the tab.
  The ada session has since released 14.4.1.
- graph-stress-layout 1.1.0: a deletion nested in a deletion draws as two
  detours.
- Plugin 10.5.0: the `key` and `extent` settings, and the above. The ada
  session then released 10.5.1, which was never published to the store.
- Plugin 10.6.0 (1aa0666d, tag v10.6.0; the store serves it,
  jbrowse-plugin-list 75e97aba): walk-fed lanes read against the reference
  from each step's stored place, with a `laneRibbons` setting. It uses that
  reading only where the lanes display says, in its requests, that it reads
  lanes against the anchor; on hosted beta.20, beta.22 and the hosted main
  build of that day it is pixel-identical to 10.5.1 at six loci.
- jbrowse-components main, pushed by the owner's checkout that evening: the
  lanes' fit and header fixes, lanes read against the anchor on a source's
  asking, and array records drawn as repeat bands
  (`todo/lanes-headers-and-fit-at-inversions.md`,
  `todo/lanes-ribbons-against-reference.md`).
- jbrowse-components local main, one commit ahead of origin and not pushed:
  51e36f0549, the lanes display states in its requests that it reads lanes
  against the anchor. No hosted JBrowse draws walk-fed lanes against the
  reference until a build with it is deployed.

## Waiting on the owner

- **Two ticks on the page:** the repeat band's look (grey hatching is the
  recommendation; the looks are jbrowse-components branch
  `repeat-band-looks`, built on commit ids main no longer has), and the pggb
  index reader.
- **A study the owner means to commission:** how readers should draw a
  graph whose reference revisits nodes. The prompt is
  `takeover/prompt-revisited-reference-study.md`. Until it reports, land
  none of the pggb reader work.
- **Another session's proposal on the same cause,** written the same day:
  `2026-11-22-pggb-place-by-chain.md`, that the walk writer place each
  haplotype by a co-linear chain. Nothing in it is built. The study should
  read it beside the reader prototype here.

## Owed to other sessions

- **paper-a9** (the paper's figures): told that 10.6.0 is out and that its
  Figure 5 build must hold jbrowse-components 51e36f0549. Still owed: the
  pggb chrY numbers and two wordings for `paper.tex` near line 560 and the
  letter's line 79 (`todo/paper-graph-figures-and-timings.md`).
- **jb2hubs-5d** (pangenome pages): nothing owed. It holds a cow walk-file
  build until it rebuilds the graph with current Minigraph-Cactus, since
  the 2023 graph's reference revisits 181,357 nodes on chr29; and its cut
  validator belongs in graph-walks
  (`todo/rgfacut-doc-whole-bubbles-and-a-source-check.md`).

## On branches, not landed

- **pggb windows from a node/link index**
  (`todo/dense-pggb-chain-joints-drawn-as-skips.md`): graph-walks
  `window-joined-cut` in `~/src/graph-walks-windowjoined`, bandage-core
  `skips-need-a-vouch` in `~/src/bandage-core-skipsvouch`. Correct on 60 of
  61 windows and not useful at arrays or later-pass windows; its faults are
  listed in the todo.
- **Run merging across like-end links:** bandage-core `fmmmtime` in
  `~/src/bandage-core-fmmmtime`. Held: its gain was on windows the reader
  fix shrinks. Measure again after that fix.
- **Rejected, kept for its pictures:** bandage-core `loops-rule` in
  `~/src/bandage-core-loopsrule`.

## Running when this was written

- Subagents of this session; they stop if it does.
  - The paper's pggb re-measurement: edits `~/src/jb2bench` on a worktree
    branch, runs on ada beside `~/work/scratch/graph-repro-2026-11-22`, and
    is told to commit and push jb2bench. It waits for ada to quieten.
  - A spread of draw times over 240 windows on three plugin builds: rows in
    ada `~/work/scratch/cut-speed-prof/out/spread-2026-11-22/rows.jsonl`.
    The Minigraph-Cactus part is whole (the 10.5.0 code equals 10.4.4,
    about 0.55–0.6 s to drawn); its pggb part measures the layout the todo
    above calls an artefact.

## The ada session

- `2026-11-21-ada-next.md` holds what it was told today: pull before
  touching bandage-core or the plugin, re-pin BandageJS and ggbandage, the
  aligner is off its queue, leave `WalkTabixSyntenyAdapter` to the laptop.
- It stalled twice on 2026-11-22, on a permission prompt and on its usage
  limit, and is releasing again.

## Worktrees left behind

- Landed, safe to remove with their branches: the plugin's
  `-keyoverlay`, `-rel105`, `-rel106` and `-placement`, and its `-cutspeed`.
- Scratch with uncommitted changes, from the stalled paper session and this
  one's render harnesses; look before removing:
  `~/src/jbrowse-plugin-graphgenomeviewer-nestedfix`, `-nestedrender`,
  `~/src/bandage-core-nestedharness`, `~/src/bandage-core-cutspeed`,
  `~/src/jbrowse-components-nestedfix`, `~/src/jbrowse-components-keyoverlay`.
- On ada, this session's agents wrote only under
  `~/work/walks8-gates/agents/`, `~/work/scratch/cut-speed-prof/` and
  `~/work/synteny-extract-1122/` (about 0.8 GB there before today;
  `hprc_multiway_gfa.pif.gz` in it is a copy of the hosted file and can go).
