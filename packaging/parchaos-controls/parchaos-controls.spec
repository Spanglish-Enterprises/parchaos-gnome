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
Release:        9%{?dist}
Summary:        Parcha Controls, ParchaOS's control center for GNOME Shell

License:        GPL-3.0-or-later
URL:            https://github.com/Spanglish-Enterprises/parchaos-gnome
Source0:        extension.js
Source1:        metadata.json
Source2:        stylesheet.css
Source3:        parchaos-controls-symbolic.svg

BuildArch:      noarch

Requires:       gnome-shell >= 48

%description
Parcha Controls is ParchaOS's control center: a tiled panel for Wi-Fi,
Bluetooth, Focus (Do Not Disturb), dark mode, night light, display
brightness, sound and the current media player, opened from the top bar
status icons (or Super+S) in place of GNOME's Quick Settings menu.

%prep
mkdir -p src/icons
cp %{SOURCE0} %{SOURCE1} %{SOURCE2} src/
cp %{SOURCE3} src/icons/

%build

%install
UUID=parchaos-controls@parchaos.org
DEST=%{buildroot}%{_datadir}/gnome-shell/extensions/$UUID
mkdir -p "$DEST/icons"
install -m 0644 src/extension.js src/metadata.json src/stylesheet.css "$DEST/"
install -m 0644 src/icons/parchaos-controls-symbolic.svg "$DEST/icons/"

%files
%{_datadir}/gnome-shell/extensions/parchaos-controls@parchaos.org/

%changelog
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
