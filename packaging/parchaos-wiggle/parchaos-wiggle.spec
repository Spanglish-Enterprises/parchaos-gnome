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
Release:        7%{?dist}
Summary:        Cursor-magnification-on-shake GNOME Shell extension ("shake to locate cursor")

License:        GPL-2.0-only
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
# light/dark switch). ParchaOS uses the Adwaita cursors, whose arrow
# matches Wiggle's generic one, so no themed arrow ships.
Patch1:         0002-match-enlarged-cursor-to-cursor-theme.patch
# GNOME Shell 51 removed the shell's pointer watcher and
# Clutter.get_default_backend(); Patch2 replaces them (the watcher only polled
# the pointer on a timer).
Patch2:         0003-gnome-51-compatibility.patch

BuildArch:      noarch
BuildRequires:  glib2

Requires:       gnome-shell >= 45
Requires:       dconf

%description
Shake the mouse and the pointer magnifies, so it is easy to find on a
busy screen. Wraps a real, independently maintained GNOME Shell
extension.

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
glib-compile-schemas "$DEST/schemas"

%files
%license LICENSE.txt
%doc README.md
%{_datadir}/gnome-shell/extensions/wiggle@mechtifs/

%changelog
* Wed Sep 30 2026 ParchaOS packaging - 5-7
- Fedora 45 prep (ticket #37): loads on GNOME Shell 51.
* Mon Sep 28 2026 ParchaOS packaging - 5-6
- Rewrote %description to be user-facing and neutral (ticket
  #105): dropped internal build-diligence notes and lineage
  wording toward other distributions. Upstream project credit
  (authors, licenses) is kept.
* Sat Sep 26 2026 ParchaOS packaging - 5-5
- Drop the ParchaOS cursor images; the default Adwaita cursors match
  Wiggle's own enlarged arrow.
* Fri Sep 25 2026 ParchaOS packaging - 5-4
- Shaking the cursor no longer swaps it for a different-looking arrow:
  the enlarged cursor uses ParchaOS's own dark/light arrow matching the
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
