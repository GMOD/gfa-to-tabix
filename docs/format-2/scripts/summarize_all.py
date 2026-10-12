import gzip
import json
import sys

rows = []
for p in sys.argv[1:]:
    with (gzip.open(p, "rt") if p.endswith(".gz") else open(p)) as f:
        rows += [json.loads(l) for l in f]
rows = list({r["chunk_mb"]: r for r in rows}.values())
rows.sort(key=lambda r: r["chunk_mb"])
n = len(rows)
S = lambda k: sum(r[k] for r in rows)
MB = lambda b: f"{b/1e6:.1f} MB"
print(f"{n} GRCh38 chunks; steps {S('steps')/1e6:.0f} M; routes {S('routes')}; runs {S('runs')}")
print(f"rebuild failures: counts {S('fail_rebuild_counts')}, identity {S('fail_rebuild_identity')}; ref dup nodes {S('ref_dup_nodes')}")
for k in ["st_implied_backward_steps", "st_backward_jumps", "st_leading_open", "st_trailing_open", "st_jump_routes", "st_land_on_dup", "st_start_on_dup"]:
    print(f"  {k}: {sum(r.get(k, 0) for r in rows)}")
print()
w, nd, lk = S("walks_gz"), S("nodes_gz"), S("links_gz")
ro, ch, chn, nm = S("routes_gz"), S("choices_ids_gz"), S("choices_ids_nocount_gz"), S("nodes_min_gz")
print(f"today:   walks {MB(w)} + nodes {MB(nd)} + links {MB(lk)} = {MB(w+nd+lk)}")
print(f"routes:  routes {MB(ro)} + choices {MB(ch)} (no implied counts {MB(chn)}) + nodes_min {MB(nm)} = {MB(ro+ch+nm)}")
print(f"  routes+choices / walks = {(ro+ch)/w:.2f}  (walks/(r+c) = {w/(ro+ch):.1f}x);  whole set new/today = {(ro+ch+nm)/(w+nd+lk):.2f}")
print(f"  cheap path: walks + nodes_min, no links = {MB(w+nm)} = {(w+nm)/(w+nd+lk):.2f} of today")
heavy = [r for r in rows if 11.7 < r["chunk_mb"] < 12.1]
hw = sum(r["walks_gz"] for r in heavy); hr = sum(r["routes_gz"] + r["choices_ids_gz"] for r in heavy)
print(f"  11.8-12.0 Mb ({len(heavy)} chunks): walks {MB(hw)} -> routes+choices {MB(hr)} ({hr/max(1,hw):.2f}); rest: {(ro+ch-hr)/max(1,(w-hw)):.2f}")
print(f"links: file {S('links_file')} implied {S('links_implied')} file-not-implied {S('links_file_not_implied')} implied-not-file {S('links_implied_not_file')}")
print()
# per-chunk ratio distribution
rat = sorted((r["routes_gz"] + r["choices_ids_gz"]) / r["walks_gz"] for r in rows if r["walks_gz"] > 1000)
print(f"per-chunk (routes+choices)/walks: median {rat[len(rat)//2]:.2f} p90 {rat[int(len(rat)*.9)]:.2f} max {rat[-1]:.2f}; chunks over 0.5: {sum(1 for x in rat if x > 0.5)}")
wr = sorted((r["routes_gz"] + r["choices_ids_gz"] + r["nodes_min_gz"]) / (r["walks_gz"] + r["nodes_gz"] + r["links_gz"]) for r in rows if r["walks_gz"] > 1000)
print(f"per-chunk whole-window new/today: median {wr[len(wr)//2]:.2f} p90 {wr[int(len(wr)*.9)]:.2f} max {wr[-1]:.2f}")
k8 = sorted((r["routes_gz"] + r["pick8_groups_gz"] + r["nodes_min_gz"]) / (r["walks_gz"] + r["nodes_gz"] + r["links_gz"]) for r in rows if r["walks_gz"] > 1000)
print(f"per-chunk k=8 via 64-groups new/today: median {k8[len(k8)//2]:.2f} p90 {k8[int(len(k8)*.9)]:.2f}")
g = sorted(r["pick8_groups_gz"] / max(1, r["choices_ids_gz"]) for r in rows if r["haps"] > 400)
print(f"k=8 group bytes / all choices: median {g[len(g)//2]:.2f}")
bph = sorted(r["choices_ids_gz"] / r["haps"] for r in rows if r["haps"] > 400)
print(f"choices bytes per haplotype per chunk: median {bph[len(bph)//2]:.0f} p90 {bph[int(len(bph)*.9)]:.0f} max {bph[-1]:.0f}")
worst = sorted(rows, key=lambda r: -(r["routes_gz"] + r["choices_ids_gz"]))[:8]
print("heaviest new chunks:", ", ".join(f'{r["chunk_mb"]}Mb r+c {MB(r["routes_gz"]+r["choices_ids_gz"])} vs walks {MB(r["walks_gz"])}' for r in worst))
