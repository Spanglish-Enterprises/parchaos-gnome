# ==============================================================================
# Desktop widgets (ticket #165): weather, today's calendar, sticky notes and a
# clock on the desktop, under the windows. Right-click the desktop and choose
# Edit Widgets to add, move or remove them. Weather comes from the menu bar's
# reading and the calendar from GNOME's calendar server; nothing new is
# fetched from the network.
# ==============================================================================

Name:           parchaos-widgets
Version:        1.0.0
Release:        1%{?dist}
Summary:        Weather, calendar, notes and clock widgets on the ParchaOS desktop

License:        GPL-3.0-or-later
URL:            https://github.com/Spanglish-Enterprises/parchaos-gnome
Source0:        extension.js
Source1:        layout.js
Source2:        metadata.json
Source3:        stylesheet.css
Source4:        es.po
Source90:       LICENSE

BuildArch:      noarch
BuildRequires:  gettext

Requires:       gnome-shell >= 48
# The desktop-widgets and widgets-editing settings.
Requires:       parchaos-desktop-schemas >= 2026.09.23-92

%description
Small widgets that live on the desktop wallpaper, under every window: the
weather, today's events, sticky notes and a clock. They follow the Glass or
Classic style and the light or dark appearance. Right-click the desktop and
choose Edit Widgets to add, move or remove them.

%prep
cp -p %{SOURCE90} .

%build

%install
DEST=%{buildroot}%{_datadir}/gnome-shell/extensions/parchaos-widgets@parchaos.org
install -d "$DEST"
install -m 0644 %{SOURCE0} %{SOURCE1} %{SOURCE2} %{SOURCE3} "$DEST/"
# Spanish (es_PR falls back to es).
install -d %{buildroot}%{_datadir}/locale/es/LC_MESSAGES
msgfmt --check -o %{buildroot}%{_datadir}/locale/es/LC_MESSAGES/parchaos-widgets.mo %{SOURCE4}

%files
%license LICENSE
%{_datadir}/gnome-shell/extensions/parchaos-widgets@parchaos.org/
%{_datadir}/locale/es/LC_MESSAGES/parchaos-widgets.mo

%changelog
* Sat Nov 14 2026 ParchaOS packaging - 1.0.0-1
- Initial package (ticket #165): weather, calendar, note and clock widgets
  on the desktop, under the windows; an edit mode (the desktop menu's Edit
  Widgets) to add, drag and remove them; Glass/Classic and light/dark looks.
