#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Accent colours for the ParchaOS GTK themes (ticket #177).
#
# The upstream theme is compiled with one blue (#0088FF) and shades of it baked
# into every stylesheet, which also pinned libadwaita's accent to that blue, so
# GNOME's accent colour setting (org.gnome.desktop.interface accent-color) never
# reached any app. This script, run at build time, changes that:
#
#   GTK 4   every accent blue becomes var(--accent-bg-color) (or a shade() or
#           alpha() of it), and the theme's own accent_bg_color/accent_color
#           definitions are dropped, so libadwaita's system accent shows through
#           and apps follow a change at once. GTK 4 apps without libadwaita get
#           GNOME's blue from the fallback.
#   GTK 3   has no variables, so each theme gets one copy per accent colour,
#           <theme>-<Colour> (ParchaOS-Dark-Teal, ParchaOS-Light-solid-Pink, ...),
#           holding only a recoloured gtk-3.0 stylesheet; everything else links
#           to the base theme. The base theme itself is recoloured to GNOME's blue
#           so GTK 3, GTK 4 and the Shell agree. parchaos-theme-sync picks the
#           copy that matches the accent.
#   Shell   already uses -st-accent-color; nothing to do.
#
#   accent-colours.py THEMES_DIR [SKEL_GTK4_DIR]
#
# Original code for ParchaOS, GPL-3.0-or-later.

import colorsys
import os
import re
import sys

# GNOME's accent colours (libadwaita's --accent-<name>), in the order GNOME shows them.
ACCENTS = {
    'blue': '#3584e4',
    'teal': '#2190a4',
    'green': '#3a944a',
    'yellow': '#c88800',
    'orange': '#ed5b00',
    'red': '#e62d42',
    'pink': '#d56199',
    'purple': '#9141ac',
    'slate': '#6f8396',
}
BASE_THEMES = ['ParchaOS-Dark', 'ParchaOS-Light', 'ParchaOS-Dark-solid', 'ParchaOS-Light-solid']
UPSTREAM = (0x00, 0x88, 0xff)   # the blue the upstream theme is compiled with

HEX = re.compile(r'#([0-9a-fA-F]{6})\b')
RGBA = re.compile(r'rgba\(\s*(\d+),\s*(\d+),\s*(\d+),\s*([0-9.]+)\s*\)')
DEFINE = re.compile(r'^@define-color (accent_bg_color|accent_color) [^;]+;\n', re.M)


def hls(rgb):
    return colorsys.rgb_to_hls(*(c / 255 for c in rgb))


BASE_H, BASE_L, BASE_S = hls(UPSTREAM)


def shade_of_base(rgb):
    """The lightness factor if `rgb` is the upstream blue or a shade of it, else None.

    Sass derived the theme's darker and lighter blues from the one accent, so they keep
    its hue and full saturation; GNOME's own palette blues (blue_1..5) are less saturated
    and are left alone.
    """
    h, l, s = hls(rgb)
    if s < 0.85 or not 0.2 <= l <= 0.8 or abs(h * 360 - BASE_H * 360) > 12:
        return None
    return l / BASE_L


def shade(rgb, factor):
    """GTK's shade(): lightness and saturation multiplied by `factor`, clamped."""
    h, l, s = hls(rgb)
    r, g, b = colorsys.hls_to_rgb(h, min(1, max(0, l * factor)), min(1, max(0, s * factor)))
    return tuple(round(c * 255) for c in (r, g, b))


def parse(hex_colour):
    return tuple(int(hex_colour[i:i + 2], 16) for i in (1, 3, 5))


def to_hex(rgb):
    return '#%02x%02x%02x' % rgb


def recolour(css, accent):
    """GTK 3: every accent blue (and its shades) in `accent`, as plain colours."""
    target = parse(accent)

    def hex_sub(m):
        factor = shade_of_base(parse(m.group(0)))
        if factor is None:
            return m.group(0)
        return to_hex(target if abs(factor - 1) < 0.01 else shade(target, factor))

    def rgba_sub(m):
        rgb = tuple(int(m.group(i)) for i in (1, 2, 3))
        factor = shade_of_base(rgb)
        if factor is None:
            return m.group(0)
        r, g, b = target if abs(factor - 1) < 0.01 else shade(target, factor)
        return f'rgba({r}, {g}, {b}, {m.group(4)})'

    return RGBA.sub(rgba_sub, HEX.sub(hex_sub, css))


