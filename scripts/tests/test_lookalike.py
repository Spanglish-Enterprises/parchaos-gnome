#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for scripts/lookalike-check.py (the automated look-alike audit). Run:
    python3 scripts/tests/test_lookalike.py
Each case builds a small throwaway tree with its own terms and allow-list."""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CHECK = os.path.join(HERE, '..', 'lookalike-check.py')
failures = 0

TERMS = 'deny\t\\bfinder\\b\nreview\t\\bdock\\b\n'
CSV_HEAD = 'path,kind,source,license,made_by,status,notes\n'


def run(files, allow='', terms=TERMS, gate=False, csv=None):
    with tempfile.TemporaryDirectory() as root:
        for name, text in files.items():
            path = os.path.join(root, name)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            mode = 'wb' if isinstance(text, bytes) else 'w'
            with open(path, mode) as f:
                f.write(text)
        if csv is not None:
            os.makedirs(os.path.join(root, 'docs'), exist_ok=True)
            with open(os.path.join(root, 'docs', 'asset-provenance.csv'), 'w') as f:
                f.write(CSV_HEAD + csv)
        with tempfile.TemporaryDirectory() as cfg:   # outside the tree, so the check does not scan it
            t = os.path.join(cfg, 'terms.txt')
            a = os.path.join(cfg, 'allow.txt')
            open(t, 'w').write(terms)
            open(a, 'w').write(allow)
            env = dict(os.environ, LOOKALIKE_TERMS=t, LOOKALIKE_ALLOW=a)
            cmd = [sys.executable, CHECK, '--root', root] + (['--gate'] if gate else [])
            r = subprocess.run(cmd, capture_output=True, text=True, env=env)
            return r.returncode, r.stdout + r.stderr


def check(ok, what, detail=''):
    global failures
    if not ok:
        failures += 1
        print(f'FAIL {what}\n{detail}')


code, out = run({'a.md': 'Open the Finder window'})
check(code == 1 and 'finder' in out, 'a listed name fails', out)

code, out = run({'a.md': 'Open the Finder window'}, allow='a.md | finder | fact: a plain statement')
check(code == 0, 'an excused name passes', out)

code, out = run({'a.md': 'Finder'}, allow='b.md | finder | fact: elsewhere')
check(code == 1, 'an excuse for another file does not help', out)

code, out = run({'a.md': 'Finder'}, allow='a.md | finder | because I said so')
check(code != 0 and 'must start with' in out, 'a reason without a category is rejected', out)

code, out = run({'a.md': 'Finder'}, allow='a.md | * | debt: clean up later')
check(code == 0, 'a debt line passes the plain run', out)
code, out = run({'a.md': 'Finder'}, allow='a.md | * | debt: clean up later', gate=True)
check(code == 1 and 'owed a clean-up' in out, 'a debt line fails the gate', out)

code, out = run({'a.md': 'the dock'})
check(code == 0 and 'dock' in out, 'a review term is listed but does not fail', out)

code, out = run({'img.png': b'\x89PNG\0'}, csv='')
check(code == 1 and 'no provenance row for img.png' in out, 'an asset with no row fails', out)

row = 'img.png,own-drawn,drawn here,CC-BY-SA-4.0,us,verified,\n'
code, out = run({'img.png': b'\x89PNG\0'}, csv=row)
check(code == 0, 'a covered asset passes', out)

row = 'img.png,unknown,somewhere,unknown,unknown,unverified,find out\n'
code, out = run({'img.png': b'\x89PNG\0'}, csv=row)
check(code == 0, 'an unverified row passes the plain run', out)
code, out = run({'img.png': b'\x89PNG\0'}, csv=row, gate=True)
check(code == 1 and 'not settled yet' in out, 'an unverified row fails the gate', out)

row = 'img.png,mystery,x,y,z,verified,\n'
code, out = run({'img.png': b'\x89PNG\0'}, csv=row)
check(code == 1 and 'kind' in out, 'a kind outside the list is rejected', out)

row = 'icons/*,own-drawn,drawn here,CC-BY-SA-4.0,us,verified,\n'
code, out = run({'icons/a.svg': '<svg/>', 'icons/b.svg': '<svg/>'}, csv=row)
check(code == 0, 'a glob row covers several assets', out)

print('lookalike: ' + ('all checks passed' if not failures else f'{failures} check(s) failed'))
sys.exit(1 if failures else 0)
