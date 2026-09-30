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
Release:        23%{?dist}
Summary:        ParchaOS Settings, preferences specific to ParchaOS

License:        GPL-3.0-or-later
URL:            https://github.com/Spanglish-Enterprises/parchaos-gnome
Source0:        parchaos-settings
Source1:        org.parchaos.Settings.desktop
Source2:        parchaos-app-network
Source9:        parchaos-app-permissions
Source3:        parchaos-app-network-refresh.service
Source5:        es.po
Source90:       LICENSE

BuildArch:      noarch
BuildRequires:  desktop-file-utils
BuildRequires:  gettext
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
install -Dm0755 %{SOURCE9} %{buildroot}%{_libexecdir}/parchaos-app-permissions
install -Dm0644 %{SOURCE3} %{buildroot}%{_userunitdir}/parchaos-app-network-refresh.service
# Spanish (es_PR falls back to es). Add a language: Source line + one more
# msgfmt line here.
install -d %{buildroot}%{_datadir}/locale/es/LC_MESSAGES
msgfmt --check -o %{buildroot}%{_datadir}/locale/es/LC_MESSAGES/parchaos-settings.mo %{SOURCE5}
# Enabled by a packaged link: a unit that is new on an upgrade is not
# enabled by the usual scriptlets.
install -d %{buildroot}%{_userunitdir}/graphical-session.target.wants
ln -s ../parchaos-app-network-refresh.service %{buildroot}%{_userunitdir}/graphical-session.target.wants/parchaos-app-network-refresh.service

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/org.parchaos.Settings.desktop

%files
%license LICENSE
%{_datadir}/locale/es/LC_MESSAGES/parchaos-settings.mo
%{_bindir}/parchaos-settings
%{_datadir}/applications/org.parchaos.Settings.desktop
%{_libexecdir}/parchaos-app-network
%{_libexecdir}/parchaos-app-permissions
%{_userunitdir}/parchaos-app-network-refresh.service
%{_userunitdir}/graphical-session.target.wants/parchaos-app-network-refresh.service

%changelog
* Wed Sep 30 2026 ParchaOS packaging - 1.0.0-23
- Ticket #160: Privacy gains an App permissions list. Each Flatpak app shows switches
  for the network, files and devices it asks for; a switch is Flatpak's own override,
  so turning it back on undoes the change.

* Wed Sep 30 2026 ParchaOS packaging - 1.0.0-22
- Changelog header fixed (the last releases were built with it garbled).

* Wed Sep 30 2026 ParchaOS packaging - 1.0.0-21
- A "Your computer" group on the Desktop page shows the detected model and opens
  the website hardware form with the model, CPU and graphics filled in (nothing
  is sent until the user submits the form there).

* Wed Sep 30 2026 ParchaOS packaging - 1.0.0-20
- Ticket #123: a "Photo search" switch on the Desktop page (off by default) sets up
  parchaos-image-search: it installs the engine after one password prompt,
  downloads the model once and starts indexing the Pictures folder.

* Wed Sep 30 2026 ParchaOS packaging - 1.0.0-19
- Ticket #135: Appearance has an opt-in "Refractive glass" switch (off by
  default) that turns on the optional glass-effects extension.

* Wed Sep 30 2026 ParchaOS packaging - 1.0.0-18
- Ticket #146: Spanish translation of ParchaOS Settings, written in
  Puerto Rican usage (computadora, tú). Installed as "es", which is what
  es_PR falls back to.
* Wed Sep 30 2026 ParchaOS packaging - 1.0.0-17
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
