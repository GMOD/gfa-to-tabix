# Handoff, 2026-11-14: releasing walk format 8

The owner asked for gfa-to-tabix 5.0.0, which writes walk format 8, to be released across every reader as major versions with a hard cut. Format 7 support is dropped. Each step below waits on the one before it. Nothing is pushed until the gates above that step pass.

## State on 2026-11-15

One session took over both lanes, then stopped launching work when usage ran short. Nothing is pushed, tagged, published or uploaded. Everything below is local.

- **Decided: the walk header names its graph.** The `#walks` line gains `graph:Z:` (the index's hash) and `leftout:i:`. It names no writer and no version, at the owner's request: a version stamp would change every file's bytes at each writer release and force a re-upload on sync. The format number stays 8. See ADR 0015 on the branch.
  - gfa-to-tabix branch `provenance`, head 8fe5434, in ~/src/gfa-to-tabix-provenance: three commits above main 8a965ac. Not merged, because main's checkers then fail the hosted files until they are rebuilt.
  - graph-walks branch `provenance`, head ae6e0ff, in ~/src/graph-walks-provenance, on top of d20d416: fixtures rebuilt, `reader.header()` returns the two values.
  - ADR 0015 has one marked line to fill in after the whole-genome byte check.
- **Drawing fixes landed.** bandage-core `release-fixes` is at 76e0324 (~/src/bandage-core-rel) and the plugin's at 8fbe392: small skips no longer draw as darts, placeholder lengths are always labelled, the FMMM seed stretch has a straightness test, `classifyBubble.ts` is `bubbleLabel.ts`, the menu says "Show links that skip reference", and the node-thickness key shows its two ends. Checked by eye on fresh screenshots at the 571 bp gap, amylase and GSTM1.
  - Hosts must follow: the `bubbles/bubbleLabel` import, `labelledNodeLengths` in place of `nodeLengthLabels`, `depthKey` in place of `depthRange`. BandageJS still imports the old names.
  - The plugin's typecheck shows 3 errors in `GbzBaseSyntenyAdapter.ts`, put down to its hand-linked `node_modules`. Confirm on the clean install.
  - bandage-core's own SVG figure writes no node or placeholder lengths, so ggbandage's static figures lack them.
- **S5 (walk-row lengths).** The dead agent's uncommitted diff is parked as d19c255 on branch `s5-premise` in ~/src/bandage-core-s5. `release-fixes` holds nothing of it. The premise review's result is recorded at the end of this section.
- **An independent design, made from the requirement alone, says freeze format 8 as it is.** Its design and its comparison with the spec are in ~/src/walks8-evidence/22a29087/blind-design/. For open-problems.md, from it:
  - no row says a line ends or continues on another reference sequence; a tag could later;
  - tile extents and `#hole` lines may let a reader tell that a table lacks an entry, which the spec says it can't; unproved;
  - a several-megabase window of every haplotype gets only a zoom-in notice; a zoom layer or bubble hierarchy fits as a separate file under the additions rule.
- **The VCF drawing checker was written and never run.** Its source is ~/src/walks8-evidence/a36cf6aa/drawcheck/src/. The raw VCF sliced to its 66 Minigraph-Cactus windows is on ada at /mnt/sdb/cdiesh/vcfcheck/drawcheck-slice.raw.vcf.gz (+ .tbi).
- **Evidence** from all three sessions is copied to ~/src/walks8-evidence/. The release page is https://claude.ai/artifact/PFkwJvV1eSiHnGG4REsH1s.

Next, in order of dependency:
- Act on the graph-walks review. If it passes: merge d20d416, then `provenance`, put the version commit at the head, name the `-f8` files in the README, repack.
- Merge gfa-to-tabix `provenance`, rebuild both genome files on ada, run `scripts/walks-header-diff.py` on each old and new pair, fill ADR 0015's line, re-upload under the `-f8` names, then sha256 and release-check from both URLs.
- Then the gates below, none of them started: the acceptance runs, the drawing check, the reshoot and the blind layout judge, the integration pass, the parity audit.

## Done

- **Format 8 needed no byte change.** See the readiness audit and the decisions in ADRs 0012–0014.
- **Data checked against the VCF.** Every haplotype's walk was compared with HPRC's raw `vg deconstruct` VCF over 209 windows, for all 463 haplotypes. 25.6M called alleles agree, and none is missing, on the wrong haplotype or different.
- **Hosted under new names beside the format 7 files.** sha256 was read back from the URL, and release-check on both hosted URLs passes 28/28 at graph-walks 031ab8f.
  - `hprc/hprc-v2.1-mc-grch38-f8.GRCh38.walks.gz` (+ `.idx`)
  - `hprc/hprc-v2.1-mc-chm13-f8.CHM13.walks.gz` (+ `.idx`)
- **graph-walks main, at 031ab8f and later.**
  - A copy-on-cut fix for stale departure fields.
  - WalkRowError for short rows.
  - Off-reference placement from returned steps, so an abridged file cuts as the whole one does.
  - A `breakAt` fix, in progress.
- **bandage-core main 96edf31.** The format 8 port, with 81af8f1 (INV chip) and 6428b21 reverted. Drawing patches from another session sit on `release-fixes` in ~/src/bandage-core-rel: S2, R1, R2, S5, the ×4 FMMM seed stretch, and a legend fix.
- **Readers on local `format8` branches:** BandageJS, ggbandage, sequenceTubeMap, ggtubemap. The plugin is on `release-fixes` in ~/src/jb2plugins/jbrowse-plugin-graphgenomeviewer-rel.
- **The paper** (~/paper main 58d1616, unpushed) cites the `-f8` file. Its walk-file numbers are marked `\todo` to remeasure on format 8. Figures 2c and 5 are pinned to plugin 9.0.0 in jbrowse-components (8b0a989e67, unpushed).

## Gates before the first push

- **Review of graph-walks 16b4f72, 031ab8f and the `breakAt` fix.** It must be independent. The placement invariant ("an abridged file cuts as the whole one") has to be proved, and also run on a real chr22 abridged/whole pair, not only on fixtures.
- **ADR 0012's open acceptance runs, recorded under `docs/walks-container/accept-5.0.0/`:**
  - worst-window time and memory (chr2:91.41 Mb, chr2:92.08 Mb) on the 5.0.0 files with the final reader;
  - GRCh38 against the hosted format 7 file;
  - byte identity across thread counts;
  - the equality harness on pggb GRCh38 5.0.0;
  - the 4 MB read scan.
- **The drawing check against the VCF.** Nothing may be drawn without a carrier, nothing carried may be invisible, and every label number must match. It runs on the final bandage-core.
- **One consumer refresh on the final tarballs:** bandage-core, the plugin (pins from scratch, version 10.0.0), BandageJS, ggbandage, sequenceTubeMap, ggtubemap and **jb2hubs**. Each runs its full suite.
- **The owner's look at the final BEFORE/AFTER pairs.** That is ADR 0012's last acceptance item.

## Order of the release

- **graph-walks.**
  - Update the README to name the `-f8` hosted files.
  - Put the version commit at main's head.
  - Push main and tag `v7.0.0` on that head; CI publishes.
  - Re-run release-check on the hosted URLs if the reader changed after 031ab8f.
- **gfa-to-tabix.**
  - Move push.yml's rebuild-job pin from the format 7 commit to graph-walks v7.0.0's commit.
  - Run the whole CI locally.
  - Push main. That push is the 5.0.0 release (crates.io and the Release workflow), so it goes last among the gfa-to-tabix steps.
- **bandage-core 14.0.0.**
  - Pin graph-walks `^7.0.0`, and pin gfa-to-tabix's parity CI to v5.0.0.
  - Push `core-next` branches of BandageJS and the plugin that pin the published versions.
  - Then push and publish bandage-core.
- **The readers.**
  - Swap the `file:` pins to the published versions and regenerate lockfiles. ggbandage rebases onto its update-deps commits.
  - Release each the way its repo does.
  - jb2hubs: swap its HPRC config to the `-f8` file and the new pins, upload the config, and commit the uploaded stamp.
- **Configs, in one pass.**
  - Edit jbrowse-components `demos/hprc/config.json` (lines 254, 343), `demos/hprc_multiway/config.json` (307) and `test_data/graphgenomeview/hprc.json` (160) to name the `-f8` files, then deploy them with `deploy-demo.sh`.
  - `test_data/graphgenomeview/paper_hprc.json` stays on format 7 with plugin 9.0.0, by design.
- **The plugin.**
  - Wait for ci-green on the hosted config.
  - `pnpm version major` gives 10.0.0.
  - `pnpm dep` in jbrowse-plugin-list rehosts `latest/`.
  - jb2hubs must already read `-f8`, since its live page loads `latest/`.
- **The paper.** Rerun the walk-file numbers with jb2bench (`agent-docs/walk-rerun-format8.md` in ~/paper) once plugin 10 is on `latest/`, and clear the `\todo` markers. Do this before the freeze, around 2026-11-18.
- **Look at real windows afterwards.**

## Not done in this release

- Who and how many take a branch: link width by shown haplotypes (S3).
- Direction marks for inversions (S4).
- Copy counts at copy-number loci.
- The amylase knot. The bubble hierarchy is planned after the freeze.
