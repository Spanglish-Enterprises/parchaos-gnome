# SPDX-License-Identifier: GPL-3.0-or-later
# Tests for parchaos-app-permissions (ticket #160). Run:
#   python3 packaging/parchaos-settings/tests/test_app_permissions.py
import importlib.machinery
import importlib.util
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, '..', 'files', 'parchaos-app-permissions')
loader = importlib.machinery.SourceFileLoader('parchaos_app_permissions', SCRIPT)
spec = importlib.util.spec_from_loader('parchaos_app_permissions', loader)
tool = importlib.util.module_from_spec(spec)
loader.exec_module(tool)

failures = 0


def check(ok, what):
    global failures
    if not ok:
        failures += 1
        print(f'FAIL {what}')


tmp = tempfile.mkdtemp()
os.environ['XDG_DATA_HOME'] = tmp
path = os.path.join(tmp, 'flatpak', 'overrides', 'org.example.App')

check(not tool.blocked('org.example.App', 'files'), 'nothing blocked at first')
tool.set_permission('org.example.App', 'files', True)
check(tool.blocked('org.example.App', 'files'), 'files blocked')
check(not tool.blocked('org.example.App', 'network'), 'network untouched')
tool.set_permission('org.example.App', 'network', True)
tool.set_permission('org.example.App', 'devices', True)
text = open(path).read()
check('!home;!host;' in text and '!network;' in text and '!all;' in text, 'negations written')

# Turning each back on undoes it and leaves no file behind.
for perm in ('files', 'network', 'devices'):
    tool.set_permission('org.example.App', perm, False)
check(not os.path.exists(path), 'override removed when empty')

# A user's own override lines survive.
os.makedirs(os.path.dirname(path), exist_ok=True)
with open(path, 'w') as f:
    f.write('[Context]\nfilesystems=~/Music;\nshared=ipc;\n\n[Environment]\nFOO=bar\n')
tool.set_permission('org.example.App', 'files', True)
check('~/Music;!home;!host;' in open(path).read(), 'own filesystems kept')
tool.set_permission('org.example.App', 'files', False)
text = open(path).read()
check('filesystems=~/Music;' in text and 'shared=ipc;' in text and 'FOO=bar' in text,
      'own lines kept after undo')

for bad in (('../x', 'files'), ('org.example.App', 'camera')):
    try:
        tool.set_permission(*bad, True)
        check(False, f'rejects {bad}')
    except ValueError:
        pass

sys.exit(1 if failures else 0)
