---
name: alleles-keep-sample-for-two-references
description: The alleles command drops the sample from a sequence's name, so GRCh38's and CHM13's chr1 would share one, and --reference names one PanSN sample's paths at most. Keep the sample in the name when a graph's reference spans more than one, and check the allele track draws it.
metadata:
  repo: gfa-to-tabix
---

# Alleles on two reference samples

- `alleles` writes a row's sequence as the text after `sample#haplotype#`
  (`ref_name` in `src/alleles.rs`), so GRCh38's and CHM13's `chr1` would
  share one name
- `--reference` "names one sample's paths at most" (`src/cli.rs`), so a
  list naming two PanSN samples is refused
- Checked in the source on 2026-11-25; not run on a graph with two
  reference samples

## The change

Keep the sample in the name when the graph's reference spans more than
one sample, and check that the allele track draws it.

## When

When a graph's reference spans two samples.
