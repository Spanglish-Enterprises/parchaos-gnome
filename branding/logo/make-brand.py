#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""make-brand.py -- generates every ParchaOS logo asset from one design.

The ParchaOS mark is an original drawing (owner-approved concept "A",
2026-09-26): a halved passion fruit seen from above -- a rind ring, a
pith ring, the pulp, and seven seeds (one in the middle, six around it,
each pointing outward). It has no stem, leaf or bite, so it can't be
read as another company's fruit logo. Artwork: CC BY-SA 4.0
(LICENSE-ARTWORK), (c) 2026 Spanglish Enterprises LLC.

Run from the repository root: python3 branding/logo/make-brand.py
Needs rsvg-convert and Pillow. Rewrites the files listed in OUTPUTS.
"""
import math
import os
import subprocess
import tempfile

from PIL import Image, ImageDraw, ImageFont

PURPLE, PITH, PULP, SEED = "#6d28d9", "#fde68a", "#f5b700", "#3b0764"
TILE = (30, 28, 46, 255)
FONT = "/usr/share/fonts/adwaita-sans-fonts/AdwaitaSans-Regular.ttf"


def seeds(cx, cy, r_ring, rx, ry):
    """Center seed plus six radial seeds (as ellipses)."""
    out = [(cx, cy, rx, ry, 0.0)]
    for i in range(6):
        a = 2 * math.pi * i / 6 - math.pi / 2
        out.append((cx + r_ring * math.cos(a), cy + r_ring * math.sin(a), rx, ry,
                    math.degrees(a) + 90))
    return out


def color_svg():
    parts = [f'<circle cx="32" cy="32" r="30" fill="{PURPLE}"/>',
             f'<circle cx="32" cy="32" r="24.5" fill="{PITH}"/>',
             f'<circle cx="32" cy="32" r="21.5" fill="{PULP}"/>']
    for x, y, rx, ry, rot in seeds(32, 32, 11.5, 2.5, 3.7):
        parts.append(f'<ellipse cx="{x:.2f}" cy="{y:.2f}" rx="{rx}" ry="{ry}" '
                     f'transform="rotate({rot:.1f} {x:.2f} {y:.2f})" fill="{SEED}"/>')
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" '
            'viewBox="0 0 64 64">' + "".join(parts) + "</svg>\n")


def circle_path(cx, cy, r):
    return (f"M{cx - r:.3f} {cy:.3f}a{r:.3f} {r:.3f} 0 1 0 {2 * r:.3f} 0"
            f"a{r:.3f} {r:.3f} 0 1 0 {-2 * r:.3f} 0z")


def ellipse_path(cx, cy, a, b, angle):
    """Ellipse with semi-axis a along `angle` (radians) and b across it."""
    ux, uy = math.cos(angle), math.sin(angle)
    x1, y1, x2, y2 = cx + a * ux, cy + a * uy, cx - a * ux, cy - a * uy
    rot = math.degrees(angle)
    return (f"M{x1:.3f} {y1:.3f}A{a:.3f} {b:.3f} {rot:.2f} 1 0 {x2:.3f} {y2:.3f}"
            f"A{a:.3f} {b:.3f} {rot:.2f} 1 0 {x1:.3f} {y1:.3f}z")


def mono_svg(fill, size=16, symbolic=False):
    """One-color mark as a single even-odd path: disc, a ring cut between
    rind and pulp, and the seeds cut out. Tuned for 16 px."""
    c = size / 2
    s = size / 16
    d = [circle_path(c, c, 7.5 * s),      # outer edge
         circle_path(c, c, 6.1 * s),      # cut: inner edge of the rind
         circle_path(c, c, 5.1 * s)]      # pulp
    d.append(circle_path(c, c, 0.9 * s))  # center seed (hole)
    for i in range(6):                    # six seeds pointing outward
        a = 2 * math.pi * i / 6 - math.pi / 2
        d.append(ellipse_path(c + 3.0 * s * math.cos(a), c + 3.0 * s * math.sin(a),
                              1.15 * s, 0.72 * s, a))
    cls = ' class="ParchaOS-mark"' if symbolic else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
            f'viewBox="0 0 {size} {size}"><path{cls} fill="{fill}" fill-rule="evenodd" '
            f'd="{"".join(d)}"/></svg>\n')


def render(svg_text, px):
    with tempfile.NamedTemporaryFile("w", suffix=".svg", delete=False) as f:
        f.write(svg_text)
    out = f.name + ".png"
    subprocess.run(["rsvg-convert", "-w", str(px), "-h", str(px), f.name, "-o", out], check=True)
    im = Image.open(out).convert("RGBA")
    os.remove(f.name)
    os.remove(out)
    return im


def write(path, data):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        f.write(data)


def wordmark(height, mark_px, text_px, color, width=None):
    """Mark followed by the word ParchaOS, on a transparent canvas."""
    font = ImageFont.truetype(FONT, text_px)
    mark = render(mono_svg(color), mark_px)
    gap = round(mark_px * 0.3)
    text_w = ImageDraw.Draw(Image.new("RGBA", (1, 1))).textlength("ParchaOS", font=font)
    w = width or round(mark_px + gap + text_w + 2)
    im = Image.new("RGBA", (w, height), (0, 0, 0, 0))
    im.paste(mark, (0, (height - mark_px) // 2), mark)
    d = ImageDraw.Draw(im)
    ascent, descent = font.getmetrics()
    d.text((mark_px + gap, (height - ascent - descent) // 2 + 1), "ParchaOS", font=font, fill=color)
    return im


def tile(px):
    im = Image.new("RGBA", (px, px), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle((0, 0, px - 1, px - 1), radius=round(px * 0.22), fill=TILE)
    m = render(mono_svg("#ffffff"), round(px * 0.62))
    im.paste(m, ((px - m.width) // 2, (px - m.height) // 2), m)
    return im


def wallpaper(w, h, top=(22, 22, 26), bottom=(35, 35, 39), mark=(42, 42, 46), mark_px=420):
    im = Image.new("RGB", (w, h))
    px = im.load()
    for y in range(h):
        t = y / (h - 1)
        c = tuple(round(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        for x in range(w):
            px[x, y] = c
    m = render(mono_svg("#%02x%02x%02x" % mark), mark_px)
    im.paste(m, ((w - mark_px) // 2, (h - mark_px) // 2), m)
    return im


def replace_tile(path, new_tile_px_fn):
    """Paint a new tile over the old installer tile (found by its color)."""
    im = Image.open(path).convert("RGBA")
    px = im.load()
    xs, ys = [], []
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            if a > 200 and abs(r - TILE[0]) < 4 and abs(g - TILE[1]) < 4 and abs(b - TILE[2]) < 4:
                xs.append(x)
                ys.append(y)
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    size = max(x1 - x0, y1 - y0) + 1
    # Clear the old tile (and its glyph) before drawing the new one.
    bg = im.getpixel((max(x0 - 3, 0), max(y0 - 3, 0)))
    ImageDraw.Draw(im).rectangle((x0 - 1, y0 - 1, x0 + size, y0 + size), fill=bg)
    t = new_tile_px_fn(size)
    im.paste(t, (x0, y0), t)
    return im


OUTPUTS = {}


def main():
    color = color_svg()
    white = mono_svg("#ffffff")
    black = mono_svg("#000000")
    symbolic = mono_svg("#2e3436", symbolic=True)

    # Vector sources.
    write("branding/logo/parchaos-mark.svg", color)
    write("branding/logo/parchaos-mark-mono.svg", black)
    for p in ("packaging/parchaos-release/files/parchaos-logo.svg",
              "packaging/parchaos-icon-theme/parchaos-icons/parchaos-logo.svg"):
        write(p, color)
    for p in ("packaging/parchaos-release/files/parchaos-logo-symbolic.svg",
              "packaging/parchaos-icon-theme/parchaos-icons/parchaos-logo-symbolic.svg",
              "packaging/parchaos-global-menu/files/parchaos-menu-icon-symbolic.svg"):
        write(p, symbolic)
    # The shell theme's Activities button (white, drawn at 48 px from 16).
    write("packaging/parchaos-gtk-theme/parchaos-activities.svg",
          mono_svg("#fff").replace('width="16" height="16"', 'width="48" height="48"'))

    # Raster brand files (names kept; the "silhouette" files are the
    # one-color mark now).
    render(black, 572).save("branding/logo/parcha-logo-black.png")
    render(white, 572).save("branding/logo/parcha-logo-white.png")
    render(black, 570).save("branding/logo/parcha-silhouette-black.png")
    render(white, 570).save("branding/logo/parcha-silhouette-white.png")

    # Login screen and boot splash word marks (white on dark).
    wordmark(48, 40, 28, "#ffffff").save(
        "packaging/parchaos-gdm-logo/files/usr/share/pixmaps/parchaos-gdm-logo.png")
    wordmark(62, 48, 34, "#ffffff").save(
        "packaging/parchaos-gnome-plymouth-theme/files/parcha-plymouth/watermark.png")

    # Installer branding.
    cal = "packaging/parchaos-gnome-calamares-config/files/etc/calamares/branding/ParchaOS/"
    tile(256).save(cal + "icon.png")
    render(white, 256).save(cal + "logo.png")
    replace_tile(cal + "welcome.png", tile).save(cal + "welcome.png")
    replace_tile(cal + "slide1.png", tile).convert("RGB").save(cal + "slide1.png")

    # Wallpaper.
    wallpaper(3840, 2160).save(
        "packaging/parchaos-gnome-wallpaper/files/usr/share/backgrounds/parchaos/parchaos-wallpaper.png",
        optimize=True)
    print("brand assets written")


if __name__ == "__main__":
    main()
