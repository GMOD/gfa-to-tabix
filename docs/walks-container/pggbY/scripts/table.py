import json, sys, re
rows = []
cur = None
for line in open(sys.argv[1]):
    if line.startswith('CUTS '):
        cur = json.loads(line[5:])
    elif line.startswith('TIME') and cur:
        cur['proc'] = line.strip()
        rows.append(cur); cur = None
    elif line.startswith('differences') and cur is None and rows:
        pass
print(f"{'label':28} {'def':>10} {'unexp KB':>9} {'req':>4} {'ms':>6} {'rss':>5} | {'exp KB':>8} {'req':>4} {'ms':>6} {'rss':>5} | frag dep ph | proc")
for r in rows:
    d, u, x = r['defaultBudgets'], r['unexpanded'], r.get('expanded', {})
    ok = 'ok' if 'error' not in d else d['error'].split(':')[0]
    print(f"{r['label']:28} {ok:>10} {u['bytes']//1000:>9} {u['requests']:>4} {u['ms']:>6} {u['rssMB']:>5} | {x.get('bytes',0)//1000:>8} {x.get('requests',0):>4} {x.get('ms',0):>6} {x.get('rssMB',0):>5} | {u.get('fragments')} {u.get('departures')} {u.get('placeholders')} | {r['proc']}")
    if 'error' in d: print('   default:', d['error'][:300])
