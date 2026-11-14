# SPDX-License-Identifier: GPL-3.0-or-later
# Bring Your Stuff (ticket #157): the part that finds and copies, without GTK.
#
# It only ever reads the old disk: files are opened for reading, browser databases are copied
# to a temporary folder before they are read, and nothing is written next to them. Disks that
# aren't mounted yet are mounted read-only (see parchaos-bring).
#
# Original code for ParchaOS, GPL-3.0-or-later.

import json
import os
import plistlib
import re
import shutil
import sqlite3
import tempfile
import time
import uuid

HOME = os.path.expanduser('~')

# What to bring, by kind of old computer: (key, folder names to look for on the old disk).
# The key is the XDG folder it goes to here.
FOLDERS = [
    ('DOCUMENTS', ['Documents', 'My Documents', 'Documentos']),
    ('PICTURES', ['Pictures', 'My Pictures', 'Imágenes', 'Imagenes', 'Fotos']),
    ('MUSIC', ['Music', 'My Music', 'Música', 'Musica']),
    ('VIDEOS', ['Videos', 'Movies', 'My Videos', 'Vídeos']),
    ('DESKTOP', ['Desktop', 'Escritorio']),
    ('DOWNLOAD', ['Downloads', 'Descargas']),
]
DEFAULT_ON = {'DOCUMENTS', 'PICTURES', 'MUSIC', 'VIDEOS', 'DESKTOP'}

# Windows and Mac keep accounts that aren't people's.
NOT_PEOPLE = {'all users', 'default', 'default user', 'public', 'defaultapppool', 'shared',
              'guest', '.localized', 'deleted users', 'wdagutilityaccount', 'lost+found'}

# Never copied: what Windows and Macs leave in every folder, and links back into the system.
JUNK = {'desktop.ini', 'thumbs.db', '.ds_store', 'icon\r', '.localized', '$recycle.bin',
        'system volume information', '.trash', '.trashes', '.spotlight-v100', '.fseventsd',
        '.temporaryitems', 'ehthumbs.db', 'ehthumbs_vista.db'}


def xdg_dir(key):
    """This computer's folder for key (DOCUMENTS, ...), from user-dirs.dirs."""
    names = {'DOCUMENTS': 'Documents', 'PICTURES': 'Pictures', 'MUSIC': 'Music', 'VIDEOS': 'Videos',
             'DESKTOP': 'Desktop', 'DOWNLOAD': 'Downloads'}
    conf = os.path.join(os.environ.get('XDG_CONFIG_HOME') or os.path.join(HOME, '.config'), 'user-dirs.dirs')
    try:
        with open(conf, encoding='utf-8') as f:
            for line in f:
                m = re.match(rf'\s*XDG_{key}_DIR="(.*)"', line)
                if m:
                    value = m.group(1).replace('$HOME', HOME)
                    if os.path.isabs(value):
                        return value
    except OSError:
        pass
    return os.path.join(HOME, names[key])


def find_child(folder, names):
    """The first of names that is a folder inside folder, any case."""
    try:
        entries = {e.lower(): e for e in os.listdir(folder)}
    except OSError:
        return None
    for name in names:
        real = entries.get(name.lower())
        if real and os.path.isdir(os.path.join(folder, real)) and not os.path.islink(os.path.join(folder, real)):
            return os.path.join(folder, real)
    return None


def looks_like_home(path):
    return sum(find_child(path, names) is not None for _k, names in FOLDERS) >= 2


def detect_profiles(root):
    """[{kind, name, path}] for the people's folders on a disk or in a folder.
    kind: windows | mac | linux | folder."""
    found = []

    def people(base, kind):
        try:
            names = sorted(os.listdir(base))
        except OSError:
            return
        for name in names:
            path = os.path.join(base, name)
            if name.lower() in NOT_PEOPLE or name.startswith('.') or not os.path.isdir(path) or os.path.islink(path):
                continue
            if looks_like_home(path):
                found.append({'kind': kind, 'name': name, 'path': path})

    users = find_child(root, ['Users'])
    if users:
        windows = find_child(root, ['Windows']) is not None or find_child(root, ['Program Files']) is not None
        mac = find_child(root, ['Applications']) is not None or find_child(root, ['Library']) is not None
        people(users, 'windows' if windows or not mac else 'mac')
    for base in ('home', '@home'):
        homes = find_child(root, [base])
        if homes:
            people(homes, 'linux')
    if not found and looks_like_home(root):
        kind = 'linux' if os.path.isdir(os.path.join(root, '.config')) else 'folder'
        found.append({'kind': kind, 'name': os.path.basename(root.rstrip('/')) or root, 'path': root})
    if not found:
        # A drive with the person's folders right at the top, or one folder down (a backup).
        try:
            for name in sorted(os.listdir(root)):
                path = os.path.join(root, name)
                if not name.startswith('.') and os.path.isdir(path) and not os.path.islink(path) and looks_like_home(path):
                    found.append({'kind': 'folder', 'name': name, 'path': path})
        except OSError:
            pass
    return found


