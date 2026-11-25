---
name: ecoli-walk-file-per-strain
description: E. coli strains are haploid, so --walks --refs with all five strains writes one walk file per strain in that strain's own coordinates, with no code change; the E. coli demo has no walk track yet.
metadata:
  repo: jbrowse-components
---

# A walk file per E. coli strain

- `gfa-to-tabix <pggb.gfa> --walks --refs K12,Sakai,CFT073,NCTC86,IAI39`
  writes one file per strain, each holding every strain's walks in that
  strain's coordinates. The strains are haploid, so matching `--refs` by
  sample is already right
- jbrowse-components' `demos/ecoli_pangenome/config.json` has those five
  assemblies, each with its genes, and no walk track (checked 2026-11-25).
  Its graph comes from `scripts/build_ecoli_pangenome_graph.sh`, which runs
  pggb and `gfa-to-tabix build` but not `--walks`
- jb2hubs' test fixture `website/src/pangenome/fixtures/ecoli_pggb.K12.walks.gz`
  is a K12 walk file of a 54-segment piece of a pggb E. coli graph, so
  `--walks` already runs on this kind of graph
- Each file would open as a track on its strain's assembly, the way a
  diploid sample's haplotype can't yet
  (`../waiting-on-a-call/refs-take-one-haplotype.md`)
