# ==============================================================================
# ParchaOS's cloud drives -- rclone-backed cloud storage mounting (Google
# Drive, OneDrive, or any of rclone's ~70 other backends) under
# ~/Cloud/<name>, via a per-account systemd user template unit.
#
# REWRITTEN FROM SCRATCH, 2026-09-25. The previous version of this
# package's script was a near-verbatim copy of Inled's real pulsar-cloud
# script (confirmed via a direct diff: 400 vs 399 lines, differences
# limited to the pulsar-cloud -> parchaos-cloud rename). That script's
# own PKGBUILD does carry an explicit, specific `license=(GPL-3.0-or-later)`
# SPDX declaration -- a real, meaningful grant on its own -- but relying
# on a bare PKGBUILD field with no LICENSE file behind it is weaker
# ground than independent code, especially once Inled's own general
# MIT-INLED default (and its non-compete/rights-retention terms) was
# read in full while auditing this project's other Inled-derived
# component (parchaos-global-menu, since rewritten for the same reason).
# Given how small and mechanical this script's job is, rewriting it
# clean was cheap insurance. See docs/cloud-rewrite-spec.md in the main
# repo for the feature spec this rewrite was written from -- not from
# reading Inled's script. The systemd-unit-via-rclone-mount pattern
# itself is rclone's own public, documented convention, not anyone's
# original expression.
#
# Kept from the previous version, since these are neutral, functional
# identifiers rather than creative expression and changing them would
# only break existing installs: the `parchaos-cloud@.service` systemd
# template unit name, the `~/Cloud/<name>` mount location, and the
# `parchaos-cloud choose` desktop-launcher entry point.
#
# Also kept: no real trademarked OneDrive/Google Drive logo files (only
# a generic, brand-neutral cloud glyph is shipped), and the real
# Activities-searchable "Add Cloud Account" .desktop launcher.
# ==============================================================================

Name:           parchaos-cloud
Version:        2.0.0
Release:        3%{?dist}
Summary:        ParchaOS's cloud drives -- rclone-backed cloud storage under ~/Cloud

License:        MIT
URL:            https://github.com/Spanglish-Enterprises/parchaos-gnome
Source0:        parchaos-cloud-files.tar.gz
BuildArch:      noarch

Requires:       rclone
Requires:       fuse3
Requires:       zenity
Requires:       gnome-terminal
Requires:       hicolor-icon-theme

%description
ParchaOS's cloud drives: mount Google Drive, OneDrive, or any of
rclone's other ~70 supported providers under ~/Cloud/<name>, via a
per-account systemd user unit. An original implementation -- see this
spec's own banner comment and docs/cloud-rewrite-spec.md in the main
repo for why and how.

%prep
%setup -q -c -n %{name}-%{version}

%build
# Nothing to compile: a shell script, a systemd unit template, a
# .desktop file, and two icons.

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
%{_datadir}/icons/hicolor/scalable/apps/parchaos-cloud.svg

%changelog
* Sat Sep 26 2026 ParchaOS packaging - 2.0.0-3
- Setup always opens rclone's wizard in a terminal (the graphical option
  never showed anything). Remote names are escaped for systemd and the
  mount unit runs no shell.
* Sat Sep 26 2026 ParchaOS packaging - 2.0.0-2
- Full-color app icon (the ParchaOS tile with a cloud and sync arrows);
  the launcher and dock showed the plain symbolic outline before.
* Fri Sep 25 2026 ParchaOS packaging - 2.0.0-1
- Rewritten from scratch as an original implementation, replacing the
  previous near-verbatim copy of Inled's pulsar-cloud script. See this
  spec's own banner comment and docs/cloud-rewrite-spec.md for the
  full reasoning. Same real external interface kept (systemd template
  unit name, ~/Cloud/<name> mount location, desktop-launcher entry
  point) so nothing that depends on this package needs to change.
  Version reset to 2.0.0 since this is a new, independent codebase.
* Wed Sep 23 2026 ParchaOS packaging - 1.0.0-1
- Initial package: pulsar-cloud rebranded parchaos-cloud, dropped the
  real trademarked OneDrive/Google Drive logo files (never actually
  referenced by the script itself -- only used as plain text menu
  labels), added a real .desktop launcher upstream doesn't ship. Not
  yet build-tested or wired into packages.sh.
