Name:           parchaos-whatsnew
Version:        1.0.0
Release:        2%{?dist}
Summary:        What changed in this version of ParchaOS
License:        GPL-3.0-or-later
URL:            https://github.com/Spanglish-Enterprises/parchaos-gnome
Source0:        parchaos-whatsnew
Source1:        org.parchaos.WhatsNew.desktop
Source2:        parchaos-whatsnew-autostart.desktop
Source3:        whatsnew.json
Source4:        es.po
Source90:       LICENSE
BuildArch:      noarch

BuildRequires:  desktop-file-utils
BuildRequires:  gettext
BuildRequires:  python3
Requires:       python3-gobject
Requires:       gtk4
Requires:       libadwaita

%description
ParchaOS What's New: one scrolling list of what changed in this version of
ParchaOS, with a short title and a plain description for each change. It
opens once after a major update (and not on a new account's first login),
and any time from the logo menu. "Show this after major updates" turns the
automatic window off. English and Spanish.

%prep
cp -p %{SOURCE90} .

%build

%install
install -Dm0755 %{SOURCE0} %{buildroot}%{_bindir}/parchaos-whatsnew
install -Dm0644 %{SOURCE1} %{buildroot}%{_datadir}/applications/org.parchaos.WhatsNew.desktop
install -Dm0644 %{SOURCE2} %{buildroot}%{_sysconfdir}/xdg/autostart/parchaos-whatsnew.desktop
install -Dm0644 %{SOURCE3} %{buildroot}%{_datadir}/parchaos/whatsnew/whatsnew.json
# Spanish (es_PR falls back to es). Another language: a Source line and one more msgfmt line.
install -d %{buildroot}%{_datadir}/locale/es/LC_MESSAGES
msgfmt --check -o %{buildroot}%{_datadir}/locale/es/LC_MESSAGES/parchaos-whatsnew.mo %{SOURCE4}

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/org.parchaos.WhatsNew.desktop
desktop-file-validate %{buildroot}%{_sysconfdir}/xdg/autostart/parchaos-whatsnew.desktop
python3 -c "import json; d = json.load(open('%{SOURCE3}')); assert d['version'] and d['entries']"

%files
%license LICENSE
%{_bindir}/parchaos-whatsnew
%{_datadir}/applications/org.parchaos.WhatsNew.desktop
%config(noreplace) %{_sysconfdir}/xdg/autostart/parchaos-whatsnew.desktop
%{_datadir}/parchaos/whatsnew/
%{_datadir}/locale/es/LC_MESSAGES/parchaos-whatsnew.mo

%changelog
* Fri Oct 02 2026 ParchaOS packaging - 1.0.0-2
- BuildRequires python3 for the content check in %check.

* Fri Oct 02 2026 ParchaOS packaging - 1.0.0-1
- Ticket #170: first version. A scrolling list of what changed in this version (ParchaOS's own design, no slideshow): a greeting, then a card per change; shown once after a major update (never on a new account's first login or in the live session), re-openable from the logo menu; a switch turns the automatic window off. The release content is a JSON file with English and Spanish text.
