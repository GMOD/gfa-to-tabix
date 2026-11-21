Node-cap study: layout and draw time against node count in BandageJS and the JBrowse graph plugin

  In:  the hosted HPRC v2.1 MC GRCh38 format 8 walk file (a local copy with the same bytes and .idx), a BandageJS
       clone and a jbrowse-plugin-graphgenomeviewer clone with bandagejs.diff and plugin.diff applied, a jbrowse-web
       5.0.0-beta.20 build (the plugin's e2e host), Chrome 154 and puppeteer 25 from the plugin's node_modules
  Out: ../cut.tsv (graph-walks' cut of each window, three runs), ../reader-runs.jsonl (every reader run as measured),
       ../reader-runs.tsv, ../reader-points.tsv, ../cut-points.tsv and ../summary.txt (summarize.py's)

Files:
  windows.txt      the windows, chr:start:width with a 0-based start
  cut.mjs          times graph-walks' cutRegion of each window in Node, 4 haplotypes, budgets and node limit lifted
  run-cut.sh       cut.mjs over windows.txt, three runs, nice -n 10 in a 16 GB no-swap scope
  serve.mjs        a static server answering range requests with CORS, as S3 does
  urls.mjs         the address each reader opens for a window and layout
  measure.mjs      one run in a fresh headless Chrome: waits for the first paint after the layout, zooms and pans once
  drive.mjs        every run: layouts x windows x 3 runs x both readers, each once the 1-minute load is under 4
  run-readers.sh   serves the builds and the walk file, then drive.mjs
  summarize.py     the TSVs and the summary the report quotes
  bandagejs.diff   BandageJS bfa3c0e0 as measured: performance marks, and the cut's budgets and node limit lifted
  plugin.diff      plugin 0a82b467 (10.4.0) as measured: performance marks, and the cut's budgets lifted

Set-up (on ada; N is any directory):
  git clone https://github.com/GMOD/BandageJS.git $N/bjs && git -C $N/bjs apply bandagejs.diff
  git clone https://github.com/GMOD/jbrowse-plugin-graphgenomeviewer.git $N/plugin && git -C $N/plugin apply plugin.diff
  (cd $N/bjs && pnpm install && node build.mjs); (cd $N/plugin && pnpm install && pnpm build)
  npx @jbrowse/cli create $N/jbrowse --url <jbrowse-web-v5.0.0-beta.20.zip>; ln -s ../plugin/dist $N/jbrowse/plugin
  write $N/jbrowse/config.json (an hg38 assembly from chr6 and chr22 sizes, one GraphTrack hprc_v2_1_walks whose
    RgfaTabixAdapter walksUri is http://127.0.0.1:47811/data/hprc-v2.1-mc-grch38-f8.GRCh38) and
    $N/jbrowse/hg38.chrom.sizes
  link the walk file and its .idx into $N/data/
  mkdir $N/cut && (cd $N/cut && pnpm add @jbrowse/graph-walks@9.0.0)

Run:
  GRAPH_WALKS_DIR=$N/cut ./run-cut.sh ../cut.tsv
  NODECAP=$N ./run-readers.sh ../reader-runs.jsonl
  python3 summarize.py ../reader-runs.jsonl ../cut.tsv .. > ../summary.txt
