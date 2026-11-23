---
name: 2026-11-22-synthesis
description: Entry point for a new session picking up after 22 November. Four sessions left four handoffs that overlap and partly contradict each other; this orders them, says which statements a later one overturned, lists every call that waits on the owner and every debt to another session in one place, and gives the work in the order it can be done. The Fable review the owner asked for has answered that the lanes' repeat band does not solve repeat loci; prototypes of a count and a strand mark are being built for before and after pictures, and a format question waits on measurements and three reviews.
---

# Start here: state after 22 November

Written late on 2026-11-22 by a session that read the notes and checked
repo and ada state; it built and measured nothing. The session that took
it over that night added what it did. It points at the handoffs below and
does not replace them. Delete it when they are deleted.

Paths starting `takeover/`, `revisited-study/`, `repeat-review/`,
`rowcount/`, `lanespacer/` or `gapshapes/` are under
`~/src/walks8-evidence/sessions-20261122/`.

## The handoffs, and what each is for

- `2026-11-22-laptop-takeover.md`: what was released that day, the lanes
  and index-reader work, the paper's pggb chrY measurement and its command,
  worktrees left behind.
- `2026-11-22-pggb-place-by-chain.md`: a writer proposal, placing each
  haplotype by a co-linear chain. Unbuilt, and no go from the owner.
- `2026-11-22-revisited-reference-study.md` (**uncommitted**): how readers
  should draw a graph whose reference revisits nodes. What it settled with
  failing checks, six ticks, two prototypes, a blind picture review, the
  cattle rebuild trial.
- `~/paper/agent-docs/handoff-2026-11-22-graph-figures.md` (paper repo,
  **untracked**): Figures 2c and 5 on plugin 10.6.0, Table S5, the pggb
  paragraph, and the order to land them.
- `2026-11-21-ada-autonomous.md`, `2026-11-21-ada-next.md`,
  `2026-11-21-watcher.md`: the unattended "walks" session on ada. Its
  screen was attached and alive at 23:20 EST.

## One problem under most of it

- A pggb graph, and the 2023 cattle graph, have a reference that passes
  nodes more than once. Every file row is keyed by a reference position, so
  "which copy" is a pick: the index takes the first pass, the walk writer
  the nearest.
- Three layers each have an answer, from three sessions that did not weigh
  each other's:
  - **the writer:** place by chain. Unbuilt.
  - **the graph track:** the walk file as source, a count or skip drawn as
    fact only where the cut holds every pass of the reference over the
    node, colour by node. Prototyped on branches.
  - **the lanes:** array records merged into one repeat band. Released, in
    jbrowse-components main and plugin 10.6.0
    (`todo/lanes-ribbons-against-reference.md`).
- **None is shown to make a repeat locus readable.** The study's blind
  reviewer found no row, before or after, that shows where the other copy
  is, a haplotype's copy count, or a palindrome spacer's direction
  (`revisited-study/study/reader.txt`). The study's reader rules stop false
  marks; they do not add the missing fact.
- The study's settled findings each have a check shown failing on a
  planted fault. Do not re-derive them; its handoff lists them.

## The owner's position, 22 November night

- In their words: "im having trouble making the best decisions. the gold
  repeats and merging repeats doesnt really appeal to me, unless you think
  this is really solving it. get fable 5.2 subagent review".
- "Gold repeats" is the lanes' repeat band, drawn in the scale's third
  colour; "merging" is joining overlapping array records into one band.
  The six looks are in `takeover/repeat-looks/sheet-*.png` (TSPY, DAZ, the
  palindrome): stacked gold, merged gold, grey hatching, outline, strand
  tint, criss-cross.
- No tick below has been made. Do not put the repeat band to the owner
  again as a choice of ink: their question is whether the band, and the
  reader work around it, solves the problem.

## The review's answer, 23 November

Session gfa-to-tabix-b9 took this file over that night and ran the review.
Its text is `repeat-review/review.txt` in the evidence folder.

- **No: the repeat band does not solve repeat loci,** and no ink would.
  The reader rules and the array records stop false statements, and that
  part is sound. What a reader needs is a count of walks per haplotype
  beside the reference's, and the strand of what is walked once. Neither
  depends on where the writer filed a step, and no reader states either.
