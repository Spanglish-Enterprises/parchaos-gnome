# ==============================================================================
# Parcha Controls -- ParchaOS's control center for GNOME Shell. Original
# code for ParchaOS.
#
# A tiled panel (connectivity, now playing, Focus, dark mode, night light,
# display and sound sliders, screenshot/settings/lock) that opens from the
# top bar's status icons and Super+S in place of GNOME's Quick Settings.
# The tiles mirror and drive the Quick Settings toggles GNOME Shell already
# runs, so Wi-Fi/Bluetooth/etc. behave exactly as in stock GNOME.
# ==============================================================================

Name:           parchaos-controls
Version:        1.0.0
Release:        21%{?dist}
Summary:        Parcha Controls, ParchaOS's control center for GNOME Shell

License:        GPL-3.0-or-later
URL:            https://github.com/Spanglish-Enterprises/parchaos-gnome
Source0:        extension.js
Source1:        metadata.json
Source2:        stylesheet.css
Source3:        parchaos-controls-symbolic.svg
Source4:        parchaos-screenshot
Source5:        org.parchaos.Screenshot.desktop
Source90:       LICENSE

BuildArch:      noarch

Requires:       gnome-shell >= 48
# The Screenshot app (ticket #130) replaces the old standalone one, which
# cannot reach GNOME Shell's capture tool on Wayland.
Obsoletes:      gnome-screenshot < 99
Requires:       libnotify
BuildRequires:  desktop-file-utils

%description
Parcha Controls is ParchaOS's control center: a tiled panel for Wi-Fi,
Bluetooth, Focus (Do Not Disturb), dark mode, night light, display
brightness, sound and the current media player, opened from the top bar
status icons (or Super+S) in place of GNOME's Quick Settings menu.

%prep
mkdir -p src/icons
cp %{SOURCE0} %{SOURCE1} %{SOURCE2} src/
cp %{SOURCE3} src/icons/
cp -p %{SOURCE90} .

%build

%install
UUID=parchaos-controls@parchaos.org
DEST=%{buildroot}%{_datadir}/gnome-shell/extensions/$UUID
mkdir -p "$DEST/icons"
install -m 0644 src/extension.js src/metadata.json src/stylesheet.css "$DEST/"
install -m 0644 src/icons/parchaos-controls-symbolic.svg "$DEST/icons/"

install -Dm0755 %{SOURCE4} %{buildroot}%{_bindir}/parchaos-screenshot
desktop-file-validate %{SOURCE5}
install -Dm0644 %{SOURCE5} %{buildroot}%{_datadir}/applications/org.parchaos.Screenshot.desktop

%files
%license LICENSE
%{_bindir}/parchaos-screenshot
%{_datadir}/applications/org.parchaos.Screenshot.desktop
%{_datadir}/gnome-shell/extensions/parchaos-controls@parchaos.org/

%changelog
* Wed Sep 30 2026 ParchaOS packaging - 1.0.0-21
- Ticket #148: the Edit Controls picker is tall and sits near the left edge like the reference, categories have coloured icons and aligned labels, gallery tiles are larger.

* Wed Sep 30 2026 ParchaOS packaging - 1.0.0-20
- Ticket #148: no more square halo around the rounded Control Center and picker windows. The background blur cannot follow rounded corners, so it is gone and the panels are more opaque instead.

* Wed Sep 30 2026 ParchaOS packaging - 1.0.0-19
- Ticket #148: the Edit Controls picker is its own window in the middle of the screen (as in the reference), not attached to Control Center. Control Center stays where it was; a press outside the two, Escape or Done ends editing.

* Wed Sep 30 2026 ParchaOS packaging - 1.0.0-18
- Ticket #148: Edit Controls gets the picker panel beside Control Center: a search box, categories, a gallery of the controls that are not in the panel, and Done; clicking a control puts it back. Fixes in this build are checked against the reference screenshot.

* Wed Sep 30 2026 ParchaOS packaging - 1.0.0-17
- Ticket #148: Edit Controls redesigned. Each tile gets a round - (or +) badge on
  its corner and wiggles slightly; drag a tile onto another to move it. The old
  row of three small buttons over every tile is gone. Hidden tiles wait at the
  end, dimmed, with a + badge.

