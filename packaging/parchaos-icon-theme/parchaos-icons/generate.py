#!/usr/bin/python3
# Generates the ParchaOS app icons (original artwork, CC BY-SA 4.0) that
# replace MacTahoe's reproductions of Apple's app icons. Every icon shares
# the ParchaOS tile: a 448 px rounded square on a 512 grid with a vertical
# gradient, a light top gloss, a thin light rim and a soft drop shadow.
#
#   ./generate.py          writes <name>.svg next to this script
#
# Palette follows the existing ParchaOS icons (folder blues, white tiles,
# soft violet, passion-fruit gold). Motifs are chosen to be clearly
# different from the corresponding Apple designs.

import os

HERE = os.path.dirname(os.path.abspath(__file__))

DEFS = '''<defs><filter id="sh" x="-10%" y="-10%" width="120%" height="125%"><feDropShadow dx="0" dy="6" stdDeviation="9" flood-color="#000" flood-opacity="0.22"/></filter><linearGradient id="gloss" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity="0.28"/><stop offset="0.45" stop-color="#fff" stop-opacity="0"/></linearGradient><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{top}"/><stop offset="1" stop-color="{bottom}"/></linearGradient>{extra}</defs>'''

TILE = ('<rect x="32" y="28" width="448" height="448" rx="104" fill="url(#bg)" filter="url(#sh)"/>'
        '<rect x="32" y="28" width="448" height="448" rx="104" fill="url(#gloss)"/>'
        '<rect x="33" y="29" width="446" height="446" rx="103" fill="none" stroke="#fff" stroke-opacity="0.35" stroke-width="2"/>')


def tile(top, bottom, body, extra=''):
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">'
            + DEFS.format(top=top, bottom=bottom, extra=extra) + TILE + body + '</svg>\n')


def calendar():
    # A white month card with ring binders; days as dots, today in gold.
    dots = []
    for row in range(4):
        for col in range(5):
            cx, cy = 172 + col * 42, 256 + row * 38
            if (row, col) == (1, 2):
                dots.append(f'<circle cx="{cx}" cy="{cy}" r="17" fill="#f2b632"/>')
            else:
                dots.append(f'<circle cx="{cx}" cy="{cy}" r="8" fill="#b9a6e8"/>')
    body = ('<rect x="118" y="150" width="276" height="266" rx="30" fill="#fff"/>'
            '<rect x="118" y="150" width="276" height="62" rx="30" fill="#efeafc"/>'
            '<rect x="118" y="182" width="276" height="30" fill="#efeafc"/>'
            '<rect x="178" y="126" width="18" height="56" rx="9" fill="#5b3fb0"/>'
            '<rect x="316" y="126" width="18" height="56" rx="9" fill="#5b3fb0"/>'
            + ''.join(dots))
    return tile('#9d82f0', '#5b3fb0', body)


def clock():
    ticks = []
    for i in range(12):
        long = i % 3 == 0
        ticks.append(f'<rect x="251" y="{112 if long else 118}" width="10" height="{40 if long else 26}" rx="5" '
                     f'fill="#fff" fill-opacity="{1 if long else 0.7}" transform="rotate({i * 30} 256 252)"/>')
    body = (''.join(ticks)
            + '<rect x="248" y="162" width="16" height="96" rx="8" fill="#fff" transform="rotate(62 256 252)"/>'
            + '<rect x="249" y="186" width="14" height="72" rx="7" fill="#f2b632" transform="rotate(-38 256 252)"/>'
            + '<circle cx="256" cy="252" r="16" fill="#f2b632"/><circle cx="256" cy="252" r="6" fill="#13535c"/>')
    return tile('#2fa3a8', '#13535c', body)


def calculator():
    pill = lambda x, y, sym: (f'<rect x="{x}" y="{y}" width="130" height="92" rx="30" fill="#fff" fill-opacity="0.95"/>'
                              f'<text x="{x + 65}" y="{y + 64}" font-family="sans-serif" font-size="68" font-weight="700" '
                              f'text-anchor="middle" fill="#e85d4f">{sym}</text>')
    body = ('<rect x="112" y="112" width="288" height="72" rx="22" fill="#fff" fill-opacity="0.28"/>'
            '<rect x="300" y="138" width="80" height="20" rx="10" fill="#fff"/>'
            + pill(112, 206, '+') + pill(270, 206, '−') + pill(112, 318, '×') + pill(270, 318, '='))
    return tile('#ff9a7a', '#e2493f', body)


