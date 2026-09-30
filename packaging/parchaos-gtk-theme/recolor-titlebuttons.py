#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""recolor-titlebuttons.py [--palette NAME] [--check] DIR...

Recolors MacTahoe's window buttons (close, minimize, maximize, restore) to the
ParchaOS palette (ticket #111).

MacTahoe draws them in the shades of a well-known desktop's red / yellow /
green. Coloured round buttons are common and functional; the exact shades are
what make them read as someone else's. This rewrites every
titlebutton-*.png under the given directories (GTK 3, GTK 4 and the skeleton
copy all hold identical files).

The files are palette PNGs (colour type 3), so only the PLTE colour table is
rewritten; pixel data and transparency (tRNS) are untouched, which keeps the
hand-tuned 16 px shapes, hover glyphs and antialiasing exactly as they were.

Each coloured shade is moved by its hue/saturation/value *relative to the
button's original base colour*, so the normal state lands on the new base
colour and the darker pressed state, glyph and border shades follow it.
Greys (unfocused windows) are left alone.

Fails (non-zero exit) if a file is not a palette PNG or nothing was changed, so
a change in the upstream art cannot silently ship the old colours.

Original code for ParchaOS, GPL-3.0-or-later.
"""
import argparse
import colorsys
import os
import re
import struct
import sys
import zlib

# New base colour of each button, as it should look in its normal state.
PALETTES = {
    # Logo violet and gold plus a rose-coral for Close. Three different
    # brightnesses (gold light, rose middle, violet dark) so the buttons differ
    # for colour-blind users as well as by hue.
    "passion": {"close": "#f0566f", "minimize": "#f5b700", "maximize": "#7a58e0"},
    # The same idea with a green for Maximize, for comparison.
    "leaf": {"close": "#f0566f", "minimize": "#f5b700", "maximize": "#2fbf8a"},
}
DEFAULT_PALETTE = "passion"

# The original base colours MacTahoe draws, measured from its normal-state
# buttons, per button and per scheme ("-dark" files are for dark windows).
OLD_BASE = {
    ("close", True): "#e9524a", ("close", False): "#fe6254",
    ("minimize", True): "#f1ae1b", ("minimize", False): "#fdc92d",
    ("maximize", True): "#59c837", ("maximize", False): "#28d33f",
}
GREY_BELOW = 0.12  # saturation under which a palette entry is a grey, left as is
NAME = re.compile(r"^titlebutton-(close|minimize|maximize|restore)(-[a-z-]+)?(@2)?\.png$")
# The window-manager (metacity) copies of the same buttons are SVGs. Chromium
# draws its own title bar from these (ticket #142), so they get the palette too.
SVG_NAME = re.compile(r"^titlebutton-(close|minimize|maximize|unmaximize)(-[a-z-]+)?\.svg$")
HEX = re.compile(r"#([0-9a-fA-F]{6})\b")
PNG_SIG = b"\x89PNG\r\n\x1a\n"
MARK = b"ParchaOS-recolored"  # tEXt keyword: stops a second pass recoloring twice


def hsv(hexcolor):
    r, g, b = (int(hexcolor[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return colorsys.rgb_to_hsv(r, g, b)


def transform(rgb, old, new):
    """Move one palette colour from the old base's family to the new base.

    Done in HSV, not HLS: a darker "pressed" shade is the same colour mixed
    with black (lower value, same saturation). In HLS, lowering lightness of a
    light colour towards 0.5 *raises* its intensity, which turned Maximize's
    pressed state into an electric indigo.
    """
    h, s, v = colorsys.rgb_to_hsv(*(c / 255 for c in rgb))
    if s < GREY_BELOW:
        return rgb
    oh, os_, ov = old
    nh, ns, nv = new
    h2 = (nh + (h - oh)) % 1.0
    s2 = min(1.0, s * ns / os_)
    v2 = min(1.0, v * nv / ov)
    return tuple(round(c * 255) for c in colorsys.hsv_to_rgb(h2, s2, v2))


def rewrite(data, family, dark, palette):
    """Return the PNG bytes with a recolored PLTE, and how many entries moved."""
    if data[:8] != PNG_SIG:
        raise ValueError("not a PNG")
    old = hsv(OLD_BASE[(family, dark)])
    new = hsv(PALETTES[palette][family])
    out, i, moved, saw_plte = [PNG_SIG], 8, 0, False
    while i < len(data):
        (n,) = struct.unpack(">I", data[i:i + 4])
        kind, body = data[i + 4:i + 8], data[i + 8:i + 8 + n]
        if kind == b"tEXt" and body.startswith(MARK + b"\x00"):
            return data, 0  # already done
        if kind == b"IHDR" and body[9] != 3:
            raise ValueError(f"colour type {body[9]}, expected 3 (palette)")
        if kind == b"PLTE":
            saw_plte = True
            entries = [tuple(body[j:j + 3]) for j in range(0, n, 3)]
            recolored = [transform(e, old, new) for e in entries]
            moved = sum(a != b for a, b in zip(entries, recolored))
            body = bytes(c for e in recolored for c in e)
        out.append(struct.pack(">I", len(body)) + kind + body
                   + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF))
        i += 12 + n
        if kind == b"IHDR":
            text = MARK + b"\x00" + palette.encode()
            out.append(struct.pack(">I", len(text)) + b"tEXt" + text
                       + struct.pack(">I", zlib.crc32(b"tEXt" + text) & 0xFFFFFFFF))
    if not saw_plte:
        raise ValueError("no PLTE chunk")
    return b"".join(out), moved


def rewrite_svg(text, family, palette):
    """Recolor every saturated hex colour of an SVG button; greys stay."""
    old = hsv(OLD_BASE[(family, True)])
    new = hsv(PALETTES[palette][family])

    def swap(m):
        rgb = tuple(int(m.group(1)[i:i + 2], 16) for i in (0, 2, 4))
        out = transform(rgb, old, new)
        return "#%02x%02x%02x" % out

    return HEX.sub(swap, text)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="+")
    ap.add_argument("--palette", default=DEFAULT_PALETTE, choices=sorted(PALETTES))
    ap.add_argument("--check", action="store_true", help="report only, write nothing")
    args = ap.parse_args(argv)

    files = changed = done = 0
    for top in args.dirs:
        for root, _dirs, names in os.walk(top):
            for name in sorted(names):
                sm = SVG_NAME.match(name)
                if sm:
                    path = os.path.join(root, name)
                    if os.path.islink(path):
                        continue
                    family = "maximize" if sm.group(1) == "unmaximize" else sm.group(1)
                    text = open(path, encoding="utf-8").read()
                    new_text = rewrite_svg(text, family, args.palette)
                    files += 1
                    if new_text == text:
                        done += 1
                        continue
                    changed += 1
                    if not args.check:
                        with open(path, "w", encoding="utf-8") as f:
                            f.write(new_text)
                    continue
                m = NAME.match(name)
                if not m:
                    continue
                path = os.path.join(root, name)
                if os.path.islink(path):
                    continue
                family = "maximize" if m.group(1) == "restore" else m.group(1)
                dark = "-dark" in name
                data = open(path, "rb").read()
                new, moved = rewrite(data, family, dark, args.palette)
                files += 1
                if new == data:
                    done += 1
                    continue
                changed += 1
                if not args.check:
                    with open(path, "wb") as f:
                        f.write(new)
    print(f"titlebuttons: {changed} of {files} files recolored ({args.palette}), {done} already done")
    if files == 0 or changed + done == 0:
        print("recolor-titlebuttons: no titlebutton PNGs found -- did the upstream art move?", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
