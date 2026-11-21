#!/usr/bin/env python3
"""Synthetic haplotypes recombined from a GFA's real W lines.

scale-synth.py GFA REF OUT_PREFIX SEED N1 [N2 ...]

Writes OUT_PREFIX.<total>.gfa.gz for each N: every line of GFA unchanged,
then N synthetic haplotypes, <total> = N plus the real haplotypes. The sets
are nested: the first N1 synthetic haplotypes of the largest set make the
smallest. Also OUT_PREFIX.switches.tsv.gz (one row per switch) and
OUT_PREFIX.synth.txt (counts and the junction-link check).

Each synthetic haplotype, SYN0001#1 on, copies the contig layout of a real
haplotype (its template, cycled through the real haplotypes in a shuffled
order). Each synthetic contig starts as the template's contig and switches
to another real haplotype's contig at anchors: nodes the reference REF steps
once that both contigs step exactly once and in REF's orientation. A
contig mostly against REF is turned around first, which is the same path.
Segments are max(500 kb, an exponential draw of mean 6 Mb) of REF; a
contig ends at the first anchor at or past the template contig's last
anchor, or where its donor ends. A junction joins the donor's step into
the anchor to the next donor's step out of it, so its links are both real
walks' links; each is checked against the L lines anyway.

Needs numpy and pigz.
"""

import subprocess
import sys

import numpy as np

MIN_SEGMENT = 500_000
MEAN_SEGMENT = 6_000_000
ANCHOR_WINDOW = 20_000
DONOR_TRIES = 40
TO_SPACE = bytes.maketrans(b"<>", b"  ")


def handle_key(h1, h2):
    a = h1 * (1 << 28) + h2
    b = (h2 ^ 1) * (1 << 28) + (h1 ^ 1)
    return np.minimum(a, b)


class Walk:
    def __init__(self, sample, hap, seq, start, end, text):
        self.sample = sample
        self.hap = hap
        self.seq = seq
        self.start = start
        self.end = end
        self.set_text(text)

    def set_text(self, text):
        self.text = text
        raw = np.frombuffer(text, dtype=np.uint8)
        self.offsets = np.flatnonzero((raw == 62) | (raw == 60)).astype(np.int64)
        self.reverse = raw[self.offsets] == 60
        self.ids = np.fromstring(text.translate(TO_SPACE), dtype=np.int64, sep=" ").astype(np.int32)
        assert len(self.ids) == len(self.offsets)
        self.offsets = np.append(self.offsets, len(text))

    def turned(self):
        return b"".join(
            (b">" if self.reverse[i] else b"<") + self.text[self.offsets[i] + 1 : self.offsets[i + 1]]
            for i in range(len(self.ids) - 1, -1, -1)
        )

    def slice(self, a, b):
        return self.text[self.offsets[a] : self.offsets[b]]

    def handles(self):
        return self.ids.astype(np.int64) * 2 + self.reverse


def read_gfa(path, out_streams, ref):
    lengths = {}
    l_keys = []
    walks = []
    reader = subprocess.Popen(["pigz", "-dc", path], stdout=subprocess.PIPE, bufsize=1 << 24)
    for line in reader.stdout:
        for o in out_streams:
            o.write(line)
        kind = line[:2]
        if kind == b"S\t":
            cols = line.rstrip(b"\n").split(b"\t")
            seq = cols[2]
            n = len(seq)
            if seq == b"*":
                tag = next(c for c in cols[3:] if c.startswith(b"LN:i:"))
                n = int(tag[5:])
            lengths[int(cols[1])] = n
        elif kind == b"L\t":
            cols = line.split(b"\t", 5)
            l_keys.append((int(cols[1]) * 2 + (cols[2] == b"-"), int(cols[3]) * 2 + (cols[4] == b"-")))
        elif kind == b"W\t":
            cols = line.rstrip(b"\n").split(b"\t")
            walks.append(Walk(cols[1], cols[2], cols[3], int(cols[4]), int(cols[5]), cols[6]))
    assert reader.wait() == 0
    top = max(lengths) + 1
    length = np.zeros(top, dtype=np.int64)
    for k, v in lengths.items():
        length[k] = v
    pairs = np.array(l_keys, dtype=np.int64)
    assert pairs.max() < 1 << 28
    keys = np.unique(handle_key(pairs[:, 0], pairs[:, 1]))
    return length, keys, walks


