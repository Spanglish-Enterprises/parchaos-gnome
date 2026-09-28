# ==============================================================================
# A recurring nightly "Focus mode" / Do Not Disturb schedule for GNOME.
# Toggles GNOME's own Do Not Disturb switch
# (org.gnome.desktop.notifications show-banners) on at the start time and
# off at the end time, and works out the right state from the clock at
# login, after sleep, and whenever the schedule changes in Settings.
#
# Default schedule: 22:00-08:00 nightly. Change by editing the
# installed *.timer files' OnCalendar= values (or copying them to
# ~/.config/systemd/user/ for a per-user override, standard systemd
# practice).
#
# History: 1.0.0-1/1.0.0-2 used two systemd --user timers calling the
# freedesktop.org Notifications Inhibit/UnInhibit D-Bus methods. That
# worked on KDE Plasma but GNOME Shell does not implement
# Notifications.Inhibit at all ("No such method"), so on GNOME the
# timers fired but never silenced anything. 1.1.0 switches to GNOME's
# own show-banners setting, and only undoes it in the morning if the
# schedule is what turned it on.
#
# parchaos-* since this is a product-original addition with no pearOS
# upstream relationship at all.
# ==============================================================================

Name:           parchaos-focus-schedule
Version:        1.1.0
Release:        4%{?dist}
Summary:        Recurring nightly Do Not Disturb schedule (22:00-08:00 by default)

License:        GPL-3.0-or-later
URL:            https://github.com/Spanglish-Enterprises/parchaos-gnome
Source0:        parchaos-focus-schedule-files.tar.gz
Source90:       LICENSE
BuildArch:      noarch

Requires:       parchaos-desktop-schemas >= 2026.09.23-33
Requires:       glib2
Requires:       python3-gobject
BuildRequires:  systemd-rpm-macros

%description
Scheduled Do Not Disturb: a small user service turns GNOME's own Do Not
Disturb on during a daily period (22:00 to 08:00 by default) and back
off afterwards. It works out the right state from the clock at login,
after sleep, at each start and end time, and whenever the schedule is
changed in ParchaOS Settings, so a computer that was off or asleep at
the boundary still ends up right. A Do Not Disturb the user switched on
themselves is left alone.

%prep
%setup -q -c -n %{name}-%{version}
cp -p %{SOURCE90} .

%install
install -Dm0755 usr/bin/parchaos-focus-schedule %{buildroot}%{_bindir}/parchaos-focus-schedule
install -Dm0644 usr/lib/systemd/user/parchaos-focus-schedule.service \
    %{buildroot}%{_userunitdir}/parchaos-focus-schedule.service
# Enabled for everyone, including existing installs (a preset only
# applies on first install).
mkdir -p %{buildroot}%{_userunitdir}/graphical-session.target.wants
ln -s ../parchaos-focus-schedule.service \
    %{buildroot}%{_userunitdir}/graphical-session.target.wants/parchaos-focus-schedule.service

%post
# Releases before 1.1.0 used two timers enabled globally by preset.
rm -f %{_sysconfdir}/systemd/user/timers.target.wants/parchaos-focus-start.timer \
      %{_sysconfdir}/systemd/user/timers.target.wants/parchaos-focus-end.timer || :

%files
%license LICENSE
%{_bindir}/parchaos-focus-schedule
%{_userunitdir}/parchaos-focus-schedule.service
%{_userunitdir}/graphical-session.target.wants/parchaos-focus-schedule.service

%changelog
* Sat Sep 26 2026 ParchaOS packaging - 1.1.0-4
- Rewrite the spec banner: the package is GNOME-only now (toggles
  show-banners), so lead with that instead of the old KDE/timers
  research. Keep the history as a note.
* Sat Sep 26 2026 ParchaOS packaging - 1.1.0-3
- Ship the license text (%license) with an accurate SPDX License tag.
* Sat Sep 26 2026 ParchaOS packaging - 1.1.0-2
- Require parchaos-desktop-schemas (the settings schema) instead of
  relying on the desktop meta-package.
* Sat Sep 26 2026 ParchaOS packaging - 1.1.0-1
- Replace the two fixed timers with a user service that works out the
  right Do Not Disturb state from the clock at login, after sleep, at
  each boundary and when the schedule changes; times and on/off come
  from ParchaOS settings (org.parchaos.desktop focus-schedule, focus-
  start, focus-end).
* Fri Sep 25 2026 ParchaOS packaging - 1.0.0-2
- Real bug found on real hardware: GNOME Shell has no
  Notifications.Inhibit method, so focus-start failed every night and
  nothing was ever silenced. Switched to GNOME's Do Not Disturb setting
  (show-banners), leaving a user's own Do Not Disturb untouched. Verified
  by running both services on the live session and reading show-banners
  back, including the already-on case.
* Tue Sep 22 2026 ParchaOS packaging - 1.0.0-1
- Initial package. Verified the Inhibit/UnInhibit D-Bus calls succeed
  and are idempotent against a real running Plasma session (the build VM) --
  not yet visually confirmed that a real notification popup is
  actually suppressed while inhibited (would need a live screenshot
  cycle, not attempted). Not yet confirmed the timers themselves fire
  correctly on their real schedule (would need waiting for a real
  22:00/08:00 boundary or manually adjusting the system clock to
  test) -- the underlying systemd --user timer mechanism itself is
  standard, well-established behavior already used successfully
  elsewhere in this project (parchaos-boot-sound), so this is lower
  risk than the D-Bus/notification behavior itself.
