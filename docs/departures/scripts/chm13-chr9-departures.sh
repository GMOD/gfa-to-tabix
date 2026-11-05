#!/usr/bin/env bash
# Ran on ada against the genome-wide format 6 build of 2026-11-04: the
# CHM13 file's departure rows by Mb of chr9, its chr9 records with their
# stretch lengths and kinds, and the GRCh38 file's rows by sequence. The
# outputs are in results/minimal/genome/
set -uo pipefail
cd ~/work/rebuild/genome
F=hprc-v2.1-mc-grch38-f6.CHM13.walks.bed.gz
G=hprc-v2.1-mc-grch38-f6.GRCh38.walks.bed.gz
# rows per Mb of CHM13 chr9, by row start
tabix $F "CHM13#0#chr9~departure" | awk -F"\t" '{h[int($2/1e6)]++} END {for (k in h) printf "%d\t%d\n", k, h[k]}' | sort -n > chr9.rows-per-mb.txt
# distinct records of CHM13 chr9, with their stretch and own bp
tabix $F "CHM13#0#chr9~departure" | cut -f4- | sort -u -S 12G --parallel=8 > chr9.records.txt
wc -l chr9.records.txt > chr9.records.count.txt
# records per Mb of the leave breakpoint, stretch length by log10 bucket, own bp 0 share, kinds
awk -F"\t" '{
  leave=$6; rejoin=$8; ls=$7; rs=$9; own=$4
  rec[int(leave/1e6)]++
  s = leave > rejoin ? leave - rejoin : rejoin - leave
  b = s == 0 ? 0 : int(log(s)/log(10)) + 1
  st[b]++
  if (own == 0) zero++
  if (ls != rs) kind["switch"]++
  else if (leave == rejoin) kind["adjacent"]++
  else if ((ls == "+" && rejoin < leave) || (ls == "-" && rejoin > leave)) kind["back"]++
  else kind["forward"]++
  n++
}
END {
  print "# records per Mb of the leave breakpoint"
  for (k in rec) printf "%d\t%d\n", k, rec[k] | "sort -n"
  close("sort -n")
  print "# stretch length, log10 bucket (0: 0 bp, 1: 1-9, 2: 10-99 ...)"
  for (k in st) printf "%d\t%d\n", k, st[k] | "sort -n"
  close("sort -n")
  printf "# own bp 0: %d of %d\n", zero, n
  for (k in kind) printf "# kind %s: %d\n", k, kind[k]
}' chr9.records.txt > chr9.records.summary.txt
# GRCh38 rows by sequence
for s in $(tabix -l $G | grep "~departure"); do printf "%s\t%s\n" "$s" "$(tabix $G "$s" | wc -l)"; done > grch38.departure-rows-by-seq.txt
echo done > chr9.done
