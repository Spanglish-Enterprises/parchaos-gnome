Name:           parchaos-gaming
Version:        1.0.0
Release:        1%{?dist}
Summary:        Gaming on ParchaOS: Flathub game launchers, gamemode, gamescope and Game Mode
License:        GPL-3.0-or-later
URL:            https://github.com/Spanglish-Enterprises/parchaos-gnome
Source0:        parchaos-gaming
Source1:        org.parchaos.Gaming.desktop
Source2:        parchaos-game-mode
Source3:        parchaos-game-mode.desktop
Source4:        es.po
Source90:       LICENSE
BuildArch:      noarch

BuildRequires:  desktop-file-utils
BuildRequires:  gettext
BuildRequires:  python3
Requires:       python3-gobject
Requires:       gtk4
Requires:       libadwaita
Requires:       flatpak
# In the base image (ticket #201): CPU/GPU tuning while a game runs, the
# gamescope compositor (also the Game Mode session), and the udev rules
# that let the Steam Flatpak see controllers and VR headsets.
Requires:       gamemode
Requires:       gamescope
Requires:       steam-devices

%description
Gaming on ParchaOS, Flatpak-first. The Gaming app installs Steam, Heroic,
Lutris and Bottles from Flathub with one click, plus the MangoHud and
gamescope Vulkan layers for their runtimes. The Steam Flatpak carries its
own 32-bit libraries, so it keeps working when Fedora drops i686. gamemode,
gamescope and the controller rules come with this package. "Game Mode" on
the login screen starts straight into Steam's full-screen view under
gamescope. English and Spanish.

%prep
cp -p %{SOURCE90} .

%build

%install
install -Dm0755 %{SOURCE0} %{buildroot}%{_bindir}/parchaos-gaming
install -Dm0644 %{SOURCE1} %{buildroot}%{_datadir}/applications/org.parchaos.Gaming.desktop
install -Dm0755 %{SOURCE2} %{buildroot}%{_libexecdir}/parchaos-game-mode
install -Dm0644 %{SOURCE3} %{buildroot}%{_datadir}/wayland-sessions/parchaos-game-mode.desktop
install -d %{buildroot}%{_datadir}/locale/es/LC_MESSAGES
msgfmt --check -o %{buildroot}%{_datadir}/locale/es/LC_MESSAGES/parchaos-gaming.mo %{SOURCE4}

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/org.parchaos.Gaming.desktop
python3 -m py_compile %{SOURCE0}

%files
%license LICENSE
%{_bindir}/parchaos-gaming
%{_datadir}/applications/org.parchaos.Gaming.desktop
%{_libexecdir}/parchaos-game-mode
%{_datadir}/wayland-sessions/parchaos-game-mode.desktop
%{_datadir}/locale/es/LC_MESSAGES/parchaos-gaming.mo

%changelog
* Sun Nov 08 2026 ParchaOS packaging - 1.0.0-1
- Ticket #201: first version. The Gaming app installs Steam (on by default), Heroic, Lutris and Bottles from Flathub, plus the MangoHud and gamescope Vulkan layers matching their runtime branch. Requires gamemode, gamescope and steam-devices so they are in the base image. A "Game Mode" login session runs Steam's full-screen view under gamescope (the Gaming app if Steam is missing).
