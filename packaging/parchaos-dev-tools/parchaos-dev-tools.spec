Name:           parchaos-dev-tools
Version:        1.0.0
Release:        1%{?dist}
Summary:        First-class developer tooling integration for ParchaOS

License:        MIT
URL:            https://github.com/Spanglish-Enterprises/parchaos-gnome
Source0:        parchaos-dev-tools-files.tar.gz
Source90:       LICENSE

BuildArch:      noarch
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

%files
%license LICENSE
%{_bindir}/parchaos-install-claude-code
%{_datadir}/applications/parchaos-install-claude-code.desktop

%changelog
* Mon Sep 28 2026 ParchaOS Project <hello@parchaos.com> - 1.0.0-1
- Initial release with Claude Code installer (Ticket #121)
