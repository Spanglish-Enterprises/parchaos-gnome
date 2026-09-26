#!/usr/bin/env bash
# ==============================================================================
# ParchaOS build engine — generic, profile-driven Fedora live-ISO builder.
#
# Mirrors the phase structure and engine/profile split of Pear-Project/iso's
# build-iso.sh (the Debian pearOS build), rewritten against Fedora's own
# tooling (dnf/rpm/dracut) instead of debootstrap/apt/dpkg. Nothing
# profile-specific belongs in this file — package lists, repo definitions,
# branding, and boot menu text all live under profiles/<name>/.
#
# Tooling note (Phase 1): Lorax/livemedia-creator and kiwi were evaluated as
# alternatives to hand-rolled `dnf --installroot` + mksquashfs + xorriso.
# Both wrap the whole pipeline behind a single kickstart/XML file, which
# would collapse the granular profile_setup_repo()/profile_customize() hook
# model this engine mirrors from the Debian build into one opaque %post
# blob. Manual assembly was chosen instead specifically to keep that
# engine/profile separation. Revisit if the manual ISO-assembly phase (7)
# below proves too fragile in practice.
#
# UNTESTED: this repo was written without access to a Fedora build host
# (see docs/phase0-findings.md for the environment this was developed in).
# Steps marked "VERIFY ON REAL HOST" are the ones most likely to need
# iteration — everything else (arg parsing, profile loading, dnf bootstrap
# logic) is straightforward enough to be confident in, but none of it has
# actually been run end-to-end yet.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "$(readlink -f -- "$0")")" && pwd)"
REPO_ROOT="$(dirname -- "$SCRIPT_DIR")"

# ---- defaults ----------------------------------------------------------------
# Real bug found 2026-09-24 (see docs/gnome-phase0-findings.md's "KDE-only
# cruft" section): this used to default to "pearos" when --profile was
# omitted, which silently built the wrong product for any invocation that
# forgot the flag, and made it unsafe to ever delete profiles/pearos/ (a
# future omitted --profile would just silently break instead of failing
# loudly). No default now — --profile is required, see the check below.
PROFILE=""
BRANCH=""            # a Fedora release number ("44", ...) or "rawhide"; default from profile.conf
LOCAL=0               # install profile RPMs from build/local-rpms/ instead of COPR
CLEAN_BASE=0          # wipe and rebuild the dnf --installroot base cache
CLEAN_TARGET=0        # wipe and re-clone the working rootfs from the base cache
DROP_TO_CHROOT=0      # drop into an interactive shell in the target rootfs
NVIDIA=0              # pull in akmod-nvidia + friends from RPM Fusion
SKIP_BRANDING=0       # skip Phase 5 (repo+PROFILE_REPO_PACKAGES) and Phase 5.5
                      # (profile_customize) entirely — builds packages.list's
                      # plain base only. This is the Phase 1 "unbranded
                      # baseline" checkpoint: it doesn't need the profile's
                      # COPR to exist yet (Phase 2), just packages.list.
ISO_VERSION="$(date +%Y.%m.%d)"

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

  --profile <name>     Profile under profiles/ to build (required, no default)
  --branch <ver>        Fedora release to target: a number or "rawhide"
                         (default: $BRANCH)
  --local                Install profile RPMs from build/local-rpms/ instead
                         of the profile's COPR repo
  --clean-base           Rebuild the dnf --installroot base cache from scratch
  --clean-target         Re-clone the working rootfs from the base cache
  --chroot               Drop into a shell in the target rootfs before
                         packaging, instead of building the ISO
  --nvidia               Include RPM Fusion's proprietary NVIDIA packages
  --skip-branding         Skip repo setup, PROFILE_REPO_PACKAGES, and
                         profile_customize — build packages.list's plain
                         base only (doesn't need the profile's COPR to
                         exist yet)
  --version <ver>        ISO filename version tag (default: today's date)
  -h, --help             Show this help
EOF
}

# Saved BEFORE the arg-parsing loop below, which consumes "$@" via
# `shift` — FOUND 2026-09-22 via a real build that silently reverted to
# every hardcoded default (branch 42 instead of the requested 44, etc):
# the sudo self-re-exec further down used to reference "$@" too, but by
# that point the parsing loop had already shifted through the entire
# original argument list, leaving it empty. The re-exec'd (root) process
# then re-parsed nothing and fell back to this script's own compiled-in
# defaults, discarding every flag the caller actually passed —
# invisibly, since the script still ran and produced *an* ISO, just not
# the one asked for.
ORIGINAL_ARGS=("$@")

