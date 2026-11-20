#!/usr/bin/env python3
"""Print every W or P line a walk file holds, as `path start end steps`.

The reader docs/walks-format-in-brief.md describes. It reads the directory,
each sequence's table and every unit, rebuilds the reference's lines from
their `ref` rows and every other line from its `walk` rows, and joins each
line's pieces in order. A viewer fetches the byte ranges of the units over
its window where this script reads the whole file.

Usage: scripts/walks-brief.py FILE.walks.gz
"""
import gzip
import re
import sys
from collections import defaultdict


def split(token):
    difference = token // 2
    return difference, token - 2 * difference


def handles(column, previous=0):
    out = []
    for token in ([] if column == '.' else column.split(',')):
        difference, reverse = split(int(token))
        previous += difference
        out.append(2 * previous + reverse)
    return out, previous


def flipped(route):
    entry, interior, leave = route
    return (leave if leave is None else leave ^ 1,
            [h ^ 1 for h in reversed(interior)],
            entry if entry is None else entry ^ 1)


def lines_of(data, offset, length):
    text = gzip.decompress(data[offset:offset + length]).decode()
    return [line.split('\t') for line in text.splitlines()]


def units_of(path):
    data = open(path, 'rb').read()
    walks, _, *later = (line.split('\t') for line in open(path + '.idx').read().split('\n') if line)
    if 'format:i:8' not in walks:
        sys.exit(f'{path} is not walk format 8')
    units = {}
    for _, offset, length in (line for line in later if not line[0].startswith('#')):
        for _, seq, _, _, kind, name, at, size in lines_of(data, int(offset), int(length))[1:]:
            units[(seq, kind, name)] = lines_of(data, int(at), int(size))[1:]
    return units


def reference_path(rows):
    path = []
    for row in sorted((r for r in rows if r[3] == 'ref'), key=lambda r: int(r[6])):
        offset = int(row[6])
        for handle, length in zip(handles(row[9])[0], map(int, row[10].split(','))):
            path.append((handle, length, offset))
            offset += length
    return path


def pieces_of(rows, R):
    places = defaultdict(list)
    for i, (handle, _, _) in enumerate(R):
        places[handle >> 1].append(i)
    lengths = {}
    routes = []
    previous = 0
    pieces = []
    for row in rows:
        if row[3] == 'nodes':
            node = 0
            for difference, length in zip(row[4].split(','), row[5].split(',')):
                node += int(difference)
                lengths[node] = int(length)
        elif row[3] == 'route':
            entry, previous = handles(row[4], previous)
            interior, previous = handles(row[5], previous)
            leave, previous = handles(row[6], previous)
            routes.append((entry[0] if entry else None, interior, leave[0] if leave else None))
        elif row[3] == 'walk':
            pieces.append((row[4], int(row[5]), int(row[7]), walk(row, R, places, routes, lengths)))
    return pieces


def walk(row, R, places, routes, lengths):
    nsteps, start, choices = int(row[8]), row[9].split('@'), row[10]
    handle = int(start[0])
    at = places[handle >> 1][int(start[1]) if len(start) > 1 else 0]
    taken = []
    route = 0
    for choice in ([] if choices == '.' else choices.split(',')):
        token, leave_at, land_at = re.fullmatch(r'(-?\d+)(?::(\d+))?(?:@(\d+))?', choice).groups()
        difference, flip = split(int(token))
        route += difference
        taken.append((flipped(routes[route]) if flip else routes[route], leave_at, land_at))

    def off_reference(interior):
        return [(h, lengths[h >> 1], None) for h in interior]

    steps = off_reference(taken.pop(0)[0][1]) if taken and taken[0][0][0] is None else []
    steps.append((handle, R[at][1], R[at][2]))

    def along_reference():
        nonlocal handle, at
        forward = R[at][0] == handle
        at += 1 if forward else -1
        handle = R[at][0] if forward else R[at][0] ^ 1
        steps.append((handle, R[at][1], R[at][2]))

    for (entry, interior, leave), leave_at, land_at in taken:
        while handle != entry if leave_at is None else at != places[entry >> 1][int(leave_at)]:
            along_reference()
        steps += off_reference(interior)
        if leave is not None:
            here = at
            at = (places[leave >> 1][int(land_at)] if land_at is not None
                  else min(places[leave >> 1], key=lambda place: (abs(place - here), -place)))
            handle = leave
            steps.append((handle, R[at][1], R[at][2]))
    while len(steps) < nsteps:
        along_reference()
    return steps


def lines_in(units):
    lines = defaultdict(list)
    for (seq, kind, name), rows in units.items():
        if kind == 'tile':
            R = reference_path(rows)
            pieces = pieces_of(rows, R)
            for detail in sorted({row[10] for row in rows if row[3] == 'abridged'}):
                pieces += pieces_of(units[(seq, 'detail', f'{name}:{detail}')], R)
            for row in rows:
                if row[3] == 'ref':
                    steps = zip(handles(row[9])[0], map(int, row[10].split(',')))
                    pieces.append((row[4], int(row[5]), int(row[7]), [(h, length, None) for h, length in steps]))
            for path, start, piece, steps in pieces:
                lines[(path, start)].append((piece, steps))
    return lines


if __name__ == '__main__':
    for (path, start), pieces in sorted(lines_in(units_of(sys.argv[1])).items()):
        steps = [step for _, part in sorted(pieces, key=lambda p: p[0]) for step in part]
        text = ''.join(('<' if handle & 1 else '>') + str(handle >> 1) for handle, _, _ in steps)
        print(path, start, start + sum(length for _, length, _ in steps), text, sep='\t')
