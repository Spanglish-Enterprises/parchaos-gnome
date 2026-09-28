# ==============================================================================
# parchaos-updates -- check for COPR + Fedora updates and notify the user.
#
# A systemd user timer + service that runs `dnf check-update` every 6 hours
# and sends a desktop notification when updates are available. Previously,
# updates only surfaced when the user manually ran `sudo dnf upgrade` or opened
# GNOME Software; the 6-hour COPR metadata_expire only kept metadata fresh,
# nothing actually checked or notified.
#
# Original code for ParchaOS, GPL-3.0-or-later.
# ==============================================================================

Name:           parchaos-updates
Version:        1.0.0
Release:        1%{?dist}
Summary:        Check for ParchaOS updates and notify

License:        GPL-3.0-or-later
URL:            https://github.com/Spanglish-Enterprises/parchaos-gnome
Source0:        parchaos-updates-check
Source1:        usr/lib/systemd/user/parchaos-updates.service
Source2:        usr/lib/systemd/user/parchaos-updates.timer
Source90:       LICENSE
BuildArch:      noarch

Requires:       dnf
Requires(post): systemd

%description
A systemd user timer and service that checks for available package updates
every 6 hours and sends a desktop notification when updates are found. This
surfaces both COPR and Fedora updates that would otherwise only appear when
the user manually runs dnf upgrade or opens GNOME Software.

%prep
cp -p %{SOURCE90} .

%build

%install
install -Dm0755 %{SOURCE0} %{buildroot}%{_bindir}/parchaos-updates-check
install -Dm0644 %{SOURCE1} %{buildroot}%{_userunitdir}/parchaos-updates.service
install -Dm0644 %{SOURCE2} %{buildroot}%{_userunitdir}/parchaos-updates.timer

%post
%systemd_user_post parchaos-updates.service
%systemd_user_post parchaos-updates.timer

%preun
%systemd_user_preun parchaos-updates.service
%systemd_user_preun parchaos-updates.timer

%postun
%systemd_user_postun parchaos-updates.service
%systemd_user_postun parchaos-updates.timer

%files
%license LICENSE
%{_bindir}/parchaos-updates-check
%{_userunitdir}/parchaos-updates.service
%{_userunitdir}/parchaos-updates.timer

%changelog
* Sun Sep 27 2026 ParchaOS packaging - 1.0.0-1
- Initial package. Adds a systemd user timer + service that checks for
  updates every 6 hours and sends a desktop notification.
