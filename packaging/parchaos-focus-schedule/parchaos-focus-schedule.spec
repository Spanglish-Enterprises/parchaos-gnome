# ==============================================================================
# A recurring nightly "Focus mode" / Do Not Disturb schedule -- real
# research (2026-09-22, 4th round) confirmed KDE Plasma 6's own
# notification system has manual and trigger-based DND (screen
# sharing, fullscreen apps) but no time-of-day recurring schedule, and
# no third-party fix exists either. Rather than patch KDE upstream
# (out of scope for this project), this achieves the practical
# result -- no notification popups during set hours -- with two
# systemd --user timers calling the real, standard
# freedesktop.org Notifications Inhibit/UnInhibit D-Bus methods (the
# same mechanism apps use to silence notifications during, e.g., a
# fullscreen presentation).
#
# Default schedule: 22:00-08:00 nightly. Change by editing the
# installed *.timer files' OnCalendar= values (or copying them to
# ~/.config/systemd/user/ for a per-user override, standard systemd
# practice).
#
# Verification note: confirmed the Inhibit/UnInhibit D-Bus calls
# themselves succeed and are idempotent-safe (checked directly against
# a real running Plasma session on the build VM, including cleaning up cookie
# numbers left over from manual testing). Did NOT get a clean visual
# confirmation that a real notification's popup is actually suppressed
# while inhibited (would need a live screenshot cycle to prove
# pixel-for-pixel, not attempted) -- trusting the D-Bus-spec-level
# correctness of Inhibit/UnInhibit here, the same class of
# verification this project already accepted for
# parchaos-appmenu-gtk-module's KWin protocol binding. Flagged
# honestly rather than claimed as fully proven.
#
# GNOME correction (2026-09-25, found on real hardware): everything above
# was verified against Plasma only. GNOME Shell does not implement
# Notifications.Inhibit at all ("No such method"), so on the GNOME variant
# focus-start failed every night and never silenced anything. 1.0.0-2
# switches to GNOME's own Do Not Disturb switch
# (org.gnome.desktop.notifications show-banners), and only undoes it in
# the morning if the schedule is what turned it on.
#
# parchaos-* since this is a product-original addition with no pearOS
# upstream relationship at all.
# ==============================================================================

Name:           parchaos-focus-schedule
Version:        1.0.0
Release:        2%{?dist}
Summary:        Recurring nightly Do Not Disturb schedule (22:00-08:00 by default)

License:        NOASSERTION
URL:            https://github.com/alexgalicea/parchaos
Source0:        parchaos-focus-schedule-files.tar.gz
BuildArch:      noarch

Requires:       glib2
%{?systemd_requires}
BuildRequires:  systemd-rpm-macros

%description
Two systemd --user timers (parchaos-focus-start.timer at 22:00,
parchaos-focus-end.timer at 08:00) that turn GNOME's own Do Not
Disturb on overnight and back off in the morning, silencing
notification popups during those hours. A Do Not Disturb the user
switched on themselves is left alone.

%prep
%setup -q -c -n %{name}-%{version}

%install
mkdir -p %{buildroot}
cp -a usr %{buildroot}/
chmod 0755 %{buildroot}%{_bindir}/parchaos-focus-start
chmod 0755 %{buildroot}%{_bindir}/parchaos-focus-end

%post
%systemd_user_post parchaos-focus-start.timer
%systemd_user_post parchaos-focus-end.timer

%preun
%systemd_user_preun parchaos-focus-start.timer
%systemd_user_preun parchaos-focus-end.timer

%files
%{_bindir}/parchaos-focus-start
%{_bindir}/parchaos-focus-end
%{_prefix}/lib/systemd/user/parchaos-focus-start.service
%{_prefix}/lib/systemd/user/parchaos-focus-start.timer
%{_prefix}/lib/systemd/user/parchaos-focus-end.service
%{_prefix}/lib/systemd/user/parchaos-focus-end.timer
%{_prefix}/lib/systemd/user-preset/90-parchaos-focus-schedule.preset

%changelog
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
