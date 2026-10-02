#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""make-brand.py -- generates every ParchaOS logo asset from one design.

The ParchaOS mark is an original drawing (owner-approved concept "A",
revised 2026-09-26 after a WIPO image search): a halved passion fruit
seen from above -- a rind with an open gap at the upper right, a pith
ring, the pulp and irregular, hand-placed seeds. It has no stem, leaf or
bite, and no radial symmetry, so it doesn't read as another company's
fruit logo or as a ring-of-dots mark. Artwork: CC BY-SA 4.0
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


# Seeds as (cx, cy, half-length, half-width, angle in degrees) on a
# 64-unit canvas: hand-placed and irregular, like a real cut passion
# fruit, so the mark has no radial symmetry (no rosette, spokes or dot
# grid). SMALL_SEEDS is the simplified set for 16-32 px glyphs.
SEEDS = [(24.5, 23.0, 4.1, 2.5, -35), (35.0, 20.5, 3.8, 2.4, 20), (43.0, 28.0, 4.0, 2.5, 70),
         (29.5, 32.0, 3.6, 2.3, 110), (38.5, 36.5, 4.2, 2.6, -15), (22.0, 39.0, 3.9, 2.4, 60),
         (31.0, 44.0, 4.0, 2.5, -60), (42.5, 43.5, 3.5, 2.2, 35)]
SMALL_SEEDS = [(25.5, 24.5, 5.0, 3.2, -35), (38.5, 25.0, 4.8, 3.1, 35), (31.0, 34.5, 5.0, 3.2, 100),
               (22.5, 39.5, 4.6, 3.0, 40), (40.5, 40.5, 5.0, 3.2, -20)]
# The rind has an open gap at the upper right (degrees; 0 = right, up is
# negative), which gives the mark its own silhouette.
GAP = (-62, -28)
GAP_SMALL = (-62, -24)


def ring_with_gap(r_out, r_in, gap, c=32):
    """A ring (annulus) with the angular range `gap` cut out."""
    a0, a1 = gap
    pt = lambda r, a: (c + r * math.cos(math.radians(a)), c + r * math.sin(math.radians(a)))
    x1, y1 = pt(r_out, a1)
    x2, y2 = pt(r_out, a0 + 360)
    x3, y3 = pt(r_in, a0 + 360)
    x4, y4 = pt(r_in, a1)
    return (f"M{x1:.2f} {y1:.2f}A{r_out} {r_out} 0 1 1 {x2:.2f} {y2:.2f}"
            f"L{x3:.2f} {y3:.2f}A{r_in} {r_in} 0 1 0 {x4:.2f} {y4:.2f}Z")


def seed_path(x, y, half_len, half_w, angle):
    a = math.radians(angle)
    ux, uy = math.cos(a), math.sin(a)
    x1, y1, x2, y2 = x + half_len * ux, y + half_len * uy, x - half_len * ux, y - half_len * uy
    return (f"M{x1:.2f} {y1:.2f}A{half_len:.2f} {half_w:.2f} {angle:.1f} 1 0 {x2:.2f} {y2:.2f}"
            f"A{half_len:.2f} {half_w:.2f} {angle:.1f} 1 0 {x1:.2f} {y1:.2f}Z")


def circle_path(cx, cy, r):
    return (f"M{cx - r:.3f} {cy:.3f}a{r:.3f} {r:.3f} 0 1 0 {2 * r:.3f} 0"
            f"a{r:.3f} {r:.3f} 0 1 0 {-2 * r:.3f} 0z")


def color_svg():
    parts = [f'<path fill="{PURPLE}" d="{ring_with_gap(30, 24.5, GAP)}"/>',
             f'<circle cx="32" cy="32" r="24.5" fill="{PITH}"/>',
             f'<circle cx="32" cy="32" r="21.5" fill="{PULP}"/>']
    parts += [f'<path fill="{SEED}" d="{seed_path(*sd)}"/>' for sd in SEEDS]
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" '
            'viewBox="0 0 64 64">' + "".join(parts) + "</svg>\n")


