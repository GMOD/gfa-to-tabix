#!/usr/bin/env python3
# Lists the test titles of a graph-walks checkout's format 7 reader tests,
# one a line, sorted: the list docs/walks-container/reader/graph-walks-tests.txt
# keeps, which check-claims.py checks claims7.md's graph-walks checks against.
# A `test.each(table)(title, ...)` counts once, by its title.
# Usage: scripts/graph-walks-tests.py <graph-walks checkout>
import pathlib
import re
import sys

CALL = re.compile(r'\b(?:test|it)\b(\.each)?\s*\(')


def balanced(text, at):
    # the index after the parenthesis group opening at `at`
    depth = 0
    while at < len(text):
        if text[at] == '(':
            depth += 1
        elif text[at] == ')':
            depth -= 1
            if depth == 0:
                return at + 1
        at += 1
    return at


def title(text, at):
    # the string literal at `at`, or None
    quote = text[at]
    if quote not in '\'"`':
        return None
    out, at = [], at + 1
    while at < len(text) and text[at] != quote:
        if text[at] == '\\':
            at += 1
        out.append(text[at])
        at += 1
    return ' '.join(''.join(out).split())


titles = set()
for path in sorted(pathlib.Path(sys.argv[1], 'src').glob('*.test.ts')):
    text = path.read_text()
    for match in CALL.finditer(text):
        at = match.end()
        if match.group(1):
            at = balanced(text, match.start() + match.group(0).rfind('('))
            rest = re.match(r'\s*\(\s*', text[at:])
            if not rest:
                continue
            at += rest.end()
        else:
            at += len(text[at:]) - len(text[at:].lstrip())
        name = title(text, at)
        if name:
            titles.add(f'{path.name}: {name}')
print('\n'.join(sorted(titles)))
