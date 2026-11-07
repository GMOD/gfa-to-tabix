I traced eight walk formats in 30 days, and format 8 is mostly the next symptom: it trims an over-built mechanism but does nothing about how this project decides formats. That is my verdict.

## History

| Format | Trigger | Added / removed | Driven by | Broke within 1–2 days |
|---|---|---|---|---|
| 1 (10-08) | first build | pieces filed under chunks, 3 files | none | 10-11 handoff asks for a smaller format |
| 2 (10-12, hosted) | size on chr22 | one file per reference; ref, route and walk rows | chr22 measurements | readers can't tell the bp between a contig's W lines |
| 3 (10-16, hosted) | that gap | ng/nr/pg/pr tags | none | pggb chr22 makes 95.3 M rows (1.65 GB) (ADR 0001) |
| 4 (10-19) | pggb repeats | stay, reader rule 3 | walks-truth.py | 225 CHM13 windows over 8 MB (ADR 0003); pggb satellite windows up to 166 MB (ADR 0004) |
| 5 (10-20, hosted) | pggb satellites | abridged and detail tier, skip rows | ADR 0004 | the user (10-30): skipped stretches labelled "deletion" |
| 6 (11-04, never released) | that | departure records, `@k`; removed skip rows and pv/nx/ng/nr | prototype, 6 reviews, ADR 0009 amended 5 times | a 10-08 fake key nobody measured: plain tabix finds nothing in 98 of 100 windows (ADR 0010 Context) |
| 7 (11-05, never released) | that | units, unit table, `ownTiles`; removed Tabix | 4 reviews, 2 arbiters | `ownTiles` gave 6 log entries in 24 h; 15 of 115 claims false (reports/henli-fundamental.md) |
| 8 (11-06) | that review | R1, R3, 0 bp drop | 1 spike, 2 deciders | — |

## Root causes, ranked

**1. Nothing outside the agents has been in the loop since format 5.**
- Formats 2–5 were hosted, and each was triggered by real data.
- Formats 6, 7 and 8 never reached a user.
- Of 124 issues-log entries, one comes from the user and 118 are dated 11-05 or 11-06 (`docs/issues-log.md`).
- Henli-fundamental measured five to eight findings per mechanism within a day, at a steady rate. Redesigns driven by reviews therefore never converge; they stop only when the reviewers tire.

**2. Most of the work went to a graph nobody hosts.**
- ADRs 0001, 0003, 0004, 0005, 0006, 0008, 0009's copy names and 0011 are all triggered or measured on pggb, or on CHM13 repeats.
- Every hosted walk file is MC (`walks-format.md:871`). Both deciders checked: "no pggb walk file exists".
- On MC, those mechanisms do nothing (`out/deps.base.mc22.json`: 0 copies named, 0 records ending on a revisited node).
- So a problem with no fixed coordinate, collapsed repeats projected onto GRCh38, drove a month of design for zero users.

**3. One session briefs the proposal, the measurement and the verdict, then accepts it the same night.**
- The proposal's brief (`recover/henli-problem.brief.md`) forbade ada and planted a wrong number ("183 KB of it the table"). The proposal repeated it, and the spike later refuted it (`reshape/report.md`, R3).
- The spike's brief names henli-problem.md as "the proposal you're measuring" and spells out R1's change word for word (`subagents/agent-aa499fcb8cd1e30c1.jsonl`, first message).
- The two "independent" deciders received byte-identical briefs (I diffed them):
  - the same "judge it the way Heng Li would" persona as the proposal
  - a "What matters" list of B's numbers
  - option C pre-labelled "loses pggb"
- The ADR was committed at 23:33:41, a few minutes after both deciders finished (their transcript files are stamped 23:32).
- ADR 0011's validity evidence is "passes verify7.py and claims7.py". Those checkers were being repaired that same day because their "0 failures" was partly bookkeeping (`agent-rules.md`).
- Bytes per window get measured carefully. Truth was measured once, as agreement with MC (35.9%), and is never re-run.

## Does format 8 address each cause?

- **Cause 1, partly.** The freeze is the first stop rule this project has had. But it is ADR text, and the same session has amended its ADRs within days before (0009 five times; 0010 the next day).
- **Cause 2, half.** It correctly removes the false coordinates and leaves MC rows unchanged. But it keeps pggb in scope with a picture one decider calls "nothing but spanning bars for 865 Mbp", and its own Consequences says alignment-based placement would be "a later format with its own ADR". That breaks the Convergence criterion ("nothing foreseeable forces a format 9") by its own text.
- **Cause 3, no.** Format 8 is a product of that process.

**What would make it the last format:**
- Record pggb collapsed-repeat usefulness as a non-goal in ADR 0011. Then format 9 becomes a response to a user asking for it, not a foreseen gap.
- Strike verify7/claims7 from the ADR's evidence until they have been shown to fail on a broken writer.
- Ship format 8 to the plugin and bandage-core before anything else.

## The smallest set of rules that would have prevented the churn

- **Ship gate.** No ADR for format N+1 until a consumer has read format N from a hosted file. After that, a format change needs an issues-log entry whose source is the user or a consumer working against that hosted file. This alone blocks formats 7 and 8.
- **Scope gate.** An ADR's trigger must be measured on a graph that is hosted or that a named user asked for. Anything else goes to open-problems.md. This blocks the pggb-driven mechanisms (stay, copy names, pass fields).
- **Split briefs.** The person or session that briefs a proposal does not brief its measurement. Deciders get the measurement and the acceptance criteria, not the proposal, and not the proposer's persona. At least one decider's brief comes from the owner.
- **Overnight acceptance.** An ADR is accepted no earlier than the next session, after the owner has read the decider briefs.
- **Checker evidence.** An ADR may cite a checker only alongside that checker's recorded failure on a broken writer.

The numbers above come from:
- `/home/cdiesh/src/gfa-to-tabix/docs/walks-container/reshape/out/`
- `/home/cdiesh/src/gfa-to-tabix/docs/issues-log.md`
- `/home/cdiesh/src/gfa-to-tabix/docs/adr/`
- `/home/cdiesh/work/review-2026-11-06/recover/henli-problem.brief.md`
- the spike and decider transcripts under `/home/cdiesh/.claude/projects/-home-cdiesh-src-gfa-to-tabix/817ce9cc-1377-498a-8e03-85283c80a331/subagents/`: `agent-aa499fcb8cd1e30c1.jsonl`, `agent-abe28f51670f569ee.jsonl` and `agent-ae0802511a3aee448.jsonl`