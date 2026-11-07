# Format 8 review: the shared brief

## The project
- **gfa-to-tabix** (/home/cdiesh/src/gfa-to-tabix, Rust) turns pangenome graphs into indexed "walk files". The inputs are GFA, HPRC Minigraph-Cactus (MC) and pggb.
- **What a walk file is for:** a genome browser fetches it by HTTP range requests from a static host, to draw which haplotypes take which path through a region of a reference such as GRCh38.
- **graph-walks** (/home/cdiesh/src/graph-walks, TypeScript) is the reader.
- **The consumers** are a JBrowse graph plugin and bandage-core. They still read format 5 (plugin 8.6.0, graph-walks 4). Formats 6 and 7 were built but never reached a user.

## What is proposed
[ADR 0011, since withdrawn to a proposal](../proposal.md) proposes format 8:
- **A step is placed only on a node its reference sequence passes once.** Steps on collapsed-repeat nodes become unplaced route interior. A haplotype crossing such a repeat shows as a departure record spanning it.
- **Detail entries move to a table of their own.**
- **0 bp segments are dropped on read.**
- **The format is then frozen** until the consumers ship.

ADR 0011 was accepted today, after one measurement spike and two reviewers who both chose it. The owner isn't convinced, and wants it checked seriously before anything is built.

## Read
- docs/adr/0011-placement-is-a-fact.md, and its data in docs/walks-container/reshape/
  - `report.md` is the spike's report
  - `out/results.txt` is the summary
  - `out/inspect.pggbY.jsonl` has concrete windows
  - `henli-*.md` are the two design reviews behind the proposal
- docs/adr/0010-walks-unit-table.md (format 7) and docs/walks-format.md (the format 7 spec, 143 claim IDs)
- docs/adr/0001-step-placement.md, 0008 and 0009, for the history of placement and departures
- docs/open-problems.md
- docs/issues-log.md: skim its Sources section and the last 60 entries
- `git log --format='%ad %s' --date=short` in both repos, for the history
- /home/cdiesh/work/review-2026-11-06/reports/: twelve reports from today's bug hunt, vibe checks and design reviews

## Acceptance criteria
The parent session wrote these for "a format that works". Judge format 8 against them, and attack any criterion you think is wrong or missing.
- **Truth.** Every position, stretch and departure a file states is a fact of the input graph. It is never the outcome of a writer's tie-break or heuristic, unless the file marks it as such.
- **Usefulness.** A biologist looking at a window gets a true and readable picture of which haplotypes do what there. The windows that matter are on MC, and on pggb including its collapsed repeats: chrY palindromes, LCR22, and acrocentric arms.
- **Cost.** Bytes per window and open cost are no worse than format 7 at the median and p90, on MC chr22 and pggb chrY.
- **Simplicity.** One person can hold the spec in their head. The reader is small. Every rule pays for itself in measured bytes or truth.
- **Convergence.** This is the last format before the consumers ship. Nothing foreseeable forces a format 9 within months.

## Rules
- **Read only.** Edit nothing in the repos.
- **Keep runs light on this machine (30 GB, shared).** Run python and the writer under `(ulimit -v 4000000; nice -n 10 <cmd>)`. Never open files over 100 MB here.
- **Use ada for anything big.** `ssh ada` has 125 GB. The inputs are in ~/work/arb-format-opus/in/ (mc22.gfa, pggbY.gfa), the format 7 and R1 outputs are in ~/work/reshape/out/, and the R1 writer branch is in ~/work/reshape/r1. Cap ada runs with `systemd-run --user --scope -q -p MemoryMax=60G -p MemorySwapMax=0`. Don't touch the `claims7.py --shard` processes running there.
- **Every number you cite points at a file.**
- **Give a verdict, not a survey.** The owner wants convergence. If format 8 is wrong, say what is right and why it would be the last change.