- **Checked before relaying** (the files are named at the foot of the
  review):
  - at TSPY the lane header's number is one record's: HG00280 reads "about
    7 times and hg38 about 9 times" and walks the unit 33 times;
  - at the palindrome 10.6.0 heads every lane "390 kb repeat over 390 kb",
    where 10.5.1's records told apart the four haplotypes whose 40 kb
    spacer runs the other way;
  - the walk rows' lengths at TSPY already equal 85 kb plus 20.4 kb a
    unit for 45, 28, 33, 22 and 25 units.
- **Not rechecked:** the unit counts, which every reviewer took from one
  scan, `reader/gfascan.jsonl` on ada.
- **Two prototypes are built and pictured,** on local branches on ada,
  unlanded. The owner's page of before and after pictures, with two ticks
  (collection `approvals`: `land-rows`, `land-lanes`), is
  `https://claude.ai/artifact/HfHAVRkJzszSu6EWsN71Gb`, private to the
  `~/.claude3` account; its source is `repeat-review/page/`.
  - **Walk rows:** bandage-core 2b472fc and f1427f7, plugin 09214af3,
    branch `rows-count` in `~/work/walks8-gates/agents/rowcount/`, as
    switch levels 4 to 6 on `revisited-colour`. At TSPY every row ends in
    its length and count ("1003 kb · 45×"), equal to the GFA's on all
    nine rows, and at the palindrome the spacer runs the right way in all
    eight. Sheets and checks in `rowcount/`.
  - **Lanes:** plugin d19b5ad4, branch `lanes-spacer` on v10.6.0, in
    `agents/lanespacer/`. A run of steps on once-passed nodes that places
    10 kb or more keeps its exact record inside an array stretch, so the
    palindrome's spacer is a ribbon, same strand as GRCh38 on four lanes
    and the other on four; each array record carries its lane's count.
    The 55 Minigraph-Cactus windows give the same records. Sheets and
    checks in `lanespacer/`.
  - **One count,** reached by the two agents apart: the median, weighted
    by node length, of how often the row or lane steps each node the
    reference steps more than once.
  - **Left for a real implementation:** the rows' switch is read from the
    served folder's name; the plugin's typecheck could not resolve
    bandage-core in that build; the rows' direction needs two extra cuts a
    window wide, whose cost is unmeasured; the lanes' released "justified"
    check needs its amended wording.
  - **For jbrowse-components, not asked yet:** the lane header should
    show the count in place of "580 kb repeat over 210 kb", and array
    records should not vote on a lane's direction (six of eight palindrome
    lanes draw reversed).
  - **What neither changes:** at `chrY:24,659,511-24,669,511` three lanes
    still read "no step on the reference across 19 Mb" and the rows' key
    says "no step on the reference" for haplotypes whose steps were filed
    at the 25.00 Mb copy.
- **The format question is parked, with no change made.** Five routes to
  "where the reference's other passes lie" and "how often a haplotype walks
  them" were measured against criteria fixed beforehand; none met all six,
  so by ADR 0011 the format stays. The numbers and what it would take are
  in `agent-docs/ideas/waiting-on-a-call/reference-other-passes.md`. No
  reviews were run and the chain spike was not started; both wait on
  someone asking for pggb walk tracks to be hosted.
- **The owner asked on 23 November whether the whole concept is broken,**
  and for goals to be cut back if that is what it takes to stop showing
  users anything false. The working boundary since then: a position on the
  reference is drawn only where it is a fact, which is every file stating
  `revisited:i:0`; elsewhere one repeat mark with a count, nothing from
  where the writer filed a step, and no new marks or format work. The
  owner also asked that the rainbow keep one meaning, position on the
  reference.
  - The rows prototype has a plain level for this (bandage-core 8031e2a,
    plugin f80d79ae, switch `cv-s0r7t0h0`): the reference keeps its
    rainbow, a run on nodes the reference steps more than once is one flat
    tone, the count stays, and it fetches what the released reader
    fetches. Sheets in `rowcount/plain/`. Two faults are left in it: the
    palindrome's spacer runs the wrong way on five rows, as in 10.6.0, and
    the key says "no step on the reference" for haplotypes whose steps are
    filed at another copy.
  - Colouring by node, the extra cuts for row direction, the ticks and the
    hairline are dropped.
  - Two things were started to put evidence under the boundary, both
    running when this was written: an audit of what the released readers
    draw on the hosted HPRC graph (ada `agents/hostedaudit/`, results to
    `hostedaudit/`), to be followed by a blind reading of its sheets; and a
    review of what the field draws at tandem arrays, palindromes and
    segmental duplications, from papers and tool documentation.
  - The owner's page no longer carries ticks. Nothing lands before the
    audit is in and the owner has seen its result. The audit is done: see 2026-11-23-hosted-audit.md.
