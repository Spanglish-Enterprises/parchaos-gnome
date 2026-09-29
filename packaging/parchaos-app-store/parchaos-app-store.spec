Name:           parchaos-app-store
Version:        1.0.0
Release:        1%{?dist}
Summary:        ParchaOS App Store integrations and helpers

License:        MIT
URL:            https://github.com/Spanglish-Enterprises/parchaos-gnome
Source0:        parchaos-app-store-files.tar.gz
Source90:       LICENSE

BuildArch:      noarch
Requires:       bash
Requires:       flatpak
Requires:       gnome-software

%description
Provides integration scripts and helpers for the ParchaOS App Store,
including a clean, dependency-tracked app uninstall helper that removes
orphaned Flatpak and RPM configuration directories.

%prep
%setup -q -c -n %{name}-%{version}
cp -p %{SOURCE90} .

%build
# Nothing to compile

%install
mkdir -p %{buildroot}
cp -a usr %{buildroot}/
chmod 0755 %{buildroot}%{_libexecdir}/parchaos-app-store-uninstall-helper

%files
%license LICENSE
%{_libexecdir}/parchaos-app-store-uninstall-helper

%changelog
* Mon Sep 28 2026 ParchaOS Project <hello@parchaos.com> - 1.0.0-1
- Initial package with clean app uninstall helper (Ticket #125)
