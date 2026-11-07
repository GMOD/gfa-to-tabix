**Verdict: the direction is right, but this is churn, not progress. Ship.**

**Direction and status**
- The core design looks sound: one file per reference, 64 kb tiles, a route dictionary per tile, a unit table. ADR 0010 has real measurements behind it, and every design review, both Heng Li ones included, keeps it.
- The status is not healthy:
  - Seven walk formats in about four weeks, two of them in 48 hours.
  - Format 6 was ported to all five consumers and green on 11-05, then dropped within hours. Users are still on format 5 with plugin 8.6.0. Nothing hosted has changed since 10-30.
  - 64 commits in gfa-to-tabix and 24 in graph-walks are unpushed, spread across about ten worktrees on a box that was OOM-killed today.
  - The issues log is 1,490 lines. henli-fundamental is right that findings arrive at a steady rate per mechanism. Reviews find bugs because there are so many mechanisms, not because the work is sloppy.

**The decisions**
- **Refusing revisited references: right, and it shouldn't be an "option".** Both hosted targets have `revisited` = 0: GRCh38 in its own graph, and the CHM13 graph's 90.8 M nodes (issues-log, around line 348). The refusal costs no hosted file a byte, and it deletes machinery no hosted file uses. On pggb that machinery is mostly the placement rule talking: 97% of records end on a revisited node, and only 35.9% agree with MC within 10 kb. This needs no new measurement; decide it now.
- **Neighbour fields on walk rows: this one is wrong as framed.** It reverses ADR 0009's "Walk rows carry no neighbour tags", decided on 11-04 after a vibe check and two reviews. The two design reviews also disagree on the fix: henli-problem wants neighbour fields, henli-fundamental wants pieces cut only where reference steps are adjacent. Its "a few bytes" figure comes from maize with 25 haplotypes. ADR 0011 has to say what changed since 11-04. Only adopt it if attach fetches and `ownTiles` go away entirely and MC's p90 window bytes don't get worse. Otherwise leave it out.
- **"One table per sequence": the measurement may be testing a strawman.** ADR 0010 already reads one table per sequence; the 183 KB is chr1's own table. The measured gain is in format-design.md: detail entries are 37–67% of that table, and they could be split out. Check what the remote-host run is actually comparing.
- **Freeze, no more review rounds, the parent ports directly: all right, and overdue.** Add a deadline. Add a rule that a post-port finding goes into open-problems.md and does not trigger another bump.
- **"Stop hardening format-7 code": the running agents contradict it.**
  - The checker-repair agent is mostly hardening claims7.py, much of which the reshape deletes. Narrow it to the checks that survive (verify7's header and the unit/table checks), or stop it.
  - The writer agent's 0 bp normalisation and node-id memory fixes survive the reshape.
  - The duplicate-departure abort does not survive if departure records go.
- **Missing: push.** Push both mains, or at least a branch, today. Several issues-log "guards" point into `~/work/review-…/scratchpad` or `/tmp`, which makes them notes rather than guards. Move the repros the log relies on into the repo.

**Biggest risk nobody is watching**
Every check here is agents checking agents. The 143 claims, the mutants and the twelve reviews all measure whether the code matches the spec. None of them measures whether a biologist looking at LCR22A in JBrowse sees something true and useful. No human has looked at a format since 5, and nobody outside (HPRC, the pggb team) has looked at all. The pattern so far is that each review round re-decides the design, so the next review will find a reason to make format 9. The freeze is the only thing standing in the way, so it has to hold against reviews too.

**The one sentence**
Delete the pggb machinery, put the neighbour-field idea through a strict measurement or drop it, then put an MC file in front of a real user before anyone writes another review.