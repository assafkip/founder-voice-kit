#!/usr/bin/env python3
"""Sweep the shipped slop-shape patterns over YOUR OWN writing before trusting them.

Run this FIRST. The shapes in `config/slop-shapes.json` block by default, and a
blocking word-pattern that matches its own author is the classic failure of this
whole category of tool: the gate goes on, the author's real voice starts getting
refused, and the author concludes the tool is broken rather than the pattern.

    python3 scripts/check-slop-shapes-against-corpus.py path/to/your-samples/

Point it at your published posts, your sent emails, whatever you actually wrote.
Zero hits means the defaults are safe to leave blocking. Any hit means that pattern
is part of how you write, and you should turn it off in
`config/slop-shapes.local.json` rather than let it silence you.

Reference point: the shipped defaults were swept over a 103-post corpus and scored
zero hits before they were made blocking. A looser variant of the contrast-bridge
pattern scored one hit on that same corpus and was REJECTED for it.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_shapes():
    with open(os.path.join(HERE, "config", "slop-shapes.json"), encoding="utf-8") as fh:
        return json.load(fh)["shapes"]


def texts_under(root):
    if os.path.isfile(root):
        yield root, open(root, encoding="utf-8", errors="ignore").read()
        return
    for base, _dirs, files in os.walk(root):
        for name in files:
            path = os.path.join(base, name)
            try:
                yield path, open(path, encoding="utf-8", errors="ignore").read()
            except OSError:
                continue


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    shapes = load_shapes()
    hits = []
    scanned = 0
    for path, text in texts_under(argv[1]):
        scanned += 1
        for shape in shapes:
            found = re.search(shape["pattern"], text)
            if found:
                hits.append((shape["rule"], path, found.group().strip()[:70]))
    print("scanned %d file(s) against %d shape(s)" % (scanned, len(shapes)))
    print("")
    if not hits:
        print("0 hits. The shipped defaults do not match your writing, so leaving")
        print("them blocking cannot silence you.")
        return 0
    print("%d hit(s). Each one is a shape YOU use:" % len(hits))
    print("")
    for rule, path, snippet in hits:
        print("  %s" % rule)
        print("    %s" % path)
        print("    %r" % snippet)
        print("")
    print("Turn these off in config/slop-shapes.local.json. A pattern that matches")
    print("your real writing is your voice, not slop.")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