def contacts():
    body = ('<rect x="104" y="128" width="304" height="256" rx="34" fill="#fff"/>'
            '<circle cx="186" cy="226" r="46" fill="#bfe5c7"/>'
            '<circle cx="186" cy="212" r="20" fill="#2f9e56"/>'
            '<path d="M150 262a36 30 0 0 1 72 0z" fill="#2f9e56"/>'
            '<rect x="252" y="196" width="118" height="20" rx="10" fill="#2f9e56"/>'
            '<rect x="252" y="232" width="90" height="16" rx="8" fill="#bfe5c7"/>'
            '<rect x="136" y="306" width="240" height="16" rx="8" fill="#e5f3e8"/>'
            '<rect x="136" y="338" width="170" height="16" rx="8" fill="#e5f3e8"/>')
    return tile('#6ed48b', '#2f9e56', body)


def mail():
    body = ('<rect x="100" y="152" width="312" height="214" rx="30" fill="#fff"/>'
            '<path d="M112 172 L256 276 L400 172" fill="none" stroke="#f0d9a8" stroke-width="18" stroke-linecap="round" stroke-linejoin="round"/>'
            '<circle cx="256" cy="286" r="34" fill="#7a55d6"/>'
            '<path d="M244 286a12 12 0 0 1 24 0" fill="none" stroke="#fff" stroke-width="8" stroke-linecap="round"/>')
    return tile('#ffc75a', '#e8912a', body)


def settings():
    row = lambda y, knob: (f'<rect x="116" y="{y - 9}" width="280" height="18" rx="9" fill="#fff" fill-opacity="0.45"/>'
                           f'<rect x="116" y="{y - 9}" width="{knob - 116}" height="18" rx="9" fill="#fff"/>'
                           f'<circle cx="{knob}" cy="{y}" r="30" fill="#fff"/>'
                           f'<circle cx="{knob}" cy="{y}" r="12" fill="#556277"/>')
    body = row(166, 300) + row(252, 184) + row(338, 262)
    return tile('#8d9bb3', '#46526a', body)


def terminal():
    body = ('<path d="M136 188 L212 252 L136 316" fill="none" stroke="#7ee39a" stroke-width="34" stroke-linecap="round" stroke-linejoin="round"/>'
            '<rect x="244" y="296" width="118" height="36" rx="12" fill="#f2b632"/>')
    return tile('#3b3f86', '#1b1d45', body)


def text_editor():
    body = ('<rect x="120" y="108" width="236" height="296" rx="28" fill="#fff"/>'
            '<rect x="156" y="164" width="164" height="16" rx="8" fill="#cfe2f7"/>'
            '<rect x="156" y="204" width="140" height="16" rx="8" fill="#cfe2f7"/>'
            '<rect x="156" y="244" width="152" height="16" rx="8" fill="#cfe2f7"/>'
            '<rect x="156" y="284" width="96" height="16" rx="8" fill="#cfe2f7"/>'
            '<g transform="rotate(40 330 300)">'
            '<rect x="306" y="170" width="48" height="190" rx="12" fill="#f2b632"/>'
            '<rect x="306" y="170" width="48" height="34" rx="12" fill="#e2493f"/>'
            '<path d="M306 360 L330 404 L354 360z" fill="#f6dcae"/>'
            '<path d="M322 390 L330 404 L338 390z" fill="#46526a"/></g>')
    return tile('#6aa9f0', '#2f6fc9', body)


def weather():
    body = ('<circle cx="304" cy="206" r="72" fill="#ffd166"/>'
            '<circle cx="304" cy="206" r="96" fill="#ffd166" fill-opacity="0.22"/>'
            '<path d="M162 364h178a58 58 0 0 0 0-116 84 84 0 0 0-160 28 44 44 0 0 0-18 88z" fill="#fff"/>')
    return tile('#ffab76', '#7b5bd6', body)


def screenshot():
    corner = lambda d: f'<path d="{d}" fill="none" stroke="#fff" stroke-width="22" stroke-linecap="round" stroke-linejoin="round"/>'
    body = (corner('M124 188 V140 H172') + corner('M340 140 H388 V188')
            + corner('M388 316 V364 H340') + corner('M172 364 H124 V316')
            + '<rect x="196" y="194" width="120" height="116" rx="18" fill="#fff" fill-opacity="0.3" stroke="#fff" stroke-width="8" stroke-dasharray="16 12"/>'
            '<path d="M256 222 V282 M226 252 H286" stroke="#fff" stroke-width="12" stroke-linecap="round"/>')
    return tile('#ff8a8a', '#d84a6e', body)


