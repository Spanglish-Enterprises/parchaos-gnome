# ==============================================================================
# ParchaOS (GNOME) desktop meta-package -- exists for exactly one reason:
# real end-user feedback (2026-09-23) that `dnf update` alone does NOT
# pick up packages added to this profile after a user's already installed
# it. That's correct, standard dnf behavior -- `update`/`upgrade` only
# touches packages already installed; it never installs something new
# just because it now exists in an enabled repo. This project's own ISO
# build (engine/build-iso.sh Phase 5) installs every
# profiles/pulsaros/packages.sh entry as an individually, directly
# requested package -- there was no single thing tying them together
# that a later `dnf update` could expand.
#
# The fix is the standard RPM/dnf pattern for exactly this problem (the
# same shape as Debian/Ubuntu's `ubuntu-desktop`, or Fedora's own
# `@workstation-product-environment` comps group, just done as a plain
# meta-package instead of a comps group since this project's engine
# doesn't have comps.xml infrastructure and retrofitting one is a much
# bigger change than this deserves): a package with no real content of
# its own, just a `Requires:` line naming every package this profile
# ships. Once THIS package is installed on a real system, bumping its
# Release with an EXPANDED Requires: list (whenever a new package gets
# added to packages.sh) means a plain `sudo dnf update` on that real
# system will pull the new dependency in automatically as part of the
# same transaction that upgrades this package -- genuine "OTA blanket
# update" behavior, no manual `dnf install <new-package-name>` needed
# going forward.
#
# MAINTENANCE: whenever profiles/pulsaros/packages.sh gains or loses an
# entry, update the Requires: list below to match and bump Release. The
# two lists are NOT auto-generated from each other (deliberately kept
# simple rather than adding build-pipeline machinery for this) -- it's
# on whoever edits packages.sh to keep this spec in sync, same as any
# other two-places-must-agree convention already in this project (e.g.
# a package's %files list vs. what it actually installs).
#
# Deliberately excludes PROFILE_NVIDIA_PACKAGES (akmod-nvidia and
# friends) -- those are opt-in via --nvidia at build time for a real
# hardware-dependent reason (no point requiring NVIDIA kernel modules on
# a machine that doesn't have an NVIDIA GPU), not part of "the desktop".
# ==============================================================================

Name:           parchaos-desktop
Version:        2026.09.23
Release:        1%{?dist}
Summary:        ParchaOS (GNOME) desktop meta-package -- installing/updating this pulls in the full profile

License:        NOASSERTION
URL:            https://github.com/alexgalicea/parchaos-gnome
BuildArch:      noarch

Requires:       parchaos-finder
Requires:       parchaos-dock
Requires:       parchaos-global-menu
Requires:       parchaos-gtk-theme
Requires:       parchaos-icon-theme
Requires:       parchaos-gnome-calamares-config
Requires:       parchaos-gnome-plymouth-theme
Requires:       parchaos-gnome-wallpaper
Requires:       parchaos-macos-remap
Requires:       parchaos-cloud
Requires:       parchaos-focus-schedule
Requires:       parchaos-yin-yang
Requires:       parchaos-tmog
Requires:       pafari

%description
A real, no-content meta-package: installing it (or updating it) simply
pulls in every package this ParchaOS GNOME profile ships, via a plain
Requires: list kept in sync with profiles/pulsaros/packages.sh. Exists
so a plain `sudo dnf update` becomes a genuine "OTA" mechanism for this
project's own packages going forward -- without this, `dnf update`
never installs a package that's new since the user's own install, only
upgrades ones already present. See this spec's own banner comment for
the full reasoning and the maintenance rule (keep Requires: in sync
with packages.sh, bump Release on every change).

%prep
%build
%install
mkdir -p %{buildroot}

%files

%changelog
* Wed Sep 23 2026 ParchaOS packaging - 2026.09.23-1
- Initial package, in direct response to real user feedback that
  `dnf update` alone doesn't pick up newly-added ParchaOS packages.
  Requires: list matches profiles/pulsaros/packages.sh's
  PROFILE_REPO_PACKAGES as of this date (14 packages).