- **The hairline and the band should not share ink:** the hairline is a
  fact of the graph and the band's extent is the writer's policy. This
  undoes the link between the study's fifth tick and the band's look.
- **The chain spike** is judged worth running by the review, and does not
  replace the count. Still no go from the owner.
- **jbrowse-components-05 asked for counts of lane gap shapes** behind
  its "replaced by" and "complex" headers, and got them: a census of the
  8-haplotype PIF in `gapshapes/`, then a run of its commit 56cc94c330
  through the same harness in `gapshapes/candidate-56cc94c/`. It is
  rebuilding the rule on that and will send one more sha for the same
  checks; the census agent's harness on ada in `agents/gapshapes/` runs a
  commit's real `laneIndelsOf` over every record.

## What a later note overturned

- **The takeover page's "pggb index reader" tick** asks about the
  `window-joined-cut` and `skips-need-a-vouch` prototype. The study showed
  its skip rule unsound: two graphs with byte-identical indexes differ in
  whether the reference takes a link. The same rule in
  `todo/dense-pggb-chain-joints-drawn-as-skips.md` is superseded.
- **"The walk file draws these loci well"** (the study's brief, and that
  todo) holds for shape only: a quarter of its skips are the reference's
  own steps, and at `chrY:24.66 Mb` a half drawn as "1 walk pass" is
  stepped by 122 haplotypes.
- **The 2023 cattle graph is progressive Cactus, not Minigraph-Cactus.**
  The takeover handoff and the study's brief call it Minigraph-Cactus.
  This is an agent's reading of the authors' pipeline; only the source
  file was confirmed.
- **The paper's pggb sentence** ("up to 17,570 nodes", "four refused")
  describes the anchored index and not the graph's windows, and times
  loading and not drawing.
- **jbrowse-components 51e36f0549 is pushed:** on origin/main at 23:20 EST.
  The takeover handoff and the lanes todo say it is not. Whether any hosted
  JBrowse is deployed with it was not checked; until one is, no hosted site
  draws walk-fed lanes against the reference.

## Waiting on the owner

- **Whether the reader and lanes work solves repeat loci:** the first item
  of work below. Its answer reframes the ticks, so bring it first.
- **Study page, six ticks,** each with the study lead's recommendation:
  - the walk file as the graph track's source at every zoom: yes;
  - `build` writes a walk file and names it: yes, first 8 haplotypes;
  - the reference alone in place of a refusal: yes;
  - no skip from an index that does not state "no revisits": yes;
    `ecoli_cactus` then loses its 51 skip marks for good;
  - colour by node, the hairline and the skip rule: yes, once row
    direction is fixed. The hairline's ink is meant to match the repeat
    band's, so this one hangs on the owner's doubt above;
  - cattle: no longer waiting. The owner told the jb2hubs session on
    22 November to rebuild every pangenome species with Minigraph-Cactus,
    cow included (jb2hubs a82bc484fc63,
    `agent-docs/todo/walks-and-genes-for-every-pangenome.md`). All twelve
    of the trial's sheets have now been looked at: from the walk file
    each rebuilt window draws the reference as one line with short
    bubbles or a single branch. At `chr29:5,570,001-5,580,000` the rebuilt
    index draws the reference as a closed ring, not looked into.
- **Takeover page, two ticks:** the repeat band's look, and the index
  reader, which the study overturned. On the look the owner left the box
  unticked with the note "i feel like non-merged" (22:41 EST), and on the
  lanes tick, earlier, "the gold doesn't look very good". No tick on the
  study page had been made by 23:45 EST.
- **Place by chain:** go or no go on the spike.
- **Format questions,** neither with the three reviews a format change
  needs: `revisited:i:N` on the header of the index and its tiers, which
  one reviewer recommends and the study lead did not; and a table of where
  the reference's other passes lie, which both independent reviews point
  at and nobody proposed.
