Name:           parchaos-app-store
Version:        1.0.0
Release:        1%{?dist}
Summary:        ParchaOS App Store integrations and helpers

License:        MIT
URL:            https://github.com/Spanglish-Enterprises/parchaos-gnome
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch
Requires:       bash
Requires:       flatpak
Requires:       gnome-software

%description
Provides integration scripts and helpers for the ParchaOS App Store,
including a clean, dependency-tracked app uninstall helper that removes
orphaned Flatpak and RPM configuration directories.

%prep
%setup -q -c -T

%build
# Nothing to build

%install
mkdir -p %{buildroot}
cp -a %{_sourcedir}/files/* %{buildroot}/
chmod +x %{buildroot}/usr/libexec/parchaos-app-store-uninstall-helper

%files
%license %{_sourcedir}/LICENSE
/usr/libexec/parchaos-app-store-uninstall-helper

%changelog
* Mon Sep 28 2026 ParchaOS Project <hello@parchaos.com> - 1.0.0-1
- Initial package with clean app uninstall helper (Ticket #125)
