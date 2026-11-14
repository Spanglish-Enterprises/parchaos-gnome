# ==============================================================================
# Screen Lookup (ticket #180): press Ctrl+Shift+Space (physical Super+Shift+Space
# on the ParchaOS keyboard layout), drag a box around part of the screen, and
# copy the text in it, search the web for it or ask the assistant. The text is
# read on this computer by Tesseract (Apache-2.0; its English and Spanish data
# are Apache-2.0 too, in Fedora); nothing leaves the machine unless Search the
# Web is chosen.
# ==============================================================================

Name:           parchaos-lookup
Version:        1.0.0
Release:        1%{?dist}
Summary:        Look up the text in any part of the screen on ParchaOS

License:        GPL-3.0-or-later
URL:            https://github.com/Spanglish-Enterprises/parchaos-gnome
Source0:        extension.js
Source1:        metadata.json
Source2:        org.parchaos.lookup.gschema.xml
Source3:        parchaos-lookup-ocr
Source4:        stylesheet.css
Source5:        es.po
Source90:       LICENSE

BuildArch:      noarch
BuildRequires:  glib2
BuildRequires:  python3
BuildRequires:  gettext

Requires:       gnome-shell >= 48
Requires:       tesseract
Requires:       tesseract-langpack-eng
Requires:       tesseract-langpack-spa
Requires:       python3-gobject
Requires:       gdk-pixbuf2

%description
Press Ctrl+Shift+Space (Super+Shift+Space on the ParchaOS keyboard layout),
drag a box around text anywhere on the screen - in a picture, a paused video
or an app that will not let you select it - and copy the text, search the web
for it or ask the assistant. The text is read on this computer.

%prep
cp -p %{SOURCE90} .
python3 -m py_compile %{SOURCE3}

%build

%install
UUID=parchaos-lookup@parchaos.org
DEST=%{buildroot}%{_datadir}/gnome-shell/extensions/$UUID
mkdir -p "$DEST/schemas"
install -m 0644 %{SOURCE0} %{SOURCE1} %{SOURCE4} "$DEST/"
install -m 0644 %{SOURCE2} "$DEST/schemas/"
glib-compile-schemas "$DEST/schemas"
install -Dm0755 %{SOURCE3} %{buildroot}%{_libexecdir}/parchaos-lookup/parchaos-lookup-ocr
# Spanish (es_PR falls back to es).
install -d %{buildroot}%{_datadir}/locale/es/LC_MESSAGES
msgfmt --check -o %{buildroot}%{_datadir}/locale/es/LC_MESSAGES/parchaos-lookup.mo %{SOURCE5}

%files
%license LICENSE
%{_libexecdir}/parchaos-lookup/
%{_datadir}/gnome-shell/extensions/parchaos-lookup@parchaos.org/
%{_datadir}/locale/es/LC_MESSAGES/parchaos-lookup.mo

%changelog
* Fri Nov 13 2026 ParchaOS packaging - 1.0.0-1
- Initial package (ticket #180): Screen Lookup. The shortcut dims the screen;
  drag a box, and a glass popover offers Copy Text, Search the Web and Ask
  the Assistant for the text in it, read on this computer by Tesseract.
