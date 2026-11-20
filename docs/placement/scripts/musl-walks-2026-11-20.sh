#!/usr/bin/env bash
# The runs of docs/placement/mc22-walks-build.txt: 5.0.0's release binary
# (static, x86_64-unknown-linux-musl) against the same source built with cargo
# (glibc), on --walks for MC chr22, alternating, each pair's walk file compared
set -uo pipefail
D=~/work/rollout-audit-1120/musl-walks
G=~/work/perf-1119/out/mc22.gfa.gz
A=gfa-to-tabix-x86_64-unknown-linux-musl
mkdir -p $D && cd $D
rm -f time.txt
curl -fsLO https://github.com/GMOD/gfa-to-tabix/releases/download/v5.0.0/$A.tar.gz
curl -fsLO https://github.com/GMOD/gfa-to-tabix/releases/download/v5.0.0/$A.tar.gz.sha256
sha256sum -c $A.tar.gz.sha256 > asset.log 2>&1 && tar xzf $A.tar.gz
[ -d src ] || git clone -q --branch v5.0.0 --depth 1 https://github.com/GMOD/gfa-to-tabix src
(cd src && nice -n 10 cargo build --release --locked -j 8 > ../build.log 2>&1)
echo "input: $(sha256sum < $G | cut -c1-16) $(stat -c %s $G) bytes" >> time.txt
echo "load before: $(cut -d" " -f1-3 /proc/loadavg)" >> time.txt
for round in 1 2; do
  for v in musl glibc; do
    bin=$A/gfa-to-tabix; [ $v = glibc ] && bin=src/target/release/gfa-to-tabix
    /usr/bin/time -f "5.0.0 ($v) round $round: %e s wall, %U s user, %S s system, %M KB peak" -a -o time.txt \
      nice -n 10 "$bin" "$G" --walks --refs GRCh38 -o $v > $v.log 2>&1
  done
done
cmp musl.GRCh38.walks.gz glibc.GRCh38.walks.gz && cmp musl.GRCh38.walks.gz.idx glibc.GRCh38.walks.gz.idx \
  && echo "walk file and directory byte-identical" >> time.txt
echo "load after: $(cut -d" " -f1-3 /proc/loadavg)" >> time.txt
cat time.txt
