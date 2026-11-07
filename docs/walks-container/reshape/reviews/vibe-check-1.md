**Verdict: the design is converging; the project is not.** The core idea (file per reference, 64 kb tiles, per-tile dictionary, unit table) has been independently confirmed three times today and has real numbers behind it. But the project is 30 days old (first commit 2026-10-07), has produced seven walk formats in 24 days (2 on 10-12, 3 on 10-16, 4 and 5 on 10-20, 6 on 11-04, 7 on 11-05), and the spike running now is format 8 in all but name. Format 6 was released as 3.0.0 on 11-05 and superseded the same night. Users still read format 5 through plugin 8.6.0 and graph-walks 4; nothing built since has been seen by anyone outside these repos.

**Direction evidence**

- Issues log: 124 entries, 118 of them on 11-05 and 11-06. The design review's count is right that the per-mechanism yield is flat: each mechanism added (ownTiles on 11-05 yielded six entries in 24 h) produces five to eight findings within a day. Reviews are finding at the rate reviewers look, not at a rate that is falling.
- Commit rate: 107 commits in two days across both repos, 88 unpushed. The spec carries 143 claim IDs. A clean-room reader written from the spec found the writer disagreeing with it on strand; mutants found checks that copy the code. These are symptoms of a format too large to hold in one head, which the henli-fundamental review states plainly.
- The consumer ports have been "next, in order" since the 11-05 handoff and have been displaced four times: by format 7, by the claims audit, by figures, and now by a twelve-reviewer bug hunt and a reshape.

**Healthy**

- The core is measured, and all three design reviews independently say keep it. That is rare and worth protecting.
- The reader fixes landed with 37/37 mutants killed and tests that fail on the old code. The issues-log discipline (source, fix, guard) is real, and today's agent rules enforce "prove the check can fail".
- The reshape is the right cut: it deletes `--stay`, `@k`/`:k`, pass fields and most departure records, which on MC changes zero bytes and on pggb removes machinery describing placements that are right 36% of the time.

**Warning signs**

- Three formats built, zero shipped to a user since format 5. There is no external friction. "No backcompat" plus "agent decides" plus this much agent throughput means the format rewrites itself whenever a review suggests it can.
- Review effort now exceeds build effort. ADR 0010 was "measured by four reviews, two arbiters, a cross-examination and a prior-art review." Today added twelve more reports. The format most of that validated is about to change.
- Worktrees: the handoff lists nine to delete. Two artifact accounts. A handoff file dated 10-31 is the live state document at 440+ lines.

**Stop**

- Fixing format 7 writer defects on degenerate inputs (NUL bytes, `--tile 2^55`, 0 bp reference W lines) while the reshape may delete the code they live in. Drop 0 bp nodes at read time and move on.
- Any further review round until a consumer has run against a frozen format.
- Forms in the release gate.

**Start**

- A written freeze rule: no format bump until the plugin and bandage-core have shipped against the current one and a hosted file has been viewed. Put it in ADR 0011 with the reshape.
- Refuse `revisited > 0` instead of placing it. One honest limitation beats five mechanisms.

**Next week instead of the plan:** decide the reshape by the ada numbers in one sitting, build it once from the fixed fixture corpus, port the plugin and bandage-core yourself rather than fanning out, release, host, push. Nothing else.

**The sentence:** nobody outside these two repos has used anything built since format 5, and until the plugin ships against a frozen format, every measured ADR and every logged finding is rehearsal.