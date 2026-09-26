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
Release:        4%{?dist}
Summary:        ParchaOS's full-screen app launcher for GNOME Shell

License:        GPL-3.0-or-later
URL:            https://github.com/alexgalicea/parchaos-gnome
Source0:        extension.js
Source1:        metadata.json
Source2:        stylesheet.css
Source3:        parchaos-launcher-apps

BuildArch:      noarch

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
%{_datadir}/gnome-shell/extensions/parchaos-launcher@parchaos.org/

%changelog
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
