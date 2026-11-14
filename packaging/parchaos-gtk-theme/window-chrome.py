#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
# ParchaOS window chrome (ticket #178), applied to the built GTK themes at build time.
#
#   * Title buttons: ParchaOS's own glass discs (SVG, drawn here) in the ParchaOS colours,
#     replacing the upstream PNG buttons. One file per upstream name, so the upstream
#     stylesheet's states (normal, hover, pressed, unfocused) keep working; the PNG
#     references are pointed at the SVGs. Unfocused windows show them at half strength.
#   * One corner radius: the windows' 24 px becomes 12 px in GTK 3 and GTK 4 (which also
#     draws the frames of apps without their own title bar).
#   * Unfocused windows: title text at half strength too.
#   * GTK 4: a short bounce on hover (1.0 -> 1.08 -> 1.0 over 120 ms). GTK 3 has no transforms.
#   * GTK 4: sidebars run to the window's edges (the upstream theme floats them as an inset
#     card) with a hairline to the content.
#
#   window-chrome.py THEMES_DIR [SKEL_GTK4_DIR]
#
# Original code for ParchaOS, GPL-3.0-or-later.

import colorsys
import os
import re
import sys

RADIUS_FROM, RADIUS_TO = '24px', '12px'
# The ParchaOS button colours (the same as recolor-titlebuttons.py's "passion" palette).
COLOURS = {'close': '#f0566f', 'minimize': '#f5b700', 'maximize': '#7a58e0', 'restore': '#7a58e0'}
INACTIVE_OPACITY = 0.5

# Our own glyphs on a 16 px grid, shown on hover and when pressed.
GLYPHS = {
    'close': '<path d="M5.7 5.7l4.6 4.6M10.3 5.7l-4.6 4.6"/>',
    'minimize': '<path d="M5.2 8h5.6"/>',
    'maximize': '<rect x="5.6" y="5.6" width="4.8" height="4.8" rx="1.2"/>',
    'restore': '<rect x="6.4" y="6.4" width="3.2" height="3.2" rx="0.8"/>',
}
NAME = re.compile(r'^titlebutton-(close|minimize|maximize|restore)((?:-[a-z]+)*?)(-dark)?(@2)?\.png$')
SCALED = re.compile(r'-gtk-scaled\(url\("windows-assets/(titlebutton-[a-z-]+)\.png"\),\s*'
                    r'url\("windows-assets/\1@2\.png"\)\)')
RADIUS = re.compile(r'((?:border(?:-(?:top|bottom)-(?:left|right))?-radius):[^;]*;)')

CSS = '''
/* ParchaOS window chrome (ticket #178): unfocused windows' titles at half strength. */
headerbar .title:backdrop, headerbar windowtitle:backdrop, .titlebar .title:backdrop {
  opacity: %(op)s;
}
''' % {'op': INACTIVE_OPACITY}

CSS_GTK4 = '''
/* ParchaOS window chrome (ticket #178): a short bounce when the pointer reaches a title button. */
@keyframes parchaos-titlebutton-bounce {
  from { transform: scale(1); }
  50% { transform: scale(1.08); }
  to { transform: scale(1); }
}
headerbar windowcontrols button.close:hover:not(:backdrop),
headerbar windowcontrols button.minimize:hover:not(:backdrop),
headerbar windowcontrols button.maximize:hover:not(:backdrop) {
  animation: parchaos-titlebutton-bounce 120ms ease-out;
}
:root { --window-radius: 12px; }
/* Sidebars to the window's edges, a hairline between them and the content. */
.sidebar-pane, .content-pane .sidebar-pane, .sidebar-pane .content-pane {
  margin: 0;
  border-radius: 0;
}
.sidebar-pane:dir(ltr):not(.end), .sidebar-pane.end:dir(rtl) {
  box-shadow: inset -1px 0 alpha(currentColor, 0.08);
}
.sidebar-pane:dir(rtl):not(.end), .sidebar-pane.end:dir(ltr) {
  box-shadow: inset 1px 0 alpha(currentColor, 0.08);
}
'''


