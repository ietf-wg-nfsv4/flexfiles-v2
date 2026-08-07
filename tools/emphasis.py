#!/usr/bin/env python3
"""Report Markdown bold outside ~~~ fences, including spans that wrap lines.

A per-line `grep` for `\\*\\*...\\*\\*` misses emphasis broken across a line
break, which is most of it in a wrapped draft: a 2026-08-06 review found
ten sites where the line-based sweep found seven.  Exits 1 on any hit.

Usage: tools/emphasis.py <draft.md>
"""
import re
import sys

src = open(sys.argv[1]).read().split('\n')
text, charline, fence = [], [], False
for n, line in enumerate(src, 1):
    if line.startswith('~~~'):
        fence = not fence
        line = ''                     # keep the line count, drop the content
    elif fence:
        line = ''
    seg = line + '\n'
    text.append(seg)
    charline.extend([n] * len(seg))

joined = ''.join(text)
hits = [(charline[m.start()], ' '.join(m.group(1).split()))
        for m in re.finditer(r'\*\*([^*]+?)\*\*', joined, re.S)]
for n, body in hits:
    print(f"{sys.argv[1]}:{n}: **{body[:60]}**")
sys.exit(1 if hits else 0)
