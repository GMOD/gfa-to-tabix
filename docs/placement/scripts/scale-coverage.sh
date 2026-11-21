#!/usr/bin/env bash
# The bp each haplotype's W lines cover (end - start, summed), real against
# synthetic (SYN...), GRCh38 and CHM13 left out: count, min, p10, median,
# p90, max. Run on scale-synth.py's largest GFA.
#   bash scale-coverage.sh synth/mc22.5000.gfa.gz
pigz -dc "$1" | awk -F'\t' '$1=="W" && $2!="GRCh38" && $2!="CHM13" {t[$2"#"$3]+=$6-$5}
  END {for (h in t) print (h ~ /^SYN/ ? "synthetic" : "real"), t[h]}' |
  sort -k1,1 -k2,2n |
  awk '{a[$1][++n[$1]]=$2}
    END {print "haplotypes\tcount\tmin\tp10\tmedian\tp90\tmax"
      for (k in a) {m=n[k]; print k"\t"m"\t"a[k][1]"\t"a[k][int(m*0.1)]"\t"a[k][int(m/2)]"\t"a[k][int(m*0.9)]"\t"a[k][m]}}'
