"""At the sites that hold most route bytes, how alike are the routes? And a
nodes variant that keeps placement coordinates for rank-1 nodes only."""
import gzip
import sys
from collections import Counter, defaultdict

sys.path.insert(0, sys.argv[0].rsplit("/", 1)[0])
from eval_routes import CHUNK, Encoder, canon, decode, gz, hap_of, rows, SEQ  # noqa: E402

d = sys.argv[1]
for mb in sys.argv[2:]:
    start = int(float(mb) * 1e6) // CHUNK * CHUNK
    node_rows = rows(d, "nodes", start)
    walk_rows = rows(d, "walks", start)
    ref_rows = sorted((r for r in walk_rows if r[3].startswith("GRCh38#")), key=lambda r: int(r[6]))
    ref_path = [h for r in ref_rows for h in decode(r[8])]
    enc = Encoder(ref_path)
    count = Counter()
    for r in walk_rows:
        if r[3].startswith("GRCh38#"):
            continue
        e = enc.encode(decode(r[8]))
        if e is None:
            continue
        for route, _, _ in e[1]:
            count[canon(route)[0]] += 1
    sites = defaultdict(list)
    for k in count:
        sites[(k[0], k[2])].append(k)
    total_steps = sum(len(k[1]) for k in count)
    by_bytes = sorted(sites.values(), key=lambda ks: -sum(len(k[1]) for k in ks))
    print(f"== chunk {start/1e6:.3f} Mb: {len(count)} routes, {total_steps} route steps, {len(sites)} sites")
    shown = 0
    for ks in by_bytes[:4]:
        steps = sum(len(k[1]) for k in ks)
        top = max(ks, key=lambda k: count[k])
        topset = set(top[1])
        shared = sum(sum(1 for h in k[1] if h in topset) for k in ks)
        # node-set diff: interior nodes not in the most common route
        novel = sum(sum(1 for h in k[1] if h not in topset) for k in ks)
        lens = sorted(len(k[1]) for k in ks)
        print(
            f"  site {ks[0][0]}..{ks[0][2]}: {len(ks)} routes, {sum(count[k] for k in ks)} uses, "
            f"{steps} steps ({100*steps/total_steps:.0f}% of chunk's route steps); top route {count[top]} carriers, {len(top[1])} steps; "
            f"route lengths med {lens[len(lens)//2]} max {lens[-1]}; steps on nodes outside the top route: {novel} ({100*novel/max(1,steps):.1f}%)"
        )
        shown += 1
    # an edit-encoding estimate: per route, runs of steps shared with the top route collapse to one token
    tokens = 0
    for ks in sites.values():
        top = max(ks, key=lambda k: count[k])
        topset = set(top[1])
        for k in ks:
            if k is top:
                tokens += len(k[1])
                continue
            prev_shared = False
            for h in k[1]:
                s = h in topset
                if not s or not prev_shared:
                    tokens += 1
                prev_shared = s
    print(f"  edit-vs-site-consensus tokens: {tokens} against {total_steps} plain steps ({100*tokens/max(1,total_steps):.0f}%)")
    # nodes variants
    prefix = f"{SEQ}\t{start}\t{start + 1}\t"
    plain = "".join("\t".join(r) + "\n" for r in node_rows)
    prev = int(node_rows[0][3])
    mn, keep1 = [], []
    for r in node_rows:
        nid = int(r[3])
        ln = int(r[7]) - int(r[6])
        mn.append(f"{prefix}{nid - prev}\t{ln}\n")
        keep1.append(f"{prefix}{nid - prev}\t{ln}\n" if r[4] == "0" else f"{prefix}{nid - prev}\t{ln}\t{r[5]}\t{r[6]}\n")
        prev = nid
    print(f"  nodes: as filed {gz(plain)/1e3:.0f} KB; id+len {gz(''.join(mn))/1e3:.0f} KB; id+len+rank1 placement {gz(''.join(keep1))/1e3:.0f} KB ({len(node_rows)} rows)")
