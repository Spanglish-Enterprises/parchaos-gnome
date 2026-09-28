Name:           parchaos-dev-tools
Version:        1.0.0
Release:        1%{?dist}
Summary:        First-class developer tooling integration for ParchaOS

License:        MIT
URL:            https://github.com/Spanglish-Enterprises/parchaos-gnome
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch
Requires:       bash
Requires:       curl
Requires:       gnome-terminal

%description
Provides first-class developer tooling for ParchaOS, including
a one-click installer for Anthropic's Claude Code CLI.

%prep
%setup -q -c -T

%build
# Nothing to build

%install
mkdir -p %{buildroot}
cp -a %{_sourcedir}/files/* %{buildroot}/
chmod +x %{buildroot}/usr/bin/parchaos-install-claude-code

%files
%license %{_sourcedir}/LICENSE
/usr/bin/parchaos-install-claude-code
/usr/share/applications/parchaos-install-claude-code.desktop

%changelog
* Mon Sep 28 2026 ParchaOS Project <hello@parchaos.com> - 1.0.0-1
- Initial release with Claude Code installer (Ticket #121)