def system_monitor():
    body = ('<rect x="132" y="240" width="60" height="146" rx="20" fill="#9d82f0"/>'
            '<rect x="226" y="160" width="60" height="226" rx="20" fill="#f2b632"/>'
            '<rect x="320" y="206" width="60" height="180" rx="20" fill="#4cc27a"/>')
    return tile('#ffffff', '#e8ecf3', body)


def disks():
    body = ('<circle cx="236" cy="256" r="138" fill="#e9edf4"/>'
            '<circle cx="236" cy="256" r="138" fill="none" stroke="#fff" stroke-width="6"/>'
            '<circle cx="236" cy="256" r="84" fill="none" stroke="#c9d1de" stroke-width="4"/>'
            '<circle cx="236" cy="256" r="34" fill="#7f8ba1"/><circle cx="236" cy="256" r="12" fill="#e9edf4"/>'
            '<path d="M372 140 L292 306" stroke="#f2b632" stroke-width="22" stroke-linecap="round"/>'
            '<circle cx="372" cy="140" r="24" fill="#f2b632"/>')
    return tile('#6d7a92', '#3a4458', body)


def preview():
    card = lambda x, y, rot: (f'<g transform="rotate({rot} {x + 100} {y + 80})">'
                              f'<rect x="{x}" y="{y}" width="200" height="160" rx="18" fill="#fff"/>'
                              f'<rect x="{x + 14}" y="{y + 14}" width="172" height="118" rx="10" fill="#dff3f1"/>'
                              f'<path d="M{x + 14} {y + 132} L{x + 74} {y + 64} L{x + 112} {y + 106} L{x + 138} {y + 80} L{x + 186} {y + 132}z" fill="#7654dc"/>'
                              f'<circle cx="{x + 150}" cy="{y + 44}" r="14" fill="#f2b632"/></g>')
    return tile('#4cc6b8', '#1f8a8f', card(118, 150, -10) + card(176, 196, 8))


def archive():
    body = ('<rect x="120" y="150" width="272" height="236" rx="28" fill="#fff"/>'
            '<rect x="120" y="150" width="272" height="64" rx="28" fill="#efeafc"/>'
            '<rect x="120" y="188" width="272" height="26" fill="#efeafc"/>'
            '<g fill="#f2b632">' + ''.join(f'<rect x="{242 if i % 2 else 256}" y="{224 + i * 18}" width="14" height="12" rx="3"/>' for i in range(8)) + '</g>'
            '<rect x="236" y="366" width="40" height="30" rx="8" fill="#f2b632"/>')
    return tile('#9d82f0', '#5b3fb0', body)


def firmware():
    pins = ''.join(f'<rect x="{176 + i * 42}" y="110" width="16" height="44" rx="6" fill="#f2b632"/>'
                   f'<rect x="{176 + i * 42}" y="358" width="16" height="44" rx="6" fill="#f2b632"/>'
                   f'<rect x="110" y="{176 + i * 42}" width="44" height="16" rx="6" fill="#f2b632"/>'
                   f'<rect x="358" y="{176 + i * 42}" width="44" height="16" rx="6" fill="#f2b632"/>' for i in range(4))
    body = (pins + '<rect x="146" y="146" width="220" height="220" rx="34" fill="#f2b632"/>'
            '<rect x="186" y="186" width="140" height="140" rx="20" fill="#3a4458"/>'
            '<circle cx="222" cy="222" r="12" fill="#f2b632"/>')
    return tile('#6d7a92', '#3a4458', body)


def cloud():
    body = ('<path d="M150 356h212a66 66 0 0 0 0-132 94 94 0 0 0-180 30 51 51 0 0 0-32 102z" fill="#fff"/>'
            '<path d="M232 296 V252 M214 270 L232 252 L250 270" fill="none" stroke="#7654dc" stroke-width="16" stroke-linecap="round" stroke-linejoin="round"/>'
            '<path d="M288 262 V306 M270 288 L288 306 L306 288" fill="none" stroke="#7654dc" stroke-width="16" stroke-linecap="round" stroke-linejoin="round"/>')
    return tile('#7cc4ff', '#3b82e0', body)


