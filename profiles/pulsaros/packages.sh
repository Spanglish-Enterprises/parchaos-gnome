# ==============================================================================
# pulsaros profile — package groupings (sourced by engine/build-iso.sh)
# ==============================================================================
# Installed in Phase 5, against the repo set up by profile_setup_repo()
# in repo.sh (this profile's own COPR + RPM Fusion). Empty for now —
# 2026-09-22, this profile has no ported packages yet. As real Pulsar OS
# components get ported (Nautilus/Finder fork first, per this repo's own
# README's priority order), add them here the same way the KDE (pearos)
# profile's own packages.sh does, with the same kind of explanatory
# comment per package (what it replaces, why, real bugs found while
# porting it).
# ==============================================================================

PROFILE_REPO_PACKAGES=(
)

# Pulled in only with --nvidia, from RPM Fusion nonfree (enabled
# unconditionally by profile_setup_repo() in repo.sh).
PROFILE_NVIDIA_PACKAGES=(
    akmod-nvidia
    xorg-x11-drv-nvidia-cuda
    xorg-x11-drv-nvidia-power
)
