---
name: fold-leftovers
description: Two things the thread-fold fixes leave open. graph-fold merges equal-length alleles at one site without comparing their nodes, loaded or not. And at a site where every haplotype carries an allele near the threshold, only some are drawn.
metadata:
  repo: graph-fold
---

# What the thread-fold fixes leave open

Planned 2026-11-24 by a Fable read of the hosted cuts. A not-loaded stretch now folds as the loaded allele of its length at its site (graph-fold 1.2.0 on branch `owner-asks-c`, reverting e527f13; core reverts 8243162), so a fold no longer drops walk widths there: at HLA-II the fold of the default cut equals the fold of the fully loaded cut.

## Equal-length alleles merge unchecked

- graph-fold names an off-reference node by site and length (`fold.ts`, `ins:<left>:<bp>` and `stretch()`), so two alleles of one length at one site share a node whatever their sequence. A stretch the cut did not load joins the loaded allele of its length the same way.
- Nobody has measured whether that ever joins different content on hosted data. It needs a check comparing the nodes each walk takes.

## The threshold cliff

- At SV-mul-10k-100k chr19:7061813 all eight haplotypes carry 448 to 551 bp off GRCh38, and only the two whose longest run reaches 472 bp are drawn.
- Drawing every allele at a site once any reaches the threshold would fix the picture but complicates the key's sentence; it was left out.
