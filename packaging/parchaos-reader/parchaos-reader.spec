# ==============================================================================
# Parcha Reader (ticket #184): any text in a calm reading window - large text in
# a chosen font, spacing and colours - read aloud with the current word
# highlighted. Ctrl+Alt+R (Parcha Speak) opens the selected text in it; with
# nothing selected it reads the focused app's page through the accessibility
# tree. The voice is espeak-ng through its library, so each word's moment in
# the audio is known; nothing leaves the computer.
# ==============================================================================

Name:           parchaos-reader
Version:        1.0.0
Release:        1%{?dist}
Summary:        Read any text in a calm window, aloud with each word highlighted

License:        GPL-3.0-or-later
URL:            https://github.com/Spanglish-Enterprises/parchaos-gnome
Source0:        parchaos-reader
Source1:        org.parchaos.Reader.desktop
Source2:        org.parchaos.reader.gschema.xml
Source3:        es.po
Source90:       LICENSE

BuildArch:      noarch
BuildRequires:  python3
BuildRequires:  gettext
BuildRequires:  desktop-file-utils

Requires:       python3-gobject
Requires:       gtk4
Requires:       libadwaita
Requires:       espeak-ng
# playbin, and wavparse for the speech it plays.
Requires:       gstreamer1-plugins-base
Requires:       gstreamer1-plugins-good
# The page of the focused app, when nothing is selected.
Requires:       at-spi2-core
# The voice choice (Spanish or English by the text) and the speed setting.
Requires:       parchaos-speak >= 1.0.0-3

%description
Parcha Reader shows any text in a calm reading window: large text in the font,
size, spacing and colours you choose. Read Aloud reads it with a voice on this
computer and highlights each word as it is spoken. Select text in any app and
press Ctrl+Alt+R to open it here.

%prep
cp -p %{SOURCE90} .
python3 -m py_compile %{SOURCE0}

%build

%install
install -Dm0755 %{SOURCE0} %{buildroot}%{_bindir}/parchaos-reader
install -Dm0644 %{SOURCE1} %{buildroot}%{_datadir}/applications/org.parchaos.Reader.desktop
install -Dm0644 %{SOURCE2} %{buildroot}%{_datadir}/glib-2.0/schemas/org.parchaos.reader.gschema.xml
install -d %{buildroot}%{_datadir}/locale/es/LC_MESSAGES
msgfmt --check -o %{buildroot}%{_datadir}/locale/es/LC_MESSAGES/parchaos-reader.mo %{SOURCE3}

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/org.parchaos.Reader.desktop

%files
%license LICENSE
%{_bindir}/parchaos-reader
%{_datadir}/applications/org.parchaos.Reader.desktop
%{_datadir}/glib-2.0/schemas/org.parchaos.reader.gschema.xml
%{_datadir}/locale/es/LC_MESSAGES/parchaos-reader.mo

%changelog
* Fri Nov 13 2026 ParchaOS packaging - 1.0.0-1
- Initial package (ticket #184): the reading window with font, size, line
  spacing and colours (Paper, Sepia, Night), and Read Aloud with the spoken
  word highlighted and kept in view. Text comes from Ctrl+Alt+R (the
  selection), from the focused app's page, or pasted in. English and Spanish.
