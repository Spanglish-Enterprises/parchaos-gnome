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
Release:        13%{?dist}
Summary:        ParchaOS Settings, preferences specific to ParchaOS

License:        GPL-3.0-or-later
URL:            https://github.com/Spanglish-Enterprises/parchaos-gnome
Source0:        parchaos-settings
Source1:        org.parchaos.Settings.desktop
Source90:       LICENSE

BuildArch:      noarch
BuildRequires:  desktop-file-utils

Requires:       parchaos-desktop-schemas >= 2026.09.23-33
Requires:       python3-gobject
Requires:       gtk4
Requires:       libadwaita
Requires:       parchaos-keyboard-remap >= 0.15.13-7

%description
ParchaOS Settings holds preferences specific to ParchaOS, starting with
how the Super key works (Super as Ctrl, or standard Super and Ctrl roles).

%prep
cp -p %{SOURCE90} .

%build

%install
install -Dm0755 %{SOURCE0} %{buildroot}%{_bindir}/parchaos-settings
install -Dm0644 %{SOURCE1} %{buildroot}%{_datadir}/applications/org.parchaos.Settings.desktop

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/org.parchaos.Settings.desktop

%files
%license LICENSE
%{_bindir}/parchaos-settings
%{_datadir}/applications/org.parchaos.Settings.desktop

%changelog
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
