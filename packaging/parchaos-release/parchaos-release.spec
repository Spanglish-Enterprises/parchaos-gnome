Name:           parchaos-release
Version:        1.0.0
Release:        1%{?dist}
Summary:        ParchaOS name, logo and links in os-release
License:        GPL-3.0-or-later
URL:            https://github.com/alexgalicea/parchaos-gnome
Source0:        parchaos-os-release
Source1:        parchaos-logo.svg
Source2:        parchaos-logo-symbolic.svg
BuildArch:      noarch

Requires:       fedora-release-common
Requires(post): coreutils, grep

%description
Brands the system as ParchaOS in /etc/os-release: name, logo, default
hostname and support links, which GNOME's About page, the boot menu and
other tools show. Version fields stay Fedora's, so dnf and version checks
keep working. Fedora's release package replaces /etc/os-release on every
update, so a trigger writes it again afterwards. Also installs the
ParchaOS logo the os-release LOGO field names.

%prep

%build

%install
install -Dm0755 %{SOURCE0} %{buildroot}%{_libexecdir}/parchaos-os-release
install -Dm0644 %{SOURCE1} %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/parchaos-logo.svg
install -Dm0644 %{SOURCE2} %{buildroot}%{_datadir}/icons/hicolor/symbolic/apps/parchaos-logo-symbolic.svg

%post
%{_libexecdir}/parchaos-os-release || :

%triggerin -- fedora-release-common
%{_libexecdir}/parchaos-os-release || :

%postun
# On removal, give /etc/os-release back to Fedora.
if [ "$1" -eq 0 ]; then
    ln -sf ../usr/lib/os-release /etc/os-release || :
fi

%files
%{_libexecdir}/parchaos-os-release
%{_datadir}/icons/hicolor/scalable/apps/parchaos-logo.svg
%{_datadir}/icons/hicolor/symbolic/apps/parchaos-logo-symbolic.svg

%changelog
* Sat Sep 26 2026 ParchaOS packaging - 1.0.0-1
- First release: ParchaOS os-release branding kept across Fedora
  release-package updates, and the ParchaOS logo icon.