def folders_for(profile):
    """[{key, source, dest}] of the folders this profile has."""
    out = []
    for key, names in FOLDERS:
        src = find_child(profile['path'], names)
        if src:
            out.append({'key': key, 'source': src, 'dest': xdg_dir(key)})
    return out


def is_junk(name):
    return name.lower() in JUNK or name.startswith('~$') or name.endswith(('.tmp', '.crdownload', '.part'))


def walk_files(src):
    """(relative path, full path, size) of every file to copy under src: no links, no junk."""
    for root, dirs, files in os.walk(src, onerror=lambda e: None):
        dirs[:] = sorted(d for d in dirs if not is_junk(d) and not os.path.islink(os.path.join(root, d)))
        for name in sorted(files):
            full = os.path.join(root, name)
            if is_junk(name) or os.path.islink(full):
                continue
            try:
                size = os.stat(full).st_size
            except OSError:
                continue
            yield os.path.relpath(full, src), full, size


def measure(src, cancel=None):
    """(files, bytes) under src."""
    n = total = 0
    for _rel, _full, size in walk_files(src):
        if cancel and cancel.is_set():
            break
        n += 1
        total += size
    return n, total


def free_name(path):
    if not os.path.lexists(path):
        return path
    stem, ext = os.path.splitext(path)
    n = 2
    while os.path.lexists(f'{stem} ({n}){ext}'):
        n += 1
    return f'{stem} ({n}){ext}'


class CopyReport:
    def __init__(self):
        self.copied = 0
        self.bytes = 0
        self.same = 0          # already here, the same size and date: not copied again
        self.renamed = []      # a different file had the name: kept both
        self.failed = []       # (path, reason)


def copy_folder(src, dest, report, progress=None, cancel=None):
    """Copies src into dest. Never overwrites: a file that's already here with the same size and
    time is skipped, any other clash keeps both. Reads the source only."""
    for rel, full, size in walk_files(src):
        if cancel and cancel.is_set():
            return
        target = os.path.join(dest, rel)
        tmp = None
        try:
            os.makedirs(os.path.dirname(target), exist_ok=True)
            st = os.stat(full)
            if os.path.exists(target):
                t = os.stat(target)
                if t.st_size == st.st_size and abs(t.st_mtime - st.st_mtime) < 2:
                    report.same += 1
                    if progress:
                        progress(rel, size)
                    continue
                target = free_name(target)
                report.renamed.append(os.path.relpath(target, os.path.dirname(dest)))
            tmp = os.path.join(os.path.dirname(target), '.' + os.path.basename(target) + '.part')
            with open(full, 'rb') as fin, open(tmp, 'wb') as fout:
                while True:
                    if cancel and cancel.is_set():
                        break
                    block = fin.read(1 << 20)
                    if not block:
                        break
                    fout.write(block)
            if cancel and cancel.is_set():
                os.unlink(tmp)
                return
            os.utime(tmp, (st.st_atime, st.st_mtime))
            os.replace(tmp, target)
            report.copied += 1
            report.bytes += size
        except OSError as e:
            report.failed.append((full, e.strerror or str(e)))
            if tmp:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
        if progress:
            progress(rel, size)


# ---------------------------------------------------------------------------------------------
# Bookmarks: read from the old browsers, written into Parcha Browser (Chromium).
# A bookmark tree is a list of {'name', 'url'} and {'name', 'children'}.
# ---------------------------------------------------------------------------------------------

def _chromium_tree(node):
    if node.get('type') == 'url':
        return {'name': node.get('name') or node.get('url', ''), 'url': node.get('url', '')}
    return {'name': node.get('name', ''), 'children': [_chromium_tree(c) for c in node.get('children', [])
                                                     if c.get('type') in ('url', 'folder')]}


def read_chromium(path):
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    roots = data.get('roots', {})
    out = []
    for key in ('bookmark_bar', 'other', 'synced'):
        if key in roots and roots[key].get('children'):
            out.append(_chromium_tree(roots[key]))
    return out


