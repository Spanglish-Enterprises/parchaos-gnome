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
Release:        4%{?dist}
Summary:        Cursor-magnification-on-shake GNOME Shell extension ("shake to locate cursor")

# Wiggle itself is GPL-2.0-only; the two cursor images (Source1/2) are
# vinceliuice's MacTahoe cursors, GPL-3.0 (Source3), shipped as data.
License:        GPL-2.0-only AND GPL-3.0-or-later
URL:            https://github.com/mechtifs/wiggle
%global commit  db1bec361d292ae0c465eca25db4854e422ad5e4
%global shortcommit %(c=%{commit}; echo ${c:0:7})
Source0:        %{url}/archive/%{commit}/wiggle-%{shortcommit}.tar.gz
# GNOME 49+ removed Meta.CursorTracker.set_pointer_visible(), so hiding
# the real pointer threw mid-magnify and showing it threw mid-cleanup,
# stranding the big cursor on screen (user report: it stayed large after a
# quick movement). Also: unmagnify only cleaned up in onComplete, which an
# interrupted animation never reaches. Patch0 ports to
# inhibit/uninhibit_cursor_visibility(), cleans up in onStopped, orders
# magnify() so it can't be undone by a stopped shrink, and adds a watchdog.
Patch0:         0001-fix-stuck-magnified-cursor-on-gnome-50.patch
# Shaking drew Wiggle's own generic arrow, so the cursor visibly changed
# style while enlarged (user report). Patch1 picks icons/cursor-<cursor
# theme>.svg when present (checked on every shake, so it follows the
# light/dark switch); Source1/2 are MacTahoe's own dark/light arrows from
# the same upstream as parchaos-icon-theme's cursors (cursors/src/svg*/
# default.svg at the same pinned commit).
Patch1:         0002-match-enlarged-cursor-to-cursor-theme.patch
Source1:        cursor-MacTahoe-dark.svg
Source2:        cursor-MacTahoe.svg
Source3:        LICENSE-MacTahoe-cursors

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
%autosetup -p1 -n wiggle-%{commit}

%build

%install
UUID=wiggle@mechtifs
DEST=%{buildroot}%{_datadir}/gnome-shell/extensions/$UUID
mkdir -p "$DEST/schemas" "$DEST/icons"
install -m 0644 extension.js prefs.js effect.js cursor.js history.js const.js metadata.json "$DEST/"
install -m 0644 schemas/*.gschema.xml "$DEST/schemas/"
install -m 0644 icons/cursor.svg "$DEST/icons/"
install -m 0644 %{SOURCE1} %{SOURCE2} "$DEST/icons/"
install -Dm 0644 %{SOURCE3} %{buildroot}%{_licensedir}/%{name}/LICENSE-MacTahoe-cursors
glib-compile-schemas "$DEST/schemas"

%files
%license LICENSE.txt
%{_licensedir}/%{name}/LICENSE-MacTahoe-cursors
%doc README.md
%{_datadir}/gnome-shell/extensions/wiggle@mechtifs/

%changelog
* Fri Sep 25 2026 ParchaOS packaging - 5-4
- Shaking the cursor no longer swaps it for a different-looking arrow:
  the enlarged cursor uses MacTahoe's own dark/light arrow matching the
  active cursor theme (generic arrow for other themes).
* Fri Sep 25 2026 ParchaOS packaging - 5-3
- Fix the magnified cursor getting stuck on screen: port cursor hiding to
  GNOME 49+'s inhibit/uninhibit_cursor_visibility() (set_pointer_visible
  no longer exists and threw), clean up in onStopped, make re-magnify
  during a shrink safe, add a watchdog. Verified in an isolated headless
  gnome-shell with repeated shake/stop cycles: every cycle returns to
  normal and the real pointer is visible again.
* Fri Sep 25 2026 ParchaOS packaging - 5-2
- Reworded summary/description/comments to describe features instead of
  naming macOS, per the project's trademark-caution naming policy.
* Thu Sep 24 2026 ParchaOS packaging - 5-1
- Initial package, part of the extension-polish gap-closing pass. Real
  upstream, real GPL-2.0 LICENSE.txt confirmed before packaging.
