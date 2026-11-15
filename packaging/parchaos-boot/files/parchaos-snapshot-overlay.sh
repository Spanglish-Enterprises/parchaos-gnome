#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later
# dracut pre-pivot hook (sourced, so no exit): when the boot entry asks
# for a snapshot (parchaos.snapshot=N), put a writable layer in memory over
# the read-only snapshot mounted at $NEWROOT. Everything written during
# this boot is lost at the next restart; the disk is not changed.
# Original code for ParchaOS, GPL-3.0-or-later.

command -v getarg >/dev/null || . /lib/dracut-lib.sh

if getarg parchaos.snapshot= >/dev/null && ! [ -d /run/parchaos-snapshot/lower ]; then
    _ps=/run/parchaos-snapshot
    mkdir -p "$_ps/lower" "$_ps/rw"
    mount --bind "$NEWROOT" "$_ps/lower"
    mount -t tmpfs -o mode=0755 parchaos-snapshot-rw "$_ps/rw"
    mkdir -p "$_ps/rw/upper" "$_ps/rw/work"
    # The top directory takes its attributes from the writable layer. With
    # SELinux on, labels are put right after the policy loads
    # (parchaos-snapshot-relabel.service).
    chmod 0555 "$_ps/rw/upper"
    if mount -t overlay parchaos-snapshot -o "lowerdir=$_ps/lower,upperdir=$_ps/rw/upper,workdir=$_ps/rw/work" "$NEWROOT"; then
        # The snapshot's fstab remounts / with Btrfs options (subvol=/@root),
        # which the layered root can't take. Leave / out.
        # Read first, then write: the layer reports the copied-up file with
        # the original's inode, so "grep lower > layer" looks like one file
        # to grep, which refuses and leaves an empty fstab.
        _fstab=$(grep -v -E '^[^#[:space:]]+[[:space:]]+/[[:space:]]' "$_ps/lower/etc/fstab")
        printf '%s\n' "$_fstab" > "$NEWROOT/etc/fstab"
        info "parchaos-snapshot: started from snapshot $(getarg parchaos.snapshot=) with a temporary writable layer"
    else
        warn "parchaos-snapshot: could not add the writable layer; starting read-only"
        umount "$_ps/rw" 2>/dev/null
        umount "$_ps/lower" 2>/dev/null
    fi
    unset _ps _fstab
fi
