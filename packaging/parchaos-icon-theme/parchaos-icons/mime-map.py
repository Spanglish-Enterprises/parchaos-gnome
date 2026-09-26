#!/usr/bin/python3
# Replace MacTahoe's scalable file-type (mimetype) icons with ParchaOS's
# own: every real file in <theme>/mimes/scalable becomes the
# parchaos-mime-<kind>.svg for its kind, picked from the file name.
# (The 16/22/24 px and symbolic file-type icons are plain line glyphs and
# stay.) Symlinks point at the replaced files, so they follow.
#
#   mime-map.py ICONS_DIR ARTWORK_DIR          replace, print a summary
#   mime-map.py --dry-run ICONS_DIR            print name -> kind only
#
# Original code for ParchaOS, GPL-3.0-or-later.

import os
import re
import shutil
import sys

# First match wins. Matched against the icon name without ".svg".
RULES = [
    ('pdf', r'pdf|postscript|dvi|x-xps|oxps'),
    ('spreadsheet', r'spreadsheet|excel|table|csv|gdsheet|numbers|oasis-spreadsheet|x-gnumeric|ms-works'),
    ('presentation', r'presentation|powerpoint|slide|gdslides|keynote|x-kpresenter'),
    ('database', r'database|access|sqlite|sql|oasis-database|dbf|kexi'),
    ('font', r'font|ttf|otf|woff|x-pcf|bdf'),
    ('certificate', r'certificate|pgp|pkcs|x509|pem|keystore|x-java-keystore|signature|gpg|ssh-key'),
    ('contact', r'vcard|contact|addressbook|users|x-ldif'),
    ('calendar', r'calendar|x-vcalendar|ics'),
    ('mail', r'mbox|message|rfc822|x-mail|msoutlook|x-mimearchive|eml'),
    ('disk', r'iso|disk|x-ms-wim|x-cd-image|raw-disk|virtualbox|vmdk|vhd|vdi|ovf|ova|qcow|dmg|x-apple-diskimage|efi|hdd'),
    ('package', r'appimage|flatpak|x-rpm|x-deb|debian|package|apk|android|x-msi|portable-executable|'
                r'x-executable|x-sharedlib|software|system-component|extension|addon|x-ms-dos|x-shellscript-exec|'
                r'x-desktop|snap|x-content-software|x-bat|msdownload|ms-shortcut|firmware|x-object|macbinary|x-plasma|partial-download'),
    ('archive', r'zip|tar|rar|7z|gzip|bzip|xz|lzma|lz|zstd|compress|archive|cab|x-cpio|x-ar|jar|x-ace|x-arj|'
                r'x-lha|x-stuffit|squashfs|torrent'),
    ('audio', r'(^|-)audio|clementine|ogg|playlist|podcast|x-mpegurl|x-scpls|mp3|flac|midi|x-wav|opus'),
    ('video', r'(^|-)video|x-matroska|mp4|webm|x-flv|x-ms-wmv|quicktime|vnd.rn-realmedia'),
    ('image', r'(^|-)image|visio|x-designer|photoshop|illustrator|vector|drawing|gddraw|dicom|x-xcf|x-krita|svg|x-blender|'
              r'x-gimp|x-inkscape|oasis-drawing|x-3d|model'),
    ('web', r'html|xhtml|x-mozilla-bookmarks|oasis-web|gdlink|url|x-web|rss|atom|x-webarchive'),
    ('code', r'x-c($|\+|hdr|pp|src)|x-code-workspace|x-changelog|x-cobol|x-copying|x-cmake|x-csharp|x-python|javascript|json|x-java|x-script|script|x-ruby|x-perl|x-php|x-sh|x-shellscript|'
             r'x-go|x-rust|typescript|coffeescript|x-lua|x-makefile|x-cmake|x-patch|x-diff|xml|yaml|toml|'
             r'css|x-sass|x-scss|x-less|x-csharp|x-kotlin|x-swift|x-haskell|x-erlang|x-elixir|x-scala|'
             r'x-tex|x-lisp|x-scheme|x-ocaml|x-fortran|x-pascal|x-vala|x-meson|x-gettext|x-qml|'
             r'x-matlab|mathematica|x-r|x-sql|x-authors|x-install|x-readme|x-copying|x-changelog|x-credits|'
             r'x-log|x-ini|x-dockerfile|x-nix|x-typst|x-markdown|x-rst|asciidoc|ipynb|x-ipynb'),
    ('document', r'document|chm|msword|word|rtf|oasis-text|oasis-master|opendocument|gddoc|epub|x-abiword|'
                 r'wordperfect|x-kword|pages|x-fictionbook|x-mobipocket|djvu|note|onenote|rnote|gdnote|'
                 r'gdform|formula|x-office|publisher|scribus|freeplane|minder|kplato|kmymoney|kvtml|labplot|geogebra'),
    ('text', r'^text|ascii|info|plain|blank|template|readme'),
]
COMPILED = [(kind, re.compile(pattern)) for kind, pattern in RULES]


def kind_of(name):
    for kind, pattern in COMPILED:
        if pattern.search(name):
            return kind
    return 'generic'


def targets(icons_dir):
    for theme in sorted(os.listdir(icons_dir)):
        d = os.path.join(icons_dir, theme, 'mimes', 'scalable')
        if not theme.startswith('MacTahoe') or not os.path.isdir(d) or os.path.islink(d):
            continue
        for f in sorted(os.listdir(d)):
            path = os.path.join(d, f)
            if f.endswith('.svg') and os.path.isfile(path) and not os.path.islink(path):
                yield path, f[:-4]


def main(argv):
    if argv[1:2] == ['--dry-run']:
        for _path, name in targets(argv[2]):
            print(f'{name} -> {kind_of(name)}')
        return 0
    icons_dir, artwork = argv[1], argv[2]
    counts = {}
    for path, name in targets(icons_dir):
        kind = kind_of(name)
        shutil.copyfile(os.path.join(artwork, f'parchaos-mime-{kind}.svg'), path)
        counts[kind] = counts.get(kind, 0) + 1
    print('file-type icons replaced:', ', '.join(f'{k} {n}' for k, n in sorted(counts.items())))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
