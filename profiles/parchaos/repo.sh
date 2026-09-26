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
