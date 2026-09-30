# ==============================================================================
# ParchaOS Settings -- a small preferences app for settings specific to
# ParchaOS that GNOME's own Settings app has no place for (it can't be
# extended with new pages without patching it). Original code for ParchaOS.
#
# First section: Keyboard, with the "Super as Ctrl" switch (runs
# parchaos-keyboard-style from parchaos-keyboard-remap).
# ==============================================================================

Name:           parchaos-settings
Version:        1.0.0
Release:        17%{?dist}
Summary:        ParchaOS Settings, preferences specific to ParchaOS

License:        GPL-3.0-or-later
URL:            https://github.com/Spanglish-Enterprises/parchaos-gnome
Source0:        parchaos-settings
Source1:        org.parchaos.Settings.desktop
Source2:        parchaos-app-network
Source3:        parchaos-app-network-refresh.service
Source90:       LICENSE

BuildArch:      noarch
BuildRequires:  desktop-file-utils
BuildRequires:  systemd-rpm-macros

Requires:       parchaos-desktop-schemas >= 2026.09.23-33
Requires:       python3-gobject
Requires:       gtk4
Requires:       libadwaita
Requires:       parchaos-keyboard-remap >= 0.15.13-7
# Turning an app's network access off (ticket #126).
Requires:       bubblewrap
Recommends:     flatpak

%description
ParchaOS Settings holds preferences specific to ParchaOS, starting with
how the Super key works (Super as Ctrl, or standard Super and Ctrl roles).

%prep
cp -p %{SOURCE90} .

%build

%install
install -Dm0755 %{SOURCE0} %{buildroot}%{_bindir}/parchaos-settings
install -Dm0644 %{SOURCE1} %{buildroot}%{_datadir}/applications/org.parchaos.Settings.desktop
install -Dm0755 %{SOURCE2} %{buildroot}%{_libexecdir}/parchaos-app-network
install -Dm0644 %{SOURCE3} %{buildroot}%{_userunitdir}/parchaos-app-network-refresh.service
# Enabled by a packaged link: a unit that is new on an upgrade is not
# enabled by the usual scriptlets.
install -d %{buildroot}%{_userunitdir}/graphical-session.target.wants
ln -s ../parchaos-app-network-refresh.service %{buildroot}%{_userunitdir}/graphical-session.target.wants/parchaos-app-network-refresh.service

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/org.parchaos.Settings.desktop

%files
%license LICENSE
%{_bindir}/parchaos-settings
%{_datadir}/applications/org.parchaos.Settings.desktop
%{_libexecdir}/parchaos-app-network
%{_userunitdir}/parchaos-app-network-refresh.service
%{_userunitdir}/graphical-session.target.wants/parchaos-app-network-refresh.service

%changelog
* Tue Sep 29 2026 ParchaOS packaging - 1.0.0-17
- Ticket #53: ParchaOS Settings is translation-ready. Every string shown to
  the user goes through gettext (domain parchaos-settings, catalogs read from
  the system locale directory), po/parchaos-settings.pot lists the 70
  messages, and tests check that nothing is left unmarked and that the
  template is current. No translations ship yet.
* Wed Sep 30 2026 ParchaOS packaging - 1.0.0-16
- Ticket #20: redesigned as a sidebar of sections beside the chosen page,
  like GNOME's own Settings, folding to one column in a narrow window.
  Sections: Appearance (style, folder colour), Desktop (icons: snap to grid,
  Home, Trash, icon size; sessions; focus schedule), Privacy (network access
  per app), Backups (snapshot status and Parcha Backup) and Keyboard.

* Tue Sep 29 2026 ParchaOS packaging - 1.0.0-15
- Ticket #126: a Privacy page lists your apps with a network switch each.
  Off keeps the app off the network from its next start: Flatpak apps use
  Flatpak's own permission, other apps get a per-user launcher that starts
  them without network interfaces (bubblewrap). A login service keeps those
  launchers current after app updates. Built on Flatpak and bubblewrap
  because firewalld cannot tell which app a connection belongs to.
* Tue Sep 29 2026 ParchaOS packaging - 1.0.0-14
- Ticket #79: Appearance page gains a Folder colour choice (shown when the
  desktop schema has the folder-colour key).
* Mon Sep 28 2026 ParchaOS packaging - 1.0.0-13
- Focus times: fix _update_focus_hint to read stored time strings rather
  than row subtitles (ticket #70).
* Sat Sep 26 2026 ParchaOS packaging - 1.0.0-12
- Focus times: minute step is 1 (was 5), no write-back on load, and a
  hint appears when start equals end (which disables the schedule).
* Sat Sep 26 2026 ParchaOS packaging - 1.0.0-11
- Ship the license text (%license) with an accurate SPDX License tag.
* Sat Sep 26 2026 ParchaOS packaging - 1.0.0-10
- Require parchaos-keyboard-remap 0.15.13-7 (the first build whose
  keyboard-style accepts super-ctrl and standard).
* Sat Sep 26 2026 ParchaOS packaging - 1.0.0-9
- Require parchaos-desktop-schemas (the settings schema) instead of
  relying on the desktop meta-package.
* Sat Sep 26 2026 ParchaOS packaging - 1.0.0-8
- The style switch leaves theme switching to parchaos-theme-sync.
* Sat Sep 26 2026 ParchaOS packaging - 1.0.0-7
- Choosing Classic also switches the GTK and Shell themes to ParchaOS's
  solid variants (and Glass back to the normal ones), keeping light or
  dark; other themes are left alone.
* Sat Sep 26 2026 ParchaOS packaging - 1.0.0-6
- Build the window from Adw.ApplicationWindow with a page switcher
  instead of the deprecated Adw.PreferencesWindow; same pages and
  layout.
* Sat Sep 26 2026 ParchaOS packaging - 1.0.0-5
- Use the new keyboard style names (super-ctrl, standard); requires
  parchaos-keyboard-remap 0.15.13-6.
* Sat Sep 26 2026 ParchaOS packaging - 1.0.0-4
- General: a Focus group to turn scheduled Do Not Disturb on or off and
  set its start and end times.
* Sat Sep 26 2026 ParchaOS packaging - 1.0.0-3
- General page: "Reopen apps when logging back in" (session restore).
* Sat Sep 26 2026 ParchaOS packaging - 1.0.0-2
- Appearance page: choose the Glass or Classic style.
* Fri Sep 25 2026 ParchaOS packaging - 1.0.0-1
- Initial package: Keyboard section with the Super as Ctrl switch.
