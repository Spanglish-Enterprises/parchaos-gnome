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

    # libadwaita stylesheets follow the style and appearance (ticket #135).
    with tempfile.TemporaryDirectory() as root:
        themes = os.path.join(root, 'themes')
        for name in ('ParchaOS-Dark', 'ParchaOS-Dark-solid', 'ParchaOS-Light'):
            os.makedirs(os.path.join(themes, name, 'gtk-4.0'))
            open(os.path.join(themes, name, 'gtk-4.0', 'gtk.css'), 'w').close()
        cfg = os.path.join(root, 'gtk-4.0')
        os.makedirs(cfg)
        for link in ('gtk.css', 'gtk-dark.css'):
            os.symlink('gtk-Dark.css', os.path.join(cfg, link))
        solid = os.path.join(themes, 'ParchaOS-Dark-solid', 'gtk-4.0', 'gtk.css')
        check(ts.gtk4_links(cfg, themes, 'ParchaOS-Dark-solid'), 'skel links move to the Classic theme')
        check(os.readlink(os.path.join(cfg, 'gtk.css')) == solid and
              os.readlink(os.path.join(cfg, 'gtk-dark.css')) == solid, 'both links point at the Classic theme')
        check(not ts.gtk4_links(cfg, themes, 'ParchaOS-Dark-solid'), 'second run changes nothing')
        check(ts.gtk4_links(cfg, themes, 'ParchaOS-Light'), 'and on to light')
        check(not ts.gtk4_links(cfg, themes, 'ParchaOS-Light-solid'), 'a missing theme changes nothing')
        os.remove(os.path.join(cfg, 'gtk.css'))
        with open(os.path.join(cfg, 'gtk.css'), 'w') as f:
            f.write('/* mine */')
        ts.gtk4_links(cfg, themes, 'ParchaOS-Dark')
        check(open(os.path.join(cfg, 'gtk.css')).read() == '/* mine */', "the user's own stylesheet is kept")
        check(not ts.gtk4_links(os.path.join(root, 'none'), themes, 'ParchaOS-Dark'), 'no config dir, no change')

    print('theme-sync: all checks passed' if failures == 0 else f'theme-sync: {failures} check(s) failed')
    return 0 if failures == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
