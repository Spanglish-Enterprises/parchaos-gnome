# ==============================================================================
# GNOME Overview UI tuning -- hides the search box until typing starts,
# restores wallpaper on workspace thumbnails (stock GNOME shows plain
# gray), bigger thumbnails, Firefox picture-in-picture shown in the
# overview. Part of the same extension-polish pass as
# parcha-dock/blur-my-shell/etc.
#
# Real, independently-maintained third-party extension
# (axxapy/gnome-ui-tune) -- confirmed via its own metadata.json that this
# is genuinely the same extension Pulsar OS's config references
# (UUID gnome-ui-tune@itstime.tech matches exactly), not a same-named
# but different project. Real LICENSE file (GPL-3.0) confirmed via
# GitHub API before packaging.
#
# Not a flat copy like the other three extensions in this pass -- this
# one's extension.js imports from a real src/ subdirectory
# (src/modsList.js etc., confirmed by reading extension.js directly, not
# assumed from the file listing alone), so that whole directory needs
# shipping too. The upstream Makefile's own `schemas` target is just
# `glib-compile-schemas ./schemas/` -- same mechanism used everywhere
# else in this pass, done directly in %install rather than invoking make.
# Translations (locale/) deliberately not shipped -- cosmetic-only,
# same "ship over fidelity" call already made for
# parchaos-notification-position.
#
# metadata.json declares shell-version ["50"] only -- an exact match for
# this profile's real GNOME Shell 50.5, no version-validation workaround
# needed for this one specifically.
# ==============================================================================

Name:           parchaos-ui-tune
Version:        1.0.0
Release:        2%{?dist}
Summary:        GNOME Overview UI tuning (wallpaper-on-thumbnails, hide-search-until-typing, PIP in overview)

License:        GPL-3.0-only
URL:            https://github.com/axxapy/gnome-ui-tune
%global commit  c288f0ba1e5885358cf902f1566ff129a5cb882a
%global shortcommit %(c=%{commit}; echo ${c:0:7})
Source0:        %{url}/archive/%{commit}/gnome-ui-tune-%{shortcommit}.tar.gz

BuildArch:      noarch
BuildRequires:  glib2

Requires:       gnome-shell >= 45
Requires:       dconf

%description
Tunes the GNOME Overview: the search box stays hidden until you start
typing, workspace thumbnails show the wallpaper and are larger, and
Firefox picture-in-picture appears in the overview. Wraps a real,
independently maintained GNOME Shell extension.

%prep
%autosetup -n gnome-ui-tune-%{commit}

%build

%install
UUID=gnome-ui-tune@itstime.tech
DEST=%{buildroot}%{_datadir}/gnome-shell/extensions/$UUID
mkdir -p "$DEST/schemas" "$DEST/src"
install -m 0644 extension.js prefs.js metadata.json "$DEST/"
install -m 0644 src/*.js "$DEST/src/"
install -m 0644 schemas/*.gschema.xml "$DEST/schemas/"
glib-compile-schemas "$DEST/schemas"

%files
%license LICENSE
%doc README.md
%{_datadir}/gnome-shell/extensions/gnome-ui-tune@itstime.tech/

%changelog
* Mon Sep 28 2026 ParchaOS packaging - 1.0.0-2
- Rewrote %description to be user-facing and neutral (ticket
  #105): dropped internal build-diligence notes and lineage
  wording toward other distributions. Upstream project credit
  (authors, licenses) is kept.
* Thu Sep 24 2026 ParchaOS packaging - 1.0.0-1
- Initial package, part of the extension-polish gap-closing pass. Real
  upstream, real GPL-3.0 LICENSE confirmed before packaging, UUID
  cross-checked against Pulsar OS's own config to make sure this is
  genuinely the same extension and not a same-named different project.