def reference_positions(walks, ref, length):
    top = len(length)
    refpos = np.full(top, -1, dtype=np.int64)
    refrev = np.zeros(top, dtype=bool)
    seen = np.zeros(top, dtype=np.int32)
    for w in walks:
        if w.sample == ref:
            starts = w.start + np.concatenate(([0], np.cumsum(length[w.ids])[:-1]))
            np.add.at(seen, w.ids, 1)
            refpos[w.ids] = starts
            refrev[w.ids] = w.reverse
    refpos[seen != 1] = -1
    return refpos, refrev


def find_anchors(w, refpos, refrev):
    on_ref = refpos[w.ids] >= 0
    same = on_ref & (w.reverse == refrev[w.ids])
    against = on_ref & ~same
    turned = against.sum() > same.sum()
    if turned:
        w.set_text(w.turned())
        on_ref = refpos[w.ids] >= 0
        same = on_ref & (w.reverse == refrev[w.ids])
    steps = np.flatnonzero(same)
    nodes, counts = np.unique(w.ids, return_counts=True)
    steps = steps[~np.isin(w.ids[steps], nodes[counts > 1])]
    pos = refpos[w.ids[steps]]
    order = np.argsort(pos, kind="stable")
    w.anchor_pos = pos[order]
    w.anchor_step = steps[order].astype(np.int64)
    w.first = int(w.anchor_pos[0]) if len(pos) else -1
    w.last = int(w.anchor_pos[-1]) if len(pos) else -1
    return turned


def anchors_from(w, lo, hi, after):
    a = np.searchsorted(w.anchor_pos, lo)
    b = np.searchsorted(w.anchor_pos, hi)
    keep = w.anchor_step[a:b] > after
    return w.anchor_pos[a:b][keep], w.anchor_step[a:b][keep]


def common_anchor(d, d_after, e, s, window):
    dpos, dstep = anchors_from(d, s, s + window, d_after)
    epos, estep = anchors_from(e, s, s + window, -1)
    shared, di, ei = np.intersect1d(d.ids[dstep], e.ids[estep], return_indices=True)
    if len(shared) == 0:
        return None
    best = np.argmin(dpos[di])
    return int(dstep[di[best]]), int(estep[ei[best]]), int(dpos[di[best]])


class Builder:
    def __init__(self, walks, keys, length, rng):
        self.walks = walks
        self.keys = keys
        self.length = length
        self.rng = rng
        self.firsts = np.array([w.first for w in walks])
        self.lasts = np.array([w.last for w in walks])
        self.haps = np.array([hash((w.sample, w.hap)) for w in walks])
        self.junctions = 0
        self.junction_links_missing = 0
        self.switches = []

    def segment(self):
        return max(MIN_SEGMENT, int(self.rng.exponential(MEAN_SEGMENT)))

    def donor_for(self, d, d_after, s, reach):
        window = ANCHOR_WINDOW
        while window <= 64 * ANCHOR_WINDOW:
            fits = (self.firsts <= s) & (self.lasts >= s + window) & (self.haps != hash((d.sample, d.hap)))
            far = fits & (self.lasts >= reach)
            pool = np.flatnonzero(far) if far.sum() >= 8 else np.flatnonzero(fits)
            for k in self.rng.permutation(pool)[:DONOR_TRIES]:
                found = common_anchor(d, d_after, self.walks[k], s, window)
                if found:
                    return self.walks[k], found
            window *= 4
        return None, None

    def junction_ok(self, d, d_step, e, e_step):
        h = np.array([d.handles()[d_step]]), np.array([e.handles()[e_step + 1]])
        key = handle_key(h[0], h[1])[0]
        i = np.searchsorted(self.keys, key)
        return i < len(self.keys) and self.keys[i] == key

    def contig(self, name, template):
        if template.first < 0:
            return [template.text], int(self.length[template.ids].sum())
        pieces = []
        bp = 0
        d = template
        after = -1
        start = 0
        at = template.first
        end_at = template.last
        done = False
        while not done:
            s = at + self.segment()
            if s >= end_at:
                cut = anchors_from(d, end_at, d.last + 1, after)[1]
                stop = int(cut[0]) + 1 if len(cut) and d is not template else len(d.ids)
                pieces.append(d.slice(start, stop))
                bp += int(self.length[d.ids[start:stop]].sum())
                done = True
            else:
                e, found = self.donor_for(d, after, s, min(s + MEAN_SEGMENT, end_at))
                if e is None:
                    pieces.append(d.slice(start, len(d.ids)))
                    bp += int(self.length[d.ids[start:]].sum())
                    done = True
                else:
                    d_step, e_step, pos = found
                    self.junctions += 1
                    if e_step + 1 < len(e.ids) and not self.junction_ok(d, d_step, e, e_step):
                        self.junction_links_missing += 1
                    pieces.append(d.slice(start, d_step + 1))
                    bp += int(self.length[d.ids[start : d_step + 1]].sum())
                    self.switches.append((name, pos, pos - at, d.sample, d.hap, d.seq, e.sample, e.hap, e.seq))
                    d, after, start, at = e, e_step, e_step + 1, pos
        return pieces, bp


