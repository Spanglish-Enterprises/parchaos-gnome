# SPDX-License-Identifier: GPL-3.0-or-later
# Tests for accent-colours.py (ticket #177). Run:
#   python3 packaging/parchaos-gtk-theme/tests/test_accent_colours.py
import importlib.machinery
import importlib.util
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
loader = importlib.machinery.SourceFileLoader('accent', os.path.join(HERE, '..', 'accent-colours.py'))
spec = importlib.util.spec_from_loader('accent', loader)
ac = importlib.util.module_from_spec(spec)
loader.exec_module(ac)

failures = 0


def check(ok, what):
    global failures
    if not ok:
        failures += 1
        print(f'FAIL {what}')


# A slice of the upstream stylesheet: the accent, a darker and a lighter shade of it,
# a translucent one, GNOME's own palette blue and unrelated colours.
CSS = '''@define-color accent_bg_color #0088FF;
@define-color accent_color #0088FF;
@define-color theme_selected_bg_color #0088FF;
@define-color blue_3 #3584e4;
button.suggested { background-color: #0088FF; border-color: #006dcc; }
switch:hover { background-color: #4dacff; }
selection { background-color: rgba(0, 136, 255, 0.35); color: #ffffff; }
.error { color: #ED5F5D; }
'''


def main():
    # GTK 3: plain colours, shades kept as shades.
    teal = ac.recolour(CSS, ac.ACCENTS['teal'])
    check('background-color: #2190a4;' in teal, 'the accent becomes teal')
    check('#0088FF' not in teal and '#006dcc' not in teal and '#4dacff' not in teal, 'no upstream blue is left')
    check('rgba(33, 144, 164, 0.35)' in teal, 'the translucent accent keeps its alpha')
    check('#3584e4' in teal and '#ED5F5D' in teal and '#ffffff' in teal, 'palette blue and other colours are untouched')
    dark = teal.split('border-color: ')[1][:7]
    check(ac.hls(ac.parse(dark))[1] < ac.hls(ac.parse('#2190a4'))[1], 'the darker shade stays darker')

    # GTK 4: libadwaita's accent shows through.
    dyn = ac.dynamic(CSS)
    check('@define-color accent_bg_color' not in dyn and '@define-color accent_color' not in dyn,
          'the theme no longer pins the accent')
    check('button.suggested { background-color: var(--accent-bg-color, #3584e4);' in dyn, 'the accent is the variable')
    check('shade(var(--accent-bg-color, #3584e4), 0.' in dyn, 'the darker shade is a shade() of it')
    check('alpha(var(--accent-bg-color, #3584e4), 0.35)' in dyn, 'the translucent accent is an alpha() of it')
    check('@define-color theme_selected_bg_color #3584e4;' in dyn, 'other definitions get plain GNOME blue')
    check('var(' not in ''.join(l for l in dyn.splitlines() if l.startswith('@define-color')),
          'no variable inside @define-color (GTK rejects it)')

    # The build step: base themes rewritten, one GTK 3 copy per other accent.
    with tempfile.TemporaryDirectory() as root:
        for base in ac.BASE_THEMES:
            for sub in ('gtk-3.0', 'gtk-4.0', 'gnome-shell'):
                os.makedirs(os.path.join(root, base, sub))
                for name in ('gtk.css', 'gtk-dark.css'):
                    with open(os.path.join(root, base, sub, name), 'w') as f:
                        f.write(CSS)
            os.makedirs(os.path.join(root, base, 'gtk-3.0', 'assets'))
            with open(os.path.join(root, base, 'index.theme'), 'w') as f:
                f.write('[Desktop Entry]\nName=%s\nComment=x\n[X-GNOME-Metatheme]\nGtkTheme=%s\n' % (base, base))
        ac.main(['accent-colours.py', root])
        copies = sorted(d for d in os.listdir(root) if d not in ac.BASE_THEMES)
        check(len(copies) == 4 * 8, f'32 accent copies (got {len(copies)})')
        pink = os.path.join(root, 'ParchaOS-Light-solid-Pink')
        with open(os.path.join(pink, 'gtk-3.0', 'gtk.css')) as f:
            check(ac.ACCENTS['pink'] in f.read(), 'the copy is recoloured from the upstream blue')
        check(os.path.realpath(os.path.join(pink, 'gtk-4.0')) ==
              os.path.realpath(os.path.join(root, 'ParchaOS-Light-solid', 'gtk-4.0')), 'GTK 4 is shared with the base')
        check(os.path.isdir(os.path.join(pink, 'gtk-3.0', 'assets')), 'GTK 3 assets resolve')
        with open(os.path.join(pink, 'index.theme')) as f:
            index = f.read()
        check('Name=ParchaOS-Light-solid-Pink' in index and 'GtkTheme=ParchaOS-Light-solid-Pink' in index,
              'the copy has its own name')
        with open(os.path.join(root, 'ParchaOS-Dark', 'gtk-3.0', 'gtk.css')) as f:
            check('#3584e4;' in f.read(), 'the base theme is GNOME blue')

    print('accent-colours: all checks passed' if failures == 0 else f'accent-colours: {failures} check(s) failed')
    return 0 if failures == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
