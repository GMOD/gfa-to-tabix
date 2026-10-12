import gzip
import json
import math
import statistics
import sys

HEAVY = {11.796, 18.219, 18.678, 38.076}

p = sys.argv[1]
with (gzip.open(p, "rt") if p.endswith(".gz") else open(p)) as f:
    rows = [json.loads(line) for line in f]
typical = [r for r in rows if r["chunk_mb"] not in HEAVY and r["haps"] > 400]
S = lambda k: sum(r["all"][k] for r in typical)


def exponent(k, lo):
    return statistics.median(
        math.log(r["all"][k] / r[f"sub{lo}"][k]) / math.log(r["haps"] / lo) for r in typical if r[f"sub{lo}"][k]
    )


print(f"{len(typical)} typical chunks; distinct choice sequences per run {S('distinct_seqs') / S('runs'):.2f}")
print(f"metadata {S('meta_gz') / S('choices_gz'):.2f} of choices, grows as N^{exponent('meta_gz', 200):.2f}")
print(f"{'tokens':16} {'KB/chunk':>8} {'of tok_gz':>9} {'N^ 200-463':>10} {'N^ 50-463':>9}")
for k in ["tok_gz", "tok_sorted_gz", "site_plain_gz", "site_rle_gz", "tok_xz"]:
    print(f"{k:16} {S(k) / len(typical) / 1e3:8.1f} {S(k) / S('tok_gz'):9.2f} {exponent(k, 200):10.2f} {exponent(k, 50):9.2f}")
print("metadata saved by dropping one field, as a share of metadata:")
for k in ["hap", "contig", "frag", "off", "piece", "start", "span", "tags", "contig_frag"]:
    saved = S(f"meta_saved_without_{k}")
    print(f"  {k:12} {saved / S('meta_gz'):.2f} of metadata, {saved / S('choices_gz'):.2f} of choices")
print("heavy chunks:")
for r in rows:
    if r["chunk_mb"] in HEAVY:
        a = r["all"]
        print(f"  {r['chunk_mb']} Mb: routes {a['routes']}, uses {a['route_uses']}, tok_gz {a['tok_gz']}, sorted {a['tok_sorted_gz']}, site_rle {a['site_rle_gz']}")
