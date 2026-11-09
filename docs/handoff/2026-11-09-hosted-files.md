# Handoff, 2026-11-09: the hosted files measured, and the rebuild run genome-wide

The user asked whether the two representations make sense, express
arbitrary graphs, keep fetches small and state haplotype walks
accurately, with the plugin and the other readers in mind. The answer on
the hosted graphs is yes, and no format change came out of it. What was
measured, each with its data:

- **Fetch cost, walk files:** `walks-truth.py cost` on both hosted files,
  and cuts by graph-walks 6.2 from the hosted URLs
  ([writer/README.md](../walks-container/writer/README.md#the-hosted-files-against-their-gfas-2026-11-09))
- **Fetch cost, node and link index:** the widths of the intervals the
  hosted HPRC SV index files its rows under
  ([widths](../placement/hprc-sv-interval-widths.txt)); the bytes a window
  reads through @gmod/tabix were measured in the session and not
  committed, so no doc states them
- **Accuracy:** a sample of each hosted file's paths rebuilt step for
  step against a GFA, 0 wrong, and the full run below
- **Arbitrary graphs:** eleven hand-made graphs outside the fuzz
  generator (a self loop and hairpin, a reversed reference, a tandem
  collapse, a duplication, two reference sequences with paths between
  them, an island, a path touching the reference at one node, CRLF and P
  lines without PanSN names, ids 0, 007 and 2147483646, repeated L lines,
  a diploid reference) through the writer, verify7, claims7, audit7, the
  rebuild and `graph-walks-rebuild.mjs`; all pass, and the index returns
  every node and link on a path. A twelfth, with minigraph's `s1` names,
  `--walks` refuses as documented. They are not fixtures: the one thing
  they found is the open problem below

## What changed in the repo

- `scripts/walks-truth.py rebuild` reads a gzip or plain GFA as a stream
  and parses only its shard's lines, so it runs on a genome;
  `docs/walks-container/writer/scripts/genome-check.sh` runs every shard
- [Open problems](../open-problems.md#a-path-that-crosses-onto-another-reference-sequence)
  has the one gap found: a path that steps onto another sequence of the
  reference reads as ending
- walks-format.md's sentence on handle width, its hosted-file line, the
  gbz comparison, the crate's description and index-format.md's sentence
  on wide intervals are corrected ([issues log](../issues-log.md))

## Running on ada when this was written

`ada:~/work/analysis1109/full.sh` rebuilds every path of both hosted
files, 24 shards each, 3 at once: GRCh38 against HPRC's published
`~/hprc_multiway/build/hprc-v2.1-mc-grch38.gfa.gz`, then CHM13 against
`vg convert -f` of `~/work/arb-format-opus/in/chm13.gbz`, which it writes
as a 101 GB `chm13.gfa.gz` and removes when CHM13 passes.

- `full.done` appears at the end and says `grch38 PASSED chm13 PASSED`
  or names a FAILED one; `full/grch38.rebuild.txt` and
  `full/chm13.rebuild.txt` hold each shard's last line
- When it has passed, copy those two files to
  `docs/walks-container/writer/results/genome-check.{grch38,chm13}.rebuild.txt`
  and add the result to the writer README's section for this day
- To stop it, kill `full.sh` and its `python3` children by PID; a later
  run of `genome-check.sh` with the same prefix skips the shards that
  passed
- The checker it runs, copied to `~/work/analysis1109/repo/`, is this
  commit's before two later edits that change nothing it reads on these
  graphs: lengths held in 64 bits, for a segment of 2^32 − 1 bp, and a P
  line with an empty steps field read as no steps

## Left as they are

- **bandage-core already merges unbranching runs** for layout
  (`src/layout/mergeRuns.ts`), so a cut's many short nodes, which the
  kept haplotypes alone would not need, are not a layout cost
- **The moved component's rows** in the hosted SV index are filed under
  haplotype contigs no window names
  ([stubs](../open-problems.md#stubs-for-a-component-over---max-component))
- **Walk views have no zoomed-out tier**
  ([open problems](../open-problems.md#walk-files-in-place-of-the-index-for-path-graphs))
