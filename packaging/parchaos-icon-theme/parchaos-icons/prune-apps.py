#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""prune-apps.py <icons-dir> <allowlist>

Keeps only ParchaOS's own application icons in the MacTahoe-based themes.

MacTahoe draws near-copies of the reference desktop's app icons. The
spec already replaces the ones ParchaOS uses with original artwork; this
removes every other app icon so apps fall back to GNOME's own icons
(Adwaita, hicolor):

- In each theme's apps*/scalable directory, a file is kept only if its
  name is on the allow-list (the targets the spec replaced), and a link
  only if it resolves to a kept file.
- Kept files with a reference-desktop product name get a neutral name,
  and the links to them are repointed.
- Every fixed-size and symbolic apps directory is emptied: the replaced
  art is scalable and covers every size.
- Outside apps/, MacTahoe's drawings of Apple hardware and file types
  (iPhone, iPad, iPod, disk images, Wallet passes; names matching
  APPLE_ART) are removed so GNOME's own icons show instead.
- Links left dangling by the removals are deleted everywhere.
- Names on EXCLUDED must not survive; the script fails if one does.
"""
import os
import re
import sys

RENAMES = {"safari": "parchaos-web-browser-app", "icloud": "parchaos-cloud-app"}
EXCLUDED = re.compile(
    r"(?i)^(.*[._-])?(safari|icloud|appstore|app-store|finder|facetime|itunes|"
    r"imessage|keynote|garageband|imovie|xcode|launchpad|siri|photo-?booth|"
    r"dictionary\.app|preview\.app|macos|apple)([._-].*)?$")


APPLE_ART = re.compile(r"(?i)(^|[._-])(apple|iphone|ipad|ipod)([._-]|$)")


def stem(name):
    return name[:-4] if name.endswith(".svg") else name


def prune_scalable(d, keep):
    # Rename kept targets that carry a product name.
    for old, new in RENAMES.items():
        path = os.path.join(d, old + ".svg")
        if os.path.isfile(path) and not os.path.islink(path):
            os.replace(path, os.path.join(d, new + ".svg"))
    keep = {RENAMES.get(k, k) for k in keep}
    kept_files = {n for n in os.listdir(d)
                  if os.path.isfile(os.path.join(d, n)) and not os.path.islink(os.path.join(d, n))
                  and stem(n) in keep}
    for name in os.listdir(d):
        path = os.path.join(d, name)
        if name in kept_files:
            continue
        if os.path.islink(path):
            target = os.path.basename(os.readlink(path))
            # Follow link chains inside the directory.
            seen = set()
            while os.path.islink(os.path.join(d, target)) and target not in seen:
                seen.add(target)
                target = os.path.basename(os.readlink(os.path.join(d, target)))
            target = RENAMES.get(stem(target), stem(target)) + ".svg"
            if target in kept_files and not EXCLUDED.match(stem(name)):
                os.remove(path)
                os.symlink(target, path)
                continue
        if os.path.isdir(path) and not os.path.islink(path):
            continue
        os.remove(path)


def empty_dir(d):
    for name in os.listdir(d):
        path = os.path.join(d, name)
        if os.path.isfile(path) or os.path.islink(path):
            os.remove(path)


def main():
    icons, allowlist = sys.argv[1], sys.argv[2]
    keep = {l.strip() for l in open(allowlist) if l.strip() and not l.startswith("#")}
    for theme in sorted(os.listdir(icons)):
        root = os.path.join(icons, theme)
        if not theme.startswith("MacTahoe") or not os.path.isdir(root):
            continue
        for top in os.listdir(root):
            apps = os.path.join(root, top)
            if not top.startswith("apps") or os.path.islink(apps) or not os.path.isdir(apps):
                continue
            for sub in os.listdir(apps):
                d = os.path.join(apps, sub)
                if os.path.islink(d) or not os.path.isdir(d):
                    continue
                if sub == "scalable":
                    prune_scalable(d, keep)
                else:
                    empty_dir(d)

    # Apple hardware and file-type drawings outside apps/.
    for theme in sorted(os.listdir(icons)):
        if not theme.startswith("MacTahoe"):
            continue
        for dirpath, _, files in os.walk(os.path.join(icons, theme)):
            if "/apps" in dirpath:
                continue
            for f in files:
                if APPLE_ART.search(f):
                    os.remove(os.path.join(dirpath, f))

    # Links whose targets were removed.
    changed = True
    while changed:
        changed = False
        for dirpath, _, files in os.walk(icons):
            for f in files:
                p = os.path.join(dirpath, f)
                if os.path.islink(p) and not os.path.exists(p):
                    os.remove(p)
                    changed = True

    # Self-test: no excluded name under apps*, no Apple art anywhere,
    # no dangling links.
    bad = []
    for dirpath, _, files in os.walk(icons):
        for f in files:
            if "/apps" not in dirpath:
                if APPLE_ART.search(f):
                    bad.append(os.path.join(dirpath, f))
                continue
            p = os.path.join(dirpath, f)
            if EXCLUDED.match(stem(f)):
                bad.append(p)
            elif os.path.islink(p) and not os.path.exists(p):
                bad.append(p + " (dangling)")
    if bad:
        sys.exit("prune-apps: still present:\n  " + "\n  ".join(bad[:50]))
    kept = sum(1 for dp, _, fs in os.walk(icons) if "/apps" in dp for _ in fs)
    print(f"prune-apps: kept {kept} app icon entries")


if __name__ == "__main__":
    main()
