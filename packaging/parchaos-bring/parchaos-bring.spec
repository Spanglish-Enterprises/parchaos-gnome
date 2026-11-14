# ==============================================================================
# Bring Your Stuff (ticket #157): copy Documents, Pictures, Music, Videos, the
# desktop and downloads from another computer's disk (Windows, Mac or Linux), a
# backup drive or a network share, and its browser bookmarks (Chromium-based
# browsers, Firefox and the Mac's own browser) into Parcha Browser. The old disk is
# only read; one that isn't mounted is mounted read-only. Offered in Welcome.
# ==============================================================================

Name:           parchaos-bring
Version:        1.0.0
Release:        1%{?dist}
Summary:        Bring your files and bookmarks from another computer

License:        GPL-3.0-or-later
URL:            https://github.com/Spanglish-Enterprises/parchaos-gnome
Source0:        parchaos-bring
Source1:        bringlib.py
Source2:        org.parchaos.Bring.desktop
Source3:        es.po
Source90:       LICENSE

BuildArch:      noarch
BuildRequires:  python3
BuildRequires:  gettext
BuildRequires:  desktop-file-utils

Requires:       python3-gobject
Requires:       gtk4
Requires:       libadwaita
# Read-only mounting of the old disk; NTFS and exFAT are read by the kernel.
Requires:       udisks2
Recommends:     ntfs-3g
Recommends:     exfatprogs

%description
Bring Your Stuff copies your Documents, Pictures, Music, Videos, desktop and
downloads from another computer's disk, a backup drive or a network share, and
adds its browser bookmarks to Parcha Browser. It shows what it found and how
big it is first, never changes the old disk, never replaces a file here, and
says what it skipped.

%prep
cp -p %{SOURCE90} .
python3 -m py_compile %{SOURCE0} %{SOURCE1}

%build

%install
install -Dm0755 %{SOURCE0} %{buildroot}%{_bindir}/parchaos-bring
install -Dm0644 %{SOURCE1} %{buildroot}%{_datadir}/parchaos-bring/bringlib.py
install -Dm0644 %{SOURCE2} %{buildroot}%{_datadir}/applications/org.parchaos.Bring.desktop
install -d %{buildroot}%{_datadir}/locale/es/LC_MESSAGES
msgfmt --check -o %{buildroot}%{_datadir}/locale/es/LC_MESSAGES/parchaos-bring.mo %{SOURCE3}

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/org.parchaos.Bring.desktop

%files
%license LICENSE
%{_bindir}/parchaos-bring
%{_datadir}/parchaos-bring/
%{_datadir}/applications/org.parchaos.Bring.desktop
%{_datadir}/locale/es/LC_MESSAGES/parchaos-bring.mo

%changelog
* Sat Nov 14 2026 ParchaOS packaging - 1.0.0-1
- Initial package (ticket #157): finds people's folders on a Windows, Mac or
  Linux disk, a backup drive or a share; counts them; copies the chosen ones
  without overwriting (same files skipped, clashes kept with a number,
  unreadable files listed); imports bookmarks from Chromium-based browsers,
  Firefox and the Mac's own browser into Parcha Browser; lists Wi-Fi networks and explains
  what can't be brought (passwords). English and Spanish.