while [ $# -gt 0 ]; do
    case "$1" in
        --profile) PROFILE="$2"; shift 2 ;;
        --branch|-b) BRANCH="$2"; shift 2 ;;
        --local) LOCAL=1; shift ;;
        --clean-base) CLEAN_BASE=1; shift ;;
        --clean-target) CLEAN_TARGET=1; shift ;;
        --chroot) DROP_TO_CHROOT=1; shift ;;
        --nvidia) NVIDIA=1; shift ;;
        --skip-branding) SKIP_BRANDING=1; shift ;;
        --version|-v) ISO_VERSION="$2"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown option: $1" >&2; usage; exit 1 ;;
    esac
done

if [ -z "$PROFILE" ]; then
    echo "Error: --profile is required (no default — see usage below)." >&2
    usage
    exit 1
fi

if [ "$(id -u)" -ne 0 ]; then
    echo "Re-executing under sudo (dnf --installroot and chroot need root)..."
    exec sudo -E "$0" "${ORIGINAL_ARGS[@]}"
fi

for bin in dnf mksquashfs xorriso grub2-mkstandalone rpm2cpio; do
    command -v "$bin" >/dev/null 2>&1 || { echo "Missing required tool: $bin" >&2; exit 1; }
done

# ---- Phase 1: load the profile ------------------------------------------------
PROFILE_DIR="$REPO_ROOT/profiles/$PROFILE"
[ -d "$PROFILE_DIR" ] || { echo "No such profile: $PROFILE_DIR" >&2; exit 1; }

# shellcheck source=/dev/null
source "$PROFILE_DIR/profile.conf"
# shellcheck source=/dev/null
source "$PROFILE_DIR/packages.sh"
# shellcheck source=/dev/null
source "$PROFILE_DIR/repo.sh"
# shellcheck source=/dev/null
source "$PROFILE_DIR/customize.sh"

# The live ISO's boot menu (UEFI and BIOS): the normal quiet boot with the
# splash, a basic-graphics fallback for GPUs the kernel can't drive yet,
# and a troubleshooting entry with kernel messages on the serial console
# (what automated VM tests read).
live_menu_entries() {
    local base="root=live:CDLABEL=$PROFILE_ISO_LABEL rd.live.image"
    cat <<MENU
menuentry "Start $PROFILE_DISPLAY_NAME" {
    set gfxpayload=keep
    linux (\$root)/boot/vmlinuz $base rhgb quiet
    initrd (\$root)/boot/initramfs.img
}
menuentry "Start $PROFILE_DISPLAY_NAME in basic graphics mode" {
    linux (\$root)/boot/vmlinuz $base nomodeset quiet
    initrd (\$root)/boot/initramfs.img
}
menuentry "Troubleshooting: start with kernel messages" {
    set gfxpayload=keep
    linux (\$root)/boot/vmlinuz $base console=tty0 console=ttyS0,115200n8
    initrd (\$root)/boot/initramfs.img
}
MENU
}

# The Fedora release: --branch, else the profile's own, else 44.
BRANCH="${BRANCH:-${PROFILE_FEDORA_RELEASE:-44}}"
: "${PROFILE_DISPLAY_NAME:?profile.conf must set PROFILE_DISPLAY_NAME}"
: "${PROFILE_SLUG:?profile.conf must set PROFILE_SLUG}"
: "${PROFILE_ISO_LABEL:?profile.conf must set PROFILE_ISO_LABEL}"
: "${PROFILE_SESSION:=wayland}"   # "wayland" or "x11" — see docs/phase0-findings.md

BUILD_DIR="$REPO_ROOT/build"
BASE_CACHE="$BUILD_DIR/base-cache-$BRANCH"
ROOTFS_TARGET="$BUILD_DIR/rootfs-$PROFILE-$BRANCH"
ISO_WORKDIR="$BUILD_DIR/iso-$PROFILE-$BRANCH"
mkdir -p "$BUILD_DIR"

echo "=== ParchaOS build: profile=$PROFILE branch=$BRANCH nvidia=$NVIDIA local=$LOCAL ==="

# ---- Phase 2: base cache (dnf --installroot bootstrap) ------------------------
# Mirrors the Debian engine's mmdebstrap step: a minimal Fedora rootfs shared
# across builds of the same branch, rebuilt only when packages.list changes
# or --clean-base is passed.
PKGLIST_HASH="$(sha256sum "$PROFILE_DIR/packages.list" | cut -d' ' -f1)"
BASE_MARKER="$BASE_CACHE/.parchaos-base-hash"

if [ "$CLEAN_BASE" -eq 1 ]; then
    rm -rf "$BASE_CACHE"
fi

