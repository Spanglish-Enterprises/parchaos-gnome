# SPDX-License-Identifier: GPL-3.0-or-later
# Tests for window-chrome.py (ticket #178). Run:
#   python3 packaging/parchaos-gtk-theme/tests/test_window_chrome.py
import importlib.machinery
import importlib.util
import os
import sys
import tempfile
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
loader = importlib.machinery.SourceFileLoader('chrome', os.path.join(HERE, '..', 'window-chrome.py'))
spec = importlib.util.spec_from_loader('chrome', loader)
wc = importlib.util.module_from_spec(spec)
loader.exec_module(wc)

failures = 0


def check(ok, what):
    global failures
    if not ok:
        failures += 1
        print(f'FAIL {what}')


CSS = '''window.csd { border-radius: 24px; margin: 24px; }
headerbar:first-child { border-top-left-radius: 24px; border-top-right-radius: 24px; }
button.pill { border-radius: 9999px; }
headerbar windowcontrols button.close {
  background-image: -gtk-scaled(url("windows-assets/titlebutton-close-dark.png"), url("windows-assets/titlebutton-close-dark@2.png"));
}
headerbar windowcontrols button.close:backdrop {
  background-image: -gtk-scaled(url("windows-assets/titlebutton-close-backdrop-dark.png"), url("windows-assets/titlebutton-close-backdrop-dark@2.png"));
}
'''


def main():
    out = wc.restyle(CSS, gtk4=True)
    check('border-radius: 12px;' in out and 'border-top-left-radius: 12px;' in out, 'window corners become 12 px')
    check('margin: 24px;' in out, 'only radii change, not other 24 px values')
    check('9999px' in out, 'other radii are untouched')
    check('url("windows-assets/titlebutton-close-dark.svg")' in out and '.png' not in out, 'buttons point at our SVGs')
    check('@keyframes parchaos-titlebutton-bounce' in out, 'GTK 4 gets the hover bounce')
    check('@keyframes' not in wc.restyle(CSS, gtk4=False), 'GTK 3 does not (no transforms)')
    check('.title:backdrop' in out, 'unfocused titles are dimmed')

    states = ['', 'hover', 'active', 'backdrop', 'backdrop-hover']
    for kind in wc.COLOURS:
        for state in states:
            svg = wc.button(kind, state, dark=True)
            ET.fromstring(svg)   # well-formed
            check(('stroke-linecap' in svg) == (state in ('hover', 'active', 'backdrop-hover')),
                  f'{kind} {state or "normal"}: glyph only when pointed at or pressed')
    check(f'opacity="{wc.INACTIVE_OPACITY}"' in wc.button('close', 'backdrop', False), 'unfocused buttons at half strength')
    check(wc.COLOURS['close'] in wc.button('close', '', False), 'close is the ParchaOS rose')

    with tempfile.TemporaryDirectory() as root:
        names = ['titlebutton-close.png', 'titlebutton-close@2.png', 'titlebutton-maximize-backdrop-hover-dark.png',
                 'titlebutton-restore-active.png', 'unrelated.png']
        for theme in ('ParchaOS-Dark',):
            for gtk in ('gtk-3.0', 'gtk-4.0'):
                assets = os.path.join(root, theme, gtk, 'windows-assets')
                os.makedirs(assets)
                for name in names:
                    open(os.path.join(assets, name), 'w').close()
                with open(os.path.join(root, theme, gtk, 'gtk.css'), 'w') as f:
                    f.write(CSS)
        os.makedirs(os.path.join(root, 'ParchaOS-Dark-Teal'))
        os.symlink('../ParchaOS-Dark/gtk-4.0', os.path.join(root, 'ParchaOS-Dark-Teal', 'gtk-4.0'))
        wc.main(['window-chrome.py', root])
        made = sorted(n for n in os.listdir(os.path.join(root, 'ParchaOS-Dark', 'gtk-4.0', 'windows-assets'))
                      if n.endswith('.svg'))
        check(made == ['titlebutton-close.svg', 'titlebutton-maximize-backdrop-hover-dark.svg',
                       'titlebutton-restore-active.svg'], f'one SVG per upstream button name (got {made})')
        with open(os.path.join(root, 'ParchaOS-Dark', 'gtk-4.0', 'gtk.css')) as f:
            once = f.read()
        check(once.count('ParchaOS window chrome') == 2, 'the GTK 4 rules are added once each')

    print('window-chrome: all checks passed' if failures == 0 else f'window-chrome: {failures} check(s) failed')
    return 0 if failures == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
