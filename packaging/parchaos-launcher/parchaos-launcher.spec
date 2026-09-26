# ==============================================================================
# ParchaOS Launcher -- a full-screen app launcher for GNOME Shell that
# replaces the overview's app grid. Original code for ParchaOS.
#
# Anything that would open the app grid (the dock's Show Apps button,
# Super+A, Show Apps from inside the overview) opens the launcher instead:
# blurred desktop, search field, a paged 7x5 grid with page dots, and
# folders from GNOME's own org.gnome.desktop.app-folders that open in
# place. Esc clears the search, then closes; Enter launches the first
# search result; scroll, swipe or arrow keys change pages.
# ==============================================================================

Name:           parchaos-launcher
Version:        1.0.0
Release:        14%{?dist}
Summary:        ParchaOS's full-screen app launcher for GNOME Shell

License:        GPL-3.0-or-later
URL:            https://github.com/Spanglish-Enterprises/parchaos-gnome
Source0:        extension.js
Source1:        metadata.json
Source2:        stylesheet.css
Source3:        parchaos-launcher-apps
Source90:       LICENSE

BuildArch:      noarch

Requires:       parchaos-desktop-schemas >= 2026.09.23-33
Requires:       dnf5daemon-server
Requires:       gnome-shell >= 48
# Edit mode's helper (removability checks and uninstall).
Requires:       python3-gobject
Requires:       polkit
Requires:       flatpak

%description
A full-screen app launcher for GNOME Shell: blurred desktop background,
search, a paged grid of apps with page dots, and app folders that open
in place. Replaces the overview app grid (dock Show Apps button, Super+A).

%prep
mkdir -p src
cd src
cp %{SOURCE0} %{SOURCE1} %{SOURCE2} %{SOURCE3} .
# %%prep works in src/; %%license reads from the build directory.
cp -p %{SOURCE90} ..

%build

%install
UUID=parchaos-launcher@parchaos.org
DEST=%{buildroot}%{_datadir}/gnome-shell/extensions/$UUID
mkdir -p "$DEST"
install -m 0644 src/extension.js "$DEST/"
install -m 0644 src/metadata.json "$DEST/"
install -m 0644 src/stylesheet.css "$DEST/"
install -m 0755 src/parchaos-launcher-apps "$DEST/"

%files
%license LICENSE
%{_datadir}/gnome-shell/extensions/parchaos-launcher@parchaos.org/

%changelog
* Sat Sep 26 2026 ParchaOS packaging - 1.0.0-14
- Dragging the only app of a folder back onto that folder no longer
  deletes the folder; a folder emptied by a drag leaves the saved order.
- Uninstall removes nothing unless the removal still matches the list
  the user confirmed; Flatpak removal can ask for the administrator
  password through polkit.
* Sat Sep 26 2026 ParchaOS packaging - 1.0.0-13
- Rebuild: install the license file from the build directory (the
  previous build failed to find it).
* Sat Sep 26 2026 ParchaOS packaging - 1.0.0-12
- Ship the license text (%license) with an accurate SPDX License tag.
* Sat Sep 26 2026 ParchaOS packaging - 1.0.0-11
- Require parchaos-desktop-schemas (the settings schema) instead of
  relying on the desktop meta-package.
* Sat Sep 26 2026 ParchaOS packaging - 1.0.0-10
- Closing the launcher while edit mode or the uninstall check is still
  loading no longer touches the closed launcher.
* Sat Sep 26 2026 ParchaOS packaging - 1.0.0-9
- Drag to rearrange: other icons make room, holding at a page edge turns
  the page, holding over an app makes a folder and over a folder adds to
  it, and dragging out of an open folder takes an app out. Folder names
  are editable in place. The arrangement is saved.
* Sat Sep 26 2026 ParchaOS packaging - 1.0.0-8
- Uninstall goes through dnf5daemon instead of pkexec dnf remove -y: the
  confirmation lists every package the removal takes with it, refuses
  plans that would touch ParchaOS or core packages, and asks for
  authorization through polkit.
* Sat Sep 26 2026 ParchaOS packaging - 1.0.0-7
- Arrow keys and Enter work inside an open folder (Enter no longer opens the hidden main grid's selection); page and scroll timers are removed when the launcher closes.
* Sat Sep 26 2026 ParchaOS packaging - 1.0.0-6
- Point the extension's website link at the ParchaOS website.
* Sat Sep 26 2026 ParchaOS packaging - 1.0.0-5
- Follow the ParchaOS style setting (glass or classic).
* Fri Sep 25 2026 ParchaOS packaging - 1.0.0-4
- Edit mode: a long press (or right-click) on an app makes the icons
  pulse gently and puts a remove badge on apps that can be uninstalled;
  the badge asks for confirmation, then uninstalls (Flatpak apps through
  flatpak, packages through pkexec dnf with the usual password prompt)
  and reports the result as a notification. ParchaOS's own packages,
  anything parchaos-desktop requires, core desktop apps and packages
  other installed software depends on are never offered. Esc or a click
  on empty space leaves edit mode.
* Fri Sep 25 2026 ParchaOS packaging - 1.0.0-3
- Fix a black background on multi-monitor setups: the wallpaper actor
  was placed at the monitor's global position inside the launcher, which
  is off-screen for any primary monitor not at 0,0.
* Fri Sep 25 2026 ParchaOS packaging - 1.0.0-2
- Background is the blurred wallpaper only, from the launcher's own
  background actor; open windows no longer show through.
- Folder tiles are the same size as app icons, with a proper 3x3 grid
  of mini icons.
- Keyboard selection: arrow keys move a highlight (flipping pages at the
  edges), Enter opens it; search preselects the first result.
* Fri Sep 25 2026 ParchaOS packaging - 1.0.0-1
- Initial package. Verified in an isolated headless gnome-shell: opens
  from the dock's Show Apps button (from the desktop and from inside the
  overview) and Super+A; search filters and Enter launches; Esc clears
  then closes; folders open in place.
