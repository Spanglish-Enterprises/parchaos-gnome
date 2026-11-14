# SPDX-License-Identifier: GPL-3.0-or-later
# Tests for parchaos-lookup-ocr (ticket #180). Run:
#   python3 packaging/parchaos-lookup/tests/test_lookup.py
import importlib.machinery
import importlib.util
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, '..', 'parchaos-lookup-ocr')
loader = importlib.machinery.SourceFileLoader('parchaos_lookup_ocr', SCRIPT)
spec = importlib.util.spec_from_loader('parchaos_lookup_ocr', loader)
tool = importlib.util.module_from_spec(spec)
loader.exec_module(tool)

failures = 0


def check(ok, what):
    global failures
    if not ok:
        failures += 1
        print(f'FAIL {what}')


# Small selections are enlarged (up to 4x), big ones are not, and nothing passes 4000 px.
check(tool.scale_for(300, 40) == 4.0, 'a one-line selection is enlarged 4x')
check(tool.scale_for(800, 600) == 2.0, 'a mid-size selection is enlarged 2x')
check(tool.scale_for(1600, 1400) == 1.0, 'a large selection is left as it is')
check(max(3000, 300) * tool.scale_for(3000, 300) <= tool.MAX_SIDE, 'never past the size cap')

check(tool.tidy('  Total  $5.50 \f\n\n\n\n|\n— \nGracias  ') == 'Total  $5.50\n\nGracias', 'tidy lines and noise')
check(tool.tidy('\f') == '', 'empty page')

# End to end with a stand-in Tesseract that records what it was asked.
tmp = tempfile.mkdtemp()
log = os.path.join(tmp, 'args')
fake = os.path.join(tmp, 'tesseract')
with open(fake, 'w') as f:
    f.write(f'''#!/bin/sh
if [ "$1" = --list-langs ]; then printf 'List of available languages (3):\\neng\\nosd\\nspa\\n'; exit 0; fi
echo "$@" > {log}
python3 -c "import sys; print(open(sys.argv[1], 'rb').read(8) == b'\\\\x89PNG\\\\r\\\\n\\\\x1a\\\\n')" "$1" >> {log}
printf 'Panader\\303\\255a La Esquina\\n\\f'
''')
os.chmod(fake, 0o755)
image = os.path.join(tmp, 'area.png')
try:
    import gi
    gi.require_version('GdkPixbuf', '2.0')
    from gi.repository import GdkPixbuf
    GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, False, 8, 120, 30).savev(image, 'png', [], [])
except (ImportError, ValueError) as err:
    print(f'lookup: end-to-end skipped ({err})')
    image = None
if image:
    env = dict(os.environ, PARCHAOS_TESSERACT=fake)
    out = subprocess.run([sys.executable, SCRIPT, image], capture_output=True, text=True, env=env)
    check(out.returncode == 0 and out.stdout.strip() == 'Panadería La Esquina', f'text printed (got {out.stdout!r} {out.stderr!r})')
    args = open(log).read().split('\n')
    check(args[0].endswith('stdout -l eng+spa'), f'English and Spanish asked for (got {args[0]!r})')
    check(args[1] == 'True', 'Tesseract is given a PNG')
    check(not args[0].startswith(image), 'it reads the enlarged copy, not the original')
    bad = subprocess.run([sys.executable, SCRIPT], capture_output=True, text=True, env=env)
    check(bad.returncode == 2, 'usage error without an image')

print('lookup: all checks passed' if failures == 0 else f'lookup: {failures} check(s) failed')
sys.exit(0 if failures == 0 else 1)
