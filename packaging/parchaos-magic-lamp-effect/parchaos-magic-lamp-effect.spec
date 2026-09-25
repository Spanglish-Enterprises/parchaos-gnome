# ==============================================================================
# The "genie effect" -- windows suck into the dock on minimize. Part of the same extension-polish pass
# as parcha-dock/blur-my-shell/etc. (see customize.sh's own comment).
#
# Pulsar OS's own real config uses this exact same extension
# (compiz-alike-magic-lamp-effect@hermes83.github.com,
# hermes83/compiz-alike-magic-lamp-effect) -- a real, independently
# maintained third-party extension (not Inled's own original work), with
# a real LICENSE file confirmed via GitHub API (GPL-3.0), unlike the
# Inled-original pieces this project has found blocked elsewhere (Sayri,
# pulsaros-timemachine, etc.). No licensing concern here.
#
# Flat JS extension, no compiled build step -- confirmed via the real
# repo listing (extension.js, prefs.js, settings_data.js, metadata.json,
# schemas/*.gschema.xml, no Makefile/meson.build at all). Only
# glib-compile-schemas needed at package time, same as
# parchaos-notification-position. The repo's own assets/ dir
# (get-it-on-ego.png, screenshot.png) is EGO store promo material, not
# runtime assets -- confirmed by checking what extension.js actually
# references, deliberately not shipped.
#
# metadata.json's own shell-version list already includes "50" --
# unlike parchaos-notification-position, this one is natively compatible
# with this profile's real GNOME Shell 50.5 with no version-validation
# workaround needed (customize.sh's disable-extension-version-validation
# is still set globally for the other extensions that DO need it).
# ==============================================================================

Name:           parchaos-magic-lamp-effect
Version:        25
Release:        2%{?dist}
Summary:        Compiz-alike magic lamp (genie) minimize effect for GNOME Shell

License:        GPL-3.0-only
URL:            https://github.com/hermes83/compiz-alike-magic-lamp-effect
%global commit  eb2aff167146b0a9eca780ad0fe30eafaab3a26f
%global shortcommit %(c=%{commit}; echo ${c:0:7})
Source0:        %{url}/archive/%{commit}/compiz-alike-magic-lamp-effect-%{shortcommit}.tar.gz

BuildArch:      noarch
BuildRequires:  glib2

Requires:       gnome-shell >= 45
Requires:       dconf

%description
A real, independently-maintained (not Inled-original) GNOME Shell
extension: the classic Compiz "magic lamp" genie effect for minimizing
windows into the dock, the familiar genie-style minimize
animation. Same real upstream Pulsar OS's own config uses. See this
spec's own banner comment for the license diligence.

%prep
%autosetup -n compiz-alike-magic-lamp-effect-%{commit}

%build

%install
UUID=compiz-alike-magic-lamp-effect@hermes83.github.com
DEST=%{buildroot}%{_datadir}/gnome-shell/extensions/$UUID
mkdir -p "$DEST/schemas"
install -m 0644 extension.js prefs.js settings_data.js metadata.json "$DEST/"
install -m 0644 schemas/*.gschema.xml "$DEST/schemas/"
glib-compile-schemas "$DEST/schemas"

%files
%license LICENSE
%doc README.md
%{_datadir}/gnome-shell/extensions/compiz-alike-magic-lamp-effect@hermes83.github.com/

%changelog
* Fri Sep 25 2026 ParchaOS packaging - 25-2
- Reworded summary/description/comments to describe features instead of
  naming macOS, per the project's trademark-caution naming policy.
* Thu Sep 24 2026 ParchaOS packaging - 25-1
- Initial package, part of the extension-polish gap-closing pass. Real
  upstream, real GPL-3.0 LICENSE file confirmed before packaging.
