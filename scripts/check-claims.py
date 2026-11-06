#!/usr/bin/env python3
"""Keeps walk format 7's claims and their checks together.

Fails when:
- a claim ID in the docs (`<!-- C76 -->`) has no row in
  docs/departures/claims7.md, or a row names an ID no doc holds;
- a row names no check, or a check that doesn't exist;
- a sentence of walks-format.md or ADR 0010 holding every, each, never,
  always, only, unique or exactly has no claim ID.

The last is a tripwire, not a parser: a sentence ends at a full stop and
space before a capital, or at the end of its paragraph, list item or table,
and a comment right after a full stop belongs to the sentence before it.
A table is one sentence. Code blocks are skipped, and so is a section whose
heading is followed by `<!-- record -->`, a record of measurements or
history, or `<!-- background -->`, about graphs, hosts or other software
rather than the file; the script names each section it skips.

A check is `kind:what`, in backticks in the row's Check column:
- `build:f` and `test:f`, a function `f` in src/ or tests/
- `claims7:ID`, a claim of docs/departures/scripts/claims7.py
- `verify7:text` and `audit7:text`, text in verify7.py or audit7.py
- `script:path`, a file of the repository that runs the check
- `graph-walks:title`, a test of graph-walks' format 7 reader, as
  docs/walks-container/reader/graph-walks-tests.txt lists them. With
  GRAPH_WALKS=<checkout>, the list must also match that checkout's tests

Usage: scripts/check-claims.py
"""
import os
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
TRIPPED = ['docs/walks-format.md', 'docs/adr/0010-walks-unit-table.md']
CLAIMED = TRIPPED + ['docs/adr/0009-departure-records.md', 'README.md']
TABLE = ROOT / 'docs/departures/claims7.md'
TESTS = ROOT / 'docs/walks-container/reader/graph-walks-tests.txt'
UNIVERSAL = re.compile(r'\b(every|each|never|always|only|unique|exactly)\b', re.I)
ID = re.compile(r'<!--((?:\s*C\d+)+)\s*-->')
failures = []


def fail(message):
    failures.append(message)


def text_of(path):
    return (ROOT / path).read_text()


def blocks(text):
    # paragraphs, list items and tables, outside code, with each block's
    # line and whether its section is a record
    out, block, start, fenced, record, level = [], [], 0, False, False, 7
    lines = text.split('\n')
    for n, line in enumerate(lines, 1):
        if line.startswith('```'):
            fenced = not fenced
            continue
        if fenced:
            continue
        heading = re.match(r'(#+) ', line)
        if heading:
            depth = len(heading.group(1))
            if record and depth <= level:
                record = False
            if not record and n < len(lines) and lines[n].strip() in ('<!-- record -->', '<!-- background -->'):
                record, level = True, depth
                print(f'check-claims: skipping {lines[n].strip()[5:-4]} {line.strip()}')
        starts = (not line.strip() or heading or re.match(r'\s{0,2}([-*]|\d+\.) ', line)
                  or (line.startswith('|') and not (block and block[-1].startswith('|'))))
        if starts and block:
            out.append((start, ' '.join(block), record))
            block = []
        if line.strip() and not heading:
            if not block:
                start = n
            block.append(line.strip())
    if block:
        out.append((start, ' '.join(block), record))
    merged = []
    for start, body, record in out:
        if merged and ID.fullmatch(body.strip()) and merged[-1][1].startswith('|'):
            merged[-1] = (merged[-1][0], merged[-1][1] + ' ' + body, merged[-1][2])
        else:
            merged.append((start, body, record))
    return merged


def sentences(body):
    if body.startswith('|'):
        return [body]
    body = re.sub(r'\.\s+((?:<!--[^>]*-->\s*)+)', r' \1. ', body)
    return re.split(r'(?<=\.)\s+(?=[A-Z`*\[(])', body)


doc_ids = {}
for path in CLAIMED:
    text = text_of(path)
    for match in ID.finditer(text):
        line = text.count('\n', 0, match.start()) + 1
        for claim in match.group(1).split():
            doc_ids.setdefault(claim, f'{path}:{line}')
    if path in TRIPPED:
        for start, body, record in blocks(text):
            if record:
                continue
            for sentence in sentences(body):
                word = UNIVERSAL.search(ID.sub('', sentence))
                if word and not ID.search(sentence):
                    fail(f'{path}:{start}: "{word.group(0)}" in a sentence with no claim ID: '
                         f'{sentence[:100]}')

rows = {}
for n, line in enumerate(TABLE.read_text().split('\n'), 1):
    cells = [c.strip() for c in line.strip().strip('|').split('|')]
    if line.startswith('| C') and re.fullmatch(r'C\d+', cells[0]):
        if cells[0] in rows:
            fail(f'claims7.md:{n}: {cells[0]} has two rows')
        rows[cells[0]] = (n, cells)

sources = {
    'src': '\n'.join(p.read_text() for p in (ROOT / 'src').glob('*.rs')),
    'tests': '\n'.join(p.read_text() for p in (ROOT / 'tests').glob('*.rs')),
    'claims7': text_of('docs/departures/scripts/claims7.py'),
    'verify7': text_of('docs/departures/scripts/verify7.py'),
    'audit7': text_of('docs/departures/scripts/audit7.py'),
}
reader_tests = set(TESTS.read_text().split('\n')) - {''}


def exists(kind, what):
    if kind == 'build':
        return re.search(rf'\bfn {re.escape(what)}\b', sources['src'])
    if kind == 'test':
        return re.search(rf'\bfn {re.escape(what)}\b', sources['tests'] + sources['src'])
    if kind == 'claims7':
        return f"claim('{what}'," in sources['claims7']
    if kind in ('verify7', 'audit7'):
        return what in sources[kind]
    if kind == 'script':
        return (ROOT / what).is_file()
    if kind == 'graph-walks':
        return what in reader_tests
    return False


for claim, (n, cells) in sorted(rows.items(), key=lambda kv: int(kv[0][1:])):
    if claim not in doc_ids:
        fail(f'claims7.md:{n}: {claim} is in no doc')
    checks = re.findall(r'`([a-z0-9-]+):([^`]+)`', cells[2] if len(cells) > 2 else '')
    if not checks:
        fail(f'claims7.md:{n}: {claim} names no check')
    for kind, what in checks:
        if not exists(kind, what):
            fail(f'claims7.md:{n}: {claim}: no check {kind}:{what}')
for claim, where in sorted(doc_ids.items(), key=lambda kv: int(kv[0][1:])):
    if claim not in rows:
        fail(f'{where}: {claim} has no row in claims7.md')

if os.environ.get('GRAPH_WALKS'):
    found = subprocess.run([sys.executable, '-I', str(ROOT / 'scripts/graph-walks-tests.py'),
                            os.environ['GRAPH_WALKS']], capture_output=True, text=True, check=True).stdout
    if set(found.split('\n')) - {''} != reader_tests:
        fail(f'{TESTS.relative_to(ROOT)} differs from the tests in {os.environ["GRAPH_WALKS"]}; '
             'regenerate it with scripts/graph-walks-tests.py')

for message in failures:
    print(message)
print(f'check-claims: {len(doc_ids)} claim IDs, {len(rows)} rows, {len(failures)} failures')
sys.exit(1 if failures else 0)
