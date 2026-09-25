# ==============================================================================
# Wiggle -- magnifies the cursor when the mouse is moved rapidly ("shake
# to locate cursor", ported to GNOME). Part of the
# same extension-polish pass as parcha-dock/blur-my-shell/etc.
#
# Real, independently-maintained third-party extension (mechtifs/wiggle),
# not Inled's own original work -- real LICENSE.txt (GPL-2.0) confirmed
# via GitHub API before packaging, same diligence applied to every real
# port in this project.
#
# Flat JS extension, no compiled build step (extension.js, prefs.js,
# effect.js, cursor.js, history.js, const.js, metadata.json,
# schemas/*.gschema.xml, icons/cursor.svg -- confirmed via the real repo
# listing, no Makefile/meson.build). icons/cursor.svg IS a real runtime
# asset (the enlarged-cursor image the effect displays), unlike
# parchaos-magic-lamp-effect's assets/ dir which was EGO promo material
# only -- checked which is which before deciding what to ship, not
# assumed either way.
#
# metadata.json's own shell-version list only goes to 48, not this
# profile's real GNOME Shell 50.5 -- relies on customize.sh's
# disable-extension-version-validation=true (already set globally for
# parchaos-notification-position's own compatibility gap).
# ==============================================================================

Name:           parchaos-wiggle
Version:        5
Release:        2%{?dist}
Summary:        Cursor-magnification-on-shake GNOME Shell extension ("shake to locate cursor")

License:        GPL-2.0-only
URL:            https://github.com/mechtifs/wiggle
%global commit  db1bec361d292ae0c465eca25db4854e422ad5e4
%global shortcommit %(c=%{commit}; echo ${c:0:7})
Source0:        %{url}/archive/%{commit}/wiggle-%{shortcommit}.tar.gz

BuildArch:      noarch
BuildRequires:  glib2

Requires:       gnome-shell >= 45
Requires:       dconf

%description
A real, independently-maintained (not Inled-original) GNOME Shell
extension that magnifies the mouse cursor when shaken/moved rapidly --
"shake to locate cursor". Same real
upstream Pulsar OS's own config uses. See this spec's own banner
comment for the license diligence and the compatibility gap it relies
on customize.sh to work around.

%prep
%autosetup -n wiggle-%{commit}

%build

%install
UUID=wiggle@mechtifs
DEST=%{buildroot}%{_datadir}/gnome-shell/extensions/$UUID
mkdir -p "$DEST/schemas" "$DEST/icons"
install -m 0644 extension.js prefs.js effect.js cursor.js history.js const.js metadata.json "$DEST/"
install -m 0644 schemas/*.gschema.xml "$DEST/schemas/"
install -m 0644 icons/cursor.svg "$DEST/icons/"
glib-compile-schemas "$DEST/schemas"

%files
%license LICENSE.txt
%doc README.md
%{_datadir}/gnome-shell/extensions/wiggle@mechtifs/

%changelog
* Fri Sep 25 2026 ParchaOS packaging - 5-2
- Reworded summary/description/comments to describe features instead of
  naming macOS, per the project's trademark-caution naming policy.
* Thu Sep 24 2026 ParchaOS packaging - 5-1
- Initial package, part of the extension-polish gap-closing pass. Real
  upstream, real GPL-2.0 LICENSE.txt confirmed before packaging.