- **`docs/open-problems.md`:** split the page into one file an item and
  change the routing lines in `agent-docs/CLAUDE.md` and
  `handoffs/README.md`, or only file new items that way. Asked, not
  answered.
- **Two stale `until` loops on ada** (pids 147291 and 151897 at 23:20 EST,
  waiting on `~/work/handoff-1121/runs/singlebuild/timing.log`), and the
  cattle trial's 4.1 GB job store: harmless, and removal needs the owner's
  word.

Both pages are private to the `~/.claude3` account and cannot be read from
the `~/.claude` config. Their sources are `takeover/page/index.html` and
`revisited-study/page/revisited-reference-study.html`.

## Owed to other sessions

- **paper-a9:** the pggb chrY numbers and two wordings (`paper.tex` near
  line 560, the letter's line 79). It knows the numbers are not ready.
- **jb2hubs:** paid. Its plan already called the 2023 set progressive
  Cactus and put cow last, after a one-chromosome pilot. The session had
  closed, so its handoff `walks-for-every-species.md` now points at the
  chr29 trial as that pilot (jb2hubs a6f5c5ebfe05, local and unpushed).
- **gfa-to-tabix-64 and gfa-to-tabix-d8:** could not be reached about
  place by chain; its handoff is how they learn of it.

## On branches, not landed

All local, none pushed. Each handoff has the commit ids and folders.

- **Graph track on a revisited reference:** `revisited-colour`
  (bandage-core, plugin) and `revisited-index` (graph-walks, bandage-core,
  plugin). The second still carries the unsound skip rule. It supersedes
  `window-joined-cut` and `skips-need-a-vouch`.
- **Layout:** bandage-core `fmmmtime`, held until measured again after the
  reader work; `loops-rule`, rejected and kept for its pictures.
- **Lanes:** jbrowse-components `repeat-band-looks`, built on commit ids
  main no longer has.
- **Paper:** jbrowse-components `fig5-reshoot` in
  `~/src/jbrowse-components-fig5`; jb2bench `pggb-drawn-clock` in
  `~/src/jb2bench-pggb-drawn`, marked partial; `~/paper-walkfig` with
  uncommitted changes to seven files.

## Work, in the order it can be done

- **The review the owner asked for** is done; see "The review's answer"
  above. Still owed from it: the before and after pictures on one page for
  the owner, once the two running prototypes report.
- **The paper's figures and text.** The paper handoff says the author put
  them in a holding pattern on the night of 22 November, so they wait on
  the owner; the order is in that handoff, "To land".
- **The paper's pggb chrY measurement,** when ada's 1-minute load is under
  about 8. It was 14 at 23:35 EST, and the load is jb2hubs' fly
  Minigraph-Cactus build on 20 cores, which its handoff expects to run at
  least a day. The command and the counts to check against are in the
  takeover handoff, "Left unfinished". It times the index. The study's
  advice is to time the walk file too, on seeded windows of each kind,
  once the source rule is released. The owner's note on the takeover
  page's timing tick asks for a spread over many windows and calls the
  number "not super critical". Until then the paper can quote the
  186-window Minigraph-Cactus spread and no pggb time.
- **The three format reviews.** The first review keeps the table of other
  passes alive, so they are owed, after the measurements and the picture
  listed above. Brief them with both cases. `revisited:i:N` on the index
  header is a separate question and has no new evidence.
- **Housekeeping:** the paper handoff is still untracked in `~/paper`.
  Of the plugin worktrees the takeover handoff marks safe, `-keyoverlay`,
  `-rel105`, `-rel106` and `-cutspeed` are removed; branch `cut-speed`
  stays, since git would not delete it against its upstream though its tip
  is on origin/main, and `-placement` stays, since `lanes-from-placement`
  bbe6670a is on no remote (its changes landed as other commits).

## Standing constraints

- Land, release or flip nothing a user would see before the owner has
  seen before and after pictures. Until the ticks are made, land none of
  the pggb reader work.
- A format change is raised loudly and needs three fresh Fable reviews.
- Heavy runs go on ada, one command at a time over the shared connection;
  leave `~/work/handoff-1121/` and the "walks" session's branches alone.
- Not covered by anything above: BandageJS and ggbandage were not opened;
  only pggb chrY and cattle chr29 were measured; every timing of the day
  was taken under load.
