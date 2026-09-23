# ==============================================================================
# ParchaOS's cloud drives -- rclone-backed cloud storage mounting (Google
# Drive, OneDrive, iCloud, or any of rclone's ~70 other backends) under
# ~/Cloud/<name>, real Pulsar OS original work
# (Inled-Pulsar-OS/PKG/arch/pkgbuilds/pulsaros-cloud, GPL-3.0-or-later --
# explicit SPDX license in the real PKGBUILD, verified directly, not
# guessed), repackaged for Fedora. Unlike most of this project's other
# ports, the real upstream source here isn't a separate git repo -- the
# PKGBUILD's own `source=()` array lists plain sibling files checked
# directly into the monorepo (a shell script, a systemd user template
# unit, and icon assets), so this spec vendors them the same way rather
# than fetching a tarball.
#
# What changed from upstream, and why:
#   - Renamed pulsar-cloud -> parchaos-cloud (script, systemd template
#     unit name, .desktop) for this project's own product identity, same
#     rebrand pattern as every other Pulsar OS-derived package here
#     (parcha-dock, parchaos-global-menu, Parcher/parchaos-finder).
#   - Dropped the upstream package's onedrive.svg and google-drive.svg
#     icon files entirely -- real, literal Microsoft/Google trademarked
#     logos (confirmed by inspecting the actual SVG content: Google
#     Drive's exact four-color triangle mark, Microsoft's exact OneDrive
#     cloud gradient), not generic/stylized art. The real pulsar-cloud
#     script itself never references these files at all -- "Google
#     Drive"/"OneDrive" only ever appear as plain text menu labels in
#     the terminal wizard (cmd_add) -- so nothing is lost by not
#     shipping them, and it avoids real trademark exposure ahead of
#     this project's planned public release (the same standard already
#     applied rigorously to this project's own macOS/Apple branding
#     avoidance). Only the generic, brand-neutral cloud glyph
#     (pulsar-cloud-symbolic.svg, a plain Material-style cloud outline)
#     is kept.
#   - Added a real .desktop launcher (usr/share/applications/
#     parchaos-cloud.desktop, `Exec=parchaos-cloud choose`) so "Add
#     Cloud Account" is reachable from Activities search -- the upstream
#     package ships no .desktop of its own; its entry point was presumably
#     meant to be wired into Pulsar OS's own Finder sidebar via a
#     mechanism not found in the real pulsar-cloud script itself (no
#     org.freedesktop.CloudProviders D-Bus service is implemented here;
#     mounted remotes just appear under ~/Cloud as ordinary folders,
#     which Parcher (parchaos-finder, built with cloudproviders support)
#     shows like any other directory once mounted -- deeper sidebar
#     integration, if Pulsar OS's real Finder patches have any beyond
#     that, was not found and is not claimed here).
#   - No systemd user-preset: unlike parchaos-macos-remap, the
#     parchaos-cloud@.service template is deliberately NOT auto-enabled
#     for every user -- the script itself calls `systemctl --user enable
#     --now` only once a real account is actually configured
#     (activate_account), matching upstream's own on-demand activation
#     model exactly.
# ==============================================================================

Name:           parchaos-cloud
Version:        1.0.0
Release:        1%{?dist}
Summary:        ParchaOS's cloud drives -- rclone-backed cloud storage under ~/Cloud

License:        GPL-3.0-or-later
URL:            https://github.com/Inled-Pulsar-OS/PKG
Source0:        parchaos-cloud-files.tar.gz
BuildArch:      noarch

Requires:       rclone
Requires:       fuse3
Requires:       zenity
Requires:       gnome-terminal
Requires:       curl
Requires:       hicolor-icon-theme

%description
ParchaOS's cloud drives: mount Google Drive, OneDrive, iCloud, or any of
rclone's other ~70 supported providers under ~/Cloud/<name>, via a
per-account systemd user unit. Real Pulsar OS original work
(pulsaros-cloud, GPL-3.0-or-later), repackaged for Fedora with the
project's own branding and a real Activities-searchable "Add Cloud
Account" launcher.

%prep
%setup -q -c -n %{name}-%{version}

%build
# Nothing to compile: a shell script, a systemd unit template, a
# .desktop file, and one icon.

%install
mkdir -p %{buildroot}
cp -a usr %{buildroot}/
chmod 0755 %{buildroot}%{_bindir}/parchaos-cloud

%post
gtk-update-icon-cache -q -t -f %{_datadir}/icons/hicolor &>/dev/null || :
update-desktop-database -q %{_datadir}/applications &>/dev/null || :

%postun
gtk-update-icon-cache -q -t -f %{_datadir}/icons/hicolor &>/dev/null || :
update-desktop-database -q %{_datadir}/applications &>/dev/null || :

%files
%{_bindir}/parchaos-cloud
%{_prefix}/lib/systemd/user/parchaos-cloud@.service
%{_datadir}/applications/parchaos-cloud.desktop
%{_datadir}/icons/hicolor/symbolic/apps/parchaos-cloud-symbolic.svg

%changelog
* Wed Sep 23 2026 ParchaOS packaging - 1.0.0-1
- Initial package: pulsar-cloud rebranded parchaos-cloud, dropped the
  real trademarked OneDrive/Google Drive logo files (never actually
  referenced by the script itself -- only used as plain text menu
  labels), added a real .desktop launcher upstream doesn't ship. Not
  yet build-tested or wired into packages.sh.
