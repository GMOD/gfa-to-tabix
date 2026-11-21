#!/usr/bin/env bash
# From a checkout, with GRAPH_WALKS=<graph-walks checkout>: sets up ada:~/work/gfaidx-compare for build.sh, windows.sh and times.sh, with this commit's source built in release mode, the gfaidx 2.3.2 release binary, fusepy for pagelog.py, graph-walks with its dependencies and these scripts
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
git -C "$GRAPH_WALKS" archive --format=tar --prefix=graph-walks/ HEAD -- package.json pnpm-lock.yaml pnpm-workspace.yaml src tsconfig.json |
  ssh ada "set -e; export PATH=~/.local/node/bin:\$PATH; cd ~/work/gfaidx-compare; rm -rf graph-walks; tar x
    echo $(git -C "$GRAPH_WALKS" show HEAD:package.json | sed -n 's/^  "version": "\(.*\)",/\1/p') $(git -C "$GRAPH_WALKS" rev-parse --short HEAD) > graph-walks.commit
    cd graph-walks; pnpm install --frozen-lockfile --prod"