def main():
    path, ref, prefix, seed = sys.argv[1], sys.argv[2].encode(), sys.argv[3], int(sys.argv[4])
    counts = sorted(int(n) for n in sys.argv[5:])
    rng = np.random.default_rng(seed)
    sinks = {}
    real_haps = None
    tmp = [open(f"{prefix}.{n}.body.tmp", "wb", buffering=1 << 24) for n in counts]
    length, keys, walks = read_gfa(path, tmp, ref)
    for t in tmp:
        t.close()
    refpos, refrev = reference_positions(walks, ref, length)
    donors = [w for w in walks if w.sample not in (ref, b"CHM13")]
    turned = sum(find_anchors(w, refpos, refrev) for w in donors)
    by_hap = {}
    for w in donors:
        by_hap.setdefault((w.sample, w.hap), []).append(w)
    real_haps = len({(w.sample, w.hap) for w in walks})
    templates = list(by_hap)
    order = rng.permutation(len(templates))
    builder = Builder(donors, keys, length, rng)
    for n in counts:
        total = n + real_haps
        sinks[n] = subprocess.Popen(
            f"cat {prefix}.{n}.body.tmp - | pigz -p 6 > {prefix}.{total}.gfa.gz", shell=True, stdin=subprocess.PIPE
        )
    contigs = 0
    lines_bp = []
    for k in range(counts[-1]):
        sample = f"SYN{k + 1:04d}".encode()
        hap = templates[order[k % len(templates)]]
        for j, template in enumerate(by_hap[hap]):
            name = sample + b"#1#c" + str(j + 1).encode()
            pieces, bp = builder.contig(name.decode(), template)
            line = b"".join([b"W\t", sample, b"\t1\tc", str(j + 1).encode(), b"\t0\t", str(bp).encode(), b"\t", *pieces, b"\n"])
            for n, sink in sinks.items():
                if k < n:
                    sink.stdin.write(line)
            contigs += 1
            lines_bp.append(bp)
        if (k + 1) % 250 == 0:
            print(f"{k + 1} synthetic haplotypes, {builder.junctions} switches", file=sys.stderr, flush=True)
    for n, sink in sinks.items():
        sink.stdin.close()
        assert sink.wait() == 0
        subprocess.run(["rm", f"{prefix}.{n}.body.tmp"], check=True)
    with subprocess.Popen(f"gzip > {prefix}.switches.tsv.gz", shell=True, stdin=subprocess.PIPE) as z:
        z.stdin.write(b"name\tpos\tsegment_bp\tfrom_sample\tfrom_hap\tfrom_seq\tto_sample\tto_hap\tto_seq\n")
        for row in builder.switches:
            z.stdin.write("\t".join(x.decode() if isinstance(x, bytes) else str(x) for x in row).encode() + b"\n")
    seg = np.array([r[2] for r in builder.switches])
    per_hap = np.bincount([int(r[0][3:7]) for r in builder.switches], minlength=counts[-1] + 1)[1:]
    with open(f"{prefix}.synth.txt", "w") as f:
        print(f"real haplotypes (W samples#hap, references included)\t{real_haps}", file=f)
        print(f"donor contigs (W lines, references left out)\t{len(donors)}", file=f)
        print(f"donor contigs turned to face {ref.decode()}\t{turned}", file=f)
        print(f"synthetic haplotypes\t{counts[-1]}", file=f)
        print(f"synthetic contigs\t{contigs}", file=f)
        print(f"switches\t{builder.junctions}", file=f)
        print(f"junction links missing from the L lines\t{builder.junction_links_missing}", file=f)
        print(f"switches per synthetic haplotype, min median max\t{per_hap.min()}\t{int(np.median(per_hap))}\t{per_hap.max()}", file=f)
        print(f"bp from one switch to the next, min median max\t{seg.min()}\t{int(np.median(seg))}\t{seg.max()}", file=f)
        print(f"synthetic contig bp, median\t{int(np.median(lines_bp))}", file=f)
        for n in counts:
            print(f"OUT\t{prefix}.{n + real_haps}.gfa.gz\t{n} synthetic + {real_haps} real", file=f)


main()
