# ==============================================================================
# Speak selection (ticket #162): select text in any app, press Ctrl+Alt+S, and
# it is read aloud; press it again to stop. The voice is espeak-ng (GPL-3.0+,
# in Fedora), so it works offline with nothing to download. Better-sounding
# voices (Piper) can be added later as an opt-in, the way dictation does it.
# ==============================================================================

Name:           parchaos-speak
Version:        1.0.0
Release:        1%{?dist}
Summary:        Read the selected text aloud on the ParchaOS desktop

License:        GPL-3.0-or-later
URL:            https://github.com/Spanglish-Enterprises/parchaos-gnome
Source0:        extension.js
Source1:        metadata.json
Source2:        org.parchaos.speak.gschema.xml
Source3:        parchaos-speak-say
Source90:       LICENSE

BuildArch:      noarch
BuildRequires:  glib2
BuildRequires:  python3

Requires:       gnome-shell >= 48
Requires:       espeak-ng
Requires:       python3

%description
Select text in any app and press Ctrl+Alt+S: it is read aloud with a voice on
this computer. Press it again to stop. Spanish text is read with a Spanish
voice and everything else with English; nothing leaves the computer.

%prep
cp -p %{SOURCE90} .
python3 -m py_compile %{SOURCE3}

%build

%install
UUID=parchaos-speak@parchaos.org
DEST=%{buildroot}%{_datadir}/gnome-shell/extensions/$UUID
mkdir -p "$DEST/schemas"
install -m 0644 %{SOURCE0} %{SOURCE1} "$DEST/"
install -m 0644 %{SOURCE2} "$DEST/schemas/"
glib-compile-schemas "$DEST/schemas"
install -Dm0755 %{SOURCE3} %{buildroot}%{_libexecdir}/parchaos-speak/parchaos-speak-say

%files
%license LICENSE
%{_libexecdir}/parchaos-speak/
%{_datadir}/gnome-shell/extensions/parchaos-speak@parchaos.org/

%changelog
* Wed Sep 30 2026 ParchaOS packaging - 1.0.0-1
- Initial package (ticket #162). Ctrl+Alt+S reads the highlighted text (or
  the clipboard) aloud with espeak-ng; pressing it again stops. The voice
  follows the text: Spanish (es-419) or US English.
