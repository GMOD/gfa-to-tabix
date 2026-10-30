Walk-file vs node/link-index graph track: what each reader draws per window

  In:  a gfa-to-tabix format 2 anchored index (X.graph.bed.gz) and a walk file
       (X.<ref sample>.walks.bed.gz, format 5) built from the same GFA, the
       reference sequence name, and a window list
  Out: out/NAME.jsonl (one record per window and haplotype mode),
       out/NAME.chunks.json (walk-file chunks holding each class 2/3 node),
       out/NAME.refvisits.json (reference nodes visited on each window, and
       those the 8-haplotype walk cut leaves undrawn),
       out/NAME.windows.tsv and the summary that analyze.py prints

Needs node 24, tabix and bgzip on PATH, python3, and @jbrowse/graph-walks
built in a graph-walks checkout beside this repository (esm/; override
with GRAPH_WALKS=).

Run (CHM13-anchored pair: swap the paths, the reference sequence and the
window list; windows.py takes NAME:LO-HI:COUNT specs in Mb as well as the
chr22/chrY presets):

  cd docs/placement/scripts
  D=<directory holding the index and walk files>
  python3 windows.py chr22 > windows-chr22.tsv
  python3 windows.py chrY > windows-chrY.tsv
  ./run.sh mc22 $D/mc.f2.graph.bed.gz $D/mc22walks.GRCh38.walks.bed.gz 'GRCh38#0#chr22' windows-chr22.tsv
  ./run.sh pggb22 $D/pggb.f2.graph.bed.gz $D/pggb-chr22.GRCh38.walks.bed.gz 'GRCh38#0#chr22' windows-chr22.tsv
  ./run.sh pggbY $D/pggb-chrY.graph.bed.gz $D/pggb-chrY.GRCh38.walks.bed.gz 'GRCh38#0#chrY' windows-chrY.tsv
  # per graph G with walk file W and reference sequence R:
  node chunkmap.mjs out/G.jsonl W out/G.chunks.json
  H=$(python3 -c "import json; print(','.join(json.loads(open('out/G.jsonl').readline())['meta']['haps8']))")
  node --max-old-space-size=8000 refvisits.mjs W R windows-X.tsv out/G.refvisits.json $H
  python3 analyze.py mc22 pggb22 pggbY > out/summary.txt

run.sh takes an optional 6th argument, the modes (default hap8,hap8rows,all,allrows):
  hap8      the 8 hosted HPRC defaultHaplotypes that the file has, topped up
            from its #haplotype header; graph layout (step budget applies)
  hap8rows  the same 8, walk-rows layout (no step budget; abridged rows of
            the 8 read in full)
  all       every haplotype, graph layout
  allrows   every haplotype, walk-rows layout
crux.mjs --haps takes hosted, first8 or a comma list.

One window by hand: node diag.mjs INDEX WALKS REFSEQ START END [HAPS]
lists the index links from a drawn node to an index-only one and which walks
in the chunks read step across them.

CHM13-anchored pggb chr22 (windows from scripts/walks-truth-regions.tsv):
  python3 windows.py arm:0-51:50 LCR22A:18.5-19.3:10 LCR22B-D:20.6-22.0:10 \
    pericentromeric:15.0-17.4:10 p-arm:0-14.5:10 control:29.4-33.4:10 > windows-chr22-chm13.tsv
  ./run.sh pggb22chm13 $D/pggb-chr22-chm13.graph.bed.gz $D/pggb-chr22.CHM13.walks.bed.gz 'CHM13#0#chr22' windows-chr22-chm13.tsv
  (then chunkmap.mjs and refvisits.mjs as above, with CHM13#0#chr22)

Follow-ups on lost class 3 nodes:
  node lostcheck.mjs G W R     per hap8 window and selected haplotype with
                               skip/none losses: where the walk file holds
                               the lost nodes and how the haplotype crosses
                               the window -> out/G.lostcheck.json
  node passcount.mjs W R out/G.passcount.json NAME:LO-HI ...
                               paths per chunk that cross it with no piece
                               there (rows a "passes this chunk" row kind
                               would add), against the skip rows it has
                               The committed passcount.txt used the strata
                               above as NAME:LO-HI, and on chrY also TSPY,
                               9 chunks around 9.4 Mb

Results in docs/placement/:
  summary-grch38.txt   python3 analyze.py mc22 pggb22 pggbY
  summary-chm13.txt    python3 analyze.py pggb22chm13
  *.windows.tsv.gz     out/G.windows.tsv, gzipped
  passcount.txt        out/G.passcount.txt for mc22, pggb22 and pggbY
