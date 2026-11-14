#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-SA-4.0
# ParchaOS "Hills" time-of-day wallpapers (ticket #166): the same rolling hills at dawn, by day,
# at dusk and at night, drawn from scratch with cairo (no photos, no third-party art). The hill
# shapes come from a fixed seed, so every run makes the same pictures.
#
#   python3 packaging/parchaos-gnome-wallpaper/make-time-of-day.py OUT_DIR [WIDTH HEIGHT]
#
# The package runs this at build time, so no pictures are kept in the repository.
#
# Writes hills-dawn.jpg, hills-day.jpg, hills-dusk.jpg, hills-night.jpg (and small -thumb.png
# copies) into OUT_DIR. A light grain is added with ImageMagick so the sky gradients don't band.
# Artwork CC BY-SA 4.0, Spanglish Enterprises LLC.

import math
import os
import random
import subprocess
import sys

import cairo

SEED = 166

# Per time of day: sky top, sky at the horizon, the glow around the sun or moon, the sun or moon
# (x, y as fractions, radius as a fraction of the height, colour), and the hills from far to near.
TIMES = {
    'dawn': {
        'sky': ('#283061', '#f2a982'), 'glow': '#ffd2a8', 'body': (0.30, 0.50, 0.045, '#fff1d6'),
        'hills': ['#c48a96', '#9b6d8f', '#715685', '#4a3f6b', '#2c2a4c'], 'stars': 0.15,
    },
    'day': {
        'sky': ('#3f86d6', '#cfe8f7'), 'glow': '#ffffff', 'body': (0.72, 0.22, 0.040, '#fffbea'),
        'hills': ['#a9d3c9', '#7fbfa6', '#58a57e', '#3f8a5f', '#2a6b47'], 'stars': 0,
    },
    'dusk': {
        'sky': ('#35295e', '#ff8f5e'), 'glow': '#ffb978', 'body': (0.66, 0.49, 0.050, '#ffd08a'),
        'hills': ['#b65f6e', '#8c4766', '#64375c', '#422a4b', '#271d36'], 'stars': 0.25,
    },
    'night': {
        'sky': ('#070b1f', '#1d2a52'), 'glow': '#9fb4ff', 'body': (0.24, 0.20, 0.030, '#eef2ff'),
        'hills': ['#2a3a66', '#223057', '#1a2547', '#131b37', '#0b1127'], 'stars': 1.0,
    },
}


def rgb(hexcolour):
    h = hexcolour.lstrip('#')
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def ridge(rng, layers):
    """One hill line: a few slow waves plus smaller ones, as fractions of the height."""
    waves = [(rng.uniform(0.6, 1.6) * (i + 1), rng.uniform(0, 2 * math.pi), 0.05 / (i + 1) ** 1.3)
             for i in range(layers)]
    return lambda x: sum(a * math.sin(f * x * 2 * math.pi + p) for f, p, a in waves)


def draw(name, spec, width, height, path):
    rng = random.Random(SEED)          # the same hills in every picture
    surface = cairo.ImageSurface(cairo.FORMAT_RGB24, width, height)
    cr = cairo.Context(surface)

    # Sky.
    top, horizon = (rgb(c) for c in spec['sky'])
    sky = cairo.LinearGradient(0, 0, 0, height * 0.78)
    sky.add_color_stop_rgb(0, *top)
    sky.add_color_stop_rgb(1, *horizon)
    cr.set_source(sky)
    cr.paint()

    # Stars, then the glow and the sun or moon.
    stars = random.Random(SEED + 1)
    for _ in range(int(900 * spec['stars'])):
        x, y = stars.random() * width, stars.random() ** 1.6 * height * 0.6
        r = stars.uniform(0.6, 1.9) * height / 2160
        cr.set_source_rgba(1, 1, 1, stars.uniform(0.25, 0.9) * spec['stars'])
        cr.arc(x, y, r, 0, 2 * math.pi)
        cr.fill()
    bx, by, br, bc = spec['body']
    bx, by, br = bx * width, by * height, br * height
    glow = cairo.RadialGradient(bx, by, br, bx, by, br * 9)
    g = rgb(spec['glow'])
    glow.add_color_stop_rgba(0, *g, 0.55)
    glow.add_color_stop_rgba(0.35, *g, 0.16)
    glow.add_color_stop_rgba(1, *g, 0)
    cr.set_source(glow)
    cr.paint()
    cr.push_group()
    cr.set_source_rgb(*rgb(bc))
    cr.arc(bx, by, br, 0, 2 * math.pi)
    cr.fill()
    if name == 'night':                # a crescent: cut a disc out of the moon, the glow shows through
        cr.set_operator(cairo.OPERATOR_CLEAR)
        cr.arc(bx + br * 0.45, by - br * 0.20, br * 0.88, 0, 2 * math.pi)
        cr.fill()
        cr.set_operator(cairo.OPERATOR_OVER)
    cr.pop_group_to_source()
    cr.paint()

    # Hills, far to near: each lower, darker and with a soft haze above it.
    count = len(spec['hills'])
    for i, colour in enumerate(spec['hills']):
        line = ridge(rng, 4)
        base = 0.50 + 0.095 * i
        cr.move_to(0, height)
        steps = 240
        for s in range(steps + 1):
            x = s / steps
            cr.line_to(x * width, (base + line(x) * (0.9 - 0.08 * i)) * height)
        cr.line_to(width, height)
        cr.close_path()
        c = rgb(colour)
        # Lighter at the ridge, darker lower down; the far hills fade into the sky (distance).
        fade = 0.22 * (count - 1 - i) / (count - 1)
        ridge_c = tuple(v * (1 - fade) + h * fade for v, h in zip(c, horizon))
        fill = cairo.LinearGradient(0, (base - 0.08) * height, 0, (base + 0.25) * height)
        fill.add_color_stop_rgb(0, *ridge_c)
        fill.add_color_stop_rgb(1, *(v * 0.78 for v in c))
        cr.set_source(fill)
        cr.fill()
    surface.write_to_png(path)


def main():
    out = sys.argv[1]
    width = int(sys.argv[2]) if len(sys.argv) > 2 else 3840
    height = int(sys.argv[3]) if len(sys.argv) > 3 else 2160
    os.makedirs(out, exist_ok=True)
    for name, spec in TIMES.items():
        raw = os.path.join(out, f'hills-{name}.raw.png')
        final = os.path.join(out, f'hills-{name}.jpg')
        draw(name, spec, width, height, raw)
        # A light grain so the long sky gradients don't show steps.
        subprocess.run(['magick', raw, '-seed', str(SEED), '-attenuate', '0.25', '+noise', 'Gaussian', '-strip',
                        '-quality', '90', '-sampling-factor', '4:4:4', final], check=True)
        os.remove(raw)
        subprocess.run(['magick', final, '-resize', '480x270', '-strip', os.path.join(out, f'hills-{name}-thumb.png')],
                       check=True)
        print(final)


if __name__ == '__main__':
    main()
