# The hosted genome-wide files, gfa-to-tabix 3.0.0 (2026-11-05)

- Inputs: HPRC v2.1's `hprc-v2.1-mc-grch38.gbz` and
  `hprc-v2.1-mc-chm13.gbz` from
  `s3://human-pangenomics/pangenomes/freeze/release2/minigraph-cactus/v2.1/`,
  checked byte-identical to the S3 objects by recomputing their multipart
  ETags (e63ecd53a3ac4680abf3327cd074ccf3-655 and
  37079e4ad21d6d6a87e091e2dfd2747c-735); converted by `vg convert -f`
  (vg version in `checksums.txt`)
- `genome3.sh` built each reference from its own graph,
  `--refs GRCh38` and `--refs CHM13`, with gfa-to-tabix 3.0.0
  (`version.txt`); `build-*.log` and `convert-*.log` give times and peaks
- `*.header.txt`: both files say `revisited:i:0`, each reference passing
  no node twice in its own graph
- `*.chr22.audit.txt`: chr22 of each audited by `audit6.py --seq`, every
  "must be 0" line 0 and every record matched
- `windows.txt`: a 64 kb window's departure read; CHM13 chr9 at 45 Mb
  reads 458 rows where the GRCh38 graph's CHM13 file read 1,680,736
- `checksums.txt`: the uploaded files' md5s, for checking the hosted copies
