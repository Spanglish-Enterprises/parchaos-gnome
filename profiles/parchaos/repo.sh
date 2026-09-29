# ==============================================================================
# parchaos profile — repository setup (sourced by engine/build-iso.sh)
# ==============================================================================
# Defines profile_setup_repo() / profile_teardown_repo(). Skipped entirely
# by --skip-branding (used for the unbranded-baseline checkpoint).
#
# Release images use only Fedora's repositories, Cisco's openh264 repo
# (enabled by fedora-release; the image itself ships the noopenh264 stub)
# and ParchaOS's COPR. RPM Fusion is only enabled for --nvidia builds,
# which are for private use and never released (scripts/check-image.sh
# rejects any RPM Fusion package).
# ==============================================================================

PROFILE_COPR="alexgalicea/parchaos-gnome"

profile_setup_repo() {
    if [ "${NVIDIA:-0}" -eq 1 ]; then
        echo "--- Enabling RPM Fusion (free + nonfree) for the NVIDIA build ---"
        run_in_target dnf -y install \
            "https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-$BRANCH.noarch.rpm" \
            "https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-$BRANCH.noarch.rpm"
    fi

    echo "--- Enabling ParchaOS GNOME COPR ($PROFILE_COPR) ---"
    run_in_target dnf -y install dnf5-plugins
    # Name the COPR chroot explicitly. The image carries the generic Remix
    # os-release, so dnf's own guess is generic-$BRANCH-x86_64, which the
    # project does not have ("Chroot not found in the given Copr project").
    # Found by the first real build of ticket #68.
    if ! run_in_target dnf copr enable -y "$PROFILE_COPR" "fedora-$BRANCH-x86_64"; then
        echo "WARNING: could not enable COPR $PROFILE_COPR — has it been" >&2
        echo "         created yet? (copr-cli create $PROFILE_COPR --chroot" >&2
        echo "         fedora-44-x86_64). Use --local with hand-built RPMs" >&2
        echo "         in build/local-rpms/ as a fallback." >&2
    fi

    # Something in the base pulls in fedora-logos as the default provider of
    # system-logos (nothing else provides it now that generic-logos is not in
    # packages.list). Installing parchaos-logos over it fails on file
    # conflicts, and that install runs before customize.sh's own swap.
    # Swap here, in one transaction, as soon as the COPR that carries
    # parchaos-logos is enabled. Found by the first real build of #68.
    if run_in_target rpm -q fedora-logos >/dev/null 2>&1; then
        echo "--- Swapping fedora-logos for parchaos-logos ---"
        run_in_target dnf -y swap fedora-logos parchaos-logos
    fi
}

profile_teardown_repo() {
    :
}