def mono_svg(fill, size=64, small=None, symbolic=False):
    """One-color mark: the rind (with its gap) and the pulp with the seeds
    cut out. Sizes of 32 px or less use the simplified seed set."""
    if small is None:
        small = size <= 32
    if small:
        rind, pulp, seeds = ring_with_gap(31, 25, GAP_SMALL), circle_path(32, 32, 20.5), SMALL_SEEDS
    else:
        rind, pulp, seeds = ring_with_gap(30, 25.5, GAP), circle_path(32, 32, 22), SEEDS
    cls = ' class="ParchaOS-mark"' if symbolic else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
            f'viewBox="0 0 64 64"><path{cls} fill="{fill}" d="{rind}"/>'
            f'<path{cls} fill="{fill}" fill-rule="evenodd" '
            f'd="{pulp}{"".join(seed_path(*sd) for sd in seeds)}"/></svg>\n')


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
    mark = render(mono_svg(color, small=mark_px <= 32), mark_px)
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


def _ss(draw_fn, size, scale=4):
    """Draw at 4x and shrink, so shapes have smooth edges."""
    im = Image.new("RGBA", (size[0] * scale, size[1] * scale), (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(im), scale)
    return im.resize(size, Image.LANCZOS)


def arrow(draw, scale, cx, cy, w, h, colour, direction):
    """A plain block arrow, drawn here (not taken from anywhere)."""
    s = scale
    shaft, head = w * 0.34, h * 0.52
    if direction == "down":
        draw.rectangle(((cx - shaft / 2) * s, (cy - h / 2) * s, (cx + shaft / 2) * s, (cy + h / 2 - head) * s), fill=colour)
        draw.polygon([((cx - w / 2) * s, (cy + h / 2 - head) * s), ((cx + w / 2) * s, (cy + h / 2 - head) * s),
                      (cx * s, (cy + h / 2) * s)], fill=colour)
    else:
        draw.rectangle(((cx - w / 2) * s, (cy - shaft / 2) * s, (cx + w / 2 - head) * s, (cy + shaft / 2) * s), fill=colour)
        draw.polygon([((cx + w / 2 - head) * s, (cy - h / 2) * s), ((cx + w / 2 - head) * s, (cy + h / 2) * s),
                      ((cx + w / 2) * s, cy * s)], fill=colour)


def installer_welcome():
    """The installer's welcome image: the ParchaOS tile with an arrow pointing down at it."""
    w, h = 900, 516
    im = Image.new("RGBA", (w, h), (0, 0, 0, 255))
    layer = _ss(lambda d, s: arrow(d, s, w / 2, 150, 70, 90, (122, 122, 133, 255), "down"), (w, h))
    im.alpha_composite(layer)
    t = tile(180)
    im.alpha_composite(t, (w // 2 - 90, 250))
    return im


def installer_slide():
    """The installer slide: the ParchaOS tile, an arrow, and a laptop drawn as plain shapes."""
    w, h = 1920, 1080
    im = Image.new("RGBA", (w, h))
    px = ImageDraw.Draw(im)
    for y in range(h):
        f = y / (h - 1)
        px.line([(0, y), (w, y)], fill=(int(28 + 10 * f), int(28 + 10 * f), int(32 + 10 * f), 255))
    im.alpha_composite(tile(300), (410, 390))

    def shapes(d, s):
        arrow(d, s, 960, 540, 150, 110, (122, 122, 133, 255), "right")
        # laptop: a rounded screen, a small dot above the base line
        d.rounded_rectangle((1210 * s, 410 * s, 1510 * s, 600 * s), radius=18 * s, fill=(205, 205, 212, 255))
        d.ellipse((1352 * s, 496 * s, 1368 * s, 512 * s), fill=(140, 140, 150, 255))
        d.rectangle((1230 * s, 566 * s, 1490 * s, 569 * s), fill=(160, 160, 170, 255))

    im.alpha_composite(_ss(shapes, (w, h)))
    return im.convert("RGB")


OUTPUTS = {}


def main():
    color = color_svg()
    white = mono_svg("#ffffff")
    black = mono_svg("#000000")
    symbolic = mono_svg("#2e3436", size=16, symbolic=True)

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
          mono_svg("#fff", size=48, small=True))

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
    # Drawn from scratch here: the shapes are plain (an arrow, a tile, a laptop outline) and nothing is
    # inherited from an earlier installer theme.
    installer_welcome().save(cal + "welcome.png")
    installer_slide().save(cal + "slide1.png")

    # Wallpaper.
    wallpaper(3840, 2160).save(
        "packaging/parchaos-gnome-wallpaper/files/usr/share/backgrounds/parchaos/parchaos-wallpaper.png",
        optimize=True)
    print("brand assets written")


if __name__ == "__main__":
    main()
