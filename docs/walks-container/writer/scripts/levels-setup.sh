#!/usr/bin/env bash
# The scratch clone levels.sh and levels-mc.sh build with: the branch at
# 76ff987 with the walk file's compression level read from $LEVEL (default
# 6), in ~/work/impl-writer/lv. Not committed to the writer.
set -euo pipefail
cd ~/work/impl-writer
rm -rf lv && git clone -q -b format7-writer writer.bundle lv && cd lv
git checkout -q 76ff987
sed -i 's/Compression::new(6), threads)/Compression::new(std::env::var("LEVEL").map_or(6, |l| l.parse().unwrap())), threads)/' src/units.rs
cargo build --release -q
