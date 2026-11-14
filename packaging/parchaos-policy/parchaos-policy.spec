# ==============================================================================
# parchaos-policy (ticket #168): managed defaults and locks for organisations from
# one file, /etc/parchaos/policy.toml. Copy the file in and a path unit applies it:
# GNOME/ParchaOS settings and locks through the dconf system database, Parcha
# Browser through Chromium managed policies, automatic updates through
# dnf5-automatic. No server, no agent. Guide: admin-guide.md (English and Spanish).
# ==============================================================================

Name:           parchaos-policy
Version:        1.0.0
Release:        2%{?dist}
Summary:        Set and lock ParchaOS settings for a school or office from one file

License:        GPL-3.0-or-later
URL:            https://github.com/Spanglish-Enterprises/parchaos-gnome
Source0:        parchaos-policy
Source1:        parchaos-policy.path
Source2:        parchaos-policy.service
Source3:        policy.example.toml
Source4:        admin-guide.md
Source5:        admin-guide.es.md
Source90:       LICENSE

BuildArch:      noarch
BuildRequires:  python3
BuildRequires:  systemd-rpm-macros

# tomllib
Requires:       python3 >= 3.11
Requires:       python3-gobject
Requires:       dconf
# Automatic updates when a policy asks for them.
Requires:       dnf5-plugin-automatic
%{?systemd_requires}

%description
Lets a school or an office set the same defaults on every ParchaOS computer,
and lock the ones people should not change, with one text file copied to
/etc/parchaos/policy.toml: appearance, screen lock, privacy switches,
extensions, the dock, automatic updates, Parcha Browser policies and any other
setting. It is applied by itself when the file changes, using Fedora's
standard dconf, Chromium and dnf5-automatic files. "parchaos-policy check"
explains a policy before it is used.

%prep
cp -p %{SOURCE90} %{SOURCE3} %{SOURCE4} %{SOURCE5} .
python3 -m py_compile %{SOURCE0}

%build

%install
install -Dm0755 %{SOURCE0} %{buildroot}%{_bindir}/parchaos-policy
install -Dm0644 %{SOURCE1} %{buildroot}%{_unitdir}/parchaos-policy.path
install -Dm0644 %{SOURCE2} %{buildroot}%{_unitdir}/parchaos-policy.service
install -d %{buildroot}%{_sysconfdir}/parchaos
install -d %{buildroot}%{_sharedstatedir}/parchaos-policy

%post
%systemd_post parchaos-policy.path parchaos-policy.service
# Watch the file from now on, not only after the next boot.
if [ $1 -eq 1 ]; then
    systemctl enable parchaos-policy.service >/dev/null 2>&1 || :
    systemctl enable --now parchaos-policy.path >/dev/null 2>&1 || :
fi

%preun
%systemd_preun parchaos-policy.path parchaos-policy.service

%postun
%systemd_postun parchaos-policy.path parchaos-policy.service

%files
%license LICENSE
%doc admin-guide.md admin-guide.es.md policy.example.toml
%{_bindir}/parchaos-policy
%{_unitdir}/parchaos-policy.path
%{_unitdir}/parchaos-policy.service
%dir %{_sysconfdir}/parchaos
%dir %{_sharedstatedir}/parchaos-policy

%changelog
* Sat Nov 14 2026 ParchaOS packaging - 1.0.0-2
- Without systemd-analyze (build machines), check the update time against the
  shapes systemd accepts instead of letting any words through.

* Sat Nov 14 2026 ParchaOS packaging - 1.0.0-1
- Initial package (ticket #168): the policy file (organisation, appearance,
  screen, privacy, extensions, apps, updates, browser, any setting), with
  defaults or locks per section; check, apply, status, remove; applied by a
  path unit when the file changes, undone when it is removed; admin guide in
  English and Spanish.
