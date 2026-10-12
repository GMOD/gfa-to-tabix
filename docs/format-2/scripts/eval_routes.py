"""Fair re-measurement of the routes/choices design on one chunk of the
Oct 8 chr22 walk build. Everything a reader needs to rebuild each walk row
step for step is encoded and the rebuild is checked.

usage: eval_routes.py DIR mb [mb ...] [--sub 50,100,200] [--json out.jsonl]
"""
import gzip
import json
import random
import subprocess
import sys
import time
from collections import Counter, defaultdict

SEQ = "GRCh38#0#chr22"
CHUNK = 65536
GROUP = 64


def rows(d, kind, start):
    out = subprocess.run(
        ["tabix", f"{d}/chr22.{kind}.bed.gz", f"{SEQ}:{start + 1}-{start + 1}"],
        capture_output=True, text=True, check=True,
    ).stdout
    return [line.split("\t") for line in out.splitlines()]


def decode(enc):
    out = []
    prev = 0
    first = True
    for tok in enc.split(","):
        v = int(tok)
        r = v & 1
        d = (v - r) >> 1
        prev = d if first else prev + d
        first = False
        out.append(2 * prev + r)
    return out


def gz(text):
    return len(gzip.compress(text.encode(), 6))


def canonical_link(a, b):
    return (b ^ 1, a ^ 1) if a > (b ^ 1) else (a, b)


def rc(route):
    e, interior, x = route
    return (
        None if x is None else x ^ 1,
        tuple(h ^ 1 for h in reversed(interior)),
        None if e is None else e ^ 1,
    )


def sort_key(route):
    e, interior, x = route
    return (-1 if e is None else e, interior, -1 if x is None else x)


def canon(route):
    other = rc(route)
    if sort_key(other) < sort_key(route):
        return other, 1
    return route, 0


def nearest(occ, i):
    # the occurrence of a node nearest index i, the later one on a tie
    best = None
    for j in occ:
        if best is None or abs(j - i) < abs(best - i) or (abs(j - i) == abs(best - i) and j > best):
            best = j
    return best


class Encoder:
    def __init__(self, ref_path):
        self.ref_path = ref_path
        self.occ = defaultdict(list)
        for i, h in enumerate(ref_path):
            self.occ[h >> 1].append(i)
        self.stats = Counter()

    def on_ref(self, h):
        return (h >> 1) in self.occ

    def encode(self, H):
        """-> (start_handle, [(route, flip, implied_n, ambiguous)], end_handle)"""
        rp, occ, st = self.ref_path, self.occ, self.stats
        i = None
        cur = None
        pending = []
        choices = []
        start = None
        implied = 0
        for h in H:
            if not self.on_ref(h):
                pending.append(h)
                continue
            if i is None:
                start = h
                i = occ[h >> 1][0]
                if len(occ[h >> 1]) > 1:
                    st["start_on_dup"] += 1
                if pending:
                    choices.append(((None, tuple(pending), h), 0, 0))
                    st["leading_open"] += 1
                cur = h
                pending = []
                continue
            fwd = i + 1 < len(rp) and rp[i + 1] == h and cur == rp[i]
            bwd = i - 1 >= 0 and (rp[i - 1] ^ 1) == h and cur == (rp[i] ^ 1)
            if not pending and fwd:
                i += 1
                implied += 1
                cur = h
            elif not pending and bwd:
                i -= 1
                implied += 1
                cur = h
                st["implied_backward_steps"] += 1
            else:
                route = (cur, tuple(pending), h)
                if not pending:
                    st["jump_routes"] += 1
                    if (occ[h >> 1][0] < i):
                        st["backward_jumps"] += 1
                j = nearest(occ[h >> 1], i)
                if len(occ[h >> 1]) > 1:
                    st["land_on_dup"] += 1
                choices.append((route, implied, 0))
                implied = 0
                i = j
                cur = h
                pending = []
        if i is None:
            st["no_ref_step_rows"] += 1
            return None
        if pending:
            choices.append(((cur, tuple(pending), None), implied, 0))
            st["trailing_open"] += 1
            implied = 0
        return start, choices, cur, implied


