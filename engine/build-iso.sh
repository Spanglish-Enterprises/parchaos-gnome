#!/usr/bin/env bash
# ==============================================================================
# plumOS build engine — generic, profile-driven Fedora live-ISO builder.
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
PROFILE="pearos"
BRANCH="42"          # a Fedora release number ("42", "41", ...) or "rawhide"
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

  --profile <name>     Profile under profiles/ to build (default: $PROFILE)
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

if [ "$(id -u)" -ne 0 ]; then
    echo "Re-executing under sudo (dnf --installroot and chroot need root)..."
    exec sudo -E "$0" "$@"
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

: "${PROFILE_DISPLAY_NAME:?profile.conf must set PROFILE_DISPLAY_NAME}"
: "${PROFILE_SLUG:?profile.conf must set PROFILE_SLUG}"
: "${PROFILE_ISO_LABEL:?profile.conf must set PROFILE_ISO_LABEL}"
: "${PROFILE_SESSION:=wayland}"   # "wayland" or "x11" — see docs/phase0-findings.md

BUILD_DIR="$REPO_ROOT/build"
BASE_CACHE="$BUILD_DIR/base-cache-$BRANCH"
ROOTFS_TARGET="$BUILD_DIR/rootfs-$PROFILE-$BRANCH"
ISO_WORKDIR="$BUILD_DIR/iso-$PROFILE-$BRANCH"
mkdir -p "$BUILD_DIR"

echo "=== plumOS build: profile=$PROFILE branch=$BRANCH nvidia=$NVIDIA local=$LOCAL ==="

# ---- Phase 2: base cache (dnf --installroot bootstrap) ------------------------
# Mirrors the Debian engine's mmdebstrap step: a minimal Fedora rootfs shared
# across builds of the same branch, rebuilt only when packages.list changes
# or --clean-base is passed.
PKGLIST_HASH="$(sha256sum "$PROFILE_DIR/packages.list" | cut -d' ' -f1)"
BASE_MARKER="$BASE_CACHE/.plumos-base-hash"

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
        run_in_target dnf -y --setopt=install_weak_deps=False install "${PROFILE_REPO_PACKAGES[@]}"
    fi

    profile_teardown_repo

    # ---- Phase 5.5: branding / customization ---------------------------------------
    echo "--- Applying profile branding/customization ---"
    profile_customize   # defined in profiles/$PROFILE/customize.sh
fi

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
run_in_target dracut --force "/boot/initramfs-$KERNEL_VER.img" "$KERNEL_VER"

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
HAVE_UEFI=0
if [ -f "$PROFILE_DIR/ploader/ploader_x64.efi" ]; then
    HAVE_UEFI=1
    echo "Building UEFI boot image (Ploader)..."
    mkdir -p "$ISO_WORKDIR/EFI/BOOT"
    EFIBOOT_IMG="$ISO_WORKDIR/EFI/efiboot.img"
    dd if=/dev/zero of="$EFIBOOT_IMG" bs=1M count=16
    mkfs.vfat "$EFIBOOT_IMG"
    mmd -i "$EFIBOOT_IMG" ::/EFI ::/EFI/BOOT
    mcopy -i "$EFIBOOT_IMG" "$PROFILE_DIR/ploader/ploader_x64.efi" ::/EFI/BOOT/BOOTX64.EFI
    if [ -d "$PROFILE_DIR/ploader/theme" ]; then
        mcopy -i "$EFIBOOT_IMG" -s "$PROFILE_DIR/ploader/theme" ::/EFI/BOOT/theme
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
# via ($root)/... . Doing the same here (untested until the next real
# boot attempt lands in docs/phase1-findings.md). Also switched
# root=live:LABEL= to root=live:CDLABEL=, matching Fedora's exact
# dracut-live invocation for optical media.
echo "Writing grub.cfg for grub2-mkrescue ---"
mkdir -p "$ISO_WORKDIR/boot/grub"
cat > "$ISO_WORKDIR/boot/grub/grub.cfg" <<EOF
# Inspired by the config used for lorax-built live media
insmod iso9660
insmod gzio
insmod ext2
search --file --set=root /boot/vmlinuz

set default=0
set timeout=5
menuentry "$PROFILE_DISPLAY_NAME" {
    linux (\$root)/boot/vmlinuz root=live:CDLABEL=$PROFILE_ISO_LABEL rd.live.image quiet
    initrd (\$root)/boot/initramfs.img
}
EOF

echo "Running grub2-mkrescue..."
ISO_NAME="$PROFILE_ISO_PREFIX-$BRANCH-$ISO_VERSION-x86_64.iso"
grub2-mkrescue -o "$BUILD_DIR/$ISO_NAME" -volid "$PROFILE_ISO_LABEL" "$ISO_WORKDIR"

sha256sum "$BUILD_DIR/$ISO_NAME" > "$BUILD_DIR/$ISO_NAME.sha256"

echo "=== Done: $BUILD_DIR/$ISO_NAME ==="
