#!/usr/bin/env python3
"""Report XDR allocations across the flexible file v2 layout draft family.

Reads the XDR blocks out of the three drafts and prints the operation,
callback, and error-code ledgers, plus any name or value collision.
Exits non-zero if a collision is found, so it can gate a publish.

Usage:
    tools/xdr-map.py [path-to-ietf-checkouts]

Defaults to assuming the three repositories are siblings of this one.
"""
import os
import re
import sys
from collections import defaultdict

ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', '..')

DOCS = [
    ('base',  'flexfiles-v2/draft-haynes-nfsv4-flexfiles-v2.md'),
    ('proxy', 'flexfiles-v2-proxy-server/'
              'draft-haynes-nfsv4-flexfiles-v2-proxy-server.md'),
    ('delta', 'flexfiles-v2-delta-writes/'
              'draft-haynes-nfsv4-flexfiles-v2-delta-writes.md'),
]


def xdr_text(path):
    """The XDR lines (/// inside ~~~ fences) of a draft, as one string."""
    out, fence = [], False
    for line in open(path).read().split('\n'):
        if line.startswith('~~~'):
            fence = not fence
            continue
        if fence:
            m = re.match(r'^\s*///\s?(.*)$', line)
            if m:
                out.append(m.group(1))
    return '\n'.join(out)


def main():
    ops, cbs, errs = {}, {}, {}
    names, consts = defaultdict(set), defaultdict(set)
    collisions = []
    missing = []

    for key, rel in DOCS:
        path = os.path.normpath(os.path.join(ROOT, rel))
        if not os.path.exists(path):
            missing.append(rel)
            continue
        x = xdr_text(path)
        prose = open(path).read()

        for name, val in re.findall(r'\b(OP_CB_[A-Z_0-9]+)\s*=\s*(\d+)', x):
            cbs.setdefault(int(val), []).append((name, key))
        for name, val in re.findall(r'(?<![A-Z_])(OP_[A-Z_0-9]+)\s*=\s*(\d+)', x):
            if name.startswith('OP_CB_'):
                continue
            ops.setdefault(int(val), []).append((name, key))
        for name, val in re.findall(r'(NFS4ERR_[A-Z_0-9]+)\s*=\s*(\d+)', x):
            errs.setdefault(int(val), []).append((name, key))
        # error codes some drafts declare only in prose
        for name, val in re.findall(r'(NFS4ERR_[A-Z_0-9]+)\s*=\s*(\d{5})', prose):
            entry = (name, key + ' (prose only)')
            if int(val) not in errs:
                errs.setdefault(int(val), []).append(entry)

        for n in re.findall(r'^\s*(?:struct|enum|union)\s+([A-Za-z_]\w*)', x, re.M):
            names[n].add(key)
        for n in re.findall(r'typedef\s+\S+\s+([A-Za-z_]\w*)', x):
            names[n].add(key)
        for n in re.findall(r'const\s+([A-Z][A-Z0-9_]*)\s*=', x):
            consts[n].add(key)

    if missing:
        print('WARNING: not found (is the checkout a sibling?):')
        for m in missing:
            print(f'  {m}')
        print()

    def ledger(title, table, nxt_from):
        print(title)
        for val in sorted(table):
            for name, who in table[val]:
                print(f'  {val:6}  {name:38}  {who}')
            if len(table[val]) > 1:
                collisions.append(f'value {val} claimed by '
                                  f'{[w for _, w in table[val]]}')
        if table:
            free = max(table) + 1
            gaps = [i for i in range(nxt_from, max(table)) if i not in table]
            print(f'  next free: {free}'
                  + (f'   gaps: {gaps}' if gaps else ''))
        print()

    ledger('OPERATIONS (nfs_opnum4)', ops, 78)
    ledger('CALLBACK OPERATIONS (nfs_cb_opnum4)', cbs, 16)
    ledger('ERROR CODES (nfsstat4)', errs, 10097)

    for n, who in sorted(names.items()):
        if len(who) > 1:
            collisions.append(f'type {n} declared in {sorted(who)}')
    for n, who in sorted(consts.items()):
        if len(who) > 1:
            collisions.append(f'constant {n} declared in {sorted(who)}')

    print(f'TYPE NAMES: ' + ', '.join(
        f'{k}={sum(1 for n, w in names.items() if k in w)}'
        for k, _ in DOCS))

    if collisions:
        print('\nCOLLISIONS:')
        for c in collisions:
            print(f'  {c}')
        return 1
    print('\nNo collisions.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
