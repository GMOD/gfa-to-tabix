#!/usr/bin/env bash
# Loose ends of the 2026-11-11 review: hosted index duplicate links, abridged
# spans on the hosted walk files, and the link dedup's cost on pggb chrY.
# Run from ~/work/loose1111 on ada, with repo/ a clone of this repository
# built in release mode. The 2026-11-11 run used an earlier copy of
# abridged-span.py that printed only its first line.
set -uo pipefail
cd ~/work/loose1111
exec > run.log 2>&1
echo "start $(date -Is) on $(hostname -s); $(git -C repo log --oneline -1)"
B=https://jbrowse.org/demos
(
for u in hprc/hprc-v2.1-mc-grch38.anchored hprc/hprc-v2.1-mc-grch38.fold10000 \
  arabidopsis_pangenome/arabidopsis-tair10-minigraph arabidopsis_pangenome/arabidopsis-tair10-minigraph.fold10000 \
  bovine_pangenome/bovine-arsucd12-minigraph bovine_pangenome/bovine-arsucd12-minigraph.fold10000 \
  mouse_pangenome/mouse-mm39-minigraph mouse_pangenome/mouse-mm39-minigraph.fold10000 \
  ecoli_pangenome/ecoli_minigraph ecoli_pangenome/ecoli_pggb ecoli_pangenome/ecoli_pggb.fold50 ecoli_pangenome/ecoli_cactus; do
  curl -sfL "$B/$u.graph.bed.gz" | gzip -dc | nice -n 10 python3 -I repo/docs/placement/scripts/duplicate-links.py "$u" || echo "$u FAILED"
done > dups.txt
) &
(
for f in hprc-v2.1-mc-grch38.GRCh38 hprc-v2.1-mc-chm13.CHM13; do
  echo "$f: $(nice -n 10 python3 -I repo/docs/walks-container/writer/scripts/abridged-span.py ~/work/genome7/$f.walks.gz )"
done > abspan.txt
) &
G=~/work/scratch/graph-repro/data/pggb/chrY.gfa
OLD=~/work/scratch/graph-repro/data/pggb/bin/gfa-to-tabix
NEW=repo/target/release/gfa-to-tabix
for round in 1 2; do
  for v in old new; do
    bin=$OLD; [ $v = new ] && bin=$NEW
    systemd-run --user --scope -q -p MemoryMax=20G -p MemorySwapMax=0 \
      /usr/bin/time -f "$v round $round: %e s, %M KB peak" -a -o chrY.time.txt \
      nice -n 10 "$bin" "$G" --reference GRCh38 -o chrY.$v > chrY.$v.log 2>&1
  done
done
echo "$($OLD --version) vs $($NEW --version)" >> chrY.time.txt
cmp chrY.old.graph.bed.gz chrY.new.graph.bed.gz && echo "chrY index byte-identical" >> chrY.time.txt || echo "chrY index DIFFERS" >> chrY.time.txt
zcat chrY.old.graph.bed.gz | grep -c -P '\tL\t' >> chrY.time.txt
zcat chrY.new.graph.bed.gz | grep -c -P '\tL\t' >> chrY.time.txt
wait
echo "done $(date -Is)"
touch done
