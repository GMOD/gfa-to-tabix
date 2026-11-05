import json, sys, glob, statistics, collections
def q(v, p):
    v = sorted(v); return v[min(len(v)-1, int(p*len(v)))] if v else 0
ORDER = ['f6p','t64b','t64bx','tn','tl','tlb','s','s7','s7t','s512']
d, res = sys.argv[1], sys.argv[2]
print(f"### {d}\n")
print("| cand | 1 kb read / +attach | 10 kb | 100 kb | 1 Mb | attach KB 1 kb med/p90 | req med/max | trips max | checked: pieces wrong / deps missing |")
print("|---|---|---|---|---|---|---|---|---|")
for cand in ORDER:
    try: rows = [json.loads(l) for l in open(f"{res}/{d}.{cand}.jsonl")]
    except FileNotFoundError: continue
    by = collections.defaultdict(list); bya = collections.defaultdict(list); att = collections.defaultdict(list)
    req=[]; trips=[]; ck=collections.Counter(); n=0
    for r in rows[1:]:
        a = (r.get('attach') or {}).get('bytes', 0)
        by[r['size']].append((r['bytes']-a)/1000); bya[r['size']].append(r['bytes']/1000); att[r['size']].append(a/1000)
        req.append(r['requests']); trips.append(r['trips'])
        if 'check' in r:
            n+=1
            for k,v in r['check'].items(): ck[k]+=v
    cells = [f"{q(by[s],.5):.0f}/{q(by[s],.9):.0f}/{q(by[s],.99):.0f} · {q(bya[s],.5):.0f}/{q(bya[s],.9):.0f}/{q(bya[s],.99):.0f}" for s in sorted(by)]
    print(f"| {cand} | " + " | ".join(cells) + f" | {q(att[1000],.5):.0f}/{q(att[1000],.9):.0f} | {statistics.median(req):.0f}/{max(req)} | {max(trips)} | {n}w: {ck['pieces']} {ck['missing']+ck['differ']+ck['extra']} / {ck['deps']} {ck['depMissing']} |")
