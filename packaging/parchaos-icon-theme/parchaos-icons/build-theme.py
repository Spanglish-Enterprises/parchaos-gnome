#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""build-theme.py <theme-dir> <theme-name> <sources-dir>

Builds one ParchaOS icon theme from ParchaOS's own drawings only (no third-party icon art):

  - theme-skeleton.tsv says which icon names the drawings answer to and where they sit: a "F" row is a real
    file (copied from <sources-dir>), a "L" row is a relative link to another entry;
  - index-sections.ini holds the directory definitions the theme needs;
  - the theme inherits Adwaita and hicolor, so every other icon falls back to GNOME's own.

Fails if a link dangles, if a source drawing is missing, or if an installed name is one that belongs to
another company (the same list the audit uses).
"""
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKELETON = os.environ.get('PARCHAOS_ICON_SKELETON', os.path.join(HERE, 'theme-skeleton.tsv'))
SECTIONS = os.environ.get('PARCHAOS_ICON_SECTIONS', os.path.join(HERE, 'index-sections.ini'))
EXCLUDED = re.compile(
    r"(?i)^(.*[._-])?(safari|icloud|appstore|app-store|finder|facetime|itunes|"
    r"imessage|keynote|garageband|imovie|xcode|launchpad|siri|photo-?booth|"
    r"dictionary\.app|preview\.app|macos|apple)([._-].*)?$")


def main(theme_dir, name, sources):
    rows = []
    for line in open(SKELETON, encoding='utf-8'):
        if line.startswith('#') or not line.strip():
            continue
        path, kind, value = line.rstrip('\n').split('\t')
        rows.append((path, kind, value))
    problems = []
    dirs = set()
    for path, kind, value in rows:
        stem = os.path.basename(path)[:-4]
        if EXCLUDED.match(stem):
            problems.append(f'excluded name installed: {path}')
        dest = os.path.join(theme_dir, path)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        dirs.add(os.path.dirname(path))
        if kind == 'F':
            src = os.path.join(sources, value)
            if not os.path.isfile(src):
                problems.append(f'missing drawing {value} for {path}')
                continue
            shutil.copyfile(src, dest)
            os.chmod(dest, 0o644)
        elif kind == 'L':
            os.symlink(value, dest)
        else:
            problems.append(f'bad row kind {kind!r} for {path}')
    for path, kind, value in rows:
        if kind == 'L' and not os.path.isfile(os.path.realpath(os.path.join(theme_dir, path))):
            problems.append(f'dangling link {path} -> {value}')
    if problems:
        print('\n'.join(problems[:30]), file=sys.stderr)
        sys.exit(f'{len(problems)} problem(s) building {name}')
    sections = open(SECTIONS, encoding='utf-8').read()
    declared = re.findall(r'^\[([^\]]+)\]', sections, re.M)
    missing = sorted(d for d in dirs if d not in declared)
    if missing:
        sys.exit(f'directories without a definition in index-sections.ini: {missing}')
    with open(os.path.join(theme_dir, 'index.theme'), 'w', encoding='utf-8') as f:
        f.write('[Icon Theme]\n')
        f.write(f'Name={name}\n')
        f.write("Comment=ParchaOS's own icons for apps, folders and file types, over GNOME's Adwaita\n")
        f.write('Inherits=Adwaita,hicolor\nExample=folder\n')
        f.write('Directories=' + ','.join(d for d in declared if d in dirs) + '\n\n')
        f.write(sections)
    print(f'{name}: {sum(1 for r in rows if r[1] == "F")} drawings, {sum(1 for r in rows if r[1] == "L")} names')


if __name__ == '__main__':
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(*sys.argv[1:])
