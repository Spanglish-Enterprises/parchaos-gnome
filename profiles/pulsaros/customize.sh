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
    # parchaos-release (packages.sh) writes it at install and keeps it
    # across Fedora release-package updates; run it once more here so the
    # branding is in place however the package set was installed.
    echo "--- Branding /etc/os-release as ParchaOS ---"
    run_in_target /usr/libexec/parchaos-os-release

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
    # Real gap found 2026-09-24 (real user feedback: keep auditing the
    # theming): cross-checked this profile's extension list against
    # Pulsar OS's own real dconf defaults (Inled-Pulsar-OS/PKG's
    # pulsaros-gnome/etc/dconf/db/local.d/00-pulsaros-theme, fetched
    # directly) -- they ship ~15 extensions for their full desktop
    # polish; this profile only shipped 5. Four of Pulsar's real
    # extensions are, confirmed via `dnf list --available` on real
    # hardware, genuine official Fedora packages with the exact same
    # UUIDs Pulsar OS's own config uses (verified via each extension's
    # real installed metadata.json, not assumed):
    # appindicatorsupport@rgcjonas.gmail.com, blur-my-shell@aunetx,
    # just-perfection-desktop@just-perfection, no-overview@fthx. Added
    # all four (packages.list). The rest of Pulsar's list
    # (compiz-alike-magic-lamp-effect, notification-position, wiggle,
    # gnome-ui-tune, ding) has no Fedora package -- would need
    # individual packaging from extensions.gnome.org the way parcha-dock
    # was, not done in this pass.
    # The default enabled-extensions list (00-parchaos-extensions) now ships
    # in parchaos-desktop, so existing installs get changes over OTA too.
    # Theme (01-parchaos-theme) and extension tuning
    # (02-parchaos-extensions-tuning) defaults ship in parchaos-desktop
    # too, so changes reach existing installs over OTA.
    run_in_target dconf update

    # ParchaOS's own Plymouth boot splash (packages.list ships
    # plymouth-theme-spinner as the base/fallback theme; this makes our
    # own the live session's actual default). Must run before
    # engine/build-iso.sh's own dracut regeneration step (right after
    # this function returns) or the old theme stays baked into the
    # initramfs -- same ordering requirement as Calamares'
    # parchaos-finalize-install script uses for installed systems.
    echo "--- Setting ParchaOS's Plymouth theme as default ---"
    run_in_target plymouth-set-default-theme parcha-plymouth

    # Flathub is a static system remote shipped by parchaos-desktop
    # (/etc/flatpak/remotes.d); no Flatpak apps are pre-installed.

    echo "--- Syncing Flatpak appstream metadata ---"
    run_in_target flatpak update --system --appstream || true
}
