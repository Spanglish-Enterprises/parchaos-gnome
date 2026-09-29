# ==============================================================================
# Desktop Icons NG (DING) -- real icons on the desktop background, one
# of the GNOME Shell extensions Pulsar OS's own real config enables
# (ding@rastersoft.com) that this profile didn't ship yet (see
# the project's development notes extension-polish pass). Real,
# GPL-3.0-licensed (confirmed via a real COPYING file in the GitLab
# repo tree, not just a license= field claim -- same diligence used
# for everything Pulsar-adjacent in this project) upstream, maintained
# directly by a GNOME contributor (Sergio Costas / rastersoft), not
# Inled -- not affected by any of the licensing gaps found elsewhere
# in this project's audit.
#
# Unlike parchaos-hanabi (packaged the same night), this needed no
# prebuild-on-a-network-connected-host workaround -- confirmed by
# reading the real meson.build/app/meson.build/po/meson.build directly
# before writing this: everything here is plain JavaScript (both the
# extension.js side and the separate app/ process DING spawns to
# actually render icons), no TypeScript/npm/esbuild toolchain at all.
# A completely normal `%%meson`/`%%meson_build`/`%%meson_install` package.
#
# One real thing deliberately dropped: apparmor/meson.build installs an
# AppArmor profile to /etc/apparmor.d/ whenever the install prefix
# starts with /usr (true for this build) -- Fedora doesn't use AppArmor
# (SELinux is Fedora's LSM), so that file would just be permanently
# inert dead weight, not a real security control on this distro.
# Removed it in %%install rather than shipping a file that can never do
# anything here.
#
# UUID kept at upstream's own default (ding@rastersoft.com, matching
# Pulsar OS's real config exactly) -- no ParchaOS rebrand needed here,
# unlike parcha-dock/parchaos-global-menu, since "Desktop Icons NG"
# isn't an Apple-adjacent name needing the same trademark-caution
# treatment.
# ==============================================================================

Name:           parchaos-desktop-icons
Version:        50
Release:        4%{?dist}
Summary:        Desktop Icons NG (DING) -- real icons on the GNOME desktop background

License:        GPL-3.0-or-later
URL:            https://gitlab.com/rastersoft/desktop-icons-ng
%global commit  ec2800c8f9d987d8ce2a7a6bd21d283da4e3b270
%global shortcommit %(c=%{commit}; echo ${c:0:7})
Source0:        %{url}/-/archive/%{commit}/desktop-icons-ng-%{commit}.tar.gz
# ParchaOS (ticket #127): a "Snap icons to the grid" setting, off by default.
# Off, an icon stays exactly where it is dropped; on, icons sit in grid cells
# as upstream does. New files and "Arrange Icons" still use the grid.
Patch0:         0001-snap-to-grid-setting.patch

BuildArch:      noarch
BuildRequires:  meson
BuildRequires:  ninja-build
BuildRequires:  python3
BuildRequires:  gettext
BuildRequires:  glib2

Requires:       gnome-shell >= 50
Requires:       dconf
# Real, hard, verified dependency -- confirmed by reading
# app/desktopManager.js directly (not assumed, after tonight's real
# pafari/epiphany-runtime five-bug saga from one unverified
# dependency): DING literally spawns `nautilus --version` at startup
# and shows a blocking "Nautilus File Manager not found... mandatory"
# error if that fails. This profile's real replacement,
# parchaos-finder, genuinely installs its binary at the literal path
# /usr/bin/nautilus (confirmed via that spec's own %%files, not just its
# Provides: nautilus tag) and is Epoch 0, matching stock nautilus's own
# Epoch 0 (confirmed via `dnf info` on real hardware) -- no repeat of
# the epoch-mismatch class of bug from tonight's pafari saga.
Requires:       nautilus

%description
Puts real files and folders on the desktop background: double-click to
open, drag to move, right-click for the usual file actions, and set
per-file permissions from the file's own properties. Wraps Desktop
Icons NG (ding@rastersoft.com), a real, actively-maintained GNOME
Shell extension (GPL-3.0), enabled by default on ParchaOS.

%prep
%autosetup -n desktop-icons-ng-%{commit} -p1

%build
%meson -Dextension_uuid=ding@rastersoft.com -Dextension_name="Desktop Icons NG (DING)"
%meson_build

%install
%meson_install
# See banner comment: AppArmor is not Fedora's LSM, this file can never
# do anything here.
rm -rf %{buildroot}%{_sysconfdir}/apparmor.d

%files
%license COPYING
%doc README.md
%{_datadir}/gnome-shell/extensions/ding@rastersoft.com/
%{_datadir}/glib-2.0/schemas/org.gnome.shell.extensions.ding.gschema.xml
%{_datadir}/locale/*/LC_MESSAGES/ding.mo

%post
glib-compile-schemas %{_datadir}/glib-2.0/schemas &>/dev/null || true

%posttrans
glib-compile-schemas %{_datadir}/glib-2.0/schemas &>/dev/null || true

%changelog
* Tue Sep 29 2026 ParchaOS packaging - 50-4
- Ticket #127: free placement of desktop icons. New gsettings key
  snap-to-grid (default false) and a switch in the preferences window. With
  it off, icons stay exactly where they are dropped and keep their position
  across restarts; with it on, behaviour is upstream's. Carried as
  0001-snap-to-grid-setting.patch.
* Mon Sep 28 2026 ParchaOS packaging - 50-3
- Rewrote %description to be user-facing and neutral (ticket
  #105): dropped internal build-diligence notes and lineage
  wording toward other distributions. Upstream project credit
  (authors, licenses) is kept.
* Fri Sep 25 2026 ParchaOS packaging - 50-2
- Reworded summary/description/comments to describe features instead of
  naming macOS, per the project's trademark-caution naming policy.
* Fri Sep 25 2026 ParchaOS packaging - 50-1
- Initial package. Real, licensed upstream (GPL-3.0, confirmed via a
  real COPYING file, not just a claim) closing one of the extension
  gaps found in the earlier Pulsar-config diff. See banner comment for
  the AppArmor-file drop and why no prebuild workaround was needed
  here.