if [ ! -f "$BASE_MARKER" ] || [ "$(cat "$BASE_MARKER" 2>/dev/null)" != "$PKGLIST_HASH" ]; then
    echo "--- Bootstrapping base cache for Fedora $BRANCH ---"
    rm -rf "$BASE_CACHE"
    mkdir -p "$BASE_CACHE"
    mapfile -t base_packages < <(grep -vE '^\s*(#|$)' "$PROFILE_DIR/packages.list")
    # --use-host-config: this engine assumes it runs on a Fedora build host,
    # so it reuses the host's own repo definitions (fedora/updates mirrors)
    # rather than seeding /etc/yum.repos.d by hand inside the installroot.
    dnf -y \
        --installroot="$BASE_CACHE" \
        --releasever="$BRANCH" \
        --use-host-config \
        --setopt=install_weak_deps=False \
        --setopt=keepcache=True \
        install "${base_packages[@]}"
    echo "$PKGLIST_HASH" > "$BASE_MARKER"
    # FOOTGUN FIX (2026-09-18): a rebuilt base cache is worthless if
    # ROOTFS_TARGET already existed and Phase 3 below just reuses it
    # unchanged — found the hard way when a packages.list fix (adding
    # systemd-pam) rebuilt the base cache correctly but the ISO still
    # shipped the old rootfs, silently, because nothing forced a
    # re-clone. Whenever the base cache itself was just rebuilt, force
    # Phase 3 to re-clone from it too, regardless of --clean-target.
    CLEAN_TARGET=1
else
    echo "--- Base cache for Fedora $BRANCH is up to date, reusing ---"
fi

# ---- Phase 3: clone base cache into the working target ------------------------
if [ "$CLEAN_TARGET" -eq 1 ] || [ ! -d "$ROOTFS_TARGET" ]; then
    echo "--- Cloning base cache into working target ---"
    rm -rf "$ROOTFS_TARGET"
    mkdir -p "$ROOTFS_TARGET"
    rsync -aHAX --numeric-ids "$BASE_CACHE"/ "$ROOTFS_TARGET"/
else
    echo "--- Reusing existing working target ($ROOTFS_TARGET) ---"
fi

# ---- Phase 4: chroot helpers ---------------------------------------------------
# systemd-nspawn handles /proc, /sys, /dev, and resolv.conf itself, so this
# engine doesn't hand-manage bind mounts the way the Debian engine's manual
# chroot() calls do.
run_in_target() {
    systemd-nspawn -D "$ROOTFS_TARGET" --resolv-conf=bind-host --quiet "$@"
}

if [ "$DROP_TO_CHROOT" -eq 1 ]; then
    echo "--- Dropping into $ROOTFS_TARGET (exit to resume, but note: --chroot stops here, it does not continue to packaging) ---"
    run_in_target /bin/bash
    exit 0
fi

# ---- Phase 5: repo setup + package installation --------------------------------
if [ "$SKIP_BRANDING" -eq 1 ]; then
    echo "--- --skip-branding given: skipping repo setup, PROFILE_REPO_PACKAGES, and profile_customize ---"
