# ==============================================================================
# Notification banner positioning -- a real GNOME Shell extension letting a
# user move where notification popups appear on screen (macOS shows them
# top-right, GNOME's own default is top-center; this is what closes that
# gap). Prioritized by real user request (2026-09-24) as part of the
# broader macOS-polish extension pass (see customize.sh's own comment for
# the other four added in that same pass).
#
# Real upstream picked with the same license diligence this project
# applies everywhere else (Sayri, pulsaros-timemachine, etc.): Pulsar OS's
# own real config uses `notification-position@drugo.dev`
# (brunodrugowick/notification-position-gnome-extension), but that repo's
# own GitHub API record confirms `license: null` -- no LICENSE file
# anywhere in its 28-file tree, none mentioned in its README either. Same
# blocker class as Sayri, not packaged. Checked two real forks instead:
# Ahmed-Sinkeat/Notification-position (MIT, but last pushed 2024-08, over
# a year stale) and marcinjakubowski/notification-position-reloaded
# (real GPL-2.0 LICENSE file confirmed present, actively maintained --
# last pushed 2025-12-08, its own metadata.json changelog notes real
# GNOME 45 compatibility work from a contributor). Picked the latter for
# both the real license and the more recent maintenance.
#
# Real compatibility gap found before packaging: this extension's
# metadata.json only declares shell-version support through 49, but this
# profile's real installed GNOME Shell is 50.5 (confirmed via
# `gnome-shell --version` on real hardware) -- it would silently refuse
# to load without disable-extension-version-validation=true. Pulsar OS's
# own real dconf defaults already set exactly this (confirmed via the
# same 00-pulsaros-theme fetch used for the button-layout/blur-my-shell
# fixes), so this profile's customize.sh now sets it too, not just for
# this one extension but as general hardening against the same class of
# gap for anything added later.
#
# No compiled build step needed -- unlike parcha-dock (SCSS/gettext),
# this extension is flat JS + a single gschema, confirmed via the real
# repo listing (extension.js, prefs.js, utils.js, metadata.json,
# schemas/*.gschema.xml, no Makefile at all). Only glib-compile-schemas
# is needed at package time, same real bug class already found and fixed
# for parcha-dock (Release 106-2) -- done correctly here from the start.
# ==============================================================================

Name:           parchaos-notification-position
Version:        1.0.0
Release:        1%{?dist}
Summary:        Notification banner position/animation customization for GNOME Shell

License:        GPL-2.0-only
URL:            https://github.com/marcinjakubowski/notification-position-reloaded
%global commit  fa8c23458e51a497b6caa3bd2cff3c45757ee01f
%global shortcommit %(c=%{commit}; echo ${c:0:7})
Source0:        %{url}/archive/%{commit}/notification-position-reloaded-%{shortcommit}.tar.gz

BuildArch:      noarch
BuildRequires:  glib2

Requires:       gnome-shell >= 45
Requires:       dconf

%description
A real GNOME Shell extension (GPL-2.0, marcinjakubowski's actively
maintained fork of brunodrugowick's original) letting the user
customize where notification banners appear on screen and how they
animate in -- the piece needed for ParchaOS's default top-right,
macOS-style notification position. See this spec's own banner comment
for the real license diligence and compatibility gap this was checked
against before packaging.

%prep
%autosetup -n notification-position-reloaded-%{commit}

%build

%install
UUID=notification-banner-reloaded@marcinjakubowski.github.com
DEST=%{buildroot}%{_datadir}/gnome-shell/extensions/$UUID
mkdir -p "$DEST/schemas"
install -m 0644 extension.js prefs.js utils.js metadata.json "$DEST/"
install -m 0644 schemas/*.gschema.xml "$DEST/schemas/"
glib-compile-schemas "$DEST/schemas"

%files
%license LICENSE
%doc README.md
%{_datadir}/gnome-shell/extensions/notification-banner-reloaded@marcinjakubowski.github.com/

%changelog
* Thu Sep 24 2026 ParchaOS packaging - 1.0.0-1
- Initial package. Real user request (priority: notification
  positioning). See banner comment for the license diligence that
  ruled out Pulsar OS's own upstream choice and the shell-version
  compatibility gap this was checked against.
