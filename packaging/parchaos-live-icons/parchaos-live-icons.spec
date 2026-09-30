# ==============================================================================
# ParchaOS Live Icons -- the Clock icon shows the current time and the
# Calendar icon shows today's date, wherever the shell draws app icons
# (dock, launcher, app switcher). Original code and artwork for ParchaOS;
# the designs match parchaos-icon-theme's static Clock and Calendar icons.
# ==============================================================================

Name:           parchaos-live-icons
Version:        1.0.0
Release:        4%{?dist}
Summary:        Live Clock and Calendar app icons for GNOME Shell

License:        GPL-3.0-or-later AND CC-BY-SA-4.0
URL:            https://github.com/Spanglish-Enterprises/parchaos-gnome
Source0:        extension.js
Source1:        metadata.json
Source90:       LICENSE
Source91:       LICENSE-ARTWORK

BuildArch:      noarch

Requires:       gnome-shell >= 48

%description
Makes the Clock app icon show the current time and the Calendar app icon
show today's date in the dock, the launcher and the app switcher.

%prep
mkdir -p src
cp %{SOURCE0} %{SOURCE1} src/
cp -p %{SOURCE90} %{SOURCE91} .

%build

%install
DEST=%{buildroot}%{_datadir}/gnome-shell/extensions/parchaos-live-icons@parchaos.org
install -Dm0644 src/extension.js "$DEST/extension.js"
install -Dm0644 src/metadata.json "$DEST/metadata.json"

%files
%license LICENSE
%license LICENSE-ARTWORK
%{_datadir}/gnome-shell/extensions/parchaos-live-icons@parchaos.org/

%changelog
* Wed Sep 30 2026 ParchaOS packaging - 1.0.0-4
- Declares GNOME Shell 51 support (Fedora 45 prep, ticket #37).

* Sat Sep 26 2026 ParchaOS packaging - 1.0.0-3
- Ship the license text (%license) with an accurate SPDX License tag.
* Sat Sep 26 2026 ParchaOS packaging - 1.0.0-2
- Point the extension's website link at the ParchaOS website.
* Sat Sep 26 2026 ParchaOS packaging - 1.0.0-1
- Initial package: live Clock (updates every minute) and Calendar
  (updates at midnight) icons. Verified in a headless shell (dock and
  launcher show the current time and date).
