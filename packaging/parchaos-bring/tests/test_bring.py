# SPDX-License-Identifier: GPL-3.0-or-later
# Tests for Bring Your Stuff (ticket #157). Run:
#   python3 packaging/parchaos-bring/tests/test_bring.py
# Builds a pretend Windows disk, Mac disk and Linux home in a temporary folder.
import importlib.util
import json
import os
import plistlib
import sqlite3
import stat
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TMP = tempfile.mkdtemp()
HOME = os.path.join(TMP, 'home-here')
os.makedirs(os.path.join(HOME, '.config'))
with open(os.path.join(HOME, '.config', 'user-dirs.dirs'), 'w') as f:
    f.write('XDG_DOCUMENTS_DIR="$HOME/Documentos"\nXDG_PICTURES_DIR="$HOME/Imágenes"\n')
os.environ['HOME'] = HOME
os.environ['XDG_CONFIG_HOME'] = os.path.join(HOME, '.config')
os.environ['PARCHAOS_BRING_CHROMIUM'] = os.path.join(HOME, '.config', 'chromium')
spec = importlib.util.spec_from_file_location('bringlib', os.path.join(HERE, '..', 'bringlib.py'))
bl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bl)

failures = 0


def check(ok, what):
    global failures
    if not ok:
        failures += 1
        print(f'FAIL {what}')