def read_firefox(path):
    """From places.sqlite, read from a copy (the original may be locked, and must not be touched)."""
    with tempfile.TemporaryDirectory() as tmp:
        copy = os.path.join(tmp, 'places.sqlite')
        shutil.copyfile(path, copy)
        for extra in ('-wal',):
            if os.path.exists(path + extra):
                shutil.copyfile(path + extra, copy + extra)
        db = sqlite3.connect(f'file:{copy}?immutable=1', uri=True)
        try:
            rows = db.execute('SELECT b.id, b.parent, b.type, b.title, p.url, b.position FROM moz_bookmarks b '
                              'LEFT JOIN moz_places p ON p.id = b.fk ORDER BY b.parent, b.position').fetchall()
            roots = {r[0]: r[1] for r in db.execute("SELECT id, guid FROM moz_bookmarks WHERE guid IN "
                                                     "('menu________', 'toolbar_____', 'unfiled_____', 'mobile______')")}
        finally:
            db.close()
    children = {}
    for bid, parent, kind, title, url, _pos in rows:
        children.setdefault(parent, []).append((bid, kind, title, url))

    def build(bid, name):
        node = {'name': name, 'children': []}
        for cid, kind, title, url in children.get(bid, []):
            if kind == 1 and url and not url.startswith('place:'):
                node['children'].append({'name': title or url, 'url': url})
            elif kind == 2:
                node['children'].append(build(cid, title or ''))
        return node
    names = {'toolbar_____': 'Bookmarks Toolbar', 'menu________': 'Bookmarks Menu',
             'unfiled_____': 'Other Bookmarks', 'mobile______': 'Mobile Bookmarks'}
    out = []
    for bid, guid in sorted(roots.items(), key=lambda kv: list(names).index(kv[1])):
        tree = build(bid, names[guid])
        if tree['children']:
            out.append(tree)
    return out


def read_plist_bookmarks(path):
    with open(path, 'rb') as f:
        data = plistlib.load(f)

    def build(node):
        kind = node.get('WebBookmarkType')
        if kind == 'WebBookmarkTypeLeaf':
            url = node.get('URLString', '')
            title = (node.get('URIDictionary') or {}).get('title') or url
            return {'name': title, 'url': url}
        if kind == 'WebBookmarkTypeList':
            title = node.get('Title', '')
            if title == 'com.apple.ReadingList':
                title = 'Reading List'
            return {'name': {'BookmarksBar': 'Favourites', 'BookmarksMenu': 'Bookmarks Menu'}.get(title, title),
                    'children': [c for c in (build(x) for x in node.get('Children', [])) if c]}
        return None
    root = build(data)
    return [c for c in (root or {}).get('children', []) if c.get('children')]


def browser_sources(profile):
    """[(browser name, reader, path)] of the bookmark files on the old computer."""
    p = profile['path']
    j = os.path.join
    chromium_like = [
        ('Google Chrome', [j(p, 'AppData/Local/Google/Chrome/User Data'), j(p, 'Library/Application Support/Google/Chrome'),
                           j(p, '.config/google-chrome')]),
        ('Microsoft Edge', [j(p, 'AppData/Local/Microsoft/Edge/User Data'), j(p, 'Library/Application Support/Microsoft Edge'),
                            j(p, '.config/microsoft-edge')]),
        ('Brave', [j(p, 'AppData/Local/BraveSoftware/Brave-Browser/User Data'),
                   j(p, 'Library/Application Support/BraveSoftware/Brave-Browser'), j(p, '.config/BraveSoftware/Brave-Browser')]),
        ('Chromium', [j(p, '.config/chromium'), j(p, 'Library/Application Support/Chromium')]),
        ('Vivaldi', [j(p, 'AppData/Local/Vivaldi/User Data'), j(p, '.config/vivaldi')]),
        ('Opera', [j(p, 'AppData/Roaming/Opera Software/Opera Stable'), j(p, '.config/opera')]),
    ]
    out = []
    for name, dirs in chromium_like:
        for d in dirs:
            for prof in ('Default', 'Profile 1', ''):
                f = j(d, prof, 'Bookmarks') if prof else j(d, 'Bookmarks')
                if os.path.isfile(f):
                    out.append((name, read_chromium, f))
                    break
            else:
                continue
            break
    for base in (j(p, 'AppData/Roaming/Mozilla/Firefox/Profiles'), j(p, 'Library/Application Support/Firefox/Profiles'),
                 j(p, '.mozilla/firefox'), j(p, 'snap/firefox/common/.mozilla/firefox'),
                 j(p, '.var/app/org.mozilla.firefox/.mozilla/firefox')):
        try:
            profiles = sorted(os.listdir(base), key=lambda n: ('default-release' not in n, n))
        except OSError:
            continue
        for prof in profiles:
            f = j(base, prof, 'places.sqlite')
            if os.path.isfile(f):
                out.append(('Firefox', read_firefox, f))
                break
        if out and out[-1][0] == 'Firefox':
            break
    plist = j(p, 'Library/Safari/Bookmarks.plist')
    if os.path.isfile(plist):
        out.append(('Safari', read_plist_bookmarks, plist))
    return out


