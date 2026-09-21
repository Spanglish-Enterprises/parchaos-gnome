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
sed -i 's/^livesys_session=.*/livesys_session="kde"/' "$ROOTFS_TARGET/etc/sysconfig/livesys"

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
    dd if=/dev/zero of="$EFIBOOT_IMG" bs=1M count=16
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
    MOK_KEY="${PLOADER_MOK_KEY:-$HOME/pearos-mok/pearos-mok.key}"
    MOK_CERT="${PLOADER_MOK_CERT:-$HOME/pearos-mok/pearos-mok.crt}"
    SIGNED_PLOADER="$SECUREBOOT_DIR/ploader_x64_signed.efi"
    if command -v sbsign >/dev/null 2>&1 && [ -f "$MOK_KEY" ] && [ -f "$MOK_CERT" ]; then
        echo "MOK signing key found ($MOK_KEY) — re-signing Ploader fresh for this build."
        SIGNED_PLOADER="$ISO_WORKDIR/ploader_x64_signed.efi"
        sbsign --key "$MOK_KEY" --cert "$MOK_CERT" --output "$SIGNED_PLOADER" \
            "$PROFILE_DIR/ploader/ploader_x64.efi"
    fi
    if [ -f "$SECUREBOOT_DIR/shimx64.efi" ] && [ -f "$SECUREBOOT_DIR/mmx64.efi" ] \
       && [ -f "$SIGNED_PLOADER" ] && [ -f "$SECUREBOOT_DIR/pearos-mok.cer" ]; then
        echo "Secure Boot signing artifacts found — chaining shim -> signed Ploader."
        mcopy -i "$EFIBOOT_IMG" "$SECUREBOOT_DIR/shimx64.efi" ::/EFI/BOOT/BOOTX64.EFI
        mcopy -i "$EFIBOOT_IMG" "$SECUREBOOT_DIR/mmx64.efi" ::/EFI/BOOT/mmx64.efi
        mcopy -i "$EFIBOOT_IMG" "$SIGNED_PLOADER" ::/EFI/BOOT/grubx64.efi
        if [ -f "$SECUREBOOT_DIR/fbx64.efi" ]; then
            mcopy -i "$EFIBOOT_IMG" "$SECUREBOOT_DIR/fbx64.efi" ::/EFI/BOOT/fbx64.efi
        fi
        mcopy -i "$EFIBOOT_IMG" "$SECUREBOOT_DIR/pearos-mok.cer" ::/EFI/BOOT/pearos-mok.cer
    else
        echo "WARNING: Secure Boot signing artifacts not found under $SECUREBOOT_DIR — shipping unsigned Ploader as BOOTX64.EFI. This boots fine with Secure Boot disabled but will be rejected with it enabled." >&2
        mcopy -i "$EFIBOOT_IMG" "$PROFILE_DIR/ploader/ploader_x64.efi" ::/EFI/BOOT/BOOTX64.EFI
    fi
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
menuentry "$PROFILE_DISPLAY_NAME" {
    set gfxpayload=keep
    linux (\$root)/boot/vmlinuz root=live:CDLABEL=$PROFILE_ISO_LABEL rd.live.image vga=791 console=tty0 console=ttyS0,115200n8
    initrd (\$root)/boot/initramfs.img
}
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
