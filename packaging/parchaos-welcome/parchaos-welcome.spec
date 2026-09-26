Name:           parchaos-welcome
Version:        1.0.0
Release:        2%{?dist}
Summary:        First-login assistant for ParchaOS
License:        GPL-3.0-or-later
URL:            https://github.com/alexgalicea/parchaos-gnome
Source0:        parchaos-welcome
Source1:        org.parchaos.Welcome.desktop
Source2:        parchaos-welcome-autostart.desktop
BuildArch:      noarch

BuildRequires:  desktop-file-utils
Requires:       python3-gobject
Requires:       gtk4
Requires:       libadwaita
Requires:       parchaos-release

%description
ParchaOS Welcome opens once at an account's first login (and any time
from the launcher). It sets the style (Glass or Classic), light or dark,
how the Super key works and whether location services are on (off unless
the user turns them on), then shows where the launcher, Parcha Controls
and the menu bar are. It doesn't run in the installer's live session.

%prep

%build

%install
install -Dm0755 %{SOURCE0} %{buildroot}%{_bindir}/parchaos-welcome
install -Dm0644 %{SOURCE1} %{buildroot}%{_datadir}/applications/org.parchaos.Welcome.desktop
install -Dm0644 %{SOURCE2} %{buildroot}%{_sysconfdir}/xdg/autostart/parchaos-welcome.desktop

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/org.parchaos.Welcome.desktop
desktop-file-validate %{buildroot}%{_sysconfdir}/xdg/autostart/parchaos-welcome.desktop

%files
%{_bindir}/parchaos-welcome
%{_datadir}/applications/org.parchaos.Welcome.desktop
%config(noreplace) %{_sysconfdir}/xdg/autostart/parchaos-welcome.desktop

%changelog
* Sat Sep 26 2026 ParchaOS packaging - 1.0.0-2
- The style and light/dark choices leave theme switching to parchaos-
  theme-sync.
* Sat Sep 26 2026 ParchaOS packaging - 1.0.0-1
- First release: style, light or dark, the Super key, location (off
  unless turned on) and a short tour; opens once per account at first
  login and any time from the launcher.
