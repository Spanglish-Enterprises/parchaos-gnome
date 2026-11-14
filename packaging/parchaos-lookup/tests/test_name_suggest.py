# SPDX-License-Identifier: GPL-3.0-or-later
# Tests for parchaos-name-suggest (ticket #185). Run:
#   python3 packaging/parchaos-lookup/tests/test_name_suggest.py
import importlib.machinery
import importlib.util
import os
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, '..', 'parchaos-name-suggest')
loader = importlib.machinery.SourceFileLoader('parchaos_name_suggest', SCRIPT)
spec = importlib.util.spec_from_loader('parchaos_name_suggest', loader)
tool = importlib.util.module_from_spec(spec)
loader.exec_module(tool)

failures = 0


def check(ok, what):
    global failures
    if not ok:
        failures += 1
        print(f'FAIL {what}')


D = tool.find_date
for var in ('LC_ALL', 'LC_TIME'):
    os.environ.pop(var, None)
os.environ['LANG'] = 'es_PR.UTF-8'
check(D('Fecha: 2026-11-13 10:42') == '2026-11-13', 'ISO date')
check(D('13/11/2026 10:42') == '2026-11-13', 'day first when the day is over 12')
check(D('11/03/2026') == '2026-11-03', 'Puerto Rico reads month first')
os.environ['LANG'] = 'es_ES.UTF-8'
check(D('11/03/2026') == '2026-03-11', 'Spain reads day first')
os.environ['LANG'] = 'en_US.UTF-8'
check(D('Signed March 3, 2025') == '2025-03-03', 'English month name')
check(D('13 de noviembre de 2026') == '2026-11-13', 'Spanish month name')
check(D('Total $5.50') is None, 'no date')
check(D('99/99/2026') is None, 'impossible date')

T = tool.title_line
check(T('\n\n13/11/2026\nPanadería La Esquina\nCalle Loíza') == 'Panadería La Esquina', 'first title-like line')
check(T('$5.50\n12345\n') is None, 'no title in numbers')
check(T('## Plan for the week ##') == 'Plan for the week', 'Markdown marks trimmed')

check(tool.clean('a/b: c?  d ') == 'a b c d', 'unsafe characters')
check(len(tool.clean('word ' * 40)) <= tool.MAX_LEN, 'length cap')

with tempfile.TemporaryDirectory() as tmp:
    def write(name, text):
        path = os.path.join(tmp, name)
        with open(path, 'w') as f:
            f.write(text)
        return path

    check(tool.suggest(write('notes.md', 'intro\n# Trip to Rincón\n')) == ['Trip to Rincón.md'], 'Markdown heading')
    check(tool.suggest(write('draft.txt', '\n\nQuarterly budget review\n')) == ['Quarterly budget review.txt'], 'first line')
    check(tool.suggest(write('Quarterly budget review.txt', 'Quarterly budget review\n')) == [], 'nothing new to suggest')

    odt = os.path.join(tmp, 'Untitled 1.odt')
    with zipfile.ZipFile(odt, 'w') as z:
        z.writestr('mimetype', 'application/vnd.oasis.opendocument.text')
        z.writestr('meta.xml', '<office:document-meta xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
                   'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:meta="urn:oasis:names:tc:opendocument:xmlns:meta:1.0">'
                   '<office:meta><dc:title>Lease Agreement</dc:title><meta:creation-date>2025-03-03T10:00:00</meta:creation-date>'
                   '</office:meta></office:document-meta>')
    check(tool.suggest(odt)[:2] == ['Lease Agreement 2025-03-03.odt', 'Lease Agreement.odt'], f'document title and date (got {tool.suggest(odt)})')

    # A picture: the text comes from the OCR helper (a stand-in here).
    fake = write('ocr', '#!/bin/sh\nprintf "Panaderia La Esquina\\nCalle Loiza 1234, San Juan\\n13/11/2026 10:42\\nTotal 5.50\\n"\n')
    os.chmod(fake, 0o755)
    tool.OCR = fake
    import base64
    png = os.path.join(tmp, 'Screenshot From 2026-11-13 10-42-11.png')
    with open(png, 'wb') as f:
        f.write(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=='))
    got = tool.suggest(png)
    check(got[0] == 'Panaderia La Esquina 2026-11-13.png', f'a receipt: shop and date (got {got})')
    check(len(got) <= tool.MAX_SUGGESTIONS, 'at most three')

print('name-suggest: all checks passed' if failures == 0 else f'name-suggest: {failures} check(s) failed')
sys.exit(0 if failures == 0 else 1)