def shade(hex_colour, lightness=0.0, saturation=1.0):
    r, g, b = (int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    r, g, b = colorsys.hls_to_rgb(h, max(0, min(1, l + lightness)), max(0, min(1, s * saturation)))
    return '#%02x%02x%02x' % tuple(round(c * 255) for c in (r, g, b))


def button(kind, state, dark):
    """One title button: a glass disc in the button's colour.

    state: '' (normal), 'hover', 'active' (pressed), 'backdrop' (unfocused window),
    'backdrop-hover' (pointer over a button of an unfocused window).
    """
    base = COLOURS[kind]
    if state == 'active':
        base = shade(base, -0.12)
    top, rim, glyph = shade(base, 0.12), shade(base, -0.22), shade(base, -0.38, 0.9)
    opacity = INACTIVE_OPACITY if state == 'backdrop' else 1
    show_glyph = state in ('hover', 'active', 'backdrop-hover')
    rim_opacity = 0.7 if dark else 0.5
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">'
        '<defs>'
        f'<radialGradient id="b" cx="8" cy="6" r="7.5" gradientUnits="userSpaceOnUse">'
        f'<stop offset="0" stop-color="{top}"/><stop offset="1" stop-color="{base}"/></radialGradient>'
        '<linearGradient id="g" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#fff" stop-opacity="0.7"/>'
        '<stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
        '</defs>'
        f'<g opacity="{opacity}">'
        '<circle cx="8" cy="8" r="6.5" fill="url(#b)"/>'
        f'<circle cx="8" cy="8" r="6.25" fill="none" stroke="{rim}" stroke-opacity="{rim_opacity}" stroke-width="0.5"/>'
        '<ellipse cx="8" cy="5.3" rx="4.3" ry="2.5" fill="url(#g)"/>'
        + (f'<g fill="none" stroke="{glyph}" stroke-width="1.3" stroke-linecap="round" '
           f'stroke-linejoin="round">{GLYPHS[kind]}</g>' if show_glyph else '')
        + '</g></svg>\n')


def write_buttons(directory):
    """An SVG for every upstream titlebutton PNG name in `directory`; returns how many."""
    count = 0
    for name in os.listdir(directory):
        m = NAME.match(name)
        if not m or m.group(4):
            continue
        kind, state, dark = m.group(1), m.group(2).lstrip('-'), bool(m.group(3))
        with open(os.path.join(directory, name[:-4] + '.svg'), 'w', encoding='utf-8') as f:
            f.write(button(kind, state, dark))
        count += 1
    return count


def restyle(css, gtk4):
    """The stylesheet with our buttons, one corner radius and the unfocused-title rule."""
    css = SCALED.sub(lambda m: f'url("windows-assets/{m.group(1)}.svg")', css)
    css = RADIUS.sub(lambda m: m.group(1).replace(RADIUS_FROM, RADIUS_TO), css)
    return css + CSS + (CSS_GTK4 if gtk4 else '')


def main(argv):
    themes = argv[1]
    dirs = [argv[2]] if len(argv) > 2 else []
    changed = 0
    for theme in sorted(os.listdir(themes)):
        for gtk in ('gtk-3.0', 'gtk-4.0'):
            path = os.path.join(themes, theme, gtk)
            if os.path.islink(path) or not os.path.isdir(path):
                continue   # the accent copies link to their base theme
            dirs.append(path)
    for path in dirs:
        assets = os.path.join(path, 'windows-assets')
        if os.path.isdir(assets) and not os.path.islink(assets):
            if not write_buttons(assets):
                sys.exit(f'window-chrome: no title buttons found in {assets}')
        for name in os.listdir(path):
            css = os.path.join(path, name)
            if not name.endswith('.css') or os.path.islink(css):
                continue
            with open(css, encoding='utf-8') as f:
                text = f.read()
            if 'ParchaOS window chrome' in text:
                continue
            with open(css, 'w', encoding='utf-8') as f:
                f.write(restyle(text, gtk4=path.endswith('gtk-4.0')))
            changed += 1
    if not changed:
        sys.exit('window-chrome: no stylesheet changed')
    print(f'window-chrome: {changed} stylesheets')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
