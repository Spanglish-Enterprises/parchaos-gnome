# SPDX-License-Identifier: GPL-3.0-or-later
# Tests for parchaos-theme-sync's pure functions (tickets #100, #79). Run:
#   python3 packaging/parchaos-desktop/tests/test_theme_sync.py
import importlib.machinery
import importlib.util
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
loader = importlib.machinery.SourceFileLoader('theme_sync', os.path.join(HERE, '..', 'files', 'parchaos-theme-sync'))
spec = importlib.util.spec_from_loader('theme_sync', loader)
try:
    ts = importlib.util.module_from_spec(spec)
    loader.exec_module(ts)
except (ImportError, ValueError) as err:
    print(f'theme-sync: skipped (GLib bindings unavailable: {err})')
    sys.exit(0)

failures = 0


def check(ok, what):
    global failures
    if not ok:
        failures += 1
        print(f'FAIL {what}')


def main():
    check(ts.wanted_theme(True, False) == 'ParchaOS-Dark', 'dark theme')
    check(ts.wanted_theme(False, True) == 'ParchaOS-Light-solid', 'classic light theme')

    icon = ts.wanted_icon_theme
    cases = [
        # (dark, colour, current icon theme, expected)
        (True, 'passion', 'ParchaOS-dark', None),          # default: no change for existing accounts
        (False, 'passion', 'ParchaOS-dark', None),
        (True, 'berry', 'ParchaOS-dark', 'ParchaOS-dark-Berry'),
        (False, 'leaf', 'ParchaOS-dark', 'ParchaOS-light-Leaf'),
        (True, 'graphite', 'ParchaOS-light-Sunny', 'ParchaOS-dark-Graphite'),
        (False, 'passion', 'ParchaOS-dark-Berry', 'ParchaOS-light'),  # back to the default colour
        (True, 'passion', 'ParchaOS-dark-Ocean', 'ParchaOS-dark'),
        (True, 'ocean', 'Papirus', None),                   # another icon theme is left alone
        (True, 'passion', 'Adwaita', None),
    ]
    for dark, colour, current, expected in cases:
        got = icon(dark, colour, current)
        check(got == expected, f'icon theme for dark={dark} colour={colour} current={current}: got {got}, want {expected}')

    # Every colour the schema allows has a matching wanted theme name.
    schema = os.path.join(HERE, '..', 'files', 'org.parchaos.desktop.gschema.xml')
    with open(schema, encoding='utf-8') as f:
        text = f.read()
    block = text[text.index('name="folder-colour"'):]
    block = block[:block.index('</key>')]
    colours = [c.split('"')[1] for c in block.split('<choice value=')[1:]]
    check(colours[0] == 'passion' and len(colours) == 6, f'six folder colours, passion first (got {colours})')

    # The #100 rename only fires when the ParchaOS twin exists system-wide.
    with tempfile.TemporaryDirectory() as root:
        os.makedirs(os.path.join(root, 'ParchaOS-Dark'))
        check(ts.migrated('MacTahoe-Dark', root) == 'ParchaOS-Dark', 'MacTahoe name is migrated when the twin exists')
        check(ts.migrated('MacTahoe-Light', root) == 'MacTahoe-Light', 'left alone when the twin is missing')
        check(ts.migrated('Adwaita', root) == 'Adwaita', 'other themes are untouched')

    print('theme-sync: all checks passed' if failures == 0 else f'theme-sync: {failures} check(s) failed')
    return 0 if failures == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
