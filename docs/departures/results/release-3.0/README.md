# Release check, gfa-to-tabix 3.0 (2026-11-05)

- `rel3.sh` built MC chr22 and pggb chrY on ada with the release writer
  (main at cc797cc) and audited both with `audit6.py`: every record
  matched (24,639 and 425,040), every "must be 0" line 0, including the
  abridged rows' stretch, detail record, ends by position and strand,
  and every path base in one piece's stretch or one record's own bp
  (`*.audit.txt`, `*.build.log`, `sizes.txt`)
- `mc22.unexpanded-vs-expanded.txt`: graph-walks 5 (dd779cc) `formsCut`
  on that MC chr22 file with every budget lifted, abridged pieces read
  unexpanded against expanded, on seven windows: every one of 463
  haplotypes has the same net and coverage
