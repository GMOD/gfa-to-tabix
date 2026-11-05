#!/usr/bin/env bash
# Ran on ada in ~/work/rebuild/genome against the genome-wide format 6 build
# of 2026-11-04. Writes, beside the files: each file's departure rows by
# sequence (chm13.departure-rows-by-seq.txt, grch38.departure-rows-by-seq.txt),
# the CHM13 file's rows by Mb of chr9 and chr14 (chr9.rows-per-mb.txt,
# chr14.rows-per-mb.txt) and by 64 kb over chr14's 13th Mb
# (chr14.rows-per-64kb.txt), its distinct chr9 records (chr9.records.txt,
# 100 MB, kept on ada) with their summary (chr9.records.summary.txt), its
# distinct chr14 records' count (chr14.records.count.txt), and what a 64 kb
# window's departure read returns at nine places (windows.txt). The repo
# holds the small outputs under results/minimal/genome/, with the file
# prefixed by its reference: CHM13.chr9.records.txt is the summary.
set -uo pipefail
cd ~/work/rebuild/genome
F=hprc-v2.1-mc-grch38-f6.CHM13.walks.bed.gz
G=hprc-v2.1-mc-grch38-f6.GRCh38.walks.bed.gz
rows_by_seq() {
  for s in $(tabix -l "$1" | grep "~departure"); do
    printf "%s\t%s\n" "$s" "$(tabix "$1" "$s" | wc -l)"
  done
}
rows_per_mb() {
  tabix $F "CHM13#0#$1~departure" |
    awk -F"\t" '{h[int($2/1e6)]++} END {for (k in h) printf "%d\t%d\n", k, h[k]}' |
    sort -n
}
[ -e chm13.departure-rows-by-seq.txt ] || rows_by_seq $F > chm13.departure-rows-by-seq.txt
[ -e grch38.departure-rows-by-seq.txt ] || rows_by_seq $G > grch38.departure-rows-by-seq.txt
[ -e chr9.rows-per-mb.txt ] || rows_per_mb chr9 > chr9.rows-per-mb.txt
[ -e chr14.rows-per-mb.txt ] || rows_per_mb chr14 > chr14.rows-per-mb.txt
[ -e chr14.rows-per-64kb.txt ] || tabix $F "CHM13#0#chr14~departure:13000000-14000000" |
  awk -F"\t" '{h[int($2/65536)*65536]++} END {for (k in h) printf "%d\t%d\n", k, h[k]}' |
  sort -n > chr14.rows-per-64kb.txt
[ -e chr14.records.count.txt ] || tabix $F "CHM13#0#chr14~departure" | cut -f4- | sort -u -S 4G | wc -l > chr14.records.count.txt
# distinct records of CHM13 chr9, with their stretch and own bp
if [ ! -e chr9.records.txt ]; then
  tabix $F "CHM13#0#chr9~departure" | cut -f4- | sort -u -S 12G --parallel=8 > chr9.records.txt
fi
wc -l chr9.records.txt > chr9.records.count.txt
# records per Mb of the leave breakpoint, stretch length by log10 bucket, own
# bp 0 share, kinds as walks-format.md derives them from the ends
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
# a 64 kb window's departure read: rows, text bytes, gzipped bytes
{
  printf "window\trows\ttext bytes\tgzipped bytes\n"
  for w in chr9:30000000 chr9:39000000 chr9:45000000 chr9:60000000 chr9:78000000 chr9:85000000 chr14:13000000 chr14:13500416 chr22:19000000; do
    s=${w#*:}; c=${w%:*}; e=$((s+65536))
    tabix $F "CHM13#0#$c~departure:$s-$e" > window.tmp
    printf "%s-%s\t%s\t%s\t%s\n" "$w" "$e" "$(wc -l < window.tmp)" "$(wc -c < window.tmp)" "$(gzip -c window.tmp | wc -c)"
  done
  rm -f window.tmp
} > windows.txt
echo done > chr9.done
