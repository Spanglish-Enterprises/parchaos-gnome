# ==============================================================================
# Parcha Nearby (ticket #149): send files to nearby computers and phones, and
# receive them, over the local network with no account. Speaks the LocalSend
# protocol (our own implementation), so it works with the LocalSend apps for
# phones and other computers, and between ParchaOS computers. Parcher's Share
# button and right-click menu hand files to it.
# ==============================================================================

Name:           parchaos-nearby
Version:        1.0.0
Release:        1%{?dist}
Summary:        Send files to nearby computers and phones, and receive them

License:        GPL-3.0-or-later
URL:            https://github.com/Spanglish-Enterprises/parchaos-gnome
Source0:        parchaos-nearby
Source1:        org.parchaos.Nearby.desktop
Source2:        parchaos-nearby.service
Source3:        es.po
Source90:       LICENSE

BuildArch:      noarch
BuildRequires:  python3
BuildRequires:  gettext
BuildRequires:  desktop-file-utils
BuildRequires:  systemd-rpm-macros

Requires:       python3-gobject
Requires:       gtk4
Requires:       libadwaita
Requires:       glib2
# The certificate is made with openssl; network addresses come from ip.
Requires:       openssl
Requires:       iproute

%description
Nearby Devices sends files to computers and phones on the same network and
receives them, with no account and nothing leaving the local network. It
speaks the LocalSend protocol, so phones and computers with the LocalSend app
show up, as do other ParchaOS computers. Receiving always asks first, and
accepted files go to Downloads.

%prep
cp -p %{SOURCE90} .
python3 -m py_compile %{SOURCE0}

%build

%install
install -Dm0755 %{SOURCE0} %{buildroot}%{_bindir}/parchaos-nearby
install -Dm0644 %{SOURCE1} %{buildroot}%{_datadir}/applications/org.parchaos.Nearby.desktop
install -Dm0644 %{SOURCE2} %{buildroot}%{_userunitdir}/parchaos-nearby.service
# On for everyone, existing installs too (a preset only applies on first install).
mkdir -p %{buildroot}%{_userunitdir}/graphical-session.target.wants
ln -s ../parchaos-nearby.service \
    %{buildroot}%{_userunitdir}/graphical-session.target.wants/parchaos-nearby.service
install -d %{buildroot}%{_datadir}/locale/es/LC_MESSAGES
msgfmt --check -o %{buildroot}%{_datadir}/locale/es/LC_MESSAGES/parchaos-nearby.mo %{SOURCE3}

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/org.parchaos.Nearby.desktop

%files
%license LICENSE
%{_bindir}/parchaos-nearby
%{_datadir}/applications/org.parchaos.Nearby.desktop
%{_userunitdir}/parchaos-nearby.service
%{_userunitdir}/graphical-session.target.wants/parchaos-nearby.service
%{_datadir}/locale/es/LC_MESSAGES/parchaos-nearby.mo

%changelog
* Sat Nov 14 2026 ParchaOS packaging - 1.0.0-1
- Initial package (ticket #149): finds nearby devices (LocalSend protocol v2:
  multicast, then the local network address by address), sends files and
  folders with progress and Stop, checks each device's certificate
  fingerprint, receives with an Accept/Decline notification into Downloads,
  shows text messages, and can be turned off. English and Spanish.