else
    echo "--- Configuring repositories ---"
    profile_setup_repo   # defined in profiles/$PROFILE/repo.sh — COPR + RPM Fusion

    if [ "$NVIDIA" -eq 1 ]; then
        PROFILE_REPO_PACKAGES+=("${PROFILE_NVIDIA_PACKAGES[@]}")
    fi

    if [ "$LOCAL" -eq 1 ]; then
        LOCAL_RPM_DIR="$BUILD_DIR/local-rpms"
        [ -d "$LOCAL_RPM_DIR" ] || { echo "--local given but $LOCAL_RPM_DIR doesn't exist" >&2; exit 1; }
        echo "--- Installing local RPMs from $LOCAL_RPM_DIR ---"
        mkdir -p "$ROOTFS_TARGET/tmp/local-rpms"
        cp "$LOCAL_RPM_DIR"/*.rpm "$ROOTFS_TARGET/tmp/local-rpms/"
        run_in_target dnf -y install /tmp/local-rpms/*.rpm
        rm -rf "$ROOTFS_TARGET/tmp/local-rpms"
    else
        echo "--- Installing profile packages from repo/COPR ---"
        # --refresh + --best: real bug found via TWO successive live
        # rebuilds (2026-09-18). When $ROOTFS_TARGET is reused across
        # builds (the normal case), dnf5's plain `install` on an
        # already-installed package has pure "ensure presence"
        # semantics — it does NOT implicitly upgrade to a newer
        # available version, confirmed directly: even with --refresh
        # added (attempt #1, wrongly assumed sufficient — see git log),
        # a full rebuild ~20 minutes after pushing a fixed
        # pearos-sddm-theme (1.0-1 -> 1.0-2) to COPR still shipped the
        # OLD 1.0-1, and the real dnf output said plainly "Package
        # ... is already installed" / "Nothing to do" for every
        # PROFILE_REPO_PACKAGES entry, --refresh or not. Verified
        # --best is what actually fixes it: manually ran `dnf install
        # --best pearos-sddm-theme` against the same stale rootfs and
        # watched it correctly upgrade 1.0-1 -> 1.0-2. --refresh is
        # still kept too, since --best only helps once dnf's metadata
        # actually reflects the newer version existing.
        run_in_target dnf -y --refresh --setopt=install_weak_deps=False install --best "${PROFILE_REPO_PACKAGES[@]}"
    fi

    profile_teardown_repo

    # ---- Phase 5.5: branding / customization ---------------------------------------
    echo "--- Applying profile branding/customization ---"
    profile_customize   # defined in profiles/$PROFILE/customize.sh
fi

# VERIFIED (2026-09-18): booting to a graphical session isn't branding —
# it's baseline desktop functionality, but it used to live inside
# profile_customize() (`systemctl set-default graphical.target`), so
# --skip-branding silently produced a text-mode-only ISO. Confirmed via
# a real boot test: the --skip-branding build reached a fully working
# multi-user environment (networking up, correct live-media hostname)
# but sat at a plain text console forever because nothing ever set
# graphical.target as default. Run this unconditionally so
# --skip-branding builds still boot to a desktop; profile_customize()
# still owns the actual branding specifics (SDDM theme, look-and-feel,
# Kvantum/GTK theme, liquid-gel enable) and stays skippable.
run_in_target systemctl set-default graphical.target

# VERIFIED (2026-09-18): same class of bug as graphical.target above —
# baseline live-boot functionality, not branding, but silently broken.
# Fedora's own livesys-scripts package (already installed — it's what
# creates the passwordless "liveuser" account and configures SDDM
# autologin at first boot) gates ALL of its desktop-specific setup
# behind /etc/sysconfig/livesys's livesys_session variable
# (usr/libexec/livesys/livesys-main: `if [ "${livesys_session}" ]; then
# . sessions.d/livesys-${livesys_session}; fi`) — on real Fedora spins
# this is set by the official kickstart's %post, which this project's
# engine doesn't run, so it defaults to empty and the whole block is
# skipped unconditionally. Confirmed via a real boot test: liveuser was
# created with no password (passwd -S showed "NP"), but
# /etc/sddm.conf's [Autologin] section never got its User=/Session=
# lines written by sessions.d/livesys-kde, so SDDM showed a normal
# interactive login prompt instead of the passwordless one-click login
# every real Fedora live image has — the very first person to boot this
# ISO would hit a login prompt with no way in. Fixed by setting the
# session type explicitly so livesys's own (already correct, already
# tested) KDE-specific hook actually runs.
: "${PROFILE_LIVESYS_SESSION:=kde}"
sed -i "s/^livesys_session=.*/livesys_session=\"$PROFILE_LIVESYS_SESSION\"/" "$ROOTFS_TARGET/etc/sysconfig/livesys"

# ---- Phase 6: initramfs ---------------------------------------------------------
echo "--- Regenerating initramfs (dracut) ---"
# systemd-nspawn allocates a pty for run_in_target by default (needed for
# --chroot's interactive shell), whose terminal (onlcr) settings leave a
# trailing \r on captured output — strip it or every use of $KERNEL_VER
# downstream silently breaks (e.g. realpath treating "...x86_64\r" as part
# of the path).
KERNEL_VER="$(run_in_target rpm -q --qf '%{VERSION}-%{RELEASE}.%{ARCH}\n' kernel-core | tail -n1 | tr -d '\r')"
# --regenerate-all doesn't take an output path or kernel version — it
# regenerates for every installed kernel using dracut's own naming
# convention. Since Phase 7 needs a known filename to copy onto the ISO,
# target this one kernel explicitly instead.
#
# VERIFIED (2026-09-18): a plain `dracut --force` here produces an
# initramfs that boots partway (past GRUB into the actual kernel/systemd
# — see the $root fix above) and then hard-fails with `dracut: FATAL:
# Don't know how to handle 'root=live:CDLABEL=...'`. dracut's hostonly
# mode (the default) decides which modules to include by inspecting the
# *build* environment — a chroot with no live media involved — so it has
# no way to detect that `dmsquash-live` (confirmed present at
# /usr/lib/dracut/modules.d/70dmsquash-live/, part of the already-listed
# dracut-live package) is needed, and silently leaves it out. `--add`
# forces it in regardless of hostonly detection. `--no-hostonly` on top
# of that because live media needs to work on whatever hardware it's
# booted on, not just this build host's — hostonly's driver/module
# pruning would otherwise ship an initramfs that might not even find its
# own root filesystem on different hardware.
run_in_target dracut --force --no-hostonly --add dmsquash-live \
    "/boot/initramfs-$KERNEL_VER.img" "$KERNEL_VER"

