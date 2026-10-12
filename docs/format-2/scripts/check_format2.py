"""Decodes format-2 walk rows independently of the Rust encoder and compares
every piece with a format-1 build of the same graph: path, fragStart,
hapOffset and steps. Format-1 rows of one piece split by --cap are joined.

usage: check_format2.py NEW.walks.bed.gz OLD.walks.bed.gz SEQ CHUNK mb [mb ...]
       (or --every K to check every K-th chunk of SEQ up to --end BP)
"""
import subprocess
import sys
from collections import defaultdict

NONE = None


def rows(path, seq, start):
    out = subprocess.run(
        ["tabix", path, f"{seq}:{start + 1}-{start + 1}"],
        capture_output=True, text=True, check=True,
    ).stdout
    return [line.split("\t") for line in out.splitlines()]


def deltas(tokens, previous=0):
    """Handles from delta tokens, each 2 * (id - previous id) + reverse."""
    out = []
    for tok in tokens:
        d = int(tok)
        r = d & 1
        previous += (d - r) // 2
        out.append(2 * previous + r)
    return out, previous


def split_list(field):
    return [] if field == "." else field.split(",")


class Path:
    def __init__(self, handles):
        self.handles = handles
        self.occ = defaultdict(list)
        for i, h in enumerate(handles):
            self.occ[h >> 1].append(i)

    def first(self, h):
        return self.occ[h >> 1][0]

    def nearest(self, h, i):
        best = None
        for j in self.occ[h >> 1]:
            if best is None or abs(j - i) <= abs(best - i):
                best = j
        return best

    def step(self, i, h):
        if self.handles[i] == h:
            return i + 1, self.handles[i + 1]
        return i - 1, self.handles[i - 1] ^ 1


def flipped(route):
    e, interior, x = route
    return (
        NONE if x is NONE else x ^ 1,
        [h ^ 1 for h in reversed(interior)],
        NONE if e is NONE else e ^ 1,
    )


def decode_walk(path, routes, start, end_field, choices_field):
    end_parts = end_field.split(":")
    end = start + int(end_parts[0])
    counted = len(end_parts) > 1
    tail = int(end_parts[1]) if counted else None
    choices = []
    previous = 0
    for tok in split_list(choices_field):
        parts = tok.split(":")
        d = int(parts[0])
        flip = d & 1
        previous += (d - flip) // 2
        route = routes[previous]
        choices.append((flipped(route) if flip else route, int(parts[1]) if counted else None))
    steps = []
    k = 0
    if choices and choices[0][0][0] is NONE:
        steps += choices[0][0][1]
        k = 1
    h = start
    i = path.first(h)
    steps.append(h)

    def follow(target, count):
        nonlocal h, i
        taken = 0
        while (taken < count) if counted else (h != target):
            i, h = path.step(i, h)
            steps.append(h)
            taken += 1

    for (e, interior, x), count in choices[k:]:
        assert e is not NONE, "an open route after the first choice"
        follow(e, count)
        assert h == e, "a walk misses its route's entry"
        steps += interior
        if x is NONE:
            return steps
        h = x
        i = path.nearest(h, i)
        steps.append(h)
    follow(end, tail)
    assert h == end, "a walk misses its last reference handle"
    return steps


def decode_chunk(lines):
    refs = sorted((r for r in lines if r[3] == "ref"), key=lambda r: int(r[6]))
    path = Path([h for r in refs for h in deltas(split_list(r[9]))[0]])
    routes = []
    previous = 0
    for r in (r for r in lines if r[3] == "route"):
        parts = []
        for field in r[4:7]:
            if field == ".":
                parts.append([])
            else:
                hs, previous = deltas(field.split(","), previous)
                parts.append(hs)
        entry = parts[0][0] if r[4] != "." else NONE
        exit_ = parts[2][0] if r[6] != "." else NONE
        routes.append((entry, parts[1], exit_))
    pieces = []
    for r in refs:
        pieces.append((r[4], int(r[5]), int(r[6]), int(r[7]), deltas(split_list(r[9]))[0], r[8]))
    for r in (r for r in lines if r[3] == "walk"):
        steps = decode_walk(path, routes, int(r[9]), r[10], r[11])
        assert len(steps) == int(r[8]), f"{r[4]}: {len(steps)} steps against nsteps {r[8]}"
        pieces.append((r[4], int(r[5]), int(r[6]), int(r[7]), steps, r[8]))
    return pieces, len(routes)


def old_pieces(lines):
    by_path = defaultdict(list)
    for r in lines:
        by_path[(r[3], int(r[4]))].append(r)
    out = []
    for (name, frag), rs in by_path.items():
        rs.sort(key=lambda r: int(r[6]))
        group = [rs[0]]
        for r in rs[1:] + [None]:
            if r is not None and int(r[6]) == int(group[-1][6]) + 1:
                group.append(r)
                continue
            steps = [h for g in group for h in deltas(g[8].split(","))[0]]
            out.append((name, frag, int(group[0][5]), steps))
            if r is not None:
                group = [r]
    return out


def check(new, old, seq, start):
    pieces, n_routes = decode_chunk(rows(new, seq, start))
    got = sorted((p[0], p[1], p[2], tuple(p[4])) for p in pieces)
    want = sorted((p[0], p[1], p[2], tuple(p[3])) for p in old_pieces(rows(old, seq, start)))
    return got == want, len(got), sum(len(p[3]) for p in got), n_routes, got, want


if __name__ == "__main__":
    args = sys.argv[1:]
    new, old, seq, chunk = args[:4]
    chunk = int(chunk)
    rest = args[4:]
    starts = []
    if rest and rest[0] == "--every":
        every = int(rest[1])
        end = int(rest[3]) if len(rest) > 3 else 51_000_000
        starts = list(range(0, end, chunk * every))
    else:
        starts = [int(float(mb) * 1e6) // chunk * chunk for mb in rest]
    bad = 0
    total_pieces = total_steps = 0
    for start in starts:
        ok, n, steps, n_routes, got, want = check(new, old, seq, start)
        total_pieces += n
        total_steps += steps
        if not ok:
            bad += 1
            missing = set(want) - set(got)
            extra = set(got) - set(want)
            print(f"{start}: MISMATCH {len(missing)} missing, {len(extra)} extra", flush=True)
            for p in list(missing)[:2]:
                print("  want", p[:3], len(p[3]))
            for p in list(extra)[:2]:
                print("  got ", p[:3], len(p[3]))
    print(f"{len(starts)} chunks, {total_pieces} pieces, {total_steps} steps, {bad} chunks differ")
    sys.exit(1 if bad else 0)
