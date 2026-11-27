---
name: hosted-views-that-draw-nothing
description: Hosted views that open with no readable picture at well-known loci, from the 27 November audit; AMY1 on genomes.jbrowse.org never draws its default graph and refuses 7 of 8 rows, BandageJS opens MHC class II and KIR blank behind "Draw anyway", and its C4 tube map is one thin line.
metadata:
  repo: jb2hubs, BandageJS
---

# Hosted views that draw nothing readable

Evidence: `~/src/walks8-evidence/sessions-20261127/hosted-audit/`.

- **genomes.jbrowse.org:** AMY1's default graph was absent after 45 s and 7 of its 8 rows answer "This stretch of the graph is too large to draw" (`hubs/amy1__default.png`); HLA refuses 1 of 6 rows, KIR 2 of 7.
- **BandageJS:** MHC class II (90 kb, 71,494 nodes) and KIR (143 kb, 29,775 nodes) with 8 samples open on a notice that the region is over the 20,000 nodes drawn by default (`bjs/B-MHC2.png`). True, and nothing is shown.
- **BandageJS tube map** at C4 with 8 samples is one thin line (`bjs/B-C4-tubemap.png`).
- **Label clutter:** BandageJS puts 12 to 15 size labels on one loop at GSTM1 and C4 (`bjs/B-GSTM1.png`); the plugin drops 2 of 7 size labels at the chr6:157,774,262 VNTR.
- **Plugin hover wording:** "(rank 0)", "1,723 reference nodes folded into it", "and 1 more threads", raw node ids, "depth 9.0".
- **Not shot:** 15 of 36 planned BandageJS views; the plugin's lanes and rGFA views were not judged.
