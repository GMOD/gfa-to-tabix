#!/usr/bin/env bash
cd ~/work/blocks/pggbY
bash windows.sh pggbY.GRCh38.walks.gz windows.GRCh38.tsv four.GRCh38 8G --four-only
bash windows.sh pggbY.CHM13.walks.gz windows.CHM13.tsv four.CHM13 8G --four-only
