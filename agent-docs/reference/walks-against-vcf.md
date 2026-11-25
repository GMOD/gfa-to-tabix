---
name: walks-against-vcf
description: The format 8 GRCh38 walk file, read through graph-walks, compared on 2026-11-14 with HPRC's raw vg deconstruct VCF over 209 windows and all 463 haplotypes - every called allele agrees, none missing, on the wrong haplotype or different; where the script, the rows and the broken-file runs are.
---

# The walks against HPRC's raw VCF, 2026-11-14

Run on ada on 2026-11-14. Everything is in
`~/src/walks8-evidence/a36cf6aa/verify/vcfcheck/`: `SUMMARY.txt` (the full
account), `vcfcheck.ts` (the check), `results.tsv` (every row),
`counts.jsonl` (per window), `windows-all.tsv`, and `broken/` with
`broken.sh`.

## What was compared

- **Walks:** the GRCh38 file built by gfa-to-tabix 5.0.0 on ada
  (`~/work/blocks/genome-5.0.0/hprc-v2.1-mc-grch38.GRCh38.walks.gz`,
  1,580,961,269 bytes), cut by graph-walks a7525fb with every walk kept,
  no budgets. The hosted `-f8` file is a later build of 1,580,961,534
  bytes (`docs/walks-container/accept-5.0.0/whole-file/`); the check was
  not rerun on it
- **Arbiter:** HPRC release 2 v2.1 Minigraph-Cactus GRCh38's raw `vg
  deconstruct` VCF, by each record's allele traversals (AT). The VCFs were
  in `/mnt/sdb/cdiesh/vcfcheck/vcf` on ada, not rechecked since
- **Windows:** 209 (9 review loci, 96 random, 50 on records changing
  length by 1 kb or more, 30 on segmental-duplication edges, 24 on
  centromere-model edges), 181 of them holding records
- **Haplotypes:** all 463 the file and the VCF share

## Result

- 61,211 records and 25,662,013 haplotype-by-record calls checked
- 25,579,310 calls agree exactly: the called allele's path is a run of
  the haplotype's steps, and no other allele's is
- 55,951 calls matched only where steps were loaded, with placeholders for
  unloaded abridged steps. Expanded, 50,096 agree, 5,841 show the walk
  passing twice, and 14 disagree at one nested record
- Missing steps, steps on the wrong haplotype, differing steps: 0
- Every other difference is on the VCF side: one nested AMY1 record whose
  child genotype contradicts its parent (chr1:103714167), and 26,746 calls
  where a haplotype crosses a site twice and the VCF's single genotype
  names one allele
- The check fails when broken: swapping two haplotypes and dropping one
  step were caught in 5 of 5 windows, and flipping one sample's phases in
  4 of 5, the fifth holding that sample homozygous
- `SUMMARY.txt` also compares the release's pgbi and wave VCFs, and lists
  wave's left-shift defects
