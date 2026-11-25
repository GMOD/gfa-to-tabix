---
name: refs-take-one-haplotype
description: What letting --refs take sample#haplotype needs beyond a matcher - refusing overlapping refs and perhaps a bare diploid sample, a diploid-reference fixture with a hole, the real-data done criteria for an HG002#1 track - and a ruling on whether the file is named HG002.1 or by the sample.
metadata:
  repo: gfa-to-tabix, jbrowse-plugin-graphgenomeviewer
---

# `--refs` taking one haplotype

From a code review of 2026-11-02 (format 5), restated for format 8. The
writer facts were checked on 2026-11-25; the rest is the review's plan,
not run. `docs/open-problems.md` has two sections on the same question, "A
reference of one haplotype of a sample can't be written" and "Walk files:
references and abridging".

## What the tools do today

- `--refs` names samples, and each is compared with a path's sample alone
  (`reference_of` in `src/walks.rs`). `--refs HG002` makes every HG002
  path a reference sequence; `--refs 'HG002#1'` is refused, "matches no
  path's sample". `src/main.rs` drops exact repeats in the list and
  nothing else
- Format 8 allows a file whose reference is one whole haplotype of its
  `#reference` sample (`docs/walks-format.md`, "Whole haplotypes"), and
  graph-walks reads one. `scripts/check-walks.sh` makes such a file by
  building the other haplotype under a stand-in sample and renaming it
- The plugin's `walkFileSample` (`src/locationName.ts`) gives no sample for
  a file name whose last dotted field is all digits, so
  `x.HG002.1.walks.gz` yields none. Mapping it to `HG002#1`, not `HG002`,
  keeps HG002#2's lane: the lanes adapter drops a lane whose sample is the
  anchor's

## The writer change

- One matcher: a ref matches a path when it equals the path's sample or
  its `sample#haplotype` (`haplotype` in `src/gfa.rs`)
- The no-match error lists haplotypes as well as samples
- **Refuse overlapping refs,** such as `--refs HG002,HG002#1` or
  `GRCh38,GRCh38#0`. On format 5 the first ref took the chunks, so the
  first file got the reference rows twice and the second only a header;
  not rechecked on format 8
- **Refuse a bare sample with more than one haplotype,** naming the
  haplotypes to pick from. This needs a call: format 8 allows a reference
  of several whole haplotypes, and `--refs HG002` writes one today
- A haplotype ref beside another ref's file, `--refs GRCh38,HG002#1`, needs
  nothing more

## File name: needs a ruling

- The 2026-11-02 plan names the file `<prefix>.HG002.1.walks.gz`: `#`
  starts a URL fragment, so it becomes `.`, matching ADR 0007's
  `SM:Z:HG002.1`
- `docs/open-problems.md` ("A reference of one haplotype of a sample can't
  be written") suggests keeping the sample's name, `<prefix>.HG002`, with
  `#reference HG002`
- The two disagree, and the plugin's file-name rule above follows
  whichever is taken

## A test fixture

`tests/data/walks-diploid-ref.gfa`, 10 bp nodes, `--tile 10`, does not
exist yet:

```
W HG002  1 chr  0  20 >1>2
W HG002  1 chr  40 60 >5>6
W HG002  2 chr  0  60 >1>7>3>4>5>6
W GRCh38 0 chr1 0  60 >1>7>3>4>5>6
```

HG002#1's chr is two lines with a hole between, as where Minigraph-Cactus
clips a haplotype; no hosted walk file's reference has one. The review's
expected rows were format 5 tags and no longer apply. What it expected
that still reads in format 8, not run:

- **gfa-to-tabix** with `--refs HG002#1`: one file, whose table lists only
  `HG002#1#chr`, with `#haplotype` lines for GRCh38#0 and HG002#2 and a
  `#hole` over 20-40; `--refs HG002,HG002#1` refused; `--refs HG002#3`
  refused, listing haplotypes; `--refs R#0,Q#0` on `walks-two-refs.gfa`
  gives the rows of `R,Q`
- **graph-walks:** a cut over 22-38 has no reference there and doesn't
  throw; a cut over 10-45 has two `HG002#1#chr` pieces either side of the
  hole, nodes 5 and 6 at 40 and 50, and GRCh38 as one piece
- **The plugin:** lanes GRCh38#0 and HG002#2 over 0-20 and 40-60 only; a
  22-38 window returns no lane and shows that no reference sequence is
  there; a subgraph over 10-45 has no duplicate reference stub path (see
  the diploid-reference bullet in `../collections/loose-ends.md`)

## On real data

- An HG002#1 file of chr22 needs a chr22 GFA.
  `docs/departures/scripts/arbitration-inputs.sh` cuts MC chr22 from HPRC
  v2.1's GRCh38 GBZ with `vg chunk --contig chr22`; whether that cut holds
  all of HG002#1's chr22 lines is not checked
- The hosted GRCh38 walk file names HG002's lines `HG002#1#chr1` and so on,
  so the file's sequence would be `HG002#1#chr22`
- jb2hubs' `website/pangenome-config/hprc-grch38.json` has an `HG002.1`
  assembly (alias `HG002#1`) whose chrom sizes name `chr1` to `chr22`
  bare, and an `HG002.1_liftoff_genes` track
- Done means, in the hosted app: an HG002.1 track drawing HG002#1's own
  coordinates and genes, lanes for GRCh38#0 and HG002#2, and a window in a
  hole saying that no reference sequence is there
