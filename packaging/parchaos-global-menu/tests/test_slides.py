# SPDX-License-Identifier: GPL-3.0-or-later
# The menu bar tint picks the picture a timed (slideshow) wallpaper shows now (ticket #166).
# Runs slideNow() from extension.js under gjs against the ParchaOS Hills slideshow. Skipped
# where gjs isn't installed.
#   python3 packaging/parchaos-global-menu/tests/test_slides.py
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, '..', '..', '..'))
if not shutil.which('gjs'):
    print('slides: gjs not installed, skipped')
    sys.exit(0)
src = open(os.path.join(HERE, '..', 'files', 'extension.js'), encoding='utf-8').read()
i = src.index('export function slideNow')
fn = src[i:src.index('\n}\n', i) + 3].replace('export function', 'function')
xml = os.path.join(REPO, 'packaging/parchaos-gnome-wallpaper/files/usr/share/backgrounds/parchaos/hills/hills-timed.xml')
test = "import GLib from 'gi://GLib';\n" + fn + f"""
const xml = new TextDecoder().decode(GLib.file_get_contents({xml!r})[1]);
let fails = 0;
for (const [h, m, want] of [[3, 0, 'night'], [5, 50, 'night'], [6, 20, 'dawn'], [7, 0, 'dawn'], [12, 0, 'day'],
                             [17, 30, 'day'], [18, 0, 'dusk'], [19, 0, 'dusk'], [20, 30, 'night'], [23, 59, 'night']]) {{
    const got = slideNow(xml, GLib.DateTime.new_local(2026, 11, 14, h, m, 0));
    if (!got.endsWith(`hills-${{want}}.jpg`)) {{ fails++; print(`FAIL ${{h}}:${{m}} -> ${{got}}`); }}
}}
if (slideNow('<background><static><file>/a.png</file></static></background>', GLib.DateTime.new_now_local()) !== '/a.png') {{
    fails++; print('FAIL no starttime: the first picture');
}}
if (fails) imports.system.exit(1);
"""
with tempfile.NamedTemporaryFile('w', suffix='.mjs', delete=False) as f:
    f.write(test)
r = subprocess.run(['gjs', '-m', f.name], capture_output=True, text=True)
os.unlink(f.name)
print(r.stdout, end='')
if r.returncode != 0:
    print(r.stderr, end='')
    print('slides: failed')
    sys.exit(1)
print('slides: all checks passed')
