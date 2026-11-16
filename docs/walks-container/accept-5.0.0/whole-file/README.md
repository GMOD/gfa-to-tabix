# The whole-file checks on the hosted bytes

Written by [table.py](table.py) from [results.jsonl](results.jsonl), which it writes from what [run.sh](run.sh) left here on 2026-11-16. Not edited by hand. The scripts that ran, by git blob ([checkers.tsv](checkers.tsv)): `verify7.py` 43090148a427, `spec8.py` a3ecdcf2b1cd.

## The local files are the hosted ones

Each local file against its hosted copy ([identity.tsv](identity.tsv)): the length against `Content-Length`, the S3 multipart ETag of the local bytes over 8 MiB parts against the hosted ETag, and the sha256 of the `.idx`.

| File | Hosted as | Bytes | Length | ETag | `.idx` | sha256 of the local data |
|---|---|---|---|---|---|---|
| grch38 | `hprc-v2.1-mc-grch38-f8.GRCh38.walks.gz` | 1,580,961,534 | equal | equal | equal | `59537b965d8994c4…` |
| chm13 | `hprc-v2.1-mc-chm13-f8.CHM13.walks.gz` | 1,784,716,865 | equal | equal | equal | `5982069f2a9d11d7…` |
| chr6-sequences | `hprc-v2.1-mc-grch38-chr6-sequences-f8.GRCh38.walks.gz` | 145,319,431 | equal | equal | equal | `6e2c7eda378e4658…` |
| pggbY | not hosted | 193,641,445 | n/a | n/a | n/a | `f4b2e0a3b0a6d378…` |

## verify7.py over each whole file

Nodes the file's `ref` rows step once, those among them in a route interior of a tile or a detail unit on any sequence, and `ref` rows whose `passes` states another count than the file's `ref` rows step.

| File | `revisited` nodes | `ref` steps | Nodes stepped once | Route interior steps read | Stepped once and in an interior | `ref` rows stating fewer | stating more | Exit | Time | Peak |
|---|---|---|---|---|---|---|---|---|---|---|
| grch38 | 0 | 83,303,684 | 83,303,684 | 679,905,395 | 0 | 0 | 0 | 0 | 318 s | 0.36 GB |
| chm13 | 0 | 90,761,410 | 90,761,410 | 840,302,328 | 0 | 0 | 0 | 0 | 380 s | 0.34 GB |
| chr6-sequences | 0 | 4,799,024 | 4,799,024 | 25,220,331 | 0 | 0 | 0 | 0 | 17 s | 0.26 GB |
| pggbY | 107,467 | 827,826 | 155,947 | 290,043,748 | 0 | 0 | 0 | 0 | 66 s | 0.65 GB |

Each summary is `verify7.<file>.json`, and its time, peak memory and exit status `verify7.<file>.time`.

## spec8.py, written from the page alone

spec8.py holds every piece of a file in memory, so it ran on the chromosome files and not on the genome files. It counts the nodes the `ref` rows step once as verify7.py does, with no code of it.

| File | Disagreements with the page | Nodes stepped once | Same as verify7 | Nodes in a route interior | Stepped once and in an interior, which the page promises nothing of where `revisited` is above 0 | Time | Peak |
|---|---|---|---|---|---|---|---|
| chr6-sequences | none | 4,799,024 | equal | 2,832,198 | n/a: the file states `revisited:i:0` | 421 s | 2.13 GB |
| pggbY | none | 155,947 | equal | 3,013,584 | 0 | 606 s | 12.60 GB |

Each report is `spec8.<file>.txt`.

## What the checks fail

[broken-matrix.txt](broken-matrix.txt) lists, for each planted file of [cases.tsv](../../../departures/scripts/broken/cases.tsv) that breaks one of these and for the unbroken files they were made from, the checkers that fail it, as [matrix.sh](matrix.sh) printed them with the same scripts.
