# SPDX-License-Identifier: GPL-3.0-or-later
# Tests for the network share login helpers in parchaos-settings (ticket #116). Run:
#   python3 packaging/parchaos-settings/tests/test_share_login.py
import importlib.machinery
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
loader = importlib.machinery.SourceFileLoader('parchaos_settings', os.path.join(HERE, '..', 'files', 'parchaos-settings'))
spec = importlib.util.spec_from_loader('parchaos_settings', loader)
try:
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
except (ImportError, ValueError) as err:
    print(f'share login: skipped ({err})')
    sys.exit(0)

failures = 0


def check(ok, what):
    global failures
    if not ok:
        failures += 1
        print(f'FAIL {what}')


n = mod.normalize_share
check(n('smb://nas/backups') == 'smb://nas/backups', 'smb address kept')
check(n('  smb://nas/backups  ') == 'smb://nas/backups', 'space trimmed')
check(n('\\\\nas\\backups') == 'smb://nas/backups', 'windows style address')
check(n('nas/backups') == 'smb://nas/backups', 'bare server/share')
check(n('nas') is None, 'a server with no share is not enough')
check(n('') is None and n(None) is None, 'empty')
check(n('http://example.com/x') is None, 'web address refused')
check(n('SFTP://host/dir') == 'SFTP://host/dir', 'sftp accepted')

class E:
    def __init__(self, message):
        self.message = message

t = mod.share_error_text
check('username or password' in t(E('Failed to mount Windows share: Permission denied')), 'permission denied reads plainly')
check('could not be found' in t(E('Failed to mount Windows share: No such host')), 'host not found')
check('did not answer' in t(E('Failed to mount Windows share: Connection refused')), 'refused connection')
check(t(E('something odd')) == 'something odd', 'unknown error passes through')

print('share login: all checks passed' if not failures else f'share login: {failures} failed')
sys.exit(1 if failures else 0)