# ---- Phase 7: package the ISO ---------------------------------------------------
echo "--- Assembling ISO ---"
rm -rf "$ISO_WORKDIR"
mkdir -p "$ISO_WORKDIR/LiveOS" "$ISO_WORKDIR/EFI/BOOT" "$ISO_WORKDIR/boot"

echo "Compressing rootfs as SquashFS (this is the slow part)..."
mksquashfs "$ROOTFS_TARGET" "$ISO_WORKDIR/LiveOS/squashfs.img" \
    -comp xz -e boot -noappend

cp "$ROOTFS_TARGET/boot/vmlinuz-$KERNEL_VER" "$ISO_WORKDIR/boot/vmlinuz"
cp "$ROOTFS_TARGET/boot/initramfs-$KERNEL_VER.img" "$ISO_WORKDIR/boot/initramfs.img"

# --- UEFI: Ploader (rEFInd fork), reused verbatim per the brief — it's an
# EFI-level binary, not something that needs rebuilding for Fedora. Ploader
# itself is Phase 4 work (see profiles/pearos/ploader/README.md) — until its
# build output exists, degrade to grub2-mkrescue's own default UEFI stub
# (or none, if the host's grub2-efi modules aren't installed) with a
# warning, so Phase 1's engine checkpoint doesn't have to wait on it.
# Reconciling grub2-mkrescue's own EFI/BOOT layout with Ploader's branded
# one is real Phase 4 work once ploader_x64.efi actually exists.
#
# Secure Boot: Ploader itself is unsigned and not enrolled with Microsoft,
# so booting it directly under Secure Boot fails. Instead of getting it
# signed by Microsoft (external, lengthy), we chainload through Fedora's
# own already-Microsoft-signed shim (shim-x64), which validates the next
# stage against a self-generated MOK the user enrolls once via shim's
# MokManager UI — the same pattern VirtualBox/ZFS/NVIDIA kernel modules
# use. Shim's hardcoded next-stage filename is grubx64.efi, sitting next
# to it — see profiles/pearos/ploader/secureboot/ for the signing
# artifacts (key generation + signing documented in
# docs/phase4-findings.md). If those artifacts aren't present, fall back
# to shipping unsigned Ploader directly as BOOTX64.EFI (works fine with
# Secure Boot disabled, which is the state most VMs/test hardware default
# to; real hardware with Secure Boot on needs the shim chain).
HAVE_UEFI=0
SECUREBOOT_DIR="$PROFILE_DIR/ploader/secureboot"
if [ -f "$PROFILE_DIR/ploader/ploader_x64.efi" ]; then
    HAVE_UEFI=1
    echo "Building UEFI boot image (Ploader)..."
    mkdir -p "$ISO_WORKDIR/EFI/BOOT"
    EFIBOOT_IMG="$ISO_WORKDIR/EFI/efiboot.img"
    # VERIFIED ROOT CAUSE (2026-09-21, see docs/phase4-findings.md "UEFI
    # reboot loop" section): the real UEFI reboot loop was neither the
    # shim/Ploader signature (a stale signed binary was a real, separate
    # bug, fixed above) nor fbx64.efi/pearos-mok.cer/theme content — it's
    # this exact QEMU 11.0.3 / pve-edk2-firmware-ovmf 4.2026.08-1 FAT
    # driver hanging/resetting on a 16MB El Torito UEFI image once
    # EFI/BOOT (or EFI/ itself) holds more than a bare 3-file minimum.
    # The deciding variable turned out to be the IMAGE SIZE, not entry
    # count: the identical "failing" content (shim+mmx64+Ploader+theme as
    # an EFI/ sibling) boots perfectly at 64MB, reproducibly, every time —
    # so this is a FAT16-root-directory-sizing boundary tied to a 16MB
    # image specifically, not a hard cap on file count. 16MB -> 64MB costs
    # nothing on a 2GB+ ISO and is the actual fix; keep this generous
    # rather than shrinking content back down if the bug ever resurfaces.
    dd if=/dev/zero of="$EFIBOOT_IMG" bs=1M count=64
    mkfs.vfat "$EFIBOOT_IMG"
    mmd -i "$EFIBOOT_IMG" ::/EFI ::/EFI/BOOT
    # The MOK private key is never committed to the repo (only the public
    # .crt/.cer are), so it only exists on a build host that was set up to
    # sign releases — resolve it from an env var first, falling back to a
    # conventional path outside the repo. If found, re-sign ploader_x64.efi
    # fresh every build rather than trusting the checked-in
    # ploader_x64_signed.efi: that checked-in binary is a point-in-time
    # artifact that can silently go stale/bad (a real instance of this bit
    # this project on 2026-09-21 — a checked-in signed binary that was
    # byte-for-byte plausible but made shim reset-loop on real UEFI
    # firmware; a fresh sbsign of the same unsigned input fixed it
    # immediately, see docs/phase4-findings.md).
    # This script normally runs under `sudo`, which resets $HOME to /root —
    # resolve the invoking user's real home (via $SUDO_USER) so the default
    # path below actually finds a key placed in a normal user's homedir.
    REAL_HOME="$HOME"
    if [ -n "${SUDO_USER:-}" ]; then
        SUDO_USER_HOME="$(getent passwd "$SUDO_USER" | cut -d: -f6)"
        [ -n "$SUDO_USER_HOME" ] && REAL_HOME="$SUDO_USER_HOME"
    fi
    MOK_KEY="${PLOADER_MOK_KEY:-$REAL_HOME/pearos-mok/pearos-mok.key}"
    MOK_CERT="${PLOADER_MOK_CERT:-$REAL_HOME/pearos-mok/pearos-mok.crt}"
    SIGNED_PLOADER="$SECUREBOOT_DIR/ploader_x64_signed.efi"
    if command -v sbsign >/dev/null 2>&1 && [ -f "$MOK_KEY" ] && [ -f "$MOK_CERT" ]; then
        echo "MOK signing key found ($MOK_KEY) — re-signing Ploader fresh for this build."
        SIGNED_PLOADER="$BUILD_DIR/ploader_x64_signed.efi"
        sbsign --key "$MOK_KEY" --cert "$MOK_CERT" --output "$SIGNED_PLOADER" \
            "$PROFILE_DIR/ploader/ploader_x64.efi"
    fi
    # UEFI KERNEL BOOT (2026-09-21): Ploader (rEFInd fork) has no working
    # UEFI-native path to the actual kernel — this project only ever builds
    # a BIOS-target (i386-pc) GRUB, which pure UEFI firmware (no CSM) can't
    # execute at all, so Ploader's own OS auto-scan never finds anything
    # bootable and just falls back to its Reboot/Shutdown menu. Building a
    # real UEFI-native bootloader by hand (grub2-mkimage, custom modules)
    # is real, substantial work; instead this uses Fedora's own real,
    # tested, already-signed grub2-efi-x64-cdboot package output (gcdx64.efi
    # — the exact binary real Fedora Live ISOs use for El Torito UEFI boot)
    # as the shim target, with our own grub.cfg (same content as the BIOS
    # config below, GRUB's scripting is platform-independent). Verified via
    # a real raw-disk boot test on the boot-test VM/the VM host: shim -> gcdx64.efi renders
    # its own GRUB menu and executes the entry with zero crash/loop.
    # Ploader is parked (still built/signed above) for future
    # re-integration as a branded front-end once this real boot path is
    # solid — shipping a working UEFI boot took priority over Ploader's
    # branding under the "ship today" call, see docs/phase4-findings.md.
    UEFI_GRUB_EFI="$(find "$ROOTFS_TARGET/usr/lib/efi/grub2" -name gcdx64.efi 2>/dev/null | head -1)"
    if [ -z "$UEFI_GRUB_EFI" ] && [ -f "$ROOTFS_TARGET/boot/efi/EFI/fedora/gcdx64.efi" ]; then
        UEFI_GRUB_EFI="$ROOTFS_TARGET/boot/efi/EFI/fedora/gcdx64.efi"
    fi
    if [ -f "$SECUREBOOT_DIR/shimx64.efi" ] && [ -f "$SECUREBOOT_DIR/mmx64.efi" ] \
       && [ -n "$UEFI_GRUB_EFI" ]; then
        echo "Chaining shim -> Fedora's real grub2-efi-x64-cdboot (gcdx64.efi) for UEFI kernel boot."
        mcopy -i "$EFIBOOT_IMG" "$SECUREBOOT_DIR/shimx64.efi" ::/EFI/BOOT/BOOTX64.EFI
        mcopy -i "$EFIBOOT_IMG" "$SECUREBOOT_DIR/mmx64.efi" ::/EFI/BOOT/mmx64.efi
        mcopy -i "$EFIBOOT_IMG" "$UEFI_GRUB_EFI" ::/EFI/BOOT/grubx64.efi
        # gcdx64.efi's own prefix/config search targets the OUTER ISO9660
        # filesystem it was booted from (i.e. (cd0) as GRUB itself sees it),
        # NOT the small efiboot.img FAT image shim loaded it out of — real
        # hands-on testing on the boot-test VM/the VM host found grub.cfg copied into
        # efiboot.img's ::/EFI/BOOT/ is never found (GRUB drops to its
        # interactive shell instead of auto-loading a menu), while the
        # identical content placed at the real ISO9660-level EFI/BOOT/ (via
        # $ISO_WORKDIR, i.e. where grub2-mkrescue's own now-otherwise-empty
        # EFI/BOOT placeholder lives) loads and boots correctly. Confirmed
        # via a manual `configfile` in GRUB's own shell: real systemd/kernel
        # boot log on screen, the first genuinely working UEFI kernel boot
        # this project has had.
        mkdir -p "$ISO_WORKDIR/EFI/BOOT/fonts"
        cat > "$ISO_WORKDIR/EFI/BOOT/grub.cfg" <<EOF
