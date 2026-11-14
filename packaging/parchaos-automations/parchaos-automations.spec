# ==============================================================================
# Parcha Automations (ticket #186): "when this happens, do that". A small window
# lists the automations with a switch each and offers ready-made ones (Work Focus
# on weekdays, tidy screenshots every week, dark mode with a projector); a user
# service watches the clock, displays, networks, running apps and folders and runs
# them. Each automation is a plain file in ~/.config/parchaos/automations/.
# ==============================================================================

Name:           parchaos-automations
Version:        1.0.0
Release:        1%{?dist}
Summary:        Let the computer do things for you at a time or when something happens

License:        GPL-3.0-or-later
URL:            https://github.com/Spanglish-Enterprises/parchaos-gnome
Source0:        parchaos-automations
Source1:        org.parchaos.Automations.desktop
Source2:        parchaos-automations.service
Source3:        es.po
Source90:       LICENSE

BuildArch:      noarch
BuildRequires:  python3
BuildRequires:  gettext
BuildRequires:  desktop-file-utils
BuildRequires:  systemd-rpm-macros

Requires:       python3-gobject
Requires:       gtk4
Requires:       libadwaita
Requires:       glib2
# Network triggers ask NetworkManager which networks are connected.
Requires:       NetworkManager
# The Focus action uses the focus-mode setting (ticket #154).
Requires:       parchaos-desktop-schemas >= 2026.09.23-33

%description
Automations lets the computer do things for you. Pick what starts it - a time,
a display or a network connecting, an app opening, a file appearing in a
folder - and what it does: open an app, change Focus, switch between light and
dark, change a setting, run a command, or move and rename files. Ready-made
ones turn on Work Focus on weekdays, tidy the screenshots folder every week and
switch to dark mode when a projector is connected. What a lasting trigger
changed is put back when it ends.

%prep
cp -p %{SOURCE90} .
python3 -m py_compile %{SOURCE0}

%build

%install
install -Dm0755 %{SOURCE0} %{buildroot}%{_bindir}/parchaos-automations
install -Dm0644 %{SOURCE1} %{buildroot}%{_datadir}/applications/org.parchaos.Automations.desktop
install -Dm0644 %{SOURCE2} %{buildroot}%{_userunitdir}/parchaos-automations.service
# On for everyone, existing installs too (a preset only applies on first install). With no
# automations it only watches its folder.
mkdir -p %{buildroot}%{_userunitdir}/graphical-session.target.wants
ln -s ../parchaos-automations.service \
    %{buildroot}%{_userunitdir}/graphical-session.target.wants/parchaos-automations.service
install -d %{buildroot}%{_datadir}/locale/es/LC_MESSAGES
msgfmt --check -o %{buildroot}%{_datadir}/locale/es/LC_MESSAGES/parchaos-automations.mo %{SOURCE3}

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/org.parchaos.Automations.desktop

%files
%license LICENSE
%{_bindir}/parchaos-automations
%{_datadir}/applications/org.parchaos.Automations.desktop
%{_userunitdir}/parchaos-automations.service
%{_userunitdir}/graphical-session.target.wants/parchaos-automations.service
%{_datadir}/locale/es/LC_MESSAGES/parchaos-automations.mo

%changelog
* Sat Nov 14 2026 ParchaOS packaging - 1.0.0-1
- Initial package (ticket #186): triggers (a time or a period, a display, a
  network, an app, a file in a folder) and actions (open, Focus, light/dark, a
  setting, a command, move and rename files), stored as plain files; the window
  with ready-made automations, the editor, Run Now; undo when a lasting trigger
  ends; a time missed while the computer was off runs once when it is back.
  English and Spanish.
