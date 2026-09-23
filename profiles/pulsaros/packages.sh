# ==============================================================================
# pulsaros profile — package groupings (sourced by engine/build-iso.sh)
# ==============================================================================
# Installed in Phase 5, against the repo set up by profile_setup_repo()
# in repo.sh (this profile's own COPR + RPM Fusion).
# ==============================================================================

PROFILE_REPO_PACKAGES=(
    # Parcher — ParchaOS's build of Pulsar OS's real, working macOS-styled
    # fork of GNOME Files/Nautilus (packaging/parchaos-finder/). Real
    # traffic-light window controls, live folder color tagging, cloud
    # drive sidebar integration. Renamed from upstream's "Files"/Pulsar
    # OS's own "Finder" branding to avoid Apple trademark exposure ahead
    # of a planned public release (see the spec's own banner comment).
    # Obsoletes/Conflicts/Provides stock nautilus directly (not listed in
    # packages.list's base set) -- a real drop-in replacement, same as
    # the actual Pulsar OS package itself.
    parchaos-finder

    # Parcha Dock — ParchaOS's rebrand of Pulsar OS's real fork of the
    # well-known Dash-to-Dock GNOME Shell extension (macOS-style hover
    # magnification, launch bounce, downloads-folder stack, live
    # minimized-window previews). Enabled by default via customize.sh's
    # dconf override (GNOME Shell extensions are inert until listed in
    # org.gnome.shell's enabled-extensions key).
    parchaos-dock

    # Parcha Menu — ParchaOS's rebrand of Pulsar OS's real in-house
    # macOS-style global menu GNOME Shell extension. Deliberately
    # scoped to exclude upstream's setuid-root lock-screen auth helper
    # and GRUB/hibernation postinst mutations -- see the spec's own
    # banner comment. Enabled by default via customize.sh.
    parchaos-global-menu

    # ParchaOS's Tahoe-styled GTK3/GTK4 + GNOME Shell theme
    # (packaging/parchaos-gtk-theme/), real upstream vinceliuice
    # MacTahoe-gtk-theme (MIT), dark variant. Installs as
    # /usr/share/themes/MacTahoe-Dark. Applied by default via
    # customize.sh's dconf override -- GTK apps read
    # org.gnome.desktop.interface gtk-theme directly, but GNOME Shell
    # itself needs the user-theme extension (below) to pick up its own
    # gnome-shell/ subdirectory.
    parchaos-gtk-theme

    # ParchaOS's Tahoe-styled icon theme (packaging/parchaos-icon-theme/),
    # real upstream vinceliuice MacTahoe-icon-theme (GPL-3.0). Installs
    # three real variants (MacTahoe, MacTahoe-light, MacTahoe-dark --
    # confirmed via rpm -qlp on the built RPM); MacTahoe-dark is applied
    # by default via customize.sh to pair with the dark GTK theme.
    parchaos-icon-theme

    # ParchaOS's own real branding for the Calamares installer --
    # passion-fruit logo/icon/welcome/slideshow images (derived from
    # branding/logo/), install-sequence module config, and the three
    # real BIOS-boot/kernel/EFI install-time fixes ported wholesale
    # from the KDE (pearos) variant's own pearos-calamares-config
    # (100% DE-agnostic content, found via that variant's own real
    # end-to-end install+reboot tests -- see the spec's own banner
    # comment). Without this, Calamares would install and boot fine
    # but show generic/no branding and lack those fixes.
    parchaos-gnome-calamares-config

    # ParchaOS's own boot splash (packaging/parchaos-gnome-plymouth-theme/),
    # Plymouth's stock two-step module with a dark background matching
    # the GTK theme and ParchaOS's real logo as the watermark. Applied
    # as the live session's default via customize.sh (the live ISO
    # ships plymouth-theme-spinner in packages.list as a fallback/base
    # dependency; this overrides it) and by Calamares'
    # parchaos-finalize-install script for installed systems.
    parchaos-gnome-plymouth-theme

    # ParchaOS's default desktop wallpaper
    # (packaging/parchaos-gnome-wallpaper/) -- a dark gradient with the
    # real logo as a subtle centered watermark, installed to
    # /usr/share/backgrounds/parchaos/ and applied by default via
    # customize.sh's dconf override.
    parchaos-gnome-wallpaper

    # ParchaOS's macOS-style keyboard remap (packaging/parchaos-macos-remap/)
    # -- swaps Cmd<->Ctrl and layers on macOS keyboard conventions
    # (Cmd-Left/Right as Home/End, Cmd-C/V/T/N/W/Q/F in the terminal,
    # Parcher's Cmd-based file shortcuts, Cmd-Tab app switching) via
    # xremap + its companion GNOME Shell extension, repackaged from
    # Pulsar OS's gnome-macos-remap-wayland as a real declarative RPM
    # (systemd user-preset, udev uaccess, dconf db) instead of an
    # interactive per-user install script -- see the spec's own banner
    # comment. The xremap@k0kubun.com extension it ships is enabled by
    # default via customize.sh.
    parchaos-macos-remap

    # ParchaOS's cloud drives (packaging/parchaos-cloud/) -- rclone-backed
    # cloud storage (Google Drive, OneDrive, iCloud, or any other rclone
    # backend) mounted under ~/Cloud/<name> via a per-account systemd
    # user unit, plus a real Activities-searchable "Add Cloud Account"
    # launcher. Real Pulsar OS original work (GPL-3.0-or-later),
    # rebranded and repackaged -- see the spec's own banner comment for
    # why the upstream package's OneDrive/Google Drive logo files were
    # deliberately dropped (real trademarks, never actually used by the
    # script itself).
    parchaos-cloud
)

# Pulled in only with --nvidia, from RPM Fusion nonfree (enabled
# unconditionally by profile_setup_repo() in repo.sh).
PROFILE_NVIDIA_PACKAGES=(
    akmod-nvidia
    xorg-x11-drv-nvidia-cuda
    xorg-x11-drv-nvidia-power
)
