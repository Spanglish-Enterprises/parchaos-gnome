# ==============================================================================
# Voice dictation (ticket #119): Ctrl+Alt+D, speak, Ctrl+Alt+D, and the words
# are typed at the cursor in any app. Everything runs on this computer.
#
# The speech engine is whisper.cpp (MIT) through Fedora's python3-pywhispercpp;
# Fedora ships no whisper.cpp command-line tool. The speech model (148 MB) is
# not in the ISO: parchaos-dictation-model fetches it on first use and checks
# its SHA-256 before using it.
# ==============================================================================

Name:           parchaos-dictation
Version:        1.0.0
Release:        4%{?dist}
Summary:        Local voice dictation for the ParchaOS desktop

License:        GPL-3.0-or-later
URL:            https://github.com/Spanglish-Enterprises/parchaos-gnome
Source0:        extension.js
Source1:        metadata.json
Source2:        org.parchaos.dictation.gschema.xml
Source3:        parchaos-dictation-transcribe
Source4:        parchaos-dictation-model
Source5:        parchaos-dictation-install-engine
Source6:        org.parchaos.dictation.policy
Source90:       LICENSE

BuildArch:      noarch
BuildRequires:  glib2
BuildRequires:  python3

Requires:       gnome-shell >= 48
Requires:       pipewire-utils
Requires:       python3
Requires:       polkit
Requires:       dnf5

%description
Press Ctrl+Alt+D, speak, and press it again: what you said is typed where
the cursor is, in any app. Recognition runs on this computer; no audio leaves
it. The speech model is downloaded once, the first time you use it.

%prep
cp -p %{SOURCE90} .
python3 -m py_compile %{SOURCE3} %{SOURCE4}

%build

%install
UUID=parchaos-dictation@parchaos.org
DEST=%{buildroot}%{_datadir}/gnome-shell/extensions/$UUID
mkdir -p "$DEST/schemas"
install -m 0644 %{SOURCE0} %{SOURCE1} "$DEST/"
install -m 0644 %{SOURCE2} "$DEST/schemas/"
glib-compile-schemas "$DEST/schemas"
install -Dm0755 %{SOURCE3} %{buildroot}%{_libexecdir}/parchaos-dictation/parchaos-dictation-transcribe
install -Dm0755 %{SOURCE4} %{buildroot}%{_libexecdir}/parchaos-dictation/parchaos-dictation-model
install -Dm0755 %{SOURCE5} %{buildroot}%{_libexecdir}/parchaos-dictation/parchaos-dictation-install-engine
install -Dm0644 %{SOURCE6} %{buildroot}%{_datadir}/polkit-1/actions/org.parchaos.dictation.policy

%files
%license LICENSE
%{_libexecdir}/parchaos-dictation/
%{_datadir}/polkit-1/actions/org.parchaos.dictation.policy
%{_datadir}/gnome-shell/extensions/parchaos-dictation@parchaos.org/

%changelog
* Wed Sep 30 2026 ParchaOS packaging - 1.0.0-4
- Declares GNOME Shell 51 support (Fedora 45 prep, ticket #37).

* Wed Sep 30 2026 ParchaOS packaging - 1.0.0-3
- Fedora 45 prep (ticket #37): synthetic keyboard input finds its backend the
  way GNOME Shell 51 expects (Clutter.get_default_backend() is gone), still
  working on 50.

* Tue Sep 29 2026 ParchaOS packaging - 1.0.0-2
- Ships with the OS. The small part (shortcut, recorder, typing) is in
  the ISO; the speech engine (python3-pywhispercpp, which drags in
  ROCm/OpenVINO libraries) and the model are fetched the first time the
  shortcut is used, after a password prompt (polkit action
  org.parchaos.dictation.install-engine, installs that one package only).
* Tue Sep 29 2026 ParchaOS packaging - 1.0.0-1
- Initial package (ticket #119). Ctrl+Alt+D starts and stops listening;
  the words are typed as key presses (works in terminals, leaves the
  clipboard alone). Verified in an isolated headless shell with a stand-in
  recorder and transcriber typing into a GTK entry.
