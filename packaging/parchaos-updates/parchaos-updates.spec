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
Release:        3%{?dist}
Summary:        Check for ParchaOS updates and notify

License:        GPL-3.0-or-later
URL:            https://github.com/Spanglish-Enterprises/parchaos-gnome
Source0:        parchaos-updates-check
Source1:        usr/lib/systemd/user/parchaos-updates.service
Source2:        usr/lib/systemd/user/parchaos-updates.timer
Source90:       LICENSE
BuildArch:      noarch

BuildRequires:  systemd-rpm-macros

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
# Enable the timer for every user with a packaged wants symlink, the way
# parchaos-desktop enables its user units. %%systemd_user_post only acts on a
# first install and needs a preset, and this package ships none, so the timer
# was installed but disabled and never ran.
mkdir -p %{buildroot}%{_userunitdir}/timers.target.wants
ln -s ../parchaos-updates.timer \
    %{buildroot}%{_userunitdir}/timers.target.wants/parchaos-updates.timer

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
%{_userunitdir}/timers.target.wants/parchaos-updates.timer

%changelog
* Tue Sep 29 2026 ParchaOS packaging - 1.0.0-3
- Two bugs found by running it on a real Fedora 44 desktop (ticket #37):
  the timer was installed but disabled (nothing enabled it: no wants
  symlink and no preset), so no notification would ever have appeared; and
  the update count included dnf5's "Upgrades" heading, so it always said one
  more than there were. Now enabled by a packaged timers.target.wants
  symlink, and only name.arch lines are counted.
* Tue Sep 29 2026 ParchaOS packaging - 1.0.0-2
- Fix the first COPR build (1.0.0-1 failed): %%{_userunitdir} and the
  %%systemd_user_* scriptlet macros come from systemd-rpm-macros, which
  was never a BuildRequires -- the spec parsed fine on a machine that
  happened to have it installed, but a clean build chroot doesn't, so the
  unit paths expanded to nothing ("File must begin with /").
* Sun Sep 27 2026 ParchaOS packaging - 1.0.0-1
- Initial package. Adds a systemd user timer + service that checks for
  updates every 6 hours and sends a desktop notification.