* Wed Sep 30 2026 ParchaOS packaging - 1.0.0-16
- Declares GNOME Shell 51 support (Fedora 45 prep, ticket #37).

* Wed Sep 30 2026 ParchaOS packaging - 1.0.0-15
- Changelog header fixed (the last releases were built with it garbled).

* Wed Sep 30 2026 ParchaOS packaging - 1.0.0-14
- Ticket #148: Edit Controls. A button at the bottom of the panel lets you hide
  tiles, bring hidden ones back, and move each tile earlier or later; the
  choice is saved and the tiles re-flow to fill the panel.

* Wed Sep 30 2026 ParchaOS packaging - 1.0.0-13
- Glass values now follow the reference UI kit: a smoked #1a1a1a pane, 34 px
  corners, hairline outline, bright rims top and bottom, 17% grey capsules.
* Wed Sep 30 2026 ParchaOS packaging - 1.0.0-12
- Ticket #135: the Glass style now looks like real glass. A clear, more
  strongly tinted pane over the blurred background, controls as glass
  capsules with a bright rim and inner glow, switched-on circles solid white
  (blue in the light appearance), and thicker white-filled slider pills.
  Classic is unchanged.
* Tue Sep 29 2026 ParchaOS packaging - 1.0.0-11
- Ticket #130: a working Screenshot app. The extension answers an
  org.parchaos.Shell.OpenScreenshotUI call on the session bus by opening
  GNOME Shell's own capture tool (the Print key's), and the new
  "Screenshot" launcher calls it. The old gnome-screenshot app, which fell
  back to X11 and failed on Wayland, is obsoleted.
* Sat Sep 26 2026 ParchaOS packaging - 1.0.0-10
- Ship the license text (%license) with an accurate SPDX License tag.
* Sat Sep 26 2026 ParchaOS packaging - 1.0.0-9
- Light appearance: with the system set to light, the panel, tiles, text
  and controls are light (both styles), switching live when Dark Mode is
  toggled.
* Sat Sep 26 2026 ParchaOS packaging - 1.0.0-8
- Point the extension's website link at the ParchaOS website.
* Sat Sep 26 2026 ParchaOS packaging - 1.0.0-7
- Use one media-player watcher for the whole session instead of one per
  panel open (it has no destroy method, so each one leaked).
- Destroy replaced now-playing artwork and the delayed sync on close.
* Sat Sep 26 2026 ParchaOS packaging - 1.0.0-6
- Follow the ParchaOS style setting (glass or classic).
* Fri Sep 25 2026 ParchaOS packaging - 1.0.0-5
- Remove the "Super as Ctrl" tile: it's a set-once preference, now in
  ParchaOS Settings (parchaos-settings), keeping Controls for things
  toggled often.
* Fri Sep 25 2026 ParchaOS packaging - 1.0.0-4
- Add a "Super as Ctrl" tile: switches the current user between the
  Super-as-Ctrl keyboard style and standard key roles (runs
  parchaos-keyboard-style from parchaos-keyboard-remap). Small tiles now
  wrap four per row.
* Fri Sep 25 2026 ParchaOS packaging - 1.0.0-3
- Show toggles that other extensions add to Quick Settings (e.g.
  GSConnect's Mobile Devices) as tiles; their name opens that
  extension's settings. They were unreachable with Quick Settings hidden.
* Fri Sep 25 2026 ParchaOS packaging - 1.0.0-2
- Dark Mode tile writes an explicit prefer-light/prefer-dark color
  scheme. GNOME's own toggle writes 'default' (no preference) for light,
  which left Electron apps such as Obsidian in the wrong mode.
* Fri Sep 25 2026 ParchaOS packaging - 1.0.0-1
- Initial package. Verified in an isolated headless gnome-shell with the
  real extension set: opens from the top bar and Super+S, closes on Esc;
  shows live Wi-Fi/wired state; Dark Mode, Focus and Night Light toggles
  change the real settings and follow outside changes.
