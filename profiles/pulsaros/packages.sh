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
)

# Pulled in only with --nvidia, from RPM Fusion nonfree (enabled
# unconditionally by profile_setup_repo() in repo.sh).
PROFILE_NVIDIA_PACKAGES=(
    akmod-nvidia
    xorg-x11-drv-nvidia-cuda
    xorg-x11-drv-nvidia-power
)