def count_bookmarks(trees):
    n = 0
    for node in trees:
        n += count_bookmarks(node['children']) if 'children' in node else 1
    return n


def chromium_profile():
    base = os.environ.get('PARCHAOS_BRING_CHROMIUM') or os.path.join(HOME, '.config', 'chromium')
    return base


def browser_running(base=None):
    """Chromium holds SingletonLock (a link to host-pid) while it runs."""
    base = base or chromium_profile()
    try:
        target = os.readlink(os.path.join(base, 'SingletonLock'))
    except OSError:
        return False
    pid = target.rsplit('-', 1)[-1]
    return pid.isdigit() and os.path.exists(f'/proc/{pid}')


EPOCH_DELTA = 11644473600  # seconds from 1601 (Chromium's clock) to 1970


def _stamp():
    return str(int((time.time() + EPOCH_DELTA) * 1_000_000))


def import_into_chromium(groups, label, base=None):
    """Adds the bookmarks as one folder, label, under Other bookmarks of Parcha Browser's
    default profile; groups = [(browser name, trees)]. Returns how many were added. Chromium must
    not be running (it would overwrite the file)."""
    base = base or chromium_profile()
    path = os.path.join(base, 'Default', 'Bookmarks')
    try:
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
    except (OSError, ValueError):
        data = None
    now = _stamp()
    if not isinstance(data, dict) or 'roots' not in data:
        data = {'roots': {
            'bookmark_bar': {'children': [], 'date_added': now, 'date_modified': '0', 'guid': '0bc5d13f-2cba-5d74-951f-3f233fe6c908',
                             'id': '1', 'name': 'Bookmarks bar', 'type': 'folder'},
            'other': {'children': [], 'date_added': now, 'date_modified': '0', 'guid': '82b081ec-3dd3-529c-8475-ab6c344590dd',
                      'id': '2', 'name': 'Other bookmarks', 'type': 'folder'},
            'synced': {'children': [], 'date_added': now, 'date_modified': '0', 'guid': '4cf2e351-0e85-532b-bb37-df045d8f8d0f',
                       'id': '3', 'name': 'Mobile bookmarks', 'type': 'folder'}},
            'version': 1}

    ids = [0]

    def scan(node):
        try:
            ids[0] = max(ids[0], int(node.get('id', 0)))
        except (TypeError, ValueError):
            pass
        for c in node.get('children', []):
            scan(c)
    for root in data['roots'].values():
        if isinstance(root, dict):
            scan(root)
    added = [0]

    def make(node):
        ids[0] += 1
        out = {'date_added': now, 'guid': str(uuid.uuid4()), 'id': str(ids[0]), 'name': node.get('name', '')}
        if 'url' in node:
            out.update(type='url', url=node['url'])
            added[0] += 1
        else:
            out.update(type='folder', date_modified=now, children=[make(c) for c in node['children']])
        return out

    if len(groups) == 1:
        folder = {'name': label, 'children': groups[0][1]}
    else:
        folder = {'name': label, 'children': [{'name': name, 'children': trees} for name, trees in groups]}
    data['roots']['other'].setdefault('children', []).append(make(folder))
    data.pop('checksum', None)   # Chromium works it out again
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        shutil.copy2(path, path + '.before-bring-your-stuff')
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=3, ensure_ascii=False)
    os.replace(tmp, path)
    return added[0]


def wifi_names(root):
    """Names of Wi-Fi networks the old computer knew, where they can be read without its keys
    (passwords never can: Windows and Macs encrypt them with the old computer's own keys)."""
    names = set()
    base = os.path.join(root, 'ProgramData', 'Microsoft', 'Wlansvc', 'Profiles', 'Interfaces')
    for dirpath, _dirs, files in os.walk(base, onerror=lambda e: None):
        for name in files:
            if name.lower().endswith('.xml'):
                try:
                    with open(os.path.join(dirpath, name), encoding='utf-8', errors='replace') as f:
                        m = re.search(r'<name>([^<]{1,64})</name>', f.read())
                    if m:
                        names.add(m.group(1))
                except OSError:
                    pass
    nm = os.path.join(root, 'etc', 'NetworkManager', 'system-connections')
    try:
        for name in os.listdir(nm):
            if name.endswith('.nmconnection'):
                names.add(name[:-len('.nmconnection')])
    except OSError:
        pass
    return sorted(names)
