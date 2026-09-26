#!/usr/bin/python3
# Compare ParchaOS's patched builds of Fedora packages with Fedora's.
#
# The ParchaOS repository has higher dnf priority, so a newer Fedora build
# of a forked package never replaces ours: users would miss Fedora's fixes
# (including same-version security rebuilds) until the fork is rebased.
# Fails when Fedora's version-release is newer than the fork's, ignoring
# the fork's own ".parchaosN" release suffix. Parcher is based on an older
# Nautilus on purpose (docs/parcher-rebase-plan.md), so it only warns.
#
# Original code for ParchaOS, GPL-3.0-or-later.

import re
import subprocess
import sys

import rpm

FORKS = {'gnome-control-center': 'packaging/gnome-control-center/gnome-control-center.spec'}
WARN_ONLY = {'nautilus': 'packaging/parcher/parcher.spec'}


def spec_evr(spec):
    out = subprocess.run(['rpmspec', '-q', '--srpm', '--qf', '%{epoch}:%{version}:%{release}', spec],
                         capture_output=True, text=True, check=True).stdout.strip()
    epoch, version, release = out.split(':', 2)
    release = re.sub(r'\.parchaos\d+', '', release)
    return ('0' if epoch in ('', '(none)') else epoch), version, release


def fedora_evr(name):
    out = subprocess.run(['dnf', '-q', 'repoquery', '--repo', 'fedora', '--repo', 'updates', '--latest-limit', '1',
                          '--qf', '%{epoch}:%{version}:%{release}\n', name],
                         capture_output=True, text=True, check=True).stdout.split()
    epoch, version, release = out[-1].split(':', 2)
    return (epoch or '0'), version, release


def fmt(evr):
    return f'{evr[1]}-{evr[2]}'


def main():
    status = 0
    for name, spec in {**FORKS, **WARN_ONLY}.items():
        ours, fedora = spec_evr(spec), fedora_evr(name)
        print(f'{name}: ParchaOS {fmt(ours)}, Fedora {fmt(fedora)}')
        if rpm.labelCompare(fedora, ours) > 0:
            if name in FORKS:
                print(f'::error::{name}: Fedora has {fmt(fedora)}, the ParchaOS fork is {fmt(ours)}. Rebase the fork.')
                status = 1
            else:
                print(f'::warning::{name}: Fedora has {fmt(fedora)}; ParchaOS is based on {fmt(ours)}. '
                      'See docs/parcher-rebase-plan.md.')
    return status


if __name__ == '__main__':
    sys.exit(main())
