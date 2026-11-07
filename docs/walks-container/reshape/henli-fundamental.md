## Verdict

Both, and design dominates. Half the log (60 of 120 bullets) is the direct cost of four design choices; the other half is mostly spec-versus-code drift, and the spec is 143 claims long because the design needed that many rules. The execution slips are the second face of the same problem: no one can hold this format in one head, so sentences drift from code and checks copy the code they check.

The project is 30 days old and has shipped six walk formats in 24 days (2 on 10-12, 3 on 10-16, 4 and 5 on 10-20, 6 on 11-04, 7 on 11-05). Each format added a mechanism to patch the previous one's leak. That is the signature of a design that cannot keep its promises, not of sloppy work.

## Counts

Per-entry tags are in `/tmp/claude-1001/-home-cdiesh-src-gfa-to-tabix/855f6c54-d3d1-4821-8cae-70124fa629a0/scratchpad/henli-diagnosis/classification.txt`.

**Execution, 60:** spec/doc drift and prose ahead of data 26; test or check gaps 11; ports and API slips 13; machine and scripts 8; one unknown; one meta entry.

**Design consequence, 60**, by generating choice:

- **Tiling a path into pieces** (attach fetches, `ownTiles`, holes, cross-tile reads): 14
- **Degenerate shapes** under "every line states its true stretch" (0 bp nodes, 0 bp sequences, points at `|S|`): 11
- **Forms/folding** in graph-walks: 9
- **Projection onto a reference that revisits nodes** (nearest pass, `stay`, pass counts, `@k`/`:k`): 8, but these carry the largest numbers in the record (chr9: 2.2 M records hopping between copies; pggb chrY: 97% of records end on a revisited node, 87% carry 0 own bp)
- **Summary rows and safeguards left to readers** (abridged `bp`, budgets, skip rows): 8
- **The Tabix fake key and its compensations** (chunk-before, `maxnode`, `#long`, pyramid): 8
- **Viewer rules from format 5 met by 6**: 2

Four entries are explicitly re-found; two more are "re-found as a class". `ownTiles`, added 11-05, produced six entries within 24 hours. The claims audit found 15 of 115 claims false, 7 ambiguous, 34 unchecked; mutation testing found 13 of 37 reader rules untested, every one an occurrence-token or tile rule.

## Is the rate falling?

No. Entries by date: 2, 1, 2, 1, then 80 on 11-05, 34 on 11-06 before noon, three more writer defects today with agents still running. Review intensity rose too, so part of this is looking harder, but the per-mechanism yield is steady: each mechanism added yields five to eight entries within a day, and format 7's writer had 55 entries at 36 hours old. Prediction: while the mechanism count stays at today's level, adversarial review will keep finding at this rate; reviews will plateau only when the reviewers tire, not when the format is right.

## Root cause

The format makes four promises it cannot keep:

- **"Every haplotype through a window against the reference, as facts."** False wherever the reference passes a node twice. ADR 0001, `stay`, pass counts, `revisited`, `@k`/`:k` and "placement choice" are all attempts to state a non-fact precisely. The project already conceded this on 11-05 (hs1 from the CHM13-referenced graph; open-problems: "no file layout makes a complete view both small and faithful") but kept shipping the machinery. rGFA's premise is one origin per segment; that premise, not a nearest-pass rule, is what makes a linear projection honest.
- **"A window finds everything about it in a bounded number of range requests."** Tiling cuts a path at tile edges, so a departure between pieces needs a record, the record's own steps need `ownTiles` and an attach fetch (p90 1.3 MB to 27 MB, up to 112 requests on pggb), and a bubble across a tile edge becomes a record while the same bubble inside a tile is a route (entry 96). The tile is a compression container that became the addressing model.
- **"Every line states its true stretch."** Impossible for things of length zero, so the spec invents coordinates (`[p, p+1)`, `[|S|-1, |S|)`, `[0, 0)` rules): the fake coordinates the owner's own rule forbids.
- **"The tools make no variant calls."** Forms fold haplotypes into states; nine entries and a two-agent arbitration followed.

## What to change, ranked

- **Require `revisited = 0`.** Build walk files only on the graph's own reference; refuse others, and leave pggb projection to an external tool (`odgi untangle` output as input), as liftover is external to BED. Removes ADR 0001, `--stay`, `passes`/`leavePasses`/`rejoinPasses`, `revisited`, the occurrence tokens, claims C2/C53/C120 and the 12 untested token rules, and the chr9/chrY blow-ups.
- **Normalize input.** Drop 0 bp nodes from paths at read time (they carry no sequence), skip empty lines, refuse 0 bp sequences. Removes 11 entries' special rules and every invented coordinate.
- **Cut pieces only between steps adjacent on the reference.** Then no departure lies between pieces: a jump is a piece with no interior reference step, its own steps travel with it, `ownTiles` and attach fetches vanish, the pyramid remains only as binning for wide pieces (the UCSC/Tabix idea, principled). One row kind instead of walk + departure + abridged-per-piece.
- **Move forms out of the release gate** into an experimental package with no claims.
- **Process.** Formats were rewritten whole by one agent (514 lines in one commit) with checks written from the code. Change to: a fixed fixture corpus (MC chr22, pggb chrY, CHM13 chr9/14, fuzz with two references, holes, 0 bp) before any mechanism; no mechanism without a failing real-data test first; checks written from the spec by a different agent, mutation score as a gate; diff test names before replacing a file; a cap on claim count as a design smell.