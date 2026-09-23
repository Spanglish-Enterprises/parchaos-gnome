# ==============================================================================
# pulsaros profile — branding/session customization (sourced by
# engine/build-iso.sh)
# ==============================================================================
# Defines profile_customize(), called by the engine in Phase 5.5, after
# PROFILE_REPO_PACKAGES are installed. Skipped entirely by --skip-branding
# (see engine/build-iso.sh) — used for the unbranded-baseline checkpoint,
# same methodology the pearos (KDE) profile used successfully in its own
# Phase 1. Kept deliberately minimal for now: only DE-agnostic identity +
# the one GNOME-specific piece needed for a passwordless live session to
# actually work (GDM autologin). Theme/branding wiring (GTK theme, GNOME
# Shell theme/extensions, Nautilus branding, etc.) gets added here once
# those pieces are actually ported — see profiles/pearos/customize.sh for
# the shape that'll eventually take.
# ==============================================================================

profile_customize() {
    # Same real bug class already found/fixed in the KDE profile: without
    # this, /etc/os-release stays untouched Fedora, which a real
    # install+reboot test found showing up verbatim in the installed
    # system's own GRUB boot menu (GRUB's BLS title generation reads
    # os-release's PRETTY_NAME).
    echo "--- Branding /etc/os-release as ParchaOS ---"
    sed -i \
        -e 's|^NAME=.*|NAME="ParchaOS"|' \
        -e 's|^PRETTY_NAME=.*|PRETTY_NAME="ParchaOS 44"|' \
        -e 's|^ID=.*|ID=parchaos|' \
        -e 's|^ANSI_COLOR=.*|ANSI_COLOR="0;38;2;93;0;147"|' \
        -e 's|^HOME_URL=.*|HOME_URL="https://github.com/alexgalicea/parchaos-gnome"|' \
        "$ROOTFS_TARGET/etc/os-release"
    grep -q '^ID_LIKE=' "$ROOTFS_TARGET/etc/os-release" || \
        echo 'ID_LIKE=fedora' >> "$ROOTFS_TARGET/etc/os-release"

    echo "--- Setting default hostname: parchaos ---"
    echo "parchaos" > "$ROOTFS_TARGET/etc/hostname"

    # NOTE: unlike an earlier draft of this file, deliberately NOT
    # hand-writing /etc/gdm/custom.conf's autologin section here. The
    # KDE (pearos) profile's own real bug/fix for this exact problem
    # (passwordless live-session login) was resolved entirely by setting
    # PROFILE_LIVESYS_SESSION correctly in profile.conf — livesys-scripts'
    # own sessions.d/livesys-{kde,gnome} hook is what actually writes the
    # display manager's autologin config at first boot, and the KDE
    # profile never needed to duplicate that by hand. Trusting the same
    # mechanism here (PROFILE_LIVESYS_SESSION="gnome") rather than
    # guessing at GDM's config format pre-emptively — verify via a real
    # boot test before adding anything manual here, per this project's
    # own established pattern of not assuming a fix works without
    # checking.

    # Enabling ParchaOS's GNOME Shell extensions by default. GNOME Shell
    # extensions are inert until listed in org.gnome.shell's
    # "enabled-extensions" gsettings key — real, standard Fedora/GNOME
    # system-wide-default mechanism (GNOME's own admin documentation,
    # not guessed): a dconf "system" database compiled from
    # /etc/dconf/db/local.d/*, layered under the user's own db via
    # /etc/dconf/profile/user, compiled with `dconf update`. Extensions
    # list starts with just Parcha Dock (packages.sh) — more UUIDs get
    # appended here as more GNOME Shell extensions are ported (blur,
    # global menu, etc.), matching the KDE profile's own pattern of
    # growing customize.sh alongside packages.sh.
    echo "--- Enabling ParchaOS's GNOME Shell extensions by default ---"
    mkdir -p "$ROOTFS_TARGET/etc/dconf/profile"
    cat > "$ROOTFS_TARGET/etc/dconf/profile/user" <<EOF
user-db:user
system-db:local
EOF
    mkdir -p "$ROOTFS_TARGET/etc/dconf/db/local.d"
    # user-theme@gnome-shell-extensions.gcampax.github.com is the real,
    # stock Fedora extension (gnome-shell-extension-user-theme package,
    # UUID confirmed via its own installed metadata.json on the build VM, not
    # assumed) -- GNOME Shell itself only reads the Shell theme's own
    # gnome-shell/ subdirectory through this extension; GTK apps read
    # gtk-theme directly and don't need it.
    cat > "$ROOTFS_TARGET/etc/dconf/db/local.d/00-parchaos-extensions" <<EOF
[org/gnome/shell]
enabled-extensions=['parcha-dock@parchaos.org', 'parchaos-global-menu@parchaos.org', 'user-theme@gnome-shell-extensions.gcampax.github.com']
disable-user-extensions=false
EOF
    # ParchaOS's Tahoe-styled theme (packaging/parchaos-gtk-theme/),
    # installed as /usr/share/themes/MacTahoe-Dark -- confirmed via
    # `rpm -qlp` on the real built RPM, not assumed. Icon theme gets
    # added here once parchaos-icon-theme's own build succeeds.
    cat > "$ROOTFS_TARGET/etc/dconf/db/local.d/01-parchaos-theme" <<EOF
[org/gnome/desktop/interface]
gtk-theme='MacTahoe-Dark'

[org/gnome/desktop/wm/preferences]
theme='MacTahoe-Dark'

[org/gnome/shell/extensions/user-theme]
name='MacTahoe-Dark'
EOF
    run_in_target dconf update

    # Flathub remote (system-wide), same as the KDE profile — deliberately
    # does NOT pre-install any Flatpak app during the build to keep the
    # build itself fast; GNOME Software (already installed, native
    # Flatpak support) can install/update from this remote once booted.
    echo "--- Adding the Flathub remote ---"
    run_in_target flatpak remote-add --system --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo

    echo "--- Syncing Flatpak appstream metadata ---"
    run_in_target flatpak update --system --appstream || true
}
