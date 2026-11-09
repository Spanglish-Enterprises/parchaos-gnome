Name:           parchaos-dev-tools
Version:        1.0.0
Release:        3%{?dist}
Summary:        First-class developer tooling integration for ParchaOS

License:        GPL-3.0-or-later
URL:            https://github.com/Spanglish-Enterprises/parchaos-gnome
Source0:        parchaos-dev-tools-files.tar.gz
Source90:       LICENSE

BuildArch:      noarch
BuildRequires:  libappstream-glib
Requires:       bash
Requires:       curl
Requires:       gnome-terminal

%description
Provides first-class developer tooling for ParchaOS, including
a one-click installer for Anthropic's Claude Code CLI.

%prep
%setup -q -c -n %{name}-%{version}
cp -p %{SOURCE90} .

%build
# Nothing to compile

%install
mkdir -p %{buildroot}
cp -a usr %{buildroot}/
chmod 0755 %{buildroot}%{_bindir}/parchaos-install-claude-code

%check
appstream-util validate-relax --nonet %{buildroot}%{_metainfodir}/parchaos-install-claude-code.metainfo.xml

%files
%license LICENSE
%{_bindir}/parchaos-install-claude-code
%{_datadir}/applications/parchaos-install-claude-code.desktop
%{_metainfodir}/parchaos-install-claude-code.metainfo.xml

%changelog
* Sun Nov 08 2026 ParchaOS packaging - 1.0.0-3
- Ticket #118: AppStream metainfo (English and Spanish), so Install Developer Tools is listed in Parcha Store and can be removed from there.

* Sun Nov 08 2026 ParchaOS packaging - 1.0.0-2
- Ticket #146: Spanish name and description in the .desktop file(s).

* Mon Sep 28 2026 ParchaOS Project <hello@parchaos.com> - 1.0.0-1
- Initial release with Claude Code installer (Ticket #121)
