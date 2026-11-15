#!/usr/bin/env python3
"""Shows that two walk files of one GFA and options differ only by tags
added at the end of the `#walks` line, as ADR 0015's graph:Z: and
leftout:i: are.

Passes when:
- the new data's `#walks` line is the old one with tags appended, and the
  directory's line 1 is the new `#walks` line plus bytes:i:;
- every other decompressed line is the same, but an `#entry` line's
  offset, which is the old one moved by the change in compressed size of
  the header unit and of the table units before it, the only units whose
  text changes;
- every byte of the data outside the header and table units is the same,
  units and EOF block alike;
- the directory's `#header` line states the new header's length and each
  sequence line its table's old offset moved the same way.

Reads both files a line or a block at a time, so it runs on whole-genome
files in little memory.

Usage: walks-header-diff.py old.walks.gz new.walks.gz [--tags graph,leftout]
"""
import argparse
import gzip
import itertools
import sys


def directory(path):
    with open(path + '.idx', 'rb') as f:
        lines = [line.rstrip(b'\n').split(b'\t') for line in f]
    header = next(int(c[2]) for c in lines if c[0] == b'#header')
    tables = [(c[0], int(c[1]), int(c[2])) for c in lines[1:] if c[0] != b'#header']
    return lines, header, tables


def same_bytes(old, new, spans, fail):
    """Compares old and new over (old start, new start, length) spans."""
    with open(old, 'rb') as a, open(new, 'rb') as b:
        for at_old, at_new, length in spans:
            a.seek(at_old)
            b.seek(at_new)
            left = length
            while left:
                n = min(left, 1 << 20)
                if a.read(n) != b.read(n):
                    fail(f'bytes differ in old {at_old}-{at_old + length}, new {at_new}-{at_new + length}')
                    break
                left -= n


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('old')
    p.add_argument('new')
    p.add_argument('--tags', default='graph,leftout', help='the names of the tags the new #walks line adds, in order')
    args = p.parse_args()
    failures = []
    fail = failures.append
    names = args.tags.split(',')
    old_dir, old_header, old_tables = directory(args.old)
    new_dir, new_header, new_tables = directory(args.new)
    if len(old_tables) != len(new_tables) or [t[0] for t in old_tables] != [t[0] for t in new_tables]:
        sys.exit(f'{args.new}: the directories list other sequences')
    growth = [(at, new[2] - length) for (_, at, length), new in zip(old_tables, new_tables)]

    def moved(offset):
        return offset + new_header - old_header + sum(d for at, d in growth if at < offset)

    added = None
    entries = 0
    with gzip.open(args.old, 'rb') as a, gzip.open(args.new, 'rb') as b:
        for n, (x, y) in enumerate(itertools.zip_longest(a, b), 1):
            if x is None or y is None:
                fail(f'line {n}: one file ends before the other')
                break
            if x == y:
                continue
            if n == 1 and y.startswith(x.rstrip(b'\n') + b'\t'):
                added = y[len(x):].rstrip(b'\n').split(b'\t')
                if [t.split(b':')[0].decode() for t in added] != names:
                    fail(f'the #walks line adds {b" ".join(added).decode()}, not tags {", ".join(names)}')
                continue
            c, d = x.rstrip(b'\n').split(b'\t'), y.rstrip(b'\n').split(b'\t')
            if c[0] == b'#entry' and len(c) == len(d) == 8 and c[:6] == d[:6] and c[7] == d[7] \
                    and int(d[6]) == moved(int(c[6])):
                entries += 1
                continue
            fail(f'line {n} differs: {x[:120]!r} -> {y[:120]!r}')
            if len(failures) > 20:
                break
    if added is None:
        fail('the #walks line adds no tags')

    walks_line = None
    with gzip.open(args.new, 'rb') as f:
        walks_line = f.readline().rstrip(b'\n').split(b'\t')
    if new_dir[0][:-1] != walks_line or not new_dir[0][-1].startswith(b'bytes:i:'):
        fail("the new directory's line 1 is not its #walks line plus bytes:i:")
    if old_dir[0][:-1] + (added or []) != new_dir[0][:-1]:
        fail("the directories' line 1 differ by more than the added tags")
    with open(args.new, 'rb') as f:
        f.seek(0, 2)
        if new_dir[0][-1] != b'bytes:i:%d' % f.tell():
            fail("the new directory's bytes:i: is not the data file's length")
    for (seq, at, _), (_, at2, _) in zip(old_tables, new_tables):
        if at2 != moved(at):
            fail(f'the table of {seq.decode(errors="replace")} is at {at2}, not {moved(at)}')

    spans, at, at2 = [], old_header, new_header
    for (_, start, length), (_, start2, length2) in zip(old_tables, new_tables):
        if start - at != start2 - at2:
            fail(f'the units before the table at {start2} take {start2 - at2} bytes, not {start - at}')
        spans.append((at, at2, min(start - at, start2 - at2)))
        at, at2 = start + length, start2 + length2
    with open(args.old, 'rb') as f, open(args.new, 'rb') as g:
        f.seek(0, 2)
        g.seek(0, 2)
        if f.tell() - at != g.tell() - at2:
            fail('the units after the last table take other bytes')
        spans.append((at, at2, min(f.tell() - at, g.tell() - at2)))
    same_bytes(args.old, args.new, spans, fail)

    for message in failures:
        print(f'{args.new}: {message}')
    print(f'{args.new}: header {old_header} -> {new_header} bytes, adds {b" ".join(added or []).decode()}, '
          f'tables {sum(t[2] for t in old_tables)} -> {sum(t[2] for t in new_tables)} bytes, '
          f'{entries} #entry offsets and {len(new_tables)} directory offsets moved, '
          f'{sum(s[2] for s in spans)} other bytes compared, {len(failures)} differences')
    sys.exit(1 if failures else 0)


main()
