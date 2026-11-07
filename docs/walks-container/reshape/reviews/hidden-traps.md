**Hidden-traps review of ADR 0011 / format 8.** Numbers not in the spike's files are in `/tmp/claude-1001/-home-cdiesh-src-gfa-to-tabix/817ce9cc-1377-498a-8e03-85283c80a331/scratchpad/hidden-traps-results.txt` (scripts `an2.py`, `an3.py`, `an4.py` beside it, run on ada against `~/work/reshape/out/{base,r1}.pggbY.GRCh38.walks.gz`, records deduplicated across pyramid blocks).

## Ranked traps

- **"Records spanning the repeat" are still copy hops.** At chrY:23.60 Mb, 2,693 of the 2,760 R1 records have ends over 1 Mb apart; 65 have both ends within 100 kb (base: 6,333 / 0). Per path, median 10 records cross the 1 kb window, max 47. HG02984#1's contig alternates leave 21,936,460 + → rejoin 26,116,297 − (8,067 own bp) then back, every ~13 kb of contig. File-wide, 14.5% of records have extent > 1 Mb (base 10.1%) and 40% switch strand (base 29%). The nearest once-passed nodes inside a collapsed stretch are copy-specific variants scattered across copies, so "every position is a fact" holds and the drawn picture is still arcs to loci 4 Mb away. The ADR's "all 124 haplotypes appear as records spanning it" hides this.
- **graph-walks re-places what the writer refuses to.** `placeAndLink` (graph-walks `src/walkChunk.ts:723-727`): "a node on any read chunk's R keeps its reference position, even where another chunk's route steps on it". Route-interior own steps on revisited nodes are drawn at the pass of whichever tile was read, i.e. nearest pass by another road, unmarked. C119 says the same. The ADR must either forbid this in the reader rules or admit the viewer places.
- **`revisited` is per reference sample, not per sequence.** `index_visits` (`src/walks.rs:745-776`) counts passes over all the sample's walks; C62 says so. The ADR's "its reference sequence passes once" is not what the patch does. Consequence: `--refs ref` on `tests/data/diploid.gfa` places 1 step of 3 under R1 (base 3); any diploid reference, or a node on two chromosomes, is unplaced. Open-problems already flagged `--refs HG002`; format 8 turns it from a wrong rule into no rows.
- **Five contigs vanish silently.** R1 leaves out 532 paths against 527 (`out/r1.pggbY.log`): HG02132#1#JBHDTR010000031.1 (155,989 steps), HG04115#1 ×2 (252,371 and 136,036), HG04157#1, NA18974#1 have no rows and no record, because every GRCh38 node they touch is revisited (C20). No tally names them.
- **Attach fetches double.** The spike measured tiles + departures only. Tiles named by `ownTiles` for records an edge-outside read needs: 23.60 Mb 521 KB → 1,108 KB; 24.03 Mb 679 → 1,336 KB; the control at 14.50 Mb 251 → 725 KB. Own steps that used to be placed now sit in the leave tile, so p90 tile bytes rise 38.9 → 54.2 KB. Open-problems' attach-fetch item gets worse.
- **`passes` cannot tell collapsed from skipped.** A record's stretch mixes passes>1 and passes=1 nodes (the hop above spans both). bandage-core's `placementChoice` (`src/gfa/departures.ts:96`) and its text go away with `leavePasses`; nothing replaces them. The viewer rule "draw collapsed from passes" is unwritten and unmeasured on these windows.
- **Minor:** one detail unit reaches 3.4 MB (tile 26607616, n>1 MB 57 vs 42) so one expand costs that; abridged paths 693 → 1,565. Base already had 3.2 MB, so not new.

## What ADR 0011 must add to be freezable

- State the collapse rule as the code has it: a node any sequence of the reference sample passes more than once, and decide `--refs <diploid>` (refuse, or per-sequence counting with a measured file).
- A reader rule replacing C119: own steps on a revisited node get no reference position, and `revisits`/C144 go.
- A stderr tally and `#header` count of W/P lines dropped because every reference node they touch is revisited.
- Attach-fetch bytes in the Evidence table, per window size, both files.
- A viewer rule for a record whose stretch holds passes>1 nodes, with the 23.60 and 24.03 Mb windows drawn once before freezing.
- Honest wording: records in collapsed repeats remain hops between copies; R1 cuts them 25–45% per path, not to one span.

## Consumer cost

graph-walks: 21 copy-decoding lines in `walkChunk.ts`, 38 test lines, 106 fixtures to rebuild, format bump. bandage-core: `placementChoice` and its text (about 10 lines). Plugin: nothing on passes. Shipping format 7 instead needs none of this; the plugin is on graph-walks ^4.6.0 and bandage-core on ^5.0.2 either way.

## Verdict

**Not freezable as written.** The placement rule is sound and the file-size story holds, but the ADR freezes a format whose central claim about repeats is not what the file shows, whose reader quietly undoes the rule, and whose diploid-reference and dropped-path behaviours are unstated. With the six additions above and one more window inspection it is freezable; without them format 9 arrives the day someone views chrY:24 Mb or builds on HG002.