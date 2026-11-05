"""S7 from an S file: every line starts `seq start end` with the true extent
of what the row describes, so a line places itself without the table.

  ref       the row's stretch of R: hapOffset to hapOffset + sum(lengths)
  walk      the piece's stretch on R: from the first base of its first R
            step to the last base of its last, over the R positions its
            decoded steps take (route interiors are off R)
  abridged  the same, from its start and end handles' positions on R
  nodes, route  the tile's extent (they belong to the tile, not a position)
  departure lines keep S's end-node extents
  detail records: rows as in the tile, with the record's tile extent

The table keeps S's shape; the per-sequence split is a matter of which
lines a reader fetches, counted in the harness as the sequence's lines.

usage: python3 -I build_s7.py S.walks.gz S.walks.idx OUTPREFIX
"""
import gzip
import struct
import sys
import zlib
from collections import defaultdict

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from decode6 import Chunk, decode_walk, handles, parse_nodes, parse_routes

src, idx_path, out = sys.argv[1:4]
BLOCK = 65280
EOF_BLOCK = bytes.fromhex("1f8b08040000000000ff0600424302001b0003000000000000000000")


class Bgzf:
    def __init__(self, path):
        self.f = open(path, "wb")
        self.buf = bytearray()
        self.offset = 0

    def write(self, data):
        self.buf += data
        while len(self.buf) >= BLOCK:
            self.block(bytes(self.buf[:BLOCK]))
            del self.buf[:BLOCK]

    def flush(self):
        while self.buf:
            self.block(bytes(self.buf[:BLOCK]))
            del self.buf[:BLOCK]

    def block(self, data):
        c = zlib.compressobj(6, zlib.DEFLATED, -15)
        body = c.compress(data) + c.flush()
        blk = (
            b"\x1f\x8b\x08\x04\x00\x00\x00\x00\x00\xff\x06\x00BC\x02\x00"
            + struct.pack("<H", len(body) + 25)
            + body
            + struct.pack("<II", zlib.crc32(data) & 0xFFFFFFFF, len(data))
        )
        self.f.write(blk)
        self.offset += len(blk)

    def close(self):
        self.flush()
        self.f.write(EOF_BLOCK)
        self.f.close()


f = open(src, "rb")


def entry_text(off, size):
    f.seek(off)
    return gzip.decompress(f.read(size)).decode()


entries = [l.rstrip("\n").split("\t") for l in open(idx_path)]
tiles = {}
for e in entries:
    if e[3] == "tile":
        tiles[(e[0], int(e[4]))] = e


def tile_rows(seq, cs, lines):
    """Rows of one tile or detail record with their extents."""
    c = Chunk(seq, cs)
    rows = []
    for line in lines:
        cols = line.split("\t")
        kind = cols[0]
        full = [seq, str(cs), str(cs + 1)] + cols
        if kind == "ref":
            c.ref.append(full)
        elif kind == "nodes":
            parse_nodes(full, c.nodes)
        elif kind == "route":
            c.routes.append(full)
        rows.append((kind, full))
    return c, rows


def with_extents(seq, cs, lines, ref_chunk=None):
    c, rows = tile_rows(seq, cs, lines)
    if ref_chunk is not None:
        c.ref = ref_chunk.ref
        c.nodes.update({k: v for k, v in ref_chunk.nodes.items()})
    c.finish()
    routes = parse_routes([r for k, r in rows if k == "route"])
    lo = min(c.offset) if c.offset else cs
    hi = c.end if c.ref else cs + 65536
    out = []
    for kind, full in rows:
        if kind == "ref":
            start = int(full[6])
            end = start + sum(int(x) for x in full[10].split(","))
        elif kind == "walk":
            p = decode_walk(c, full, routes)
            pos = [a for a, b, d in p.segments] + [b for a, b, d in p.segments]
            if pos:
                start = min(c.offset[i] for i in pos)
                end = max(c.ends[i] for i in pos)
            else:
                start, end = lo, hi
        elif kind == "abridged":
            s_h = int(full[10].split("@")[0])
            e_h = int(full[11].split("@")[0])
            s_i = c.pos[s_h >> 1][int(full[10].split("@")[1]) if "@" in full[10] else 0]
            e_i = c.pos[e_h >> 1][int(full[11].split("@")[1]) if "@" in full[11] else 0]
            a, b = sorted((s_i, e_i))
            start, end = c.offset[a], c.ends[b]
        else:
            start, end = lo, hi
        out.append(f"{seq}\t{start}\t{end}\t" + "\t".join(full[3:]))
    return out, c


w = Bgzf(out + ".walks.gz")
idx = []
chunk_of = {}
for e in entries:
    seq, a, b, kind, name, off, size = e[0], int(e[1]), int(e[2]), e[3], e[4], int(e[5]), int(e[6])
    text = entry_text(off, size)
    start = w.offset
    if kind == "header":
        w.write(text.encode())
    elif kind == "tile":
        lines = [l for l in text.split("\n") if l]
        rows, c = with_extents(seq, int(name), lines)
        chunk_of[(seq, int(name))] = c
        w.write(("\n".join(rows) + "\n").encode())
    elif kind == "departures":
        w.write(text.encode())
    elif kind == "detail":
        cs = int(name.split(":")[0])
        lines = [l for l in text.split("\n") if l]
        rows, _ = with_extents(seq, cs, lines, chunk_of[(seq, cs)])
        w.write(("\n".join(rows) + "\n").encode())
    w.flush()
    idx.append("\t".join([seq, str(a), str(b), kind, name, str(start), str(w.offset - start)]))
w.close()
with open(out + ".walks.idx", "w") as g:
    g.write("\n".join(idx) + "\n")
print("entries", len(idx))
