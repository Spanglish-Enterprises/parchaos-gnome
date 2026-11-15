#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Tests for parchaos-snapshot-boot (ticket #151) that need no Btrfs, root or
# GRUB: the boot-menu text from a fake snapshot folder, and "status".
#   python3 packaging/parchaos-boot/tests/test_snapshot_boot.py
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, '..', 'files', 'parchaos-snapshot-boot')
failures = 0


def check(cond, what):
    global failures
    if not cond:
        failures += 1
        print('FAIL', what)


def snapshot(base, n, kind, date, kernel=None, ready=None, state=None):
    d = os.path.join(base, str(n))
    os.makedirs(os.path.join(d, 'snapshot', 'boot'))
    with open(os.path.join(d, 'info.xml'), 'w') as f:
        f.write(f'<?xml version="1.0"?>\n<snapshot>\n  <type>{kind}</type>\n  <num>{n}</num>\n'
                f'  <date>{date}</date>\n  <description>dnf</description>\n</snapshot>\n')
    if kernel:
        for name in (f'vmlinuz-{kernel}', f'initramfs-{kernel}.img'):
            open(os.path.join(d, 'snapshot', 'boot', name), 'w').close()
        if ready is not None:
            # The answer lsinitrd would give is cached per snapshot and kernel.
            open(os.path.join(state, f'ready-{n}-initramfs-{kernel}.img.{"yes" if ready else "no"}'), 'w').close()


def run(args, env):
    full = dict(os.environ, TZ='UTC', **env)
    return subprocess.run(['bash', TOOL] + args, capture_output=True, text=True, env=full)


with tempfile.TemporaryDirectory() as tmp:
    snaps = os.path.join(tmp, 'snapshots')
    state = os.path.join(tmp, 'state')
    os.makedirs(snaps)
    os.makedirs(state)
    cmdline = os.path.join(tmp, 'cmdline')
    with open(cmdline, 'w') as f:
        f.write('BOOT_IMAGE=/@root/boot/vmlinuz root=UUID=abc ro rootflags=subvol=@root quiet\n')
    k = '7.3.3-200.fc44.x86_64'
    snapshot(snaps, 1, 'pre', '2026-11-10 08:00:00', '7.2.8-200.fc44.x86_64', ready=False, state=state)  # old initramfs
    snapshot(snaps, 2, 'post', '2026-11-10 08:01:00', k, ready=True, state=state)                        # not "pre"
    snapshot(snaps, 3, 'pre', '2026-11-12 09:30:00', k, ready=True, state=state)
    snapshot(snaps, 4, 'single', '2026-11-13 10:00:00', k, ready=True, state=state)                      # hourly
    snapshot(snaps, 5, 'pre', '2026-11-14 18:45:00', k, ready=True, state=state)
    snapshot(snaps, 6, 'pre', '2026-11-14 19:00:00')                                                     # no kernel
    env = {'PARCHAOS_SNAPDIR': snaps, 'PARCHAOS_SNAPSHOT_STATE': state, 'PARCHAOS_CMDLINE': cmdline,
           'PARCHAOS_FSROOT': '/@root', 'PARCHAOS_ROOT_UUID': 'abc', 'LANG': 'en_US.UTF-8',
           'GRUB_CMDLINE_LINUX': '', 'GRUB_CMDLINE_LINUX_DEFAULT': 'quiet splash'}

    out = run(['grub'], env)
    check(out.returncode == 0, f'grub exits 0 ({out.stderr})')
    text = out.stdout
    check("submenu 'Start from an earlier version'" in text, 'submenu title')
    check(text.count('menuentry ') == 2, f'two entries (pre snapshots 5 and 3), got {text.count("menuentry ")}')
    check(text.index('parchaos.snapshot=5 ') < text.index('parchaos.snapshot=3 '), 'newest first')
    check("'Before the last update (2026-11-14 18:45)'" in text, 'newest is "Before the last update"')
    check("'Before the update of 2026-11-12 09:30'" in text, 'older ones name their date')
    check('parchaos.snapshot.date=2026-11-14T18:45' in text, 'date on the command line')
    check(f'linux /@root/.snapshots/5/snapshot/boot/vmlinuz-{k} root=UUID=abc ro '
          'rootflags=subvol=@root/.snapshots/5/snapshot' in text, 'kernel path and subvolume')
    check(f'initrd /@root/.snapshots/5/snapshot/boot/initramfs-{k}.img' in text, 'initramfs path')
    check(text.index('search --no-floppy') < text.index('if [ -f'), 'root is searched before the file checks')
    check('quiet splash' in text, 'keeps GRUB_CMDLINE_LINUX_DEFAULT')
    for n in (1, 2, 4, 6):
        check(f'parchaos.snapshot={n} ' not in text, f'snapshot {n} is left out')

    es = run(['grub'], dict(env, LANG='es_ES.UTF-8'))
    check("submenu 'Iniciar desde una versión anterior'" in es.stdout, 'Spanish submenu')
    check("Antes de la última actualización (2026-11-14 18:45)" in es.stdout, 'Spanish newest entry')

    few = run(['grub'], dict(env, PARCHAOS_SNAPSHOT_MENU_MAX='1'))
    check(few.stdout.count('menuentry ') == 1, 'menu size limit')

    check(run(['status'], env).stdout.strip() == 'current', 'status: normal start')
    with open(cmdline, 'w') as f:
        f.write('BOOT_IMAGE=x root=UUID=abc ro parchaos.snapshot=5 parchaos.snapshot.date=2026-11-14T18:45 quiet\n')
    check(run(['status'], env).stdout.strip() == 'snapshot 5 2026-11-14 18:45', 'status: started from a snapshot')
    check(run(['grub'], env).stdout == '', 'no menu while started from a snapshot')
    with open(cmdline, 'w') as f:
        f.write('BOOT_IMAGE=x root=UUID=abc ro quiet\n')
    with open(os.path.join(state, 'restored'), 'w') as f:
        f.write('5 2026-11-14 18:45\n')
    check(run(['status'], env).stdout.strip() == 'restored 5 2026-11-14 18:45', 'status: after keep')

    check(run(['keep', 'x'], env).returncode != 0, 'keep refuses without root or with a bad number')

print('parchaos-snapshot-boot tests:', 'FAILED' if failures else 'passed')
sys.exit(1 if failures else 0)
