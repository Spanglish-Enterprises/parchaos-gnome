# ==============================================================================
# pulsaros profile — repository setup (sourced by engine/build-iso.sh)
# ==============================================================================
# Defines profile_setup_repo() / profile_teardown_repo(). Skipped entirely
# by --skip-branding (used for the unbranded-baseline checkpoint).
#
# Separate COPR project from the KDE (pearos) profile's
# alexgalicea/parchaos — keeps GNOME-specific packages (ported Pulsar OS
# components) from mixing with the KDE-specific ones, same reasoning a
# second GitHub repo got created for the source. NOT YET CREATED as of
# 2026-09-22 — create via `copr-cli create alexgalicea/parchaos-gnome
# --chroot fedora-44-x86_64` before this profile can build with
# --skip-branding removed. Until then, always build with --skip-branding.
# ==============================================================================

PROFILE_COPR="alexgalicea/parchaos-gnome"

profile_setup_repo() {
    echo "--- Enabling RPM Fusion (free + nonfree) ---"
    run_in_target dnf -y install \
        "https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-$BRANCH.noarch.rpm" \
        "https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-$BRANCH.noarch.rpm"

    echo "--- Enabling ParchaOS GNOME COPR ($PROFILE_COPR) ---"
    run_in_target dnf -y install dnf5-plugins
    if ! run_in_target dnf copr enable -y "$PROFILE_COPR"; then
        echo "WARNING: could not enable COPR $PROFILE_COPR — has it been" >&2
        echo "         created yet? (copr-cli create $PROFILE_COPR --chroot" >&2
        echo "         fedora-44-x86_64). Use --local with hand-built RPMs" >&2
        echo "         in build/local-rpms/ as a fallback." >&2
    fi
}

profile_teardown_repo() {
    :
}