# name -> (generator, MacTahoe file(s) it replaces)
ICONS = {
    'parchaos-calendar': (calendar, ['calendar']),
    'parchaos-clock': (clock, ['preferences-system-time']),
    'parchaos-calculator': (calculator, ['calc']),
    'parchaos-contacts': (contacts, ['addressbook']),
    'parchaos-mail': (mail, ['internet-mail']),
    'parchaos-settings': (settings, ['preferences-system']),
    'parchaos-terminal': (terminal, ['terminal']),
    'parchaos-text-editor': (text_editor, ['text-editor']),
    'parchaos-weather': (weather, ['indicator-weather']),
    'parchaos-screenshot': (screenshot, ['accessories-screenshot']),
    'parchaos-system-monitor': (system_monitor, ['utilities-system-monitor']),
    'parchaos-disks': (disks, ['gnome-disks']),
    'parchaos-preview': (preview, ['org.gnome.Loupe']),
    'parchaos-archive': (archive, ['file-roller']),
    'parchaos-firmware': (firmware, ['hwinfo']),
}

# Icons for ParchaOS's own apps, shipped by those apps (hicolor), not
# replacing anything in MacTahoe.
OWN = {
    'parchaos-cloud': cloud,
}


# --- Places (no tile): violet folders with a gold tab, a light glyph for
# the folder's purpose, and the trash. ---

FOLDER_DEFS = ('<defs><linearGradient id="front" x1="0" y1="0" x2="0" y2="1">'
               '<stop offset="0" stop-color="#a98cf6"/><stop offset="1" stop-color="#7654dc"/></linearGradient>'
               '<filter id="fsh" x="-10%" y="-10%" width="120%" height="125%"><feDropShadow dx="0" dy="5" stdDeviation="7" flood-color="#000" flood-opacity="0.2"/></filter></defs>')

GLYPH = 'fill="#fff" fill-opacity="0.55"'
FOLDER_GLYPHS = {
    'plain': '',
    'documents': (f'<rect x="212" y="258" width="88" height="112" rx="10" {GLYPH}/>'
                  '<rect x="228" y="284" width="56" height="8" rx="4" fill="#7654dc"/>'
                  '<rect x="228" y="304" width="56" height="8" rx="4" fill="#7654dc"/>'
                  '<rect x="228" y="324" width="36" height="8" rx="4" fill="#7654dc"/>'),
    'download': (f'<path d="M256 256 V330 M222 300 L256 334 L290 300" fill="none" stroke="#fff" stroke-opacity="0.6" stroke-width="18" stroke-linecap="round" stroke-linejoin="round"/>'
                 f'<rect x="206" y="352" width="100" height="16" rx="8" {GLYPH}/>'),
    'music': (f'<path d="M238 346 V270 L298 258 V334" fill="none" stroke="#fff" stroke-opacity="0.6" stroke-width="14" stroke-linejoin="round"/>'
              f'<circle cx="226" cy="348" r="18" {GLYPH}/><circle cx="286" cy="336" r="18" {GLYPH}/>'),
    'images': (f'<rect x="202" y="262" width="108" height="92" rx="12" {GLYPH}/>'
               '<path d="M212 344 L244 304 L266 328 L282 312 L302 344z" fill="#7654dc"/>'
               '<circle cx="284" cy="286" r="10" fill="#f2b632"/>'),
    'videos': (f'<rect x="200" y="266" width="112" height="84" rx="14" {GLYPH}/>'
               '<path d="M246 288 L276 308 L246 328z" fill="#7654dc"/>'),
    'desktop': (f'<rect x="200" y="262" width="112" height="72" rx="10" {GLYPH}/>'
                f'<rect x="246" y="334" width="20" height="18" {GLYPH}/><rect x="226" y="350" width="60" height="10" rx="5" {GLYPH}/>'),
    'home': (f'<path d="M256 254 L312 300 V360 H200 V300z" {GLYPH}/>'
             '<rect x="240" y="320" width="32" height="40" rx="6" fill="#7654dc"/>'),
    'templates': (f'<rect x="206" y="262" width="100" height="100" rx="12" fill="none" stroke="#fff" stroke-opacity="0.6" stroke-width="12"/>'
                  f'<path d="M206 300 H306 M246 300 V362" stroke="#fff" stroke-opacity="0.6" stroke-width="12"/>'),
    'public': (f'<circle cx="232" cy="290" r="20" {GLYPH}/><circle cx="286" cy="290" r="20" {GLYPH}/>'
               f'<path d="M196 356a36 32 0 0 1 72 0z" {GLYPH}/><path d="M250 356a36 32 0 0 1 72 0z" {GLYPH}/>'),
    'remote': (f'<circle cx="256" cy="310" r="50" fill="none" stroke="#fff" stroke-opacity="0.6" stroke-width="12"/>'
               f'<path d="M206 310 H306 M256 260 C228 290 228 330 256 360 C284 330 284 290 256 260" fill="none" stroke="#fff" stroke-opacity="0.6" stroke-width="10"/>'),
}