insmod iso9660
insmod gzio
insmod ext2
insmod all_video
search --file --set=root /boot/vmlinuz

set default=0
set timeout=5
$(live_menu_entries)
EOF
        if [ -f "$ROOTFS_TARGET/boot/grub2/fonts/unicode.pf2" ]; then
            cp "$ROOTFS_TARGET/boot/grub2/fonts/unicode.pf2" "$ISO_WORKDIR/EFI/BOOT/fonts/unicode.pf2"
        fi
    else
        echo "WARNING: shim/mmx64/grub2-efi-x64-cdboot not all found — shipping unsigned Ploader as BOOTX64.EFI (no real UEFI kernel-boot path, cosmetic menu only)." >&2
        mcopy -i "$EFIBOOT_IMG" "$PROFILE_DIR/ploader/ploader_x64.efi" ::/EFI/BOOT/BOOTX64.EFI
    fi
else
    echo "WARNING: $PROFILE_DIR/ploader/ploader_x64.efi not built yet (Phase 4) — building without Ploader's branded UEFI boot." >&2
fi

# --- BIOS boot: grub2-mkrescue, not a hand-rolled grub2-mkstandalone +
# manual El Torito image + raw xorriso invocation. The hand-rolled version
# produced a structurally valid ISO9660 image (xorriso reported success)
# that nonetheless hung forever at SeaBIOS's "Booting from DVD/CD..." on a
# real boot test — confirmed via a real VM screendump, unchanged
# across repeated checks, i.e. genuinely stuck, not just slow. Exactly the
# risk this section's old "VERIFY ON REAL HOST" comment (removed now that
# it's been verified — negatively) was flagged for. grub2-mkrescue is the
# same tool real distros use for this and handles the El Torito boot
# catalog, hybrid MBR, and (when grub2-efi modules are present) UEFI boot
# correctly, without needing any of that reimplemented by hand.
#
# grub2-mkrescue's embedded core image looks for its config at the
# upstream-conventional /boot/grub/grub.cfg on the resulting media — NOT
# /boot/grub2/ (that renamed path is a Fedora-installed-system convention
# for coexistence with legacy grub-legacy; it doesn't apply to rescue
# media grub2-mkrescue builds itself).
# VERIFIED ROOT CAUSE (2026-09-18) of the "grub_relocator_prepare_relocs:
# out of memory" boot failure: this grub.cfg never explicitly set $root,
# so it stayed at whatever bogus value grub2-mkrescue's automatic
# detection left it at (confirmed interactively: `echo root=$root`
# printed "hd96", not a real device) — bare paths like "/boot/vmlinuz"
# resolved against that broken $root well enough for `ls` to still find
# the files, but something about GRUB's internal state being wrong from
# an unset/garbage root apparently corrupts the relocator's own
# bookkeeping when `boot` actually runs. The real Fedora ISO's own
# grub.cfg never relies on automatic detection — it explicitly searches
# for a known file and sets $root from that before referencing anything
# via ($root)/... . Doing the same here — confirmed by the next real
# boot that this fixed the relocator OOM (see docs/phase1-findings.md).
# Also switched root=live:LABEL= to root=live:CDLABEL=, matching
# Fedora's exact dracut-live invocation for optical media.
#
# VIDEO MODE (2026-09-18): after the relocator/dracut-live fixes above,
# boot reached a live login/network stage (confirmed via DHCP lease)
# but the screen stayed a blank cursor, and VT-switching via QMP
# sendkey to ctrl-alt-f1..f4 produced identical screendumps every
# time — even a plain kernel getty console didn't respond, which rules
# out SDDM/Plasma specifically and points at the console/framebuffer
# itself. The real Fedora ISO's grub.cfg always loads `all_video`,
# forces `gfxpayload=keep` inside the menuentry, and falls back to
# `vga=791` on the kernel cmdline — this hand-written grub.cfg lacked
# all three, so GRUB may have left the console in a video mode the
# kernel's fbcon/DRM couldn't take over cleanly. Adding them here to
# match — TESTED (2026-09-18) and DISPROVEN: rebuilt, rebooted, and
# captured screendumps of the main console plus all four VT-switch
# targets — all five came back byte-identical (same blank-cursor
# frame as before), so this was never a video-mode mismatch. See
# docs/phase1-findings.md.
#
# SERIAL CONSOLE (2026-09-18): screendump/VT-switch has now given the
# same non-answer twice, so it can no longer distinguish "still
# booting" from "wedged" — need actual boot text instead of a
# screenshot. Adding `console=ttyS0,115200n8` as the primary console
# (last `console=` wins) and dropping `quiet` so kernel/systemd/dracut
# messages actually appear on it; `console=tty0` is kept first so the
# local VGA console/screendump path still gets something too. This
# needs a matching `--serial0 socket` device added to the VM
# to actually capture it — see docs/phase1-findings.md.
echo "Writing grub.cfg for grub2-mkrescue ---"
mkdir -p "$ISO_WORKDIR/boot/grub"
cat > "$ISO_WORKDIR/boot/grub/grub.cfg" <<EOF
# Inspired by the config used for lorax-built live media
insmod iso9660
insmod gzio
insmod ext2
insmod all_video
search --file --set=root /boot/vmlinuz

