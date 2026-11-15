# pggb chrY, walk format 8, notes

ada dir: ~/work/blocks/pggbY (src = bundle of blocks-unit 1440c39; gw = snapshot of graph-walks-blocks 676a0dd)
writer: ~/work/blocks/src/target/release/gfa-to-tabix (e3e49de; src/ identical to 1440c39)
GFA: ~/work/arb-format-opus/in/pggbY.gfa (1053 P lines; GRCh38#0#chrY, GRCh38#0#chrY_KI270740v1_random, CHM13#0#chrY)

## Builds
- GRCh38: 98.4 s, 6,888,408 KB peak, 193,514,603 B (+210 B idx); 3,245,676 lines, 1,518 units
  (399 tile, 424 departures, 684 detail, 11 blocks). format 7 release build was 187,082,886 B, 3,132,876 lines, 1,507 units
- CHM13: 134.6 s, 3,929,340 KB peak, 188,280,064 B; 11,104,925 lines, 4,001 units (559/819/2566/57)

## Stats: see stats.GRCh38.json, stats.CHM13.json

## Results (all on ada under ~/work/blocks/pggbY)
- checkers: verify7/expand7/claims7/audit7(--gfa; CHM13 in 2 shards)/spec8/rebuild(24 shards) pass on both files: *.out, *.time, *.rc
- windows: win1.GRCh38.log, win2-5.GRCh38.log, win.CHM13.log (all haplotypes, equality), four.*.log (4 haplotypes, default budgets)
- once-passed-node.tsv: the drawing check's rows for node 408455, which GRCh38 passes once at 9,394,014 and seven haplotypes walk inside the TSPY copy near 9,482,842, its link drawn as no 88.8 kb skip (bandage-core drawcheck, window Y-9.3M)
- stay: stay0.GRCh38.walks.gz, staydiff.out (1,785,011 steps moved, 0.36%; pieces 618,112 -> 471,098)
- fixture coverage: fixcov/*.json (maxK 7, passes 11, abridged/tile 51, bin lines 29)
- harness fault reduced: tiny/revref.gfa (reference walking 1-,2-,4-; link-missing in both cuts)
- by-design difference: 20.15M window, HG00642 1 bp step on node 195169 (17 passes) off this tile's R; loaded keeps it at 20,055,206
