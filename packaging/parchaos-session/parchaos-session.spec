# ==============================================================================
# ParchaOS Session Restore -- reopens the apps that were open at the end of
# the last session and puts their windows back (workspace, position, size,
# maximized/fullscreen/minimized). Original code for ParchaOS.
#
# The session is saved every 30 s while you work (so crashes and power loss
# are covered) and restored once per login. Controlled by the
# org.parchaos.desktop restore-session key (ParchaOS Settings → General).
# ==============================================================================

Name:           parchaos-session
Version:        1.0.0
Release:        2%{?dist}
Summary:        ParchaOS Session Restore for GNOME Shell

License:        GPL-3.0-or-later
URL:            https://github.com/alexgalicea/parchaos-gnome
Source0:        extension.js
Source1:        metadata.json

BuildArch:      noarch

Requires:       gnome-shell >= 48
Requires:       parchaos-desktop >= 2026.09.23-20

%description
Reopens the apps you had open when you log back in and puts their windows
back where they were. Apps that restore their own documents (browsers,
editors, note apps) come back with them.

%prep
mkdir -p src
cp %{SOURCE0} %{SOURCE1} src/

%build

%install
DEST=%{buildroot}%{_datadir}/gnome-shell/extensions/parchaos-session@parchaos.org
install -Dm0644 src/extension.js "$DEST/extension.js"
install -Dm0644 src/metadata.json "$DEST/metadata.json"

%files
%{_datadir}/gnome-shell/extensions/parchaos-session@parchaos.org/

%changelog
* Sat Sep 26 2026 ParchaOS packaging - 1.0.0-2
- Point the extension's website link at the ParchaOS website.
* Sat Sep 26 2026 ParchaOS packaging - 1.0.0-1
- Initial package. Verified across two headless shell sessions: apps
  relaunch, windows return to their saved position and size, a
  maximized window comes back maximized and a window on a second
  workspace returns there.
