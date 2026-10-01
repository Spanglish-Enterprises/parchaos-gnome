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
Release:        39%{?dist}
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
Requires:       parchaos-glass
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
* Thu Oct 01 2026 ParchaOS packaging - 1.0.0-39
- Ticket #148: the picker is centred on the screen again.

* Thu Oct 01 2026 ParchaOS packaging - 1.0.0-38
- Ticket #148: edit mode matches the reference: no panel behind Control Center (each tile is its own glass), one light glass window for the picker, placed left and larger, with divider lines between sections.

* Thu Oct 01 2026 ParchaOS packaging - 1.0.0-37
- Ticket #148: Edit Controls windows (Control Center and picker) are glass in edit mode; new Battery control that only exists when the machine has a battery.

* Thu Oct 01 2026 ParchaOS packaging - 1.0.0-36
- Ticket #148: picker gets a What's New card and a Suggestions row; gallery tiles wrap in plain rows (fixes overlapping sections).

* Thu Oct 01 2026 ParchaOS packaging - 1.0.0-35
- Ticket #148: connection tiles (Wi-Fi, Bluetooth, Wired, VPN, Airplane) can be resized to 2x2: icon on top, name and state underneath.

* Thu Oct 01 2026 ParchaOS packaging - 1.0.0-34
- Ticket #148: removed the menu-bar drop (controls go into Control Center only, as intended); the picker hint says so again.

* Thu Oct 01 2026 ParchaOS packaging - 1.0.0-32
- Ticket #135: Thin slider track, larger glyphs on small tiles.

* Thu Oct 01 2026 ParchaOS packaging - 1.0.0-31
- Ticket #135: white text on the glass tiles, thinner dark slider track with a bright fill (like the reference), panes are sized before they are shown.

* Thu Oct 01 2026 ParchaOS packaging - 1.0.0-30
- Ticket #148: a tile now really takes the size chosen (it stayed wide with only an icon). At one cell a connection shows only its icon; wider it shows the name and the state (the network name, On, Off).

* Thu Oct 01 2026 ParchaOS packaging - 1.0.0-29
- Ticket #148: like the reference, each connection (Wi-Fi, Bluetooth, Wired, VPN, Airplane Mode) is its own tile that can be resized (wide with name and state, or icon-only); plain on/off switches (Dark Mode, Night Light, Power Mode) have one fixed size; shortcut buttons (Screenshot, Settings, Lock) can be icon-only or wide.

* Thu Oct 01 2026 ParchaOS packaging - 1.0.0-28
- Ticket #135: like the reference, the smallest size of a small control shows only its icon (the tile is the circle); a wider tile adds the name beside the icon.

* Thu Oct 01 2026 ParchaOS packaging - 1.0.0-27
- Ticket #135: Tile glass panes stay on their tiles while the menu opens (checked every frame).

* Thu Oct 01 2026 ParchaOS packaging - 1.0.0-26
- Ticket #135: with refractive glass on, each tile is drawn with ParchaOS's own glass (parchaos-glass): refraction, blur, rim light and shadow, one pane per tile; the panel stays clear. The button form is used in every style.

* Thu Oct 01 2026 ParchaOS packaging - 1.0.0-25
- Ticket #148/#135: with refractive glass on, Control Center now lives inside the standard Quick Settings menu and its tiles carry the toggle classes, so the glass extension draws one glass capsule per tile (no grey pane). Edit Controls works there too. Edit mode: no wiggle, the resize handle is on every tile right away.

* Wed Sep 30 2026 ParchaOS packaging - 1.0.0-24
- Ticket #148: the resize handle is drawn like the reference: a thick white stroke that follows the tile's rounded bottom-right corner and bulges outwards (it was turned the wrong way).

* Wed Sep 30 2026 ParchaOS packaging - 1.0.0-23
- Ticket #148: resizing works like the reference: each tile has a curved white handle on its bottom-right corner; drag it and the tile snaps to the nearest size the control allows. Replaces the click-to-cycle button.

* Wed Sep 30 2026 ParchaOS packaging - 1.0.0-22
- Ticket #148: Edit Controls. The picker window opens in the middle of the screen and can be moved by its top strip; gallery tiles show each control at its real size (round, wide or square, name under); controls can be dragged from the picker onto Control Center (or clicked); empty round slots show where controls can go; each tile has a corner handle that cycles its sizes (the size is remembered); controls not in the panel no longer sit in it dimmed, they are in the picker.

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
