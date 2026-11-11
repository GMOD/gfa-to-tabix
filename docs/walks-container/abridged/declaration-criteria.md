# Criteria for how a file with `blocks` units declares itself, written 2026-11-11 before any decider ran

ADR 0012 settles the `blocks` unit. This question is only what a file
carrying it says in its header, and what readers of each generation do
with files of each generation. ADR 0012 as written (`format:i:8`,
graph-walks reading format 8 only) is the baseline. Every candidate is
judged on these, in this order:

- **Truth.** No reader states anything about an unloaded abridged piece
  that it doesn't already state today, on any file it accepts, and a
  reader that draws from blocks never meets an accepted file where it
  has to guess.
- **One way to read.** A reader that draws unloaded pieces from blocks
  has one code path for them. No second drawing path for files without
  blocks, and no compatibility shim.
- **After the freeze.** Once the paper cites the hosted file's URL and
  the tool's version, the format stops changing. What do readers
  released before then do with files written later, and with the file at
  the cited URL after a swap? Can a hosted swap ever leave a file and a
  released reader that refuse each other?
- **The spec's own rules.** The declaration follows what
  walks-format.md's Header section already says about another format and
  about later additions, or says which sentence it changes and why.
  Fewer mechanisms is better.
- **Cost of the change.** Releases, their coordination, and which
  consumers must move.
- **Burden.** A candidate must beat the baseline on the criteria above.
  When the evidence is mixed, the format number stays 7, as ADR 0011
  says of mixed evidence.
