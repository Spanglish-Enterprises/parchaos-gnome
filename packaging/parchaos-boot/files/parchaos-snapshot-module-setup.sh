#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# dracut module "parchaos-snapshot": lets the boot menu start the system
# from a read-only snapper snapshot, with a writable layer in memory on
# top (ticket #151). Does nothing unless the kernel command line has
# parchaos.snapshot=N, which only the "Start from an earlier version"
# entries add. Original code for ParchaOS, GPL-3.0-or-later.

check() {
    require_binaries mount || return 1
    return 0
}

depends() {
    echo base
}

installkernel() {
    hostonly='' instmods overlay
}

install() {
    inst_multiple -o getfattr setfattr grep
    # shellcheck disable=SC2154  # moddir is set by dracut
    inst_hook pre-pivot 50 "$moddir/parchaos-snapshot-overlay.sh"
}
