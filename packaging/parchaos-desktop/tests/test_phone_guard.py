# SPDX-License-Identifier: GPL-3.0-or-later
# Tests for parchaos-phone-guard (ticket #156). Run:
#   python3 packaging/parchaos-desktop/tests/test_phone_guard.py
import importlib.machinery
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
loader = importlib.machinery.SourceFileLoader('phone_guard', os.path.join(HERE, '..', 'files', 'parchaos-phone-guard'))
spec = importlib.util.spec_from_loader('phone_guard', loader)
try:
    guard = importlib.util.module_from_spec(spec)
    loader.exec_module(guard)
except (ImportError, ValueError) as err:
    print(f'phone-guard: skipped (GLib bindings unavailable: {err})')
    sys.exit(0)

failures = 0


def check(ok, what):
    global failures
    if not ok:
        failures += 1
        print(f'FAIL {what}')


home, cafe = 'a1b2-home', 'c3d4-cafe'
check(guard.wanted(True, [home], home), 'on at home')
check(not guard.wanted(True, [home], cafe), 'off on an untrusted network')
check(not guard.wanted(True, [home], ''), 'off with no network')
check(not guard.wanted(False, [home], home), 'off when the phone connection is turned off')
check(not guard.wanted(True, [], home), 'off until a network is trusted')

# The schema has the keys the guard and Settings use, with private defaults.
with open(os.path.join(HERE, '..', 'files', 'org.parchaos.desktop.gschema.xml'), encoding='utf-8') as f:
    schema = f.read()
check('name="phone-link"' in schema and 'name="phone-trusted-networks"' in schema, 'schema keys')
block = schema[schema.index('name="phone-trusted-networks"'):]
check('<default>[]</default>' in block[:block.index('</key>')], 'no network is trusted by default')

print('phone-guard: all checks passed' if failures == 0 else f'phone-guard: {failures} check(s) failed')
sys.exit(0 if failures == 0 else 1)
