# SPDX-License-Identifier: GPL-3.0-or-later
# Tests for parchaos-app-network (ticket #126). Run:
#   python3 packaging/parchaos-settings/tests/test_app_network.py
import importlib.machinery
import importlib.util
import os
import shlex
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, '..', 'files', 'parchaos-app-network')
loader = importlib.machinery.SourceFileLoader('parchaos_app_network', SCRIPT)
spec = importlib.util.spec_from_loader('parchaos_app_network', loader)
tool = importlib.util.module_from_spec(spec)
loader.exec_module(tool)

CALC = """[Desktop Entry]
Name=Calculator
Exec=gnome-calculator
DBusActivatable=true
Icon=org.gnome.Calculator
Actions=new-window;

[Desktop Action new-window]
Name=New Window
Exec=gnome-calculator --new-window
"""

failures = 0


def check(ok, what):
    global failures
    if not ok:
        failures += 1
        print(f'FAIL {what}')


def main():
    global failures
    out = tool.blocked_launcher(CALC)
    lines = out.splitlines()
    check(f'Exec={tool.BWRAP} gnome-calculator' in lines, 'main Exec is wrapped')
    check(f'Exec={tool.BWRAP} gnome-calculator --new-window' in lines, 'action Exec is wrapped')
    check('DBusActivatable=true' not in lines and 'DBusActivatable=false' in lines, 'D-Bus activation is off')
    check(lines.count(f'{tool.MARKER}=true') == 1, 'marked exactly once')
    check(tool.blocked_launcher(out) == out, 'wrapping twice changes nothing')
    check(out.index(f'{tool.MARKER}=true') < out.index('[Desktop Action new-window]'), 'marker sits in [Desktop Entry]')

    with tempfile.TemporaryDirectory() as tmp:
        data = os.path.join(tmp, 'data')
        share = os.path.join(tmp, 'share', 'applications')
        os.makedirs(share)
        with open(os.path.join(share, 'org.gnome.Calculator.desktop'), 'w') as f:
            f.write(CALC)
        os.environ['XDG_DATA_HOME'] = data
        os.environ['XDG_DATA_DIRS'] = os.path.join(tmp, 'share')

        if shutil.which('bwrap'):
            tool.set_native('org.gnome.Calculator.desktop', True)
            target = os.path.join(data, 'applications', 'org.gnome.Calculator.desktop')
            check(tool.is_blocked_launcher(target), 'blocking writes a marked launcher')
            tool.set_native('org.gnome.Calculator.desktop', False)
            check(not os.path.exists(target), 'allowing removes it')

            # A launcher the user made themselves is never replaced or removed.
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, 'w') as f:
                f.write('[Desktop Entry]\nName=Mine\nExec=mine\n')
            try:
                tool.set_native('org.gnome.Calculator.desktop', True)
                check(False, 'refuses to replace the user\'s own launcher')
            except RuntimeError:
                pass
            tool.set_native('org.gnome.Calculator.desktop', False)
            check(os.path.exists(target), 'allow leaves the user\'s own launcher alone')
            os.remove(target)

            # The wrapped command really has no network: no interfaces but lo.
            exec_line = [l for l in tool.blocked_launcher(CALC).splitlines() if l.startswith('Exec=')][0][5:]
            words = shlex.split(exec_line.replace('gnome-calculator', 'cat /proc/net/dev'))
            proc = subprocess.run(words, capture_output=True, text=True, timeout=30)
            names = [l.split(':')[0].strip() for l in proc.stdout.splitlines()[2:]]
            check(names == ['lo'], f'blocked command sees only lo, saw {names} ({proc.stderr.strip()})')
        else:
            print('bwrap not installed: skipped the launcher and no-network checks')

        # Flatpak overrides: other settings survive, and undoing block removes only ours.
        app = 'org.example.App'
        odir = os.path.join(data, 'flatpak', 'overrides')
        os.makedirs(odir)
        with open(os.path.join(odir, app), 'w') as f:
            f.write('[Context]\nshared=ipc;\nsockets=x11;\n\n[Environment]\nFOO=bar\n')
        check(not tool.flatpak_blocked(app), 'not blocked at first')
        tool.set_flatpak(app, True)
        check(tool.flatpak_blocked(app), 'blocked after set')
        text = open(os.path.join(odir, app)).read()
        check('sockets=x11;' in text and 'FOO=bar' in text and 'ipc;' in text, 'other overrides survive a block')
        tool.set_flatpak(app, False)
        check(not tool.flatpak_blocked(app), 'allowed again')
        text = open(os.path.join(odir, app)).read()
        check('!network' not in text and 'FOO=bar' in text and 'sockets=x11;' in text, 'undo removes only the block')
        only = 'org.example.Only'
        tool.set_flatpak(only, True)
        check(os.path.exists(os.path.join(odir, only)), 'a new override file is created')
        tool.set_flatpak(only, False)
        check(not os.path.exists(os.path.join(odir, only)), 'an emptied override file is removed')
        try:
            tool.set_flatpak('../evil', True)
            check(False, 'rejects path tricks in app ids')
        except ValueError:
            pass

    print('app-network: all checks passed' if failures == 0 else f'app-network: {failures} check(s) failed')
    return 0 if failures == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
