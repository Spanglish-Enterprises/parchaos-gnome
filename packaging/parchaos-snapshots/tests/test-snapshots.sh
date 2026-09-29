#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Tests for parchaos-snapper-setup and parchaos-snapper-dnf (ticket #116).
# Needs root, snapper and btrfs-progs. Everything happens on a scratch
# loopback Btrfs with test-only config names (pt-*); no real config is touched.
#   sudo packaging/parchaos-snapshots/tests/test-snapshots.sh
set -u
[ "$(id -u)" = 0 ] || { echo "run as root"; exit 2; }
here=$(cd "$(dirname "$0")/../files" && pwd)
img=$(mktemp /var/tmp/snapshots-test.XXXXXX)
mnt=$(mktemp -d /var/tmp/snapshots-mnt.XXXXXX)
failures=0
check() { if ! "$@" >/dev/null 2>&1; then failures=$((failures + 1)); echo "FAIL $*"; fi; }
cleanup() {
    for c in pt-root pt-home pt-plain; do snapper -c "$c" delete-config >/dev/null 2>&1; done
    umount -R "$mnt/r" >/dev/null 2>&1
    umount "$mnt/top" >/dev/null 2>&1
    rm -rf "$mnt" "$img"
}
trap cleanup EXIT

truncate -s 512M "$img" && mkfs.btrfs -q "$img" || { echo "cannot make a Btrfs"; exit 2; }
mkdir -p "$mnt/top" "$mnt/r"
mount -o loop "$img" "$mnt/top" || exit 2
btrfs subvolume create "$mnt/top/@root" >/dev/null
btrfs subvolume create "$mnt/top/@home" >/dev/null
umount "$mnt/top"
mount -o loop,subvol=@root "$img" "$mnt/r"
mkdir "$mnt/r/home" "$mnt/r/plain"
mount -o loop,subvol=@home "$img" "$mnt/r/home"

# shellcheck disable=SC1091
source "$here/parchaos-snapper-setup"

setup pt-root "$mnt/r"
setup pt-home "$mnt/r/home"
setup pt-plain "$mnt/r/plain"     # a folder, not a subvolume
setup pt-tmp /dev/shm             # not Btrfs

check test -e /etc/snapper/configs/pt-root
check test -e /etc/snapper/configs/pt-home
check test ! -e /etc/snapper/configs/pt-plain
check test ! -e /etc/snapper/configs/pt-tmp
check grep -q '^ALLOW_GROUPS="wheel"' /etc/snapper/configs/pt-root
check grep -q '^SYNC_ACL="yes"' /etc/snapper/configs/pt-root
check grep -q '^TIMELINE_LIMIT_HOURLY="6"' /etc/snapper/configs/pt-root
check grep -q '^NUMBER_LIMIT="10"' /etc/snapper/configs/pt-home

# Running it again changes nothing.
before=$(stat -c %Y /etc/snapper/configs/pt-root)
sleep 1
setup pt-root "$mnt/r"
check test "$before" = "$(stat -c %Y /etc/snapper/configs/pt-root)"

# A snapshot can be taken and listed.
check snapper -c pt-root create --description test
check bash -c "snapper -c pt-root list | grep -q test"

# The dnf hook: a pre and a post snapshot, joined.
state=$mnt/state
export PARCHAOS_SNAPPER_CONFIG=pt-root PARCHAOS_SNAPPER_STATE=$state
"$here/parchaos-snapper-dnf" pre
check test -s "$state"
"$here/parchaos-snapper-dnf" post
check test ! -e "$state"
listing=$(snapper -c pt-root list)
check grep -q "pre" <<<"$listing"
check grep -q "post" <<<"$listing"
# Without a config the hook does nothing and does not fail.
PARCHAOS_SNAPPER_CONFIG=pt-missing "$here/parchaos-snapper-dnf" pre
check test $? -eq 0
check test ! -e "$mnt/state2"

if [ "$failures" -eq 0 ]; then echo "snapshots: all checks passed"; else echo "snapshots: $failures check(s) failed"; fi
[ "$failures" -eq 0 ]
