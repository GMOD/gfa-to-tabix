#!/usr/bin/env python3
"""analyze.py NAME...  reads out/NAME.jsonl and out/NAME.chunks.json and
writes out/NAME.windows.tsv (one row per window and mode) and prints the
summary tables and worst windows."""
import json
import statistics
import sys
from collections import Counter, defaultdict

CLASSES = ["1", "2", "3", "3?", "4", "5"]
# graph-walks WALK_CONTEXT
CONTEXT = 1000


def med(xs):
    xs = [x for x in xs if x is not None]
    return statistics.median(xs) if xs else None


def placement(node, rec, chunks, ref):
    """Where the walk file holds an index-only node, against this cut's reads:
    read (a chunk the cut decoded), reach (within FOLLOW_CHUNKS of the read,
    not read), beyond, detail (only in detail records), absent."""
    w = rec["walk"]
    places = chunks.get(node["id"])
    if not places:
        return "absent", None
    main = [p["cs"] for p in places if p["where"] == "main" and p["seq"] == ref]
    if not main:
        det = [p["cs"] for p in places if p["where"] == "detail" and p["seq"] == ref]
        return ("detail" if det else "other-seq"), None
    c = w["chunk"]
    wf = rec["start"] // c * c
    wl = (rec["end"] - 1) // c * c
    dist = min(0 if wf <= cs <= wl else (wf - cs) // c if cs < wf else (cs - wl) // c for cs in main)
    read = set(w["chunksRead"])
    if any(cs in read for cs in main):
        return "read", dist
    if any(w["reachLo"] <= cs <= w["reachHi"] for cs in main):
        return "reach", dist
    return "beyond", dist


def load(name):
    ref, recs = None, []
    for line in open(f"out/{name}.jsonl"):
        r = json.loads(line)
        if "meta" in r:
            ref = r["meta"]["ref"]
            meta = r["meta"]
        else:
            recs.append(r)
    try:
        rv = json.load(open(f"out/{name}.refvisits.json"))
        visits = {int(k): set(v) for k, v in rv.get("visits", rv).items()}
        undrawn = {int(k): v for k, v in rv.get("undrawn", {}).items()}
    except FileNotFoundError:
        visits, undrawn = {}, {}
    try:
        chunks = {int(k): v for k, v in json.load(open(f"out/{name}.chunks.json")).items()}
    except FileNotFoundError:
        chunks = {}
    return meta, ref, recs, chunks, visits, undrawn


def rows(name):
    meta, ref, recs, chunks, visits, undrawn = load(name)
    out = []
    for r in recs:
        w = r["walk"]
        row = {
            "graph": name, "stratum": r["stratum"], "start": r["start"], "mode": r["mode"],
            "idx_nodes": r["index"]["nodes"], "idx_links": r["index"]["links"],
            "idx_ms": round(r["index"]["ms"]), "idx_kB": round(r["index"]["bytes"] / 1e3),
            "walk_ms": round(w["ms"]), "walk_kB": round(w["bytes"] / 1e3),
            "error": w.get("error", ""),
        }
        # hap8 cut: reference nodes visited on the window and context that
        # the walk view leaves undrawn, of how many
        u = undrawn.get(r["start"])
        if r["mode"] == "hap8" and u is not None:
            row["ref_visits"] = len(visits.get(r["start"], ()))
            row["ref_undrawn"] = len(u) if isinstance(u, list) else u
        if not row["error"]:
            io = r["indexOnly"]
            cls = Counter(str(n["cls"]) for n in io)
            places = Counter()
            dists = []
            onref = visits.get(r["start"], set())
            for n in io:
                n["visited"] = n["rank"] == 0 and int(n["id"]) in onref
                if str(n["cls"]) in ("2", "3", "3?"):
                    n["id"] = int(n["id"])
                    p, d = placement(n, r, chunks, ref)
                    n["place"], n["chunkDist"] = p, d
                    places[f'{n["cls"]}:{p}'] += 1
                    if d is not None:
                        dists.append(d)
            row.update({
                "walk_nodes": w["nodes"], "walk_links": w["links"],
                "idx_only": len(io), **{f"c{c}": cls.get(c, 0) for c in CLASSES},
                # rank 0 nodes the walk file's reference visits on the window
                # and its 1 kb context (c1v, c2v), whatever coordinate the
                # index states, and class 2 nodes it visits only elsewhere
                "c1v": sum(1 for n in io if n["cls"] == 1 and n["visited"]),
                "c2v": sum(1 for n in io if n["cls"] == 2 and n["visited"]),
                "c2o": sum(1 for n in io if n["cls"] == 2 and not n["visited"]),
                # class 3 by what the walk view shows of the selected carriers:
                # a walk of one (the node lies on it outside the drawn stretch),
                # only a skip row, or nothing
                "c3walked": sum(1 for n in io if n.get("sub") == "walked"),
                "c3skip": sum(1 for n in io if n.get("sub") == "skip"),
                "c3none": sum(1 for n in io if n.get("sub") == "none"),
                "open": len(w.get("open", [])),
                "followed": any(c < w["readFrom"] or c > (r["end"] - 1) // w["chunk"] * w["chunk"] for c in w["chunksRead"]),
                "walk_only": r["walkOnly"]["n"],
                "idx_only_links": r["indexOnlyLinks"],
                "idx_only_links_both_drawn": r["indexOnlyLinksBothDrawn"],
                "walk_only_links": r["walkOnlyLinks"],
                "clean": all(str(n["cls"]) in ("1", "4") for n in io),
                # nodes a user of the walk view loses: on-window reference
                # visits, alleles of selected haplotypes the view shows only as
                # a skip row or not at all, moved-component stubs
                "lost": sum(1 for n in io if (n["rank"] == 0 and n["visited"]) or n.get("sub") in ("skip", "none") or n["cls"] in (5, "3?")),
                "places": dict(places),
                "max_chunk_dist": max(dists) if dists else None,
                "abridged": len(w["abridged"]), "skips": len(w["skips"]),
                "chunks_read": len(w["chunksRead"]),
            })
            row["_io"] = io
            row["_skips"] = w["skips"]
            row["_abridged"] = w["abridged"]
        out.append(row)
    return meta, out


def fmt(x):
    if x is None:
        return "-"
    if isinstance(x, float):
        return f"{x:.0f}" if x >= 10 else f"{x:.1f}"
    return str(x)


def summary(all_rows):
    print("graph\tmode\tstratum\twin\terr\tidx_n\twalk_n\tidx_only\tc1\tc1v\tc2v\tc2o\tc3\tc3walked\tc3skip\tc3none\tc4\tc5\twalk_only\tidxonly_links_both_drawn\tclean\tno_loss\tmax_lost\tidx_ms\twalk_ms\tidx_kB\twalk_kB")
    groups = defaultdict(list)
    for r in all_rows:
        groups[(r["graph"], r["mode"], r["stratum"])].append(r)
        groups[(r["graph"], r["mode"], "ALL")].append(r)
    for (g, mode, s), rs in sorted(groups.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2] == "ALL", kv[0][2])):
        ok = [r for r in rs if not r["error"]]
        m = lambda k: fmt(med([r[k] for r in ok]))
        print("\t".join([g, mode, s, str(len(rs)), str(len(rs) - len(ok)),
                         m("idx_nodes"), m("walk_nodes"), m("idx_only"),
                         m("c1"), m("c1v"), m("c2v"), m("c2o"), m("c3"), m("c3walked"), m("c3skip"), m("c3none"), m("c4"), m("c5"),
                         m("walk_only"), m("idx_only_links_both_drawn"),
                         f'{sum(r["clean"] for r in ok)}/{len(ok)}',
                         f'{sum(r["lost"] == 0 and r["idx_only_links_both_drawn"] == 0 for r in ok)}/{len(ok)}',
                         fmt(max([r["lost"] for r in ok], default=None)),
                         fmt(med([r["idx_ms"] for r in rs])), fmt(med([r["walk_ms"] for r in rs])),
                         fmt(med([r["idx_kB"] for r in rs])), fmt(med([r["walk_kB"] for r in rs]))]))


