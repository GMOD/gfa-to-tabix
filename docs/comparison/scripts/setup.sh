#!/usr/bin/env bash
# From a checkout: sets up ada:~/work/gfaidx-compare for build.sh and then windows.sh, with this commit's source built in release mode, the gfaidx 2.3.2 release binary, fusepy for pagelog.py and these scripts
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
commit=$(git rev-parse --short HEAD)
release=https://github.com/fawaz-dabbaghieh/gfaidx/releases/download/v2.3.2/gfaidx-v2.3.2-linux-x86_64.tar.gz
git archive --format=tar --prefix=src/ HEAD -- Cargo.toml Cargo.lock src scripts/walks-truth.py \
  docs/walks-container/dialect/p-names.tsv docs/comparison/scripts |
  ssh ada "set -e; mkdir -p ~/work/gfaidx-compare/dl; cd ~/work/gfaidx-compare; rm -rf src; tar x
    echo $commit > gfa-to-tabix.commit; cp src/docs/comparison/scripts/* .
    curl -fsSL -o dl/gfaidx.tar.gz $release; tar xzf dl/gfaidx.tar.gz -C dl
    python3 -m venv venv; venv/bin/pip install -q fusepy
    cd src; nice -n 10 cargo build --release -j 8"
