# SPDX-License-Identifier: GPL-3.0-or-later
# Tests for the icon generator (tickets #133, #79). Run:
#   python3 packaging/parchaos-icon-theme/tests/test_icons.py
import importlib.machinery
import importlib.util
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ICONS = os.path.join(HERE, '..', 'parchaos-icons')
loader = importlib.machinery.SourceFileLoader('generate', os.path.join(ICONS, 'generate.py'))
spec = importlib.util.spec_from_loader('generate', loader)
gen = importlib.util.module_from_spec(spec)
loader.exec_module(gen)

failures = 0


def check(ok, what):
    global failures
    if not ok:
        failures += 1
        print(f'FAIL {what}')


def read(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


def main():
    # 1. The generator reproduces the committed art. A drift here is how
    #    running the generator once overwrote the shipped logos (ticket #133).
    for name, (make, _targets) in {**gen.ICONS, **gen.PLACES}.items():
        path = os.path.join(ICONS, f'{name}.svg')
        check(os.path.exists(path) and make() == read(path), f'{name}.svg matches the generator')

    # 2. Colour variants: the default palette is untouched, every other one is
    #    recoloured, and only colours change.
    check(gen.recolor('<svg fill="#7654dc"/>', 'passion') == '<svg fill="#7654dc"/>', 'passion is identity')
    base = gen.PLACES['parchaos-folder'][0]()
    for palette, colours in gen.PALETTES.items():
        if palette == 'passion':
            continue
        out = gen.recolor(base, palette)
        check(out != base, f'{palette} folder differs from passion')
        check(colours['bottom'] in out and colours['back'] in out, f'{palette} folder uses its colours')
        check(gen.PASSION['bottom'] not in out.replace(colours['tab'], ''), f'{palette} folder leaves no passion violet behind')
        check(out.count('<') == base.count('<'), f'{palette} folder keeps the same shapes')
    sunny = gen.recolor(base, 'sunny')
    check('fill="#7654dc"/>' in sunny and gen.PALETTES['sunny']['bottom'] in sunny, 'sunny keeps its violet tab')
    trash = gen.recolor(gen.PLACES['parchaos-trash'][0](), 'ocean')
    check(gen.PALETTES['ocean']['lid'] in trash and gen.PASSION['lid'] not in trash, 'trash lid follows the palette')

    # 3. --variants writes every place icon for every non-default palette.
    with tempfile.TemporaryDirectory() as tmp:
        gen.write_variants(tmp)
        for palette in gen.PALETTES:
            if palette == 'passion':
                continue
            files = sorted(os.listdir(os.path.join(tmp, palette)))
            check(files == sorted(f'{n}.svg' for n in gen.PLACES), f'{palette} variant set is complete')

    print('icons: all checks passed' if failures == 0 else f'icons: {failures} check(s) failed')
    return 0 if failures == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
