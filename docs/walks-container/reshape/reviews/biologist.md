I have what I need. Verdict below, under 600 words.

Data: `/tmp/claude-1001/-home-cdiesh-src-gfa-to-tabix/817ce9cc-1377-498a-8e03-85283c80a331/scratchpad/out/` (decoded from `~/work/reshape/out/{base,r1}.pggbY` and `base.mc22` on ada; scripts `win.py`, `hapwalk.py`, `mcsv.py` beside it, copies in `ada:~/work/review-biologist/`). Drawing semantics traced from `graph-walks/src/walkDepartures.ts` (chainEvents/readPath) and `structuralForms.ts` (markOf, changeKind, lopsidedKind); the 8.9.0 plugin still reads format 5 and draws a spanning record as a `skip` glyph (`walkLanes.ts` windowDeletion).

## Five windows, what the screen shows

**chrY:23,600,000–23,601,000 (palindrome, every node passed 4×).** Format 7: 91 haplotypes drawn as walks through the window (rule-placed, right about a third of the time) plus 6,293 records spanning it, 98% 0 bp hops, mostly 1–3.5 Mb (`win.base.chrY.23600000.json`). Format 8: no walk at all; all 124 haplotypes exist only as 2,760 spanning records, median stretch 3.47 Mb, median own 4,095 bp. HG002#1 has 561 records with both ends in 21.9–26.3 Mb, 181 over 1 Mb (`hapwalk.r1.chrY.palindrome.HG002.json`): leave 22,527,028 → rejoin 26,001,387 (380 own bp), then 26,038,384 → 22,579,715 (15,726 own bp), and so on. Under the current reader these become marks "loss 3.5 Mb" (replacement, lopsided deletion) alternating with "dup 3.5 Mb" (repeatedBp) for every haplotype. HG002 did not jump; it carries one arm whose paralogous-variant alleles match now one reference arm, now the other. Both formats' records are facts of the graph; neither is a fact about HG002.

**chrY:18,610,000 (Yq11 inverted repeat, copies 220–300 kb apart).** Format 7: 108 haplotypes walk; HG002 has 37 0 bp "switch" hops. Format 8: 70 haplotypes walk on the few single-pass nodes; HG002 has 40 records, 18 of them "switch", each 300–400 kb, carrying 300–18,000 own bp (`hapwalk.r1.chrY.18.4-18.9.HG002.json`). Drawn: 40 inversions.

**chrY:18,550,000 (nearest pass probably right).** Format 7: 46 haplotypes walk. Format 8: nobody walks; 121 haplotypes as spanning records (`win.r1.chrY.18550000.json`), own bp median 200. The 603 bp node is now unplaced although its other pass is 220 kb away.

**chrY:14,500,000 (control, no revisited node).** Identical walks (117). But 4,695 records 11–18 Mb long span the window under both formats, the 7.60 Mb ↔ 22.73 Mb copy pair's PSV hops (`win.r1.chrY.14500000.json`): a 1 kb window with no variation pays 49 KB of records.

**chr22:23,854,500 (MC, 2.6 kb common deletion, 307 haplotypes).** Same bytes in both formats: 463 haplotypes walk; 309 records 0 own bp forward 2,571 bp. Drawn as a 2.6 kb skip. Correct.

**chr22:18,690,000 (MC LCR22A).** Same in both: 0 walks; 462 haplotypes each as one record (median 50 kb own over 65 kb–2.5 Mb of reference). Drawn as one bypass per haplotype. Readable. The pggb chr22 GFA is no longer on ada (`~/work/pggb` is gone), so the pggb LCR22 picture is inferred from the chrY repeat windows: it would look like 18.61 Mb.

## Judgement

- **Format 8 in collapsed repeats: true and misleading.** It removes the rule-made hops (0 own bp 367,486 → 5,858) but keeps every hop between copy-specific nodes of different copies: 43,935 of 52,460 records in the palindrome are strand switches, median 434 per haplotype. Nothing in the file marks them, since both ends are `passes 1`. A viewer drawing records as the reader now does draws megabase deletions, duplications and inversions on every haplotype.
- **Format 7: misleading differently.** It draws confident walks that are rule picks, plus the same hops, more of them.
- **A true and useful design exists, and is small:** keep format 8's placement, and add two facts. Per record, `refBp`: the own bp on nodes the reference passes anywhere. A PSV hop has refBp ≈ ownBp; a real insertion has 0. Per reference sequence, a `#collapsed` table: each run of revisited nodes with its other passes' offsets (175 ref rows carry passes on chrY). With these a viewer folds any record whose ends lie in copies of one family into "present, copy unresolved", and draws the reference's copy structure.

## Verdict

Truth: format 8 passes. Usefulness: fails as written; the palindrome and Yq11 pictures are false calls. Convergence: therefore fails, since the plugin port will force a format 9 the day a hosted chrY is viewed. Add `refBp` and the collapsed-run table before freezing.

What a viewer must draw for format 8 to be acceptable: over a run of `passes > 1`, a reference band "×k, also at …"; a haplotype whose record crosses it as a hatched presence bar, never a deletion, insertion, duplication or inversion; strand-switch and multi-megabase records whose own bp are reference nodes folded into that bar; only records with own bp on non-reference nodes drawn as bypasses, labelled by bp, not by call.