def folder(glyph, open_=False):
    back = ('<path d="M76 108 h120 a20 20 0 0 1 16 8 l22 30 h204 a28 28 0 0 1 28 28 v214 H48 V136 a28 28 0 0 1 28-28z" fill="#5b3fb0"/>'
            '<path d="M76 108 h120 a20 20 0 0 1 16 8 l22 30 H48 V136 a28 28 0 0 1 28-28z" fill="#f2b632"/>')
    if open_:
        front = '<path d="M60 206 H468 a20 20 0 0 1 19 26 L452 390 a28 28 0 0 1 -27 22 H87 a28 28 0 0 1 -27 -22 L25 232 a20 20 0 0 1 19 -26z" fill="url(#front)" filter="url(#fsh)"/>'
    else:
        front = '<rect x="40" y="176" width="432" height="244" rx="28" fill="url(#front)" filter="url(#fsh)"/>'
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">' + FOLDER_DEFS + back + front
            + '<rect x="41" y="177" width="430" height="3" rx="1.5" fill="#fff" fill-opacity="0.35"/>'
            + FOLDER_GLYPHS[glyph] + '</svg>\n')


def trash(full):
    papers = ('<path d="M168 132 l40 -30 l56 34 l-24 42z" fill="#fff"/>'
              '<path d="M250 118 l58 -18 l30 50 l-50 24z" fill="#f6e4b8"/>'
              '<path d="M312 138 l44 10 l-10 46 l-40 -6z" fill="#fff"/>') if full else ''
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><defs>'
            '<linearGradient id="bin" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#c9cfdc"/><stop offset="1" stop-color="#8e97ab"/></linearGradient>'
            '<filter id="tsh" x="-10%" y="-10%" width="120%" height="125%"><feDropShadow dx="0" dy="5" stdDeviation="7" flood-color="#000" flood-opacity="0.22"/></filter></defs>'
            + papers +
            '<path d="M132 176 H380 L356 430 a24 24 0 0 1 -24 22 H180 a24 24 0 0 1 -24 -22z" fill="url(#bin)" filter="url(#tsh)"/>'
            '<rect x="112" y="150" width="288" height="44" rx="22" fill="#7a55d6"/>'
            '<rect x="112" y="150" width="288" height="14" rx="7" fill="#fff" fill-opacity="0.3"/>'
            '<g fill="#fff" fill-opacity="0.35"><rect x="162" y="250" width="188" height="12" rx="6"/>'
            '<rect x="170" y="310" width="172" height="12" rx="6"/><rect x="178" y="370" width="156" height="12" rx="6"/></g>'
            '</svg>\n')


# name -> (svg text factory, MacTahoe places file(s) it replaces)
PLACES = {
    'parchaos-folder': (lambda: folder('plain'), ['folder']),
    'parchaos-folder-open': (lambda: folder('plain', open_=True), ['folder-open']),
    'parchaos-folder-documents': (lambda: folder('documents'), ['folder-documents']),
    'parchaos-folder-download': (lambda: folder('download'), ['folder-download']),
    'parchaos-folder-music': (lambda: folder('music'), ['folder-music']),
    'parchaos-folder-images': (lambda: folder('images'), ['folder-images']),
    'parchaos-folder-videos': (lambda: folder('videos'), ['folder-videos']),
    'parchaos-folder-desktop': (lambda: folder('desktop'), ['user-desktop']),
    'parchaos-folder-home': (lambda: folder('home'), ['user-home']),
    'parchaos-folder-templates': (lambda: folder('templates'), ['folder-templates']),
    'parchaos-folder-public': (lambda: folder('public'), ['folder-public']),
    'parchaos-folder-remote': (lambda: folder('remote'), ['folder-html']),
    'parchaos-trash': (lambda: trash(False), ['user-trash']),
    'parchaos-trash-full': (lambda: trash(True), ['user-trash-full']),
}

if __name__ == '__main__':
    for name, (gen, _targets) in {**ICONS, **PLACES}.items():
        with open(os.path.join(HERE, f'{name}.svg'), 'w') as f:
            f.write(gen())
    for name, gen in OWN.items():
        with open(os.path.join(HERE, f'{name}.svg'), 'w') as f:
            f.write(gen())
    print(f'wrote {len(ICONS) + len(PLACES) + len(OWN)} icons')
