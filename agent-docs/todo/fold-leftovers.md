---
name: fold-leftovers
description: Three things the thread-fold fixes leave open. A fold drops walk widths wherever a not-loaded stretch is drawn, until the cut loads those stretches at fold zoom. graph-fold merges equal-length loaded alleles at one site without comparing their nodes. And at a site where every haplotype carries an allele near the threshold, only some are drawn.
metadata:
  repo: graph-fold
---

# What the thread-fold fixes leave open

Planned 2026-11-24 by a Fable read of the hosted cuts; the fixes being built are on branch `fold-truth` in graph-fold, bandage-core and the plugin.

## Walk widths lost at not-loaded stretches

- A fold now keeps a not-loaded stretch as one haplotype's node and, as unfolded, draws no thickness as a count wherever one is drawn.
- On the 17 graph-track audit windows this drops walk widths at H-AMY1, H-KIV2 and SV-mul-10k-100k.
- Getting them back truthfully needs the cut to load those stretches at fold zoom, so the fold can compare them.

## Equal-length loaded alleles merge unchecked

- graph-fold names an off-reference node by site and length (`fold.ts`, `ins:<left>:<bp>` and `stretch()`), so two loaded alleles of one length at one site share a node whatever their sequence.
- Nobody has measured whether that ever joins different content on hosted data. It needs a check comparing the nodes each walk takes.

## The threshold cliff

- At SV-mul-10k-100k chr19:7061813 all eight haplotypes carry 448 to 551 bp off GRCh38, and only the two whose longest run reaches 472 bp are drawn.
- Drawing every allele at a site once any reaches the threshold would fix the picture but complicates the key's sentence; it was left out.