def worst(all_rows, mode, k=4):
    print(f"\n# worst windows, {mode}: by nodes lost")
    for g in sorted({r["graph"] for r in all_rows}):
        rs = [r for r in all_rows if r["graph"] == g and r["mode"] == mode and not r["error"]]
        rs.sort(key=lambda r: -r["lost"])
        for r in rs[:k]:
            if r["lost"] == 0:
                break
            bp = Counter()
            for n in r["_io"]:
                if str(n["cls"]) in ("2", "3", "3?", "5"):
                    bp[str(n["cls"])] += n["len"]
            print(f'{g} {r["stratum"]} {r["start"]}: idx {r["idx_nodes"]} walk {r["walk_nodes"]} '
                  f'lost {r["lost"]} (c1v {r["c1v"]} c2v {r["c2v"]} c2o {r["c2o"]} c3 {r["c3"]} [walked {r["c3walked"]} skip {r["c3skip"]} none {r["c3none"]}] c3? {r["c3?"]} c5 {r["c5"]}; bp {dict(bp)}) '
                  f'places {r["places"]} maxdist {r["max_chunk_dist"]} '
                  f'abridged {r["abridged"]} skips {r["skips"]} open {r["open"]} followed {r["followed"]} links-lost-between-drawn {r["idx_only_links_both_drawn"]}')


def main(names):
    all_rows = []
    for name in names:
        meta, rs = rows(name)
        print(f"# {name}: haplotypes {','.join(meta['haps8'])}", file=sys.stderr)
        all_rows += rs
        keys = [k for k in rs[0] if not k.startswith("_")] if rs else []
        keys = sorted({k for r in rs for k in r if not k.startswith("_")}, key=lambda k: (k not in keys, keys.index(k) if k in keys else 0))
        with open(f"out/{name}.windows.tsv", "w") as f:
            f.write("\t".join(keys) + "\n")
            for r in rs:
                f.write("\t".join(json.dumps(r.get(k, "")) if isinstance(r.get(k), dict) else str(r.get(k, "")) for k in keys) + "\n")
    summary(all_rows)
    for mode in ("hap8", "all"):
        worst(all_rows, mode)
    errs = Counter((r["graph"], r["mode"], r["error"].split("(")[0][:90]) for r in all_rows if r["error"])
    if errs:
        print("\n# budget errors")
        for (g, mode, e), n in sorted(errs.items()):
            print(f"{g}\t{mode}\t{n}\t{e}")


if __name__ == "__main__":
    main(sys.argv[1:])
