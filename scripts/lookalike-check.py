#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""lookalike-check.py [--gate] [--report DIR] [--root DIR]

The automated parts of the look-alike audit (ticket "Look-alike audit"; the written spec is in the
Claude Memory vault, parchaos-gnome/architecture/lookalike-audit-spec.md).

  1. Names and words: scans every tracked text file for the terms in scripts/lookalike-terms.txt.
     A "deny" hit that scripts/lookalike-allow.txt does not excuse (with a reason) fails.
  2. Assets: every tracked image, font, sound or video must be covered by a row in
     docs/asset-provenance.csv saying where it came from. A shipped asset with no row fails.

Plain run (used by scripts/lint.sh): fails on a new deny hit or an asset with no row.
--image DIR  also scans a built image's root (a rootfs): desktop entries, metainfo, schemas, shell
             extensions, ParchaOS docs, and the printable strings of the packages' binaries and
             translations, because the build rewrites strings the source scan cannot see. Allow-list lines for
             it start with "image/" (the path inside the rootfs).
--gate       the release and revenue gate: also fails while any provenance row is still "unverified"
             or of kind "unknown", and while any allow-list line is marked "debt:" (clean-up still owed).
--report DIR writes a hand-over folder for counsel (summary, provenance rows still open, review hits).

Not legal advice: this finds what a script can find. The elements that need a person's eye are in the
private audit register.
"""
import csv
import fnmatch
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TERMS = os.environ.get('LOOKALIKE_TERMS', os.path.join(HERE, 'lookalike-terms.txt'))
ALLOW = os.environ.get('LOOKALIKE_ALLOW', os.path.join(HERE, 'lookalike-allow.txt'))
PROVENANCE = 'docs/asset-provenance.csv'
ASSET_EXT = {'.png', '.jpg', '.jpeg', '.svg', '.svgz', '.ico', '.icns', '.gif', '.webp', '.ttf', '.otf',
             '.woff', '.woff2', '.ogg', '.oga', '.wav', '.mp3', '.flac', '.mp4', '.webm', '.mov', '.xcf'}
KINDS = {'own-drawn', 'own-generated', 'ai-generated', 'traced-from-ai', 'upstream', 'screenshot', 'unknown'}
# files that hold the terms themselves, or are this check's own data
SKIP_SCAN = {'scripts/lookalike-terms.txt', 'scripts/lookalike-allow.txt', 'docs/asset-provenance.csv'}
MAX_BYTES = 2_000_000
REASONS = ('fact:', 'tool:', 'upstream:', 'history:', 'debt:')


def tracked_files(root):
    try:
        out = subprocess.run(['git', '-C', root, 'ls-files', '-z', '--cached', '--others', '--exclude-standard'],
                             check=True, capture_output=True).stdout.decode()
        return sorted(f for f in out.split('\0') if f and os.path.isfile(os.path.join(root, f)))
    except (OSError, subprocess.CalledProcessError):
        found = []
        for base, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d != '.git']
            found += [os.path.relpath(os.path.join(base, f), root) for f in files]
        return sorted(found)


def load_terms():
    terms = []
    for n, line in enumerate(open(TERMS, encoding='utf-8'), 1):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = line.split(None, 1)
        level, pattern = parts[0], (parts[1].strip() if len(parts) > 1 else '')
        if level not in ('deny', 'review') or not pattern:
            sys.exit(f'{TERMS}:{n}: expected "deny|review <regex>"')
        terms.append((level, re.compile(pattern, re.I)))
    return terms


def load_allow():
    allow = []
    if not os.path.exists(ALLOW):
        return allow
    for n, line in enumerate(open(ALLOW, encoding='utf-8'), 1):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = [p.strip() for p in line.split('|', 2)]
        if len(parts) != 3 or not all(parts):
            sys.exit(f'{ALLOW}:{n}: expected "path glob | term (or *) | reason" and a reason is required')
        if not parts[2].startswith(REASONS):
            sys.exit(f'{ALLOW}:{n}: the reason must start with one of {", ".join(REASONS)}')
        allow.append((parts[0], parts[1].lower(), parts[2]))
    return allow


def allowed(allow, path, term):
    return any(fnmatch.fnmatch(path, g) and (t == '*' or t == term.lower()) for g, t, _r in allow)


def read_text(root, path):
    full = os.path.join(root, path)
    try:
        if os.path.getsize(full) > MAX_BYTES:
            return None
        data = open(full, 'rb').read()
    except OSError:
        return None
    if b'\0' in data[:4096]:
        return None
    try:
        return data.decode('utf-8')
    except UnicodeDecodeError:
        return None


def scan_names(root, files):
    terms, allow = load_terms(), load_allow()
    denied, review = [], {}
    used = set()
    for path in files:
        if path in SKIP_SCAN or os.path.splitext(path)[1].lower() in ASSET_EXT:
            continue
        text = read_text(root, path)
        if text is None:
            continue
        for n, line in enumerate(text.splitlines(), 1):
            for level, rx in terms:
                for m in rx.finditer(line):
                    term = m.group(0).lower()
                    if level == 'review':
                        review.setdefault(term, set()).add(path)
                    elif allowed(allow, path, term):
                        used.add((path, term))
                    else:
                        denied.append((path, n, term, line.strip()[:140]))
    return denied, review


# Only what ParchaOS owns or builds is scanned: its own files and Parcher (the file manager); the other
# applications in the image keep their own wording.
IMAGE_TEXT = ('usr/share/doc/parchaos', 'etc/os-release', 'usr/lib/os-release', 'etc/system-release')
IMAGE_OWNED_DIRS = ('usr/share/applications', 'usr/share/metainfo', 'usr/share/glib-2.0/schemas',
                    'usr/share/polkit-1/actions')
IMAGE_OWNED_NAMES = ('parcha', 'org.parchaos', 'org.gnome.nautilus', 'org.gnome.nautilus.')
IMAGE_STRINGS = ('usr/bin/nautilus', 'usr/bin/parchaos-', 'usr/libexec/parchaos-', 'usr/lib64/nautilus')
IMAGE_MO = ('nautilus', 'parchaos', 'parcha')


def image_files(root):
    found = []
    for base, dirs, files in os.walk(root):
        rel_base = os.path.relpath(base, root)
        if rel_base.startswith(('proc', 'sys', 'dev', 'run', 'var/cache', 'var/lib/rpm')):
            dirs[:] = []
            continue
        for f in files:
            rel = os.path.normpath(os.path.join(rel_base, f))
            full = os.path.join(base, f)
            if os.path.islink(full) or not os.path.isfile(full):
                continue
            owned = rel.startswith(IMAGE_OWNED_DIRS) and os.path.basename(rel).lower().startswith(IMAGE_OWNED_NAMES)
            if rel.startswith(IMAGE_TEXT) or owned or (rel.startswith('usr/share/gnome-shell/extensions/') and
                                              ('parchaos' in rel or 'parcha' in rel)) or \
                    rel.startswith(IMAGE_STRINGS) or \
                    (rel.startswith('usr/share/locale/') and rel.endswith('.mo') and
                     os.path.basename(rel).startswith(IMAGE_MO)):
                found.append(rel)
    return sorted(found)


def printable_runs(data, minimum=6):
    out, run = [], bytearray()
    for b in data:
        if 32 <= b < 127 or b in (9,):
            run.append(b)
        else:
            if len(run) >= minimum:
                out.append(run.decode('ascii'))
            run = bytearray()
    if len(run) >= minimum:
        out.append(run.decode('ascii'))
    return out


def scan_image(root):
    terms, allow = load_terms(), load_allow()
    denied = []
    for rel in image_files(root):
        try:
            data = open(os.path.join(root, rel), 'rb').read()
        except OSError:
            continue
        lines = printable_runs(data) if b'\0' in data[:4096] else data.decode('utf-8', 'replace').splitlines()
        shown = 'image/' + rel
        for n, line in enumerate(lines, 1):
            for level, rx in terms:
                if level != 'deny':
                    continue
                for m in rx.finditer(line):
                    term = m.group(0).lower()
                    if not allowed(allow, shown, term):
                        denied.append((shown, n, term, line.strip()[:140]))
    return denied


def load_provenance(root):
    path = os.path.join(root, PROVENANCE)
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, newline='', encoding='utf-8') as f:
        for r in csv.DictReader(line for line in f if not line.lstrip().startswith('#')):
            rows.append(r)
    return rows


def check_assets(root, files):
    rows = load_provenance(root)
    problems, uncovered, stale, open_rows = [], [], [], []
    for r in rows:
        for key in ('path', 'kind', 'source', 'license', 'made_by', 'status'):
            if not (r.get(key) or '').strip():
                problems.append(f'{PROVENANCE}: row "{r.get("path")}" has no {key}')
        if r.get('kind') not in KINDS:
            problems.append(f'{PROVENANCE}: row "{r.get("path")}" has kind "{r.get("kind")}" '
                            f'(use one of {sorted(KINDS)})')
        if r.get('status') not in ('verified', 'unverified'):
            problems.append(f'{PROVENANCE}: row "{r.get("path")}" status must be verified or unverified')
        if r.get('kind') == 'unknown' and r.get('status') == 'verified':
            problems.append(f'{PROVENANCE}: row "{r.get("path")}" is kind unknown, so it cannot be verified')
        if r.get('status') != 'verified' or r.get('kind') == 'unknown':
            open_rows.append(r)
    assets = [f for f in files if os.path.splitext(f)[1].lower() in ASSET_EXT]
    for a in assets:
        if not any(fnmatch.fnmatch(a, r['path']) for r in rows if r.get('path')):
            uncovered.append(a)
    for r in rows:
        if r.get('path') and not any(fnmatch.fnmatch(a, r['path']) for a in assets):
            stale.append(r['path'])
    return problems, uncovered, stale, open_rows, len(assets)


def main(argv):
    gate = '--gate' in argv
    image = argv[argv.index('--image') + 1] if '--image' in argv else None
    root = os.getcwd()
    report = None
    if '--root' in argv:
        root = argv[argv.index('--root') + 1]
    if '--report' in argv:
        report = argv[argv.index('--report') + 1]
    files = tracked_files(root)
    failed = False

    print('== look-alike audit: names and words ==')
    denied, review = scan_names(root, files)
    for path, n, term, text in denied[:60]:
        print(f'  {path}:{n}: "{term}": {text}')
    if len(denied) > 60:
        print(f'  ... and {len(denied) - 60} more')
    if denied:
        print(f'FAIL: {len(denied)} use(s) of a listed term that is not excused. Rename it, or add a line with '
              f'a reason to scripts/lookalike-allow.txt if it is a factual statement (credits, legal notice).')
        failed = True
    else:
        print('  no unexcused names')
    if review:
        print('  for review (not failures): ' + ', '.join(f'{t} ({len(p)} files)' for t, p in sorted(review.items())))

    if image:
        print(f'== look-alike audit: the built image ({image}) ==')
        idenied = scan_image(image)
        seen = set()
        for path, n, term, text in idenied:
            key = (path, term)
            if key in seen:
                continue
            seen.add(key)
            print(f'  {path}: "{term}": {text}')
        if idenied:
            print(f'FAIL: {len(seen)} listed name(s) in what the image ships (counted once per file and name).')
            failed = True
        else:
            print('  no listed names in the shipped strings that were scanned')

    print('== look-alike audit: asset provenance ==')
    problems, uncovered, stale, open_rows, count = check_assets(root, files)
    for p in problems:
        print(f'  {p}')
    for a in uncovered[:60]:
        print(f'  no provenance row for {a}')
    if len(uncovered) > 60:
        print(f'  ... and {len(uncovered) - 60} more')
    for s in stale:
        print(f'  note: row "{s}" matches no tracked asset (stale?)')
    if problems or uncovered:
        print(f'FAIL: add rows to {PROVENANCE} (kind, source, licence, who made it, verified or not).')
        failed = True
    else:
        print(f'  all {count} assets covered; {len(open_rows)} row(s) still unverified or unknown')
    if gate:
        debts = [(g, t, r) for g, t, r in load_allow() if r.startswith('debt:')]
        if debts:
            print('GATE: names still owed a clean-up (scripts/lookalike-allow.txt, "debt:"):')
            for g, t, r in debts:
                print(f'  {g} ({t}): {r}')
            failed = True
    if gate and open_rows:
        print('GATE: these provenance rows are not settled yet:')
        for r in open_rows:
            print(f'  {r["path"]}: {r["kind"]}, {r["status"]}: {r.get("notes", "")[:100]}')
        failed = True

    if report:
        os.makedirs(report, exist_ok=True)
        with open(os.path.join(report, 'summary.txt'), 'w', encoding='utf-8') as f:
            f.write('Look-alike audit: automated results\n')
            f.write(f'Unexcused names: {len(denied)}\nAssets: {count}, uncovered: {len(uncovered)}\n')
            f.write(f'Provenance rows still open: {len(open_rows)}\n')
            f.write('Review terms: ' + ', '.join(f'{t} ({len(p)} files)' for t, p in sorted(review.items())) + '\n')
        if os.path.exists(os.path.join(root, PROVENANCE)):
            with open(os.path.join(root, PROVENANCE), encoding='utf-8') as src, \
                    open(os.path.join(report, 'asset-provenance.csv'), 'w', encoding='utf-8') as dst:
                dst.write(src.read())
        with open(os.path.join(report, 'open-rows.txt'), 'w', encoding='utf-8') as f:
            for r in open_rows:
                f.write(f'{r["path"]}\t{r["kind"]}\t{r["status"]}\t{r.get("notes", "")}\n')
        print(f'report written to {report}')

    print('look-alike audit: ' + ('FAILED' if failed else 'ok'))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
