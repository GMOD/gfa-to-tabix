---
name: 2026-11-22-revisited-reference-study
description: The study the owner commissioned on drawing a graph whose reference revisits nodes has reported. The walk file is the only file that holds the reference at every pass, an index of such a graph cannot vouch a skip, and released walk-file drawings state the writer's placement as fact in thickness, skips, rows and lanes. Two prototypes sit on local branches, six ticks wait on the owner, a format question raised by a reviewer has not had its three reviews, and a chr29 trial puts a Minigraph-Cactus rebuild of the cattle graph at about 60 to 70 CPU-hours.
---

# Drawing a graph whose reference revisits nodes, 2026-11-22

Pointers to where each thread stands. Delete this when the owner's ticks are
acted on, the format question is ruled on and the cattle trial is filed.
Nothing was pushed, landed or released, and no default was changed.

## Read first

- **The owner's page,** with the table of window kinds, before and after
  pictures, the invariants, the plan and six ticks:
  `https://claude.ai/artifact/VKZ2s29hBnXWh526S4RMVw`, private to the
  account of the `~/.claude3` config. Its source is
  `~/src/walks8-evidence/sessions-20261122/revisited-study/page/`; ticks are
  read with the artifact's data tool, collection `decisions`.
- **The blind picture review,** `study/reader.txt` in the evidence folder:
  what each row of every sheet said to a reader, checked against the GFA.
  Read it before designing any mark.
- **Evidence:** `~/src/walks8-evidence/sessions-20261122/revisited-study/`
  (`tracks/`, `colour/`, `indexnote/`, `cow/`, `page/`, and `study/` with
  the digest every reviewer was given, the claims and the reports).
- **Measurements and scripts:** ada, `~/work/walks8-gates/agents/` under
  `kinds`, `arrayscale`, `cow`, `tracks`, `breaker`, `skipswalk`, `colour`,
  `indexnote`, `tagfacts`, `cowmc`.

## What is settled, with its check

Each of these was measured with a check shown failing on a planted fault;
the page gives the numbers.

- **The walk file holds the reference at every pass,** and the node/link
  index one pass a node. On pggb chrY 310 of 2,423 bins of 10 kb are under
  5% placed in the index.
- **An index of such a graph cannot say whether the reference takes a
  link.** Pairs of graphs with byte-identical indexes differ in it
  (`breaker/t/t10*`). So the unlanded prototype's rule, a skip where the cut
  holds the reference whole between a link's ends, is unsound: this
  supersedes that rule in `todo/dense-pggb-chain-joints-drawn-as-skips.md`.
- **A fold tier cannot be told from an rGFA index by its bytes,** and the
  linear graph track reads it above 5 bp per px even when the track names a
  walk file.
- **Released walk-file drawings state placement as fact:** node thickness
  on nodes the reference passes more than once, a quarter of the links
  marked as skips, walk-row and lane texts.
- **One test covers them:** whether the cut holds every pass of the
  reference over a node, which is its reference steps in the cut equalling
  its `passes`.
- **Colour by node** makes walks over the same nodes look alike wherever
  they were placed, and leaves a file with `revisited:i:0` pixel-identical.
- **Only the step budget refuses a walk-file cut;** fewer haplotypes is the
  remedy to about 300 kb to 1 Mb, where layout time and the 20,000-node cap
  take over.
