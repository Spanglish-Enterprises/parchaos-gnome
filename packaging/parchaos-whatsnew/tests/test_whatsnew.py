# SPDX-License-Identifier: GPL-3.0-or-later
# Tests for the What's New app's logic (which text is shown, when the window opens). Run:
#   python3 packaging/parchaos-whatsnew/tests/test_whatsnew.py
import importlib.machinery
import importlib.util
import json
import os
import sys
import tempfile
import types

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, '..', 'files', 'parchaos-whatsnew')
CONTENT = os.path.join(HERE, '..', 'files', 'whatsnew.json')

try:
    import gi
    gi.require_version('Gtk', '4.0')
    gi.require_version('Adw', '1')
except (ImportError, ValueError):
    print('whatsnew: skipped (needs GTK 4 and libadwaita for Python)')
    sys.exit(0)

loader = importlib.machinery.SourceFileLoader('whatsnew', SCRIPT)
spec = importlib.util.spec_from_loader('whatsnew', loader)
wn = importlib.util.module_from_spec(spec)
loader.exec_module(wn)
failures = 0


def check(ok, what):
    global failures
    if not ok:
        failures += 1
        print(f'FAIL {what}')


content = wn.load_content(CONTENT)
check(content is not None and content['version'] and len(content['entries']) >= 3, 'the shipped content loads')
for e in content['entries']:
    for key in ('title', 'title_es', 'text', 'text_es', 'icon'):
        check(e.get(key), f'entry {e.get("title")!r} has {key}')
check(wn.pick({'a': 'x', 'a_es': 'y'}, 'a', 'es') == 'y', 'Spanish text is chosen in Spanish')
check(wn.pick({'a': 'x', 'a_es': 'y'}, 'a', '') == 'x', 'English text is chosen otherwise')
check(wn.pick({'a': 'x'}, 'a', 'es') == 'x', 'a missing translation falls back to English')

with tempfile.TemporaryDirectory() as d:
    bad = os.path.join(d, 'bad.json')
    open(bad, 'w').write('{"version": "1"}')
    check(wn.load_content(bad) is None, 'content without entries is rejected')
    open(bad, 'w').write('not json')
    check(wn.load_content(bad) is None, 'unreadable content is rejected')
    state_path = os.path.join(d, 'sub', 'whatsnew.json')
    check(wn.load_state(state_path) == {'seen': '', 'auto': True}, 'no state yet: nothing seen, automatic on')
    wn.save_state({'seen': '2026.10', 'auto': False}, state_path)
    check(wn.load_state(state_path) == {'seen': '2026.10', 'auto': False}, 'state round-trips')

c = {'version': '2026.10', 'entries': [{}]}
check(wn.should_show(c, {'seen': '', 'auto': True}, True), 'a new version opens the window')
check(not wn.should_show(c, {'seen': '2026.10', 'auto': True}, True), 'a seen version does not')
check(not wn.should_show(c, {'seen': '', 'auto': False}, True), 'turned off: it does not open')
check(not wn.should_show(c, {'seen': '', 'auto': True}, False), 'before the first-login welcome: it does not open')
check(not wn.should_show(None, {'seen': '', 'auto': True}, True), 'no content: it does not open')

print('whatsnew: ' + ('all checks passed' if not failures else f'{failures} check(s) failed'))
sys.exit(1 if failures else 0)
