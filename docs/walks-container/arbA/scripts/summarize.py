import json, sys, glob, statistics, collections
def q(v, p):
    v = sorted(v); return v[min(len(v)-1, int(p*len(v)))]
ORDER = ['a0','f6p','t','tn','t16','o','ou','s','s2','n','onochain','oabs','srel','sabs']
for d in sys.argv[1:]:
    print(f"## {d}\n")
    print("| cand | open KB | 1 kb | 10 kb | 100 kb | 1 Mb | req med / max | trips max | checked windows: pieces / wrong | departures / missing |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    splits = []
    for cand in ORDER:
        f = f"res/{d}.{cand}.jsonl"
        try: rows = [json.loads(l) for l in open(f)]
        except FileNotFoundError: continue
        op = rows[0].get('open', {})
        by = collections.defaultdict(list); req=[]; trips=[]; ck=collections.Counter(); n=0
        sp = collections.defaultdict(lambda: collections.defaultdict(list))
        for r in rows[1:]:
            by[r['size']].append(r['bytes']/1000); req.append(r['requests']); trips.append(r['trips'])
            if r.get('split'):
                for k,v in r['split'].items(): sp[r['size']][k].append(v/1000)
            elif cand in ('o','ou'):
                for k,v in r['files'].items(): sp[r['size']]['dep' if 'dep' in k else 'walk'].append(v/1000)
            if 'check' in r:
                n+=1
                for k,v in r['check'].items(): ck[k]+=v
        cells = [f"{q(by[s],.5):.0f} / {q(by[s],.9):.0f} / {q(by[s],.99):.0f}" for s in sorted(by)]
        chk = f"{n}: {ck['pieces']} / {ck['missing']+ck['differ']+ck['extra']}" if n and cand!='t16' else "n/a"
        dep = f"{ck['deps']} / {ck['depMissing']}" if n and cand!='t16' else "n/a"
        print(f"| {cand} | {op.get('bytes',0)/1000:.0f} | " + " | ".join(cells) + f" | {statistics.median(req):.0f} / {max(req)} | {max(trips)} | {chk} | {dep} |")
        if sp:
            splits.append(f"- {cand}: " + "; ".join(f"{s//1000} kb " + ", ".join(f"{k} {q(v,.5):.0f}/{q(v,.9):.0f}" for k,v in sorted(sp[s].items())) for s in sorted(sp)))
    print("\nmedian/p90 KB by part:\n" + "\n".join(splits) + "\n")