def put(path, data=b'x', mtime=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as f:
        f.write(data if isinstance(data, bytes) else data.encode())
    if mtime:
        os.utime(path, (mtime, mtime))


# A Windows disk.
win = os.path.join(TMP, 'win')
os.makedirs(os.path.join(win, 'Windows', 'System32'))
os.makedirs(os.path.join(win, 'Program Files'))
alex = os.path.join(win, 'Users', 'Alex')
put(os.path.join(alex, 'Documents', 'Taxes 2025.pdf'), b'%PDF' + b'1' * 996)
put(os.path.join(alex, 'Documents', 'School', 'essay.docx'), b'2' * 500)
put(os.path.join(alex, 'Documents', 'desktop.ini'), b'junk')
put(os.path.join(alex, 'Documents', '~$essay.docx'), b'lock')
put(os.path.join(alex, 'Pictures', 'beach.jpg'), b'3' * 2000)
put(os.path.join(alex, 'Pictures', 'Thumbs.db'), b'junk')
put(os.path.join(alex, 'Music', 'song.mp3'), b'4' * 300)
put(os.path.join(alex, 'Desktop', 'notes.txt'), b'hola')
put(os.path.join(alex, 'Downloads', 'setup.exe'), b'5' * 100)
put(os.path.join(alex, 'NTUSER.DAT'), b'registry')
os.symlink('/etc', os.path.join(alex, 'Documents', 'My Music'))   # Windows junctions look like this
os.makedirs(os.path.join(win, 'Users', 'Public', 'Documents'))
os.makedirs(os.path.join(win, 'Users', 'Public', 'Pictures'))
os.makedirs(os.path.join(win, 'Users', 'Default', 'Documents'))
os.makedirs(os.path.join(win, 'Users', 'Default', 'Pictures'))
chrome = {'checksum': 'abc', 'roots': {
    'bookmark_bar': {'type': 'folder', 'name': 'Bookmarks bar', 'id': '1', 'children': [
        {'type': 'url', 'name': 'Bank', 'url': 'https://bank.example/', 'id': '4'},
        {'type': 'folder', 'name': 'School', 'id': '5', 'children': [
            {'type': 'url', 'name': 'Library', 'url': 'https://library.example/', 'id': '6'}]}]},
    'other': {'type': 'folder', 'name': 'Other bookmarks', 'id': '2', 'children': [
        {'type': 'url', 'name': 'Recipes', 'url': 'https://recipes.example/', 'id': '7'}]},
    'synced': {'type': 'folder', 'name': 'Mobile bookmarks', 'id': '3', 'children': []}}, 'version': 1}
put(os.path.join(alex, 'AppData/Local/Google/Chrome/User Data/Default/Bookmarks'), json.dumps(chrome))
ff = os.path.join(alex, 'AppData/Roaming/Mozilla/Firefox/Profiles/x1y2.default-release/places.sqlite')
os.makedirs(os.path.dirname(ff))
db = sqlite3.connect(ff)
db.executescript('''
CREATE TABLE moz_places (id INTEGER PRIMARY KEY, url TEXT);
CREATE TABLE moz_bookmarks (id INTEGER PRIMARY KEY, type INTEGER, fk INTEGER, parent INTEGER, position INTEGER,
                            title TEXT, guid TEXT);
INSERT INTO moz_places VALUES (1, 'https://news.example/'), (2, 'place:sort=8'), (3, 'https://maps.example/');
INSERT INTO moz_bookmarks VALUES (1, 2, NULL, 0, 0, '', 'root________'),
  (2, 2, NULL, 1, 0, 'menu', 'menu________'), (3, 2, NULL, 1, 1, 'toolbar', 'toolbar_____'),
  (4, 2, NULL, 1, 2, 'unfiled', 'unfiled_____'),
  (10, 1, 1, 3, 0, 'News', 'a'), (11, 1, 2, 3, 1, 'Most Visited', 'b'),
  (12, 2, NULL, 2, 0, 'Travel', 'c'), (13, 1, 3, 12, 0, 'Maps', 'd');
''')
db.commit()
db.close()
ff_before = open(ff, 'rb').read()
wlan = os.path.join(win, 'ProgramData/Microsoft/Wlansvc/Profiles/Interfaces/{ABC}')
put(os.path.join(wlan, '1.xml'), '<WLANProfile><name>Casa</name><keyMaterial>01000000D08C</keyMaterial></WLANProfile>')
put(os.path.join(wlan, '2.xml'), '<WLANProfile><name>Cafe Wifi</name></WLANProfile>')

profiles = bl.detect_profiles(win)
check([(p['kind'], p['name']) for p in profiles] == [('windows', 'Alex')], f'Windows disk: only the person ({profiles})')
alex_p = profiles[0]
folders = {f['key']: f for f in bl.folders_for(alex_p)}
check(set(folders) == {'DOCUMENTS', 'PICTURES', 'MUSIC', 'DESKTOP', 'DOWNLOAD'}, f'folders found ({set(folders)})')
check(folders['DOCUMENTS']['dest'] == os.path.join(HOME, 'Documentos'), 'into this computer’s own folder names')
check(folders['MUSIC']['dest'] == os.path.join(HOME, 'Music'), 'default names when not set')
n, size = bl.measure(folders['DOCUMENTS']['source'])
check((n, size) == (2, 1500), f'counted without junk, lock files or links ({n}, {size})')
check(bl.wifi_names(win) == ['Cafe Wifi', 'Casa'], 'Wi-Fi names from Windows')

# Copy, never overwriting.
put(os.path.join(HOME, 'Documentos', 'Taxes 2025.pdf'), b'mine, different')
same = os.path.join(alex, 'Pictures', 'beach.jpg')
put(os.path.join(HOME, 'Imágenes', 'beach.jpg'), open(same, 'rb').read(), os.stat(same).st_mtime)
locked = os.path.join(alex, 'Pictures', 'private.png')
put(locked, b'6' * 10)
os.chmod(locked, 0)
report = bl.CopyReport()
seen = []
for key in ('DOCUMENTS', 'PICTURES', 'DESKTOP'):
    bl.copy_folder(folders[key]['source'], folders[key]['dest'], report, lambda rel, s: seen.append(rel))
os.chmod(locked, stat.S_IRUSR | stat.S_IWUSR)
docs = os.path.join(HOME, 'Documentos')
check(open(os.path.join(docs, 'Taxes 2025.pdf'), 'rb').read() == b'mine, different', 'nothing here is overwritten')
check(open(os.path.join(docs, 'Taxes 2025 (2).pdf'), 'rb').read().startswith(b'%PDF'), 'the other one kept beside it')
check(os.path.exists(os.path.join(docs, 'School', 'essay.docx')), 'subfolders copied')
check(not os.path.exists(os.path.join(docs, 'desktop.ini')) and not os.path.exists(os.path.join(docs, 'My Music')),
      'no junk, no links followed')
check(report.same == 1, f'the same picture is not copied twice ({report.same})')
check(report.copied == 3 and report.renamed == ['Documentos/Taxes 2025 (2).pdf'], f'report ({report.copied}, {report.renamed})')
if os.geteuid() != 0:
    check(len(report.failed) == 1 and report.failed[0][0] == locked, f'an unreadable file is reported ({report.failed})')
check(os.path.getmtime(os.path.join(docs, 'School', 'essay.docx')) ==
      os.path.getmtime(os.path.join(alex, 'Documents', 'School', 'essay.docx')), 'dates kept')
check(not [f for d, _s, fs in os.walk(HOME) for f in fs if f.endswith('.part')], 'no partial files left')
check(len(seen) == 5, f'progress reported for every file looked at ({seen})')

# Bookmarks.
sources = bl.browser_sources(alex_p)
check([s[0] for s in sources] == ['Google Chrome', 'Firefox'], f'browsers found ({[s[0] for s in sources]})')
trees = {name: reader(path) for name, reader, path in sources}
check(bl.count_bookmarks(trees['Google Chrome']) == 3, 'Chrome: 3 bookmarks, folders kept')
check(bl.count_bookmarks(trees['Firefox']) == 2, f'Firefox: 2, smart folders left out ({trees["Firefox"]})')
check(open(ff, 'rb').read() == ff_before and not os.path.exists(ff + '-journal'), 'the Firefox file is not touched')

n = bl.import_into_chromium(list(trees.items()), 'From Alex (Windows)')
data = json.load(open(os.path.join(HOME, '.config/chromium/Default/Bookmarks')))
folder = data['roots']['other']['children'][-1]
check(n == 5 and folder['name'] == 'From Alex (Windows)', f'imported into a new profile ({n})')
check([c['name'] for c in folder['children']] == ['Google Chrome', 'Firefox'], 'one folder per old browser')
ids = []


def collect(node):
    ids.append(node['id'])
    for c in node.get('children', []):
        collect(c)


for root in data['roots'].values():
    collect(root)
check(len(ids) == len(set(ids)), 'ids are unique')
check('checksum' not in data, 'no stale checksum')
# A second import into an existing file keeps what is there.
n = bl.import_into_chromium([('Firefox', trees['Firefox'])], 'Again')
data2 = json.load(open(os.path.join(HOME, '.config/chromium/Default/Bookmarks')))
check([c['name'] for c in data2['roots']['other']['children']] == ['From Alex (Windows)', 'Again'], 'added, not replaced')
check(data2['roots']['other']['children'][-1]['children'][0]['name'] == 'Bookmarks Toolbar', 'one browser: no extra level')
check(os.path.exists(os.path.join(HOME, '.config/chromium/Default/Bookmarks.before-bring-your-stuff')), 'a backup is kept')
check(not bl.browser_running(), 'browser not running')
lock = os.path.join(HOME, '.config/chromium/SingletonLock')
os.symlink(f'host-{os.getpid()}', lock)
check(bl.browser_running(), 'a running browser is noticed')
os.unlink(lock)

# A Mac disk.
mac = os.path.join(TMP, 'mac')
os.makedirs(os.path.join(mac, 'Applications'))
put(os.path.join(mac, 'Users', 'sam', 'Documents', 'a.pages'))
put(os.path.join(mac, 'Users', 'sam', 'Movies', 'trip.mov'))
put(os.path.join(mac, 'Users', 'sam', 'Desktop', '.DS_Store'))
os.makedirs(os.path.join(mac, 'Users', 'Shared', 'Documents'))
os.makedirs(os.path.join(mac, 'Users', 'Shared', 'Movies'))
plist_marks = {'WebBookmarkType': 'WebBookmarkTypeList', 'Children': [
    {'WebBookmarkType': 'WebBookmarkTypeList', 'Title': 'BookmarksBar', 'Children': [
        {'WebBookmarkType': 'WebBookmarkTypeLeaf', 'URLString': 'https://apple-news.example/',
         'URIDictionary': {'title': 'News'}}]},
    {'WebBookmarkType': 'WebBookmarkTypeList', 'Title': 'com.apple.ReadingList', 'Children': []}]}
put(os.path.join(mac, 'Users', 'sam', 'Library', 'Safari', 'Bookmarks.plist'), plistlib.dumps(plist_marks, fmt=plistlib.FMT_BINARY))
p = bl.detect_profiles(mac)
check([(x['kind'], x['name']) for x in p] == [('mac', 'sam')], f'Mac disk ({p})')
check({f['key'] for f in bl.folders_for(p[0])} == {'DOCUMENTS', 'VIDEOS', 'DESKTOP'}, 'Movies go to Videos')
src = bl.browser_sources(p[0])
check([s[0] for s in src] == ['Safari'] and bl.count_bookmarks(src[0][1](src[0][2])) == 1, 'Safari bookmarks')

# A Linux home chosen directly, and a backup drive with the folders one level down.
lin = os.path.join(TMP, 'old-home')
put(os.path.join(lin, 'Documents', 'x.odt'))
put(os.path.join(lin, 'Pictures', 'y.png'))
os.makedirs(os.path.join(lin, '.config'))
check([(x['kind']) for x in bl.detect_profiles(lin)] == ['linux'], 'a Linux home folder')
backup = os.path.join(TMP, 'backup')
put(os.path.join(backup, 'Laptop 2019', 'Documents', 'z.txt'))
put(os.path.join(backup, 'Laptop 2019', 'Music', 'z.mp3'))
check([(x['kind'], x['name']) for x in bl.detect_profiles(backup)] == [('folder', 'Laptop 2019')], 'a backup drive')
check(bl.detect_profiles(os.path.join(TMP, 'nothing-here')) == [], 'nothing found')

if failures:
    print(f'bring: {failures} failure(s)')
    sys.exit(1)
print('bring: all checks passed')
