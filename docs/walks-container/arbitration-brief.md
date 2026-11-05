# Arbitration brief: decide the walks file's container, for an ADR

You are one of two independent arbiters. The other works separately with the
same brief; you will not see its work. Together you settle, by measurement, a
decision that will be written as a firm ADR in gfa-to-tabix (docs/adr/0010).
The user wants a hard decision, not options: end with one design.

## Background

Read the four reviews first (each `proposal.md`, scripts and data beside it):
/tmp/claude-1001/-home-cdiesh-src-gfa-to-tabix/95217c34-cd76-4f06-8705-ae30877df61b/scratchpad/format-review/{history,native,cleansheet,reader}/
and their shared brief, brief.md, in the same directory (it has the
requirements, data locations, ada etiquette and repo pointers). Treat the
reviews' numbers as leads to re-measure, not facts: their baselines for the
same shipped file disagree (87 to 98 KB for a 1 kb window) because each built
its own harness.

What the reviews agree on:
- Format 6 files every row of a 64 kb chunk at `seq cs cs+1`, adopted in
  commit 3953bb1 with no measurement. A plain `tabix file region` returns
  nothing on it
- The excess bytes for small windows come from the "chunk before" lookback,
  @gmod/tabix reading past a chunk's end (chunks don't start on BGZF block
  boundaries), and 64 kb granularity; on pggb, from departure records, which
  graph-walks also over-reads by sizing from the file-wide maxnode
- Real-span filing is a wash on bytes with a matched index (CSI min_shift 16,
  or 16 kb chunks under TBI), worse under TBI at 64 kb; it buys honesty only

The user's position, in their words: "whatever we do, we need to make this a
firm hard adr decision. if you think a offset table would be 'cleaner' we could
consider it. the 'fake refname with 0 1' might bother me if we dont do it".
Earlier: "sometimes think like a bgzf-filehandle+fasta index type format, that
is more general and not strictly coordinate based, could be better". And:
"im really trying to get the right format not some hacky system". Weigh
honesty and simplicity of the format, not just bytes.

## Judge like Heng Li

The user asked to think about this "as if you are heng li. he is an expert at
getting the right design for sam, paf, and many formats". Judge every
candidate, format 6 included, against the design habits of SAM, PAF, GAF,
rGFA, BED and `samtools faidx`, alongside bytes:
- Each line means something on its own: a reader (or `grep` and `awk`) can
  interpret one row without state from other rows. Count every cross-row
  dependency a candidate has (route deltas chained across rows, walk rows
  naming routes by chunk-local index, pieces joined across chunks) and say
  which ones earn their keep with a number
- Columns mean what they say: coordinates are real coordinates; extras go in
  optional `TAG:TYPE:VALUE` fields a reader may ignore
- Few record types and few special mechanisms. Count them (row kinds, sibling
  sequences, header-line kinds, lookback rules, occurrence tokens) per
  candidate
- Let gzip remove redundancy; add delta encoding or cross-references only
  where measurement shows gzip can't. Measure at least one variant with plain
  absolute node ids (no deltas) to price that choice
- Lean on standard tools (bgzip, tabix, samtools faidx-style `.fai`/`.gzi`)
- Efficiency still matters at HPRC scale: simplicity that costs several times
  the bytes per window loses

The user also asked whether the detail tier's duplication (cleansheet: 27 of
chr22's 59 MB is per-path detail records repeating routes) matters. Answer it
under this lens: is a second tier needed at all, and if so, is duplication or
cross-reference the simpler cost?

## Candidates (build and measure every one)

- **F6p, patched format 6 (baseline):** today's rows and 1 bp key, with the
  no-format-change fixes: BGZF block flushed at each chunk start, @gmod/tabix
  stopping at the chunk's end (history's patched chunk.js), the narrower
  lookback rule, departure/attach reads sized from `#long` not maxnode
- **T, honest Tabix:** same rows filed at `cs cs+chunk`, the index that makes
  that free (CSI min_shift = log2(chunk), or 16 kb chunks under TBI: pick the
  better and say why), block-aligned chunks
- **O, offset table:** the same rows in a BGZF file with no fake coordinates,
  plus a small chunk index in the spirit of `.fai` + `.gzi`: per chunk its
  sequence, chunk start, and byte offset/length (state whether uncompressed
  offsets with a standard `.gzi`, so `bgzip -b off -s len` extracts a chunk
  with stock tools, or BGZF virtual offsets; prefer standard tooling).
  Decide where departure records live: they have real spans, so they may
  belong in an honest Tabix file, in the same chunk store, or elsewhere;
  measure your choice
- **N, native site rows:** native's interval-native design (its prototype
  files and scripts are in native/; native may still be finishing one count,
  the repeat-visit ambiguity on pggb)
- **S, the design Heng Li would write:** your own simplest design that meets
  the requirements under the lens above (self-contained lines, true
  coordinates or an honest chunk index, minimal record kinds), measured like
  the rest. It may coincide with one of the above; say so if it does

## Method

- One harness for all candidates: the same seeded windows (at least 300 per
  size) at 1 kb, 10 kb, 100 kb and 1 Mb on MC chr22 (ada
  `~/work/rel3/mc22.GRCh38.walks.bed.gz`, GFA `~/work/mc/chr22.gfa`) and
  pggb chrY (`~/work/pggbY.GRCh38.walks.bed.gz`)
- Count bytes the way a browser pays them: HTTP range requests against a
  local static server that logs every range, including index fetches and
  the header; report requests, bytes (median/p90/p99), round trips in
  sequence, and the bytes the window actually uses
- Correctness: for each candidate, rebuild every haplotype's path through a
  sample of windows and check it equals format 6's (graph-walks' cut, or the
  reviews' verify scripts)
- Also report file and index size, what stock tools can do with the file
  (tabix, bgzip, zcat, grep), writer and reader complexity (rough lines and
  concepts a reader must know), and failure modes (long nodes, repeats,
  inversions, abridged chunks)

## Deliverable

`OUTDIR/decision.md` (bullet lists, not numbered):
- The decision, stated as an ADR would: "The walks file is ... because ..."
- The measurement table across candidates, with method
- Why each other candidate loses, with its number
- Consequences: what changes in gfa-to-tabix, graph-walks, the spec, hosted
  data; format 6 patch or format 7
- Anything you found broken along the way (for the issues log)

Your final reply: the decision, the table, and one line per losing candidate.

## Rules

- Do not edit the gfa-to-tabix or graph-walks checkouts; prototype in your own
  `git worktree` under OUTDIR or in scratch copies
- Keep local runs small: several agents share this machine; don't run full
  test suites or builds of the main checkout
- ada is shared with other users: work under `~/work/arb-<your name>/`, cap
  memory with `systemd-run --user --scope -p MemoryMax=60G -p MemorySwapMax=0`,
  never touch the running genome-wide build or its files, and never
  `pkill -f` over ssh
