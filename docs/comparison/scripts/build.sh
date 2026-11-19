#!/usr/bin/env bash
# Index HPRC v2.1 Minigraph-Cactus chr22 and HPRC release 2 pggb chrY with gfaidx and with gfa-to-tabix on ada: time, peak memory and file sizes into results/
set -uo pipefail
cd ~/work/gfaidx-compare
IN=~/work/arb-format-opus/in
G=$PWD/dl/gfaidx-v2.3.2-linux-x86_64/gfaidx
T=$PWD/src/target/release/gfa-to-tabix
R=$PWD/results
THREADS=8
rm -rf out tmp $R
mkdir -p out tmp $R

{
  echo "gfaidx $($G --version 2>&1 | head -1 | sed 's/.* //'), the release's Linux x86-64 binary (sha256 $(sha256sum dl/gfaidx.tar.gz | cut -c1-16)), with index_gfa --threads $THREADS"
  echo "$($T --version) at commit $(cat gfa-to-tabix.commit)"
  echo "$(nproc) cores and $(free -g | awk 'NR==2{print $2}') GB of memory"
} > $R/versions.txt

printf 'graph\ttool\tstep\tseconds\tpeak_kb\tstatus\n' > $R/build.tsv
run() {
  graph=$1 tool=$2 step=$3 cap=$4
  shift 4
  systemd-run --user --scope -q -p MemoryMax=$cap -p MemorySwapMax=0 \
    nice -n 10 /usr/bin/time -f '%e\t%M' -o tmp/time.txt "$@" > "$R/$graph.$tool.$step.log" 2>&1
  status=$?
  printf '%s\t%s\t%s\t%s\t%s\n' "$graph" "$tool" "$step" "$(tail -1 tmp/time.txt)" "$status" >> $R/build.tsv
}

for g in mc22 pggbY; do
  gz=out/$g.gfaidx.gfa.gz
  run $g gfaidx index_gfa 24G $G index_gfa $IN/$g.gfa $gz --threads $THREADS --tmp_dir tmp --progress_every 0
  if [ $g = mc22 ]; then
    run $g gfaidx index_coordinates 24G $G index_coordinates $gz $gz.cdx --reference GRCh38 --progress_every 0
  else
    $G get_path $gz --print_path_names | awk -F '\t' '$1 == "P" && $2 ~ /^GRCh38#/' > tmp/$g.reference_paths.tsv
    run $g gfaidx index_coordinates 24G $G index_coordinates $gz $gz.cdx --path_names_file tmp/$g.reference_paths.tsv --progress_every 0
  fi
  cp $gz.params $R/$g.gfaidx.params.json
  run $g gfa-to-tabix walks 24G $T $IN/$g.gfa --walks --refs GRCh38 -o out/$g
  run $g gfa-to-tabix walks-sequences 32G $T $IN/$g.gfa --walks --refs GRCh38 --sequences -o out/$g.seq
  run $g gfa-to-tabix index 48G $T $IN/$g.gfa --reference GRCh38 -o out/$g
done

printf 'file\tbytes\n' > $R/sizes.tsv
stat --printf '%n\t%s\n' out/* | sed 's|^out/||' | sort >> $R/sizes.tsv
echo done > build.done
