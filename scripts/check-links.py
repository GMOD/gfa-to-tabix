#!/usr/bin/env python3
"""check-links.py

Checks every relative link and #anchor in the repository's tracked Markdown
files: the target file has to exist, and an anchor has to match a heading
slug, as GitHub computes it, or an HTML id in the target. Exits 1 on a broken
link. Leaves http(s) and mailto links alone.
"""

import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent
FENCE = re.compile(r"^\s*(```|~~~)")
HEADING = re.compile(r"^#{1,6}\s+(.*?)\s*#*\s*$")
INLINE = re.compile(r"!?\[(?:[^\[\]]|\[[^\]]*\])*\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
DEFINITION = re.compile(r"^\s*\[[^\]]+\]:\s*<?(\S+?)>?(?:\s+\"[^\"]*\")?\s*$")
HTML_TARGET = re.compile(r"""\b(?:href|src)=["']([^"']+)["']""")
HTML_ID = re.compile(r"""\b(?:id|name)=["']([^"']+)["']""")


def prose(path):
    """Yields (line number, line) outside fenced code."""
    fenced = False
    for number, line in enumerate(path.read_text().splitlines(), 1):
        if FENCE.match(line):
            fenced = not fenced
            continue
        if not fenced:
            yield number, line


def slug(heading):
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", heading)
    text = re.sub(r"<[^>]+>", "", text).replace("`", "").lower()
    return re.sub(r"[^\w\- ]", "", text).replace(" ", "-")


def anchors(path):
    found, seen = set(), {}
    for _, line in prose(path):
        found.update(HTML_ID.findall(line))
        match = HEADING.match(line)
        if match:
            base = slug(match.group(1))
            count = seen.get(base, 0)
            seen[base] = count + 1
            found.add(base if count == 0 else f"{base}-{count}")
    return found


def targets(path):
    for number, line in prose(path):
        line = re.sub(r"`[^`]*`", "", line)
        found = INLINE.findall(line) + HTML_TARGET.findall(line)
        definition = DEFINITION.match(line)
        if definition:
            found.append(definition.group(1))
        for target in found:
            yield number, target


def broken(path):
    for number, target in targets(path):
        if re.match(r"[a-z][a-z0-9+.-]*:", target, re.I):
            continue
        file, _, anchor = target.partition("#")
        dest = (path.parent / unquote(file)).resolve() if file else path
        where = f"{path.relative_to(ROOT)}:{number}: {target}"
        if not dest.exists():
            yield f"{where}: no such file"
        elif anchor and dest.suffix == ".md" and unquote(anchor) not in anchors(dest):
            yield f"{where}: no heading or id #{anchor} in {dest.relative_to(ROOT)}"


def main():
    listed = subprocess.run(["git", "ls-files", "*.md"], cwd=ROOT, check=True, capture_output=True, text=True)
    problems = [p for name in listed.stdout.split() for p in broken(ROOT / name)]
    print("\n".join(problems) or "check-links.py: every relative link resolves")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
