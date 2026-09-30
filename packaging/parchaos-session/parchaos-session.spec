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
Release:        15%{?dist}
Summary:        ParchaOS Session Restore for GNOME Shell

License:        GPL-3.0-or-later
URL:            https://github.com/Spanglish-Enterprises/parchaos-gnome
Source0:        extension.js
Source1:        metadata.json
Source2:        stylesheet.css
Source90:       LICENSE

BuildArch:      noarch

Requires:       gnome-shell >= 48
Requires:       parchaos-desktop-schemas >= 2026.09.23-33

%description
Reopens the apps you had open when you log back in and puts their windows
back where they were. Apps that restore their own documents (browsers,
editors, note apps) come back with them.

%prep
mkdir -p src
cp %{SOURCE0} %{SOURCE1} %{SOURCE2} src/
cp -p %{SOURCE90} .

%build

%install
DEST=%{buildroot}%{_datadir}/gnome-shell/extensions/parchaos-session@parchaos.org
install -Dm0644 src/extension.js "$DEST/extension.js"
install -Dm0644 src/metadata.json "$DEST/metadata.json"
install -Dm0644 src/stylesheet.css "$DEST/stylesheet.css"

%files
%license LICENSE
%{_datadir}/gnome-shell/extensions/parchaos-session@parchaos.org/

%changelog
* Wed Sep 30 2026 ParchaOS packaging - 1.0.0-15
- Ticket #135: Menu text weight, tertiary shortcut colours and a darker, less colourful refraction tint, checked side by side with the kit's Menu component.

* Wed Sep 30 2026 ParchaOS packaging - 1.0.0-14
- Ticket #135: Menus follow the UI kit's Menu component: 12 px corners, 24 px rows, 11 px separators, 12 px side padding, 13 px medium white text (dark) or black (light), shortcuts dimmed, grey hover pills. The sizing applies with or without the refractive extension; the pane is drawn by whichever is active.

* Wed Sep 30 2026 ParchaOS packaging - 1.0.0-13
- After an update that replaced shell extensions or themes, the wallpaper layer
  is rebuilt a few seconds later (twice an upgrade left the running session
  with a plain blue background), and the state of the wallpaper before and after
  is written to the journal (look for "parchaos-session: after update").

* Wed Sep 30 2026 ParchaOS packaging - 1.0.0-12
- Ticket #135: with the refractive glass extension on, it draws the menus
  itself, so the session extension's own menu glass steps aside.

* Wed Sep 30 2026 ParchaOS packaging - 1.0.0-11
- Ticket #135: in the Glass style every menu and popover is a smoked, blurred
  pane with rounded corners, a hairline edge and soft hover highlights (light
  variant for light appearance). Classic and the Quick Settings panel keep
  their own look.

* Wed Sep 30 2026 ParchaOS packaging - 1.0.0-10
- Ticket #135: menus, popovers and windows fade in (120 ms) and out (200 ms)
  instead of sliding, zooming and growing out of the bottom edge. The Quick
  Settings panel and the minimize effect keep their own animation.

* Wed Sep 30 2026 ParchaOS packaging - 1.0.0-9
- Shows a "log out and back in" notice after an update replaced the shell
  extensions or themes under the running shell (marker from parchaos-desktop).

* Wed Sep 30 2026 ParchaOS packaging - 1.0.0-8
- Declares GNOME Shell 51 support (Fedora 45 prep, ticket #37).

* Wed Sep 30 2026 ParchaOS packaging - 1.0.0-7
- Ticket #76: the save on shutdown never ran. It listened for a property
  change on the system bus, but logind announces PrepareForShutdown as a
  signal of its Manager interface. Now subscribed to that signal, and
  unsubscribed on disable.
* Sat Sep 27 2026 ParchaOS packaging - 1.0.0-6
- Track per-window 'shown' handlers so they're disconnected on disable
  (previously leaked if the extension was disabled before the window was
  shown). Also save the session on logind PrepareForShutdown, so a reboot
  that skips the end-session dialog doesn't lose the session.
* Sat Sep 26 2026 ParchaOS packaging - 1.0.0-5
- Ship the license text (%license) with an accurate SPDX License tag.
* Sat Sep 26 2026 ParchaOS packaging - 1.0.0-4
- Require parchaos-desktop-schemas (the settings schema) instead of
  relying on the desktop meta-package.
* Sat Sep 26 2026 ParchaOS packaging - 1.0.0-3
- Save when the log out, restart or power off dialog opens and stop
  saving once confirmed, so the closing-down desktop can't replace the
  session. Restore once per shell process instead of using a runtime-dir
  marker (which survived logout when the user manager lingered). Track
  every timer.
* Sat Sep 26 2026 ParchaOS packaging - 1.0.0-2
- Point the extension's website link at the ParchaOS website.
* Sat Sep 26 2026 ParchaOS packaging - 1.0.0-1
- Initial package. Verified across two headless shell sessions: apps
  relaunch, windows return to their saved position and size, a
  maximized window comes back maximized and a window on a second
  workspace returns there.