def dynamic(css):
    """GTK 4: every accent blue as an expression of libadwaita's --accent-bg-color."""
    var = 'var(--accent-bg-color, %s)' % ACCENTS['blue']

    def colour(factor):
        return var if abs(factor - 1) < 0.01 else f'shade({var}, {factor:.3f})'

    def hex_sub(m):
        factor = shade_of_base(parse(m.group(0)))
        return m.group(0) if factor is None else colour(factor)

    def rgba_sub(m):
        factor = shade_of_base(tuple(int(m.group(i)) for i in (1, 2, 3)))
        return m.group(0) if factor is None else f'alpha({colour(factor)}, {m.group(4)})'

    # @define-color cannot hold a var(); without these lines libadwaita's own accent wins.
    # The other definitions (theme_selected_bg_color, ...) only take plain colours: GNOME's blue.
    css = DEFINE.sub('', css)
    lines = []
    for line in css.splitlines(keepends=True):
        if line.startswith('@define-color '):
            lines.append(recolour(line, ACCENTS['blue']))
        else:
            lines.append(RGBA.sub(rgba_sub, HEX.sub(hex_sub, line)))
    return ''.join(lines)


def rewrite(path, change):
    if not os.path.isfile(path) or os.path.islink(path):
        return
    with open(path, encoding='utf-8') as f:
        text = f.read()
    with open(path, 'w', encoding='utf-8') as f:
        f.write(change(text))


def variant(themes, base, css, name, accent):
    """<base>-<Colour>: a recoloured gtk-3.0 stylesheet (from the upstream `css`), the rest
    links to the base theme."""
    root = os.path.join(themes, f'{base}-{name.capitalize()}')
    gtk3 = os.path.join(root, 'gtk-3.0')
    os.makedirs(gtk3, exist_ok=True)
    with open(os.path.join(gtk3, 'gtk.css'), 'w', encoding='utf-8') as f:
        f.write(recolour(css, accent))
    os.symlink('gtk.css', os.path.join(gtk3, 'gtk-dark.css'))
    for entry in os.listdir(os.path.join(themes, base, 'gtk-3.0')):
        if entry not in ('gtk.css', 'gtk-dark.css'):
            os.symlink(os.path.join('..', '..', base, 'gtk-3.0', entry), os.path.join(gtk3, entry))
    for entry in os.listdir(os.path.join(themes, base)):
        if entry not in ('gtk-3.0', 'index.theme'):
            os.symlink(os.path.join('..', base, entry), os.path.join(root, entry))
    with open(os.path.join(themes, base, 'index.theme'), encoding='utf-8') as f:
        index = f.read()
    theme = os.path.basename(root)
    index = re.sub(r'^(Name|GtkTheme|MetacityTheme)=.*$', lambda m: f'{m.group(1)}={theme}', index, flags=re.M)
    index = re.sub(r'^Comment=.*$', f'Comment=ParchaOS theme with the {name} accent colour', index, flags=re.M)
    with open(os.path.join(root, 'index.theme'), 'w', encoding='utf-8') as f:
        f.write(index)


def main(argv):
    themes = argv[1]
    for base in BASE_THEMES:
        if not os.path.isdir(os.path.join(themes, base)):
            sys.exit(f'accent-colours: {base} is missing from {themes}')
        # The copies first: they start from the upstream blue, which the base loses next.
        with open(os.path.join(themes, base, 'gtk-3.0', 'gtk.css'), encoding='utf-8') as f:
            css = f.read()
        for name, accent in ACCENTS.items():
            if name != 'blue':
                variant(themes, base, css, name, accent)
        for name in ('gtk.css', 'gtk-dark.css'):
            rewrite(os.path.join(themes, base, 'gtk-4.0', name), dynamic)
            rewrite(os.path.join(themes, base, 'gtk-3.0', name), lambda css: recolour(css, ACCENTS['blue']))
    if len(argv) > 2:
        # The libadwaita stylesheets a new account starts with (/etc/skel/.config/gtk-4.0).
        for name in ('gtk-Dark.css', 'gtk-Light.css'):
            rewrite(os.path.join(argv[2], name), dynamic)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