- **The 2023 cattle graph is the paper's progressive Cactus set,** not
  Minigraph-Cactus (the agent's reading of the authors' pipeline; the
  trial's source file is `Zenodo/cactus/29.gfa`).

## Waiting on the owner

- **Six ticks on the page:** the walk file as source at every zoom; `build`
  writing a walk file with default haplotypes; the reference alone in place
  of a refusal; no skip from an index that does not state "no revisits";
  colour by node with the hairline and the skip rule; the cattle graph.
- **The hairline's ink** should match the lanes' repeat band, whose look is
  itself a tick on the takeover page (`2026-11-22-laptop-takeover.md`). The
  index prototype's hatch for "no reference node placed here" is a second
  hatch; nobody has looked at the two side by side.

## Open, and not reviewed

- **A format question.** A reviewer deciding from the evidence alone
  recommends `revisited:i:N` on the header line of the index and its tiers.
  The study's lead did not. The three reviews a format change needs were
  not run. The facts for them are in `agents/tagfacts/` and on the page:
  only `ecoli_pggb` (423 revisited nodes on K12) and `ecoli_cactus` (source
  graph lost) are hosted path-graph indexes, released readers ignore an
  unknown tag on that line, and `graph:Z:` does not tie a tier or a
  reference to a walk file. Brief the three reviewers with both cases; the
  recommending report is `study/decider.txt`.
- **The writer's placement.** `2026-11-22-pggb-place-by-chain.md` proposes
  placing by a co-linear chain. The study did not weigh it. Its reader
  rules hold whatever the writer picks, and its numbers say where a better
  pick would show: `chrY:24,659,511-24,669,511`, where 122 haplotypes step
  nodes the file places at the other pass, and cattle chr29, where 3.8% of
  the steps that neighbours decide are placed elsewhere
  (`agents/kinds/out/at2466.jsonl`, `agents/cow/out/placement.jsonl`).
- **A table of where the reference's other passes lie** would let a reader
  say where the other copy is and fetch steps filed at another pass. It is
  a format addition and was not proposed; both independent reviews point at
  it as what a first-pass or later-pass window lacks.
- **Marks the blind review found wrong or missing,** none designed yet:
  - node thickness: every variant tried keeps a false step or adds a false
    contrast (at TSPY the nodes off the reference look like the main
    route); the key's "N walk passes" is a 1 bp node's count;
  - rows coloured by node show a palindrome's spacer the wrong way in five
    of eight rows; the reviewer's guess is that a row is drawn in its
    contig's direction, and that direction should come from nodes the
    reference passes once. Four haplotypes do carry the spacer at
    `chrY:18.64-18.68 Mb` inverted, which no picture shows;
  - the pale band for a haplotype with no step placed reads as "nothing
    here"; the index hatch and its line read as "GRCh38 is missing";
  - a gene pin for a gene outside the view (RBMY1E at 21.92 Mb), GRCh38's
    50 kb run of N at TSPY drawn as a node, "placement choice" printed in a
    window with no revisited node;
  - no number anywhere for the reference's passes or a haplotype's copies.

## The cattle rebuild trial, finished

No agent of this study was running when the session closed.

- **Cattle chr29 built with Minigraph-Cactus 4.0.0** from the 2023 paper's
  12 assemblies, bosTau9 as reference: 1 h 15 min on two cores of a loaded
  ada, 1.4 CPU-hours, 4.1 GB peak. Its walk file states `revisited:i:0`.
  Scaled by chromosome length, the 29 autosomes are about 60 to 70
  CPU-hours and a 12.5 GB peak. The report is `study/cowmc.txt`, the
  before and after sheets `cowmc/` in the evidence folder.
- **On ada:** scripts, logs and the walk file and index in
  `~/work/walks8-gates/agents/cowmc/` (`scripts/run-mc.sh` is the build
  command; the Cactus install is `opt/cactus-bin-v4.0.0/`), and the inputs
  and outputs in `/mnt/sdb/cdiesh/bovinePangenome/mc-trial/`. Its
  `build/js` is a 4.1 GB job store kept for the timings and can go.
- **What the rebuild changes** is on the page: it is not the published
  graph, the default clips 1.1% of the sequence, and duplicated regions
  carry fewer aligned assemblies.
- **Owed to jb2hubs-5d,** which holds a cow walk-file build on such a
  rebuild (the takeover handoff): this result, and that the 2023 set is
  progressive Cactus and not Minigraph-Cactus. It has not been told.
- No published Minigraph-Cactus cattle graph is on bosTau9; three on
  ARS-UCD1.3 and ARS-UCD2.0 from other assemblies are listed in the report.

## On branches, not landed

- **Colour by node, the hairline and the thickness rule:** `revisited-colour`
  in bandage-core (a90de5f) and the plugin (ea0c5928), clones on ada in
  `agents/colour/`. Variants sit behind a switch read from the served
  folder's name; the final ones are strip 3, rows 3, thickness 3, with the
  pale band of rows 2. Not yet in one build together.
- **The index-only fallback:** `revisited-index` in graph-walks (00487be),
  bandage-core (0a0e638) and the plugin (998a00f2), on ada in
  `agents/indexnote/` and copied to the laptop scratchpad it names. It still
  carries the unsound skip rule, bends an ordinary window at 14.5 Mb, and
  returns nothing for a window on a non-reference sequence in the contig
  layout.
- The earlier `window-joined-cut` and `skips-need-a-vouch` branches are the
  base of the second and are superseded by it.

## For the paper session

- The sentence that quotes pggb node counts and draw times from the
  anchored index should go; the page's paper section says what can be said.
- The measurement set up on jb2bench branch `pggb-drawn-clock` times the
  index. The study's advice is to time the walk file as well, on seeded
  windows of each kind, once the source rule is released.

## Not done

- BandageJS and ggbandage were not opened.
- Only pggb chrY and cattle chr29 were measured; not pggb chr22, not a
  CHM13-referenced file.
- Every timing was taken on ada at a load of 10 to 54.
