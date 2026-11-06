#!/usr/bin/env python3
# A BGZF file's size if each of its blocks were deflated again by zlib at the
# given levels, keeping every block boundary: per level, the total bytes,
# and the blocks' uncompressed sizes. usage: reblock.py f.gz [level ...]
import json, struct, sys, zlib
path, levels = sys.argv[1], [int(x) for x in sys.argv[2:]] or [6]
data = open(path, 'rb').read()
at, sizes, raw, blocks = 0, {l: 0 for l in levels}, 0, 0
while at < len(data):
    bsize = struct.unpack_from('<H', data, at + 16)[0] + 1
    text = zlib.decompress(data[at + 18: at + bsize - 8], -15)
    raw += len(text)
    blocks += 1
    for l in levels:
        c = zlib.compressobj(l, zlib.DEFLATED, -15)
        sizes[l] += 26 + len(c.compress(text) + c.flush())
    at += bsize
print(json.dumps({'file': path, 'bytes': len(data), 'blocks': blocks, 'uncompressed': raw,
                  'recompressed by zlib ' + zlib.ZLIB_VERSION: sizes}))