set default=0
set timeout=5
$(live_menu_entries)
EOF

echo "Running grub2-mkrescue..."
ISO_NAME="$PROFILE_ISO_PREFIX-$BRANCH-$ISO_VERSION-x86_64.iso"
STAGING_ISO="$BUILD_DIR/.staging-$ISO_NAME"
grub2-mkrescue -o "$STAGING_ISO" -volid "$PROFILE_ISO_LABEL" "$ISO_WORKDIR"

# VERIFIED ROOT CAUSE (2026-09-18, later session, see docs/phase4-findings.md
# "Secure Boot" section): grub2-mkrescue does NOT use our own
# $ISO_WORKDIR/EFI/efiboot.img (the signed shim/Ploader chain built above)
# for the actual El Torito UEFI boot catalog entry — it silently builds its
# own separate, freshly-generated (therefore unsigned) UEFI FAT image and
# points the boot catalog at THAT instead. Confirmed by extracting the real
# boot-catalog-referenced image (not the merely-present tree file) via its
# reported LBA/size and hashing its BOOTX64.EFI: a different, unsigned,
# grub2-mkrescue-built GRUB, not our shim. This silently defeated Secure
# Boot (and may mean Ploader itself was never actually in the UEFI boot
# chain at all, only BIOS). Fixed by re-assembling the ISO with a direct
# xorriso invocation that explicitly points the UEFI El Torito entry at our
# own efiboot.img, reusing grub2-mkrescue's own (separately proven-reliable)
# BIOS El Torito image rather than hand-rolling that too — see the BIOS
# section's own comment above for why hand-rolling BIOS boot was abandoned.
if [ "$HAVE_UEFI" = "1" ]; then
    echo "Re-assembling ISO with explicit El Torito control (Secure Boot fix)..."
    # eltorito.img alone is only GRUB's minimal bootstrap core.img — it
    # then loads further modules (partition-map drivers, fonts, etc.)
    # from /boot/grub/i386-pc/*.mod at runtime. FOUND BY REAL BOOT TEST
    # (2026-09-18): extracting only eltorito.img and dropping the rest of
    # grub2-mkrescue's own /boot/grub tree produced an ISO that hit
    # `grub rescue>` immediately — "part_*.mod ... file not found" for
    # every partition module GRUB tried, because none of them existed on
    # the medium at all. Extract the WHOLE /boot/grub tree instead (our
    # own grub.cfg included — unchanged, since grub2-mkrescue only read
    # it as input) so nothing GRUB relies on at runtime goes missing.
    rm -rf "$ISO_WORKDIR/boot/grub"
    xorriso -indev "$STAGING_ISO" -osirrox on \
        -extract /boot/grub "$ISO_WORKDIR/boot/grub"
    xorriso -as mkisofs \
        -iso-level 3 -full-iso9660-filenames \
        -volid "$PROFILE_ISO_LABEL" \
        -eltorito-boot boot/grub/i386-pc/eltorito.img \
            -no-emul-boot -boot-load-size 4 -boot-info-table --grub2-boot-info \
        -eltorito-alt-boot \
        -e EFI/efiboot.img -no-emul-boot \
        -isohybrid-gpt-basdat \
        --grub2-mbr /usr/lib/grub/i386-pc/boot_hybrid.img \
        -output "$BUILD_DIR/$ISO_NAME" \
        "$ISO_WORKDIR"
    rm -f "$STAGING_ISO"
else
    mv "$STAGING_ISO" "$BUILD_DIR/$ISO_NAME"
fi

sha256sum "$BUILD_DIR/$ISO_NAME" > "$BUILD_DIR/$ISO_NAME.sha256"

echo "=== Done: $BUILD_DIR/$ISO_NAME ==="
