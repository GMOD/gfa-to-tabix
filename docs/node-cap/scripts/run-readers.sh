#!/bin/bash
# Every reader run of the node-cap study: serves the reader builds and the walk file locally, then drive.mjs.
# NODECAP is the directory holding bjs/ (BandageJS built with the marks), plugin/ (the plugin built with the marks),
# jbrowse/ (jbrowse-web 5.0.0-beta.20 with plugin/ linked to the plugin's dist and config.json) and data/ (the walk file)
set -u
D=$(cd "$(dirname "$0")" && pwd)
N=${NODECAP:?}
export PATH=$HOME/.local/node/bin:$PATH
export PUPPETEER_DIR=$N/plugin
export CHROME=$HOME/.cache/puppeteer/chrome/linux-154.0.8037.57/chrome-linux64/chrome
export FONTCONFIG_FILE=$HOME/jb-capture-fonts/fonts.conf
PORT=47811
curl -sf -o /dev/null http://127.0.0.1:$PORT/config.json || { node "$D/serve.mjs" $PORT =$N/jbrowse bjs=$N/bjs/dist data=$N/data & sleep 1; }
node "$D/drive.mjs" "$1" http://127.0.0.1:$PORT 300 "${@:2}"