def rebuild(ref_path, occ, start, choices, end, tail_implied, use_counts):
    """Rebuild the handle list from start, routes and implied reference."""
    H = []
    h = start
    i = occ[start >> 1][0]
    k = 0
    if choices and choices[k][0][0] is None:
        route = choices[k][0]
        H.extend(route[1])
        k += 1
    H.append(h)

    def walk_to(target, n):
        nonlocal h, i
        direction = 1 if h == ref_path[i] else -1
        steps = 0
        while True:
            if use_counts:
                if steps == n:
                    break
            elif h == target:
                break
            i += direction
            if i < 0 or i >= len(ref_path):
                raise ValueError("ran off reference")
            h = ref_path[i] if direction > 0 else ref_path[i] ^ 1
            H.append(h)
            steps += 1

    while k < len(choices):
        (e, interior, x), n, _ = choices[k]
        k += 1
        if e is None:
            raise ValueError("leading route not first")
        walk_to(e, n)
        if h != e:
            raise ValueError("entry mismatch")
        H.extend(interior)
        if x is None:
            return H
        H.append(x)
        h = x
        i = nearest(occ[x >> 1], i)
    walk_to(end, tail_implied)
    return H


def hap_of(name):
    return "#".join(name.split("#")[:2])


def measure(d, start, subs, seed=1):
    t0 = time.time()
    node_rows = rows(d, "nodes", start)
    walk_rows = rows(d, "walks", start)
    link_rows = rows(d, "links", start)
    nodes = {}
    for r in node_rows:
        nodes[int(r[3])] = (int(r[4]), r[5], int(r[6]), int(r[7]))
    ref_rows = sorted((r for r in walk_rows if r[3].startswith("GRCh38#")), key=lambda r: int(r[6]))
    ref_path = []
    for r in ref_rows:
        ref_path.extend(decode(r[8]))
    enc = Encoder(ref_path)
    ref_rev = sum(h & 1 for h in ref_path)
    dup_nodes = sum(1 for o in enc.occ.values() if len(o) > 1)

    # join consecutive pieces of one path into a run, as a reader does
    by_path = defaultdict(list)
    for r in walk_rows:
        if r[3].startswith("GRCh38#"):
            continue
        by_path[(r[3], r[4])].append(r)
    runs = []
    for (name, frag), rs in by_path.items():
        rs.sort(key=lambda r: int(r[6]))
        from_ = 0
        for k in range(1, len(rs) + 1):
            if k == len(rs) or int(rs[k][6]) != int(rs[k - 1][6]) + 1:
                piece = rs[from_:k]
                H = []
                for r in piece:
                    H.extend(decode(r[8]))
                tags = [c for c in piece[0][9:] if c.startswith("pv:")] + [c for c in piece[-1][9:] if c.startswith("nx:")]
                runs.append((name, int(frag), int(piece[0][5]), int(piece[0][6]), H, tags))
                from_ = k

    total_steps = sum(len(H) for *_, H, _ in runs)
    encoded = []
    fail_identity = 0
    fail_counts = 0
    for name, frag, off, piece, H, tags in runs:
        e = enc.encode(H)
        if e is None:
            continue
        start_h, choices, end_h, tail = e
        encoded.append((name, frag, off, piece, start_h, choices, end_h, tail, tags))
        try:
            if rebuild(ref_path, enc.occ, start_h, choices, end_h, tail, True) != H:
                fail_counts += 1
        except ValueError:
            fail_counts += 1
        try:
            if rebuild(ref_path, enc.occ, start_h, choices, end_h, tail, False) != H:
                fail_identity += 1
        except ValueError:
            fail_identity += 1

    # links: everything the file holds against everything the walks imply
    implied = set()
    for r in walk_rows:
        H = decode(r[8])
        for a, b in zip(H, H[1:]):
            implied.add(canonical_link(a, b))
    in_file = set()
    for r in link_rows:
        a = int(r[3][:-1]) * 2 + (r[3][-1] == "-")
        b = int(r[4][:-1]) * 2 + (r[4][-1] == "-")
        in_file.add(canonical_link(a, b))

    def pos_of(h):
        return nodes[h >> 1][2] if (h >> 1) in nodes else None

    def route_tables(encoded_subset):
        count = Counter()
        for *_, choices, _, _, _ in encoded_subset:
            for route, _, _ in choices:
                key, _ = canon(route)
                count[key] += 1

        def anchor(key):
            e, interior, x = key
            ps = [pos_of(h) for h in (e, x) if h is not None and pos_of(h) is not None]
            return min(ps) if ps else 0

        ordered = sorted(count, key=lambda k: (anchor(k), sort_key(k)))
        rid = {k: i for i, k in enumerate(ordered)}
        lines = []
        prev_e = 0
        own_bp = {}
        rep_bp = {}
        for k in ordered:
            e, interior, x = k
            e_id = 0 if e is None else e >> 1
            parts = [str(rid[k]), "." if e is None else str(e - 2 * prev_e)]
            prev_e = e_id if e is not None else prev_e
            parts.append("." if x is None else str(x - 2 * e_id))
            parts.append(str(count[k]))
            steps = []
            p = e_id
            for h in interior:
                steps.append(str(2 * ((h >> 1) - p) + (h & 1)))
                p = h >> 1
            parts.append(",".join(steps) if steps else ".")
            lines.append("\t".join(parts))
            own_bp[k] = sum(nodes[h >> 1][3] - nodes[h >> 1][2] for h in interior if (h >> 1) in nodes)
            pe, px = (pos_of(e) if e is not None else None), (pos_of(x) if x is not None else None)
            rep_bp[k] = abs(px - pe) if pe is not None and px is not None else 0
        return count, rid, lines, own_bp, rep_bp

    def choice_lines(encoded_subset, rid, hap_ids=None, with_counts=True, minimal=False):
        lines = []
        for name, frag, off, piece, start_h, choices, end_h, tail, tags in encoded_subset:
            toks = []
            prev = 0
            for route, n, _ in choices:
                key, flip = canon(route)
                r = rid[key]
                toks.append(str(2 * (r - prev) + flip))
                if with_counts and not minimal:
                    toks.append(str(n))
                prev = r
            if minimal:
                lines.append(f"{hap_of(name)}\t{','.join(toks) or '.'}")
                continue
            label = name if hap_ids is None else f"{hap_ids[hap_of(name)]}#{name.split('#', 2)[2]}"
            fields = [label, str(frag), str(off), str(piece), str(start_h), str(end_h - start_h), str(tail) if with_counts else ".", ",".join(toks) or "."] + tags
            lines.append("\t".join(fields))
        return lines

    prefix = f"{SEQ}\t{start}\t{start + 1}\t"

    def text(lines):
        return "".join(prefix + l + "\n" for l in lines)

    haps = sorted({hap_of(e[0]) for e in encoded})
    hap_ids = {h: i for i, h in enumerate(haps)}
    count, rid, route_lines, own_bp, rep_bp = route_tables(encoded)
    walk_text = "".join("\t".join(r) + "\n" for r in walk_rows)
    walk_nonref = "".join("\t".join(r) + "\n" for r in walk_rows if not r[3].startswith("GRCh38#"))
    walk_ref = "".join("\t".join(r) + "\n" for r in ref_rows)
    routes_text = text(route_lines)
    ch_full = text(choice_lines(encoded, rid))
    ch_ids = text(choice_lines(encoded, rid, hap_ids))
    ch_noc = text(choice_lines(encoded, rid, hap_ids, with_counts=False))
    ch_min = text(choice_lines(encoded, rid, minimal=True))

    # per-group blocks and a k=8 pick
    by_hap = defaultdict(list)
    for e in encoded:
        by_hap[hap_of(e[0])].append(e)
    groups = [haps[g:g + GROUP] for g in range(0, len(haps), GROUP)]
    group_sizes = []
    for g in groups:
        members = [e for h in g for e in by_hap[h]]
        group_sizes.append(gz(text(choice_lines(members, rid, hap_ids))))
    rng = random.Random(seed)
    pick8 = rng.sample(haps, min(8, len(haps)))
    groups_touched = len({hap_ids[h] // GROUP for h in pick8})
    pick8_bytes = sum(group_sizes[gi] for gi in {hap_ids[h] // GROUP for h in pick8})
    one_hap_sizes = [gz(text(choice_lines(by_hap[h], rid, hap_ids))) for h in pick8]

    # tiers: a route under N bp (own and replaced) folds into the reference
    tiers = {}
    for n in (100, 1000, 10000):
        keep = [k for k in count if max(own_bp[k], rep_bp[k]) >= n]
        tiers[n] = (len(keep), sum(count[k] for k in keep))
    # nested variation: sites with many routes and the share of route step bytes
    sites = defaultdict(list)
    for k in count:
        sites[(k[0], k[2])].append(k)
    route_bytes = {k: len(route_lines[rid[k]]) for k in count}
    big_sites = [s for s, ks in sites.items() if len(ks) >= 10]
    big_site_bytes = sum(route_bytes[k] for s in big_sites for k in sites[s])
    long_routes = [k for k in count if len(k[1]) >= 50]
    long_route_bytes = sum(route_bytes[k] for k in long_routes)
    singletons = sum(1 for k in count if count[k] == 1)
    singleton_bytes = sum(route_bytes[k] for k in count if count[k] == 1)

    out = {
        "chunk_mb": round(start / 1e6, 3),
        "haps": len(haps),
        "runs": len(encoded),
        "steps": total_steps,
        "ref_steps": len(ref_path),
        "ref_rev_steps": ref_rev,
        "ref_dup_nodes": dup_nodes,
        "routes": len(count),
        "route_uses": sum(count.values()),
        "singleton_routes": singletons,
        "singleton_route_bytes_frac": round(singleton_bytes / max(1, sum(route_bytes.values())), 3),
        "max_routes_site": max((len(ks) for ks in sites.values()), default=0),
        "sites_ge10_routes": len(big_sites),
        "big_site_bytes_frac": round(big_site_bytes / max(1, sum(route_bytes.values())), 3),
        "long_route_bytes_frac": round(long_route_bytes / max(1, sum(route_bytes.values())), 3),
        "tier100_routes": tiers[100][0], "tier1k_routes": tiers[1000][0], "tier10k_routes": tiers[10000][0],
        "tier100_uses": tiers[100][1], "tier1k_uses": tiers[1000][1], "tier10k_uses": tiers[10000][1],
        "fail_rebuild_counts": fail_counts,
        "fail_rebuild_identity": fail_identity,
        **{f"st_{k}": v for k, v in enc.stats.items()},
        "walks_gz": gz(walk_text),
        "walks_nonref_gz": gz(walk_nonref),
        "walks_ref_gz": gz(walk_ref),
        "nodes_gz": gz("".join("\t".join(r) + "\n" for r in node_rows)),
        "nodes_min_gz": gz(text(f"{int(r[3]) - int(p[3])}\t{int(r[7]) - int(r[6])}" for p, r in zip([node_rows[0]] + node_rows, node_rows))),
        "nodes_rows": len(node_rows),
        "links_gz": gz("".join("\t".join(r) + "\n" for r in link_rows)),
        "routes_gz": gz(routes_text),
        "choices_full_gz": gz(ch_full),
        "choices_ids_gz": gz(ch_ids),
        "choices_ids_nocount_gz": gz(ch_noc),
        "choices_min_gz": gz(ch_min),
        "group_mean_gz": round(sum(group_sizes) / max(1, len(group_sizes))),
        "groups_sum_gz": sum(group_sizes),
        "pick8_groups": groups_touched,
        "pick8_groups_gz": pick8_bytes,
        "pick8_singles_gz": sum(one_hap_sizes),
        "links_file": len(in_file),
        "links_implied": len(implied),
        "links_file_not_implied": len(in_file - implied),
        "links_implied_not_file": len(implied - in_file),
    }
    for n in subs:
        if n >= len(haps):
            continue
        sub = set(rng.sample(haps, n))
        enc_sub = [e for e in encoded if hap_of(e[0]) in sub]
        c, r, rl, _, _ = route_tables(enc_sub)
        out[f"sub{n}_routes"] = len(c)
        out[f"sub{n}_routes_gz"] = gz(text(rl))
        out[f"sub{n}_choices_gz"] = gz(text(choice_lines(enc_sub, r, hap_ids)))
        out[f"sub{n}_walks_gz"] = gz("".join("\t".join(r_) + "\n" for r_ in walk_rows if hap_of(r_[3]) in sub))
    out["seconds"] = round(time.time() - t0, 1)
    return out


if __name__ == "__main__":
    args = sys.argv[1:]
    d = args.pop(0)
    subs = []
    jpath = None
    mbs = []
    while args:
        a = args.pop(0)
        if a == "--sub":
            subs = [int(x) for x in args.pop(0).split(",")]
        elif a == "--json":
            jpath = args.pop(0)
        else:
            mbs.append(float(a))
    for mb in mbs:
        start = int(mb * 1e6) // CHUNK * CHUNK
        m = measure(d, start, subs)
        print(json.dumps(m), flush=True)
        if jpath:
            with open(jpath, "a") as f:
                f.write(json.dumps(m) + "\n")
