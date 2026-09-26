#!/bin/bash
# check-image.sh <rootfs> <packages.tsv>
#
# Release gate for the ISO's package set. Writes every installed package
# (name, license, vendor) to <packages.tsv>, which is published next to
# the ISO, and fails if the image contains something ParchaOS can't
# redistribute or no longer ships:
#   - openh264: Cisco's license covers it only when users download it
#     from Cisco (the ISO carries Fedora's noopenh264 stub instead)
#   - fedora-logos: Fedora's logos are for official Fedora media only
#     (the ISO carries generic-logos instead)
#   - packages built by RPM Fusion (patent-encumbered or non-free);
#     only its repo-definition packages are tolerated
#   - packages ParchaOS dropped: pafari, pearos-*, parchaos-finder,
#     parchaos-macos-remap, parchaos-tmog
# It also fails if noopenh264 or generic-logos is missing.
#
# Reads the rootfs's RPM database with the host's rpm, so it doesn't
# depend on a container starting inside the image.

set -euo pipefail

rootfs="${1:?usage: check-image.sh <rootfs> <packages.tsv>}"
out="${2:?usage: check-image.sh <rootfs> <packages.tsv>}"

rpm --root "$rootfs" -qa --qf '%{NAME}\t%{LICENSE}\t%{VENDOR}\n' \
    | grep -v '^gpg-pubkey' | LC_ALL=C sort > "$out"

fail=0
while IFS=$'\t' read -r name _license vendor; do
    case "$name" in
        openh264|fedora-logos|pafari|pearos-*|parchaos-finder|parchaos-macos-remap|parchaos-tmog)
            echo "check-image: $name must not be in the image" >&2
            fail=1 ;;
    esac
    if [ "$vendor" = "RPM Fusion" ]; then
        case "$name" in
            rpmfusion-free-release|rpmfusion-nonfree-release) ;;
            *) echo "check-image: $name comes from RPM Fusion" >&2
               fail=1 ;;
        esac
    fi
done < "$out"

for required in noopenh264 generic-logos; do
    if ! cut -f1 "$out" | grep -qx "$required"; then
        echo "check-image: $required is missing from the image" >&2
        fail=1
    fi
done

if [ "$fail" -ne 0 ]; then
    echo "check-image: FAILED (package list: $out)" >&2
    exit 1
fi
echo "check-image: OK, $(wc -l < "$out") packages (list: $out)"
