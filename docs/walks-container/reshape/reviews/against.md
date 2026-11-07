**Verdict: format 8, amended.** Files: `/home/cdiesh/work/review-2026-11-06/format8-contra/rev8/` (`review8.py`, `*.json`, `data/*.jsonl`), run on ada against the spike's own builds.

**The steelmen**

- *Ship format 7.* Truth as written ("unless the file marks it") is already met: `passes`, `leavePasses`, `rejoinPasses` mark every chosen pass, and graph-walks has `placementChoice()`. "Mark placement instead of deleting" is therefore not an alternative; it is format 7. The number change is free either way, since nothing reads 7. What 7 costs is 270 lines, 10 claims, and a bug class: the clean-room's wrong-strand records live in `visit_near` (`reports/cleanroom.md`). The reviews found 5–8 entries per mechanism-day (`henli-fundamental.md`), and placement is the mechanism that does nothing on the hosted graph.
- *Smaller than ADR 0011.* R1 is already a 5-line patch. R3 and the 0 bp drop are independent, measured and cheap; nothing to cut.

**Are the 0 own bp records fiction? Yes, 94%.** I rebuilt GRCh38's path from the `ref` rows and asked, for each 0 own bp record with a revisited end, whether its two handles are adjacent anywhere on the reference: 340,377 of 361,628 are (`base.pggbY.json` → `fiction`). Those haplotypes follow the reference; the record exists because the rule placed the ends at different passes. The other 21,251 are real non-reference edges, which R1 folds into spanning records. The 5,858 once-once records are identical in both files.

**Does 26.5% growth cost nothing? No.** The growth is 2.3× the abridged paths (693 → 1,565, `r1.pggbY.log`), and windows showing abridged bars go 9 → 26 at 1 kb and 19 → 38 at 64 kb of 300 (`summary.windows_with_abridged`). Also the 1 Mb median rises 4.4% (736.7 → 769.3, `results.txt`), which breaks the Cost criterion as written.

**The unfair comparison:** `winbytes.py` counts tile and departure units only. graph-walks attaches every record with ≤ 65,536 own bp, and R1's spanning records (median 4,095 own bp) all live elsewhere. Same method, both files, 1 kb: base 589 / 1,650 KB median / p90 with 9 attach tiles; R1 1,070 / 2,395 KB with 22 (`summary.total_med_p90`, `attach_tiles_med_p90`; MC calibrates at 30 / 273 against arbA's 30 / 243). Records overlapping a window barely move, 5,101 → 4,810, because spanning records are wider. The ADR's "p90 falls at every size" holds only without attach fetches.

**Why format 8 still wins:** MC is byte-identical, so until pggb is hosted the choice buys only simplicity and truth, and it buys both: −270 lines, −10 claims, 0 records ending on a revisited node, 2.4% own0 against 86.5% (`deps.*.json`). The "right a third of the time" figure is Yp11/Yq11 by pieces; by bp outside repeats nearest pass scores 88.7–93.5% (`open-problems.md`), so the loss is real but the ADR's framing is wrong, not its decision.

**Amendments**

- Reader rule, stated in the ADR: a record, or an in-piece computed departure, whose skipped reference stretch lies wholly on revisited nodes is a collapsed crossing; draw it from `passes`, never attach it. Without this graph-walks pays 1.8× bytes and 2.4× requests at the median. It is needed in ordinary tiles too: 173 of 360 tiles in the measured range hold revisited bp, 29 of them under 1% (`refscan.base.pggbY.tsv`), so every haplotype following the reference there gets a 1 bp computed departure.
- Correct the Evidence: 1 Mb median +4.4%; abridged windows ×2–3; attach bytes as above.
- Keep C62 and the ref-row half of C2: the ADR deletes the claims that define the `passes` column it keeps.

**Where I'd be wrong:** if a pggb-on-GRCh38 file is to be hosted for users during the freeze. Then the palindrome window at chrY:23.6 Mb shows 91 haplotypes under 7 and 0 under 8 (`inspect.pggbY.jsonl`), and the right fix is alignment-guided placement (86.5–99.4% MC agreement), which needs the pass fields format 8 deletes; ship 7 and go straight to that ADR.