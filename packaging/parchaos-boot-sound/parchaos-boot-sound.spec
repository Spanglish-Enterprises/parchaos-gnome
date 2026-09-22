# ==============================================================================
# A macOS-style "startup chime" — same real feature as
# Pear-Project/pearos-boot-sound, but NOT a direct port of that repo's
# own content or mechanism:
#
# 1. Its README explicitly says the bundled boot-sound.wav is "All
#    rights reserved" by a third party (zippy#8408), which conflicts
#    with the repo's own GitHub-detected GPL-3.0 license tag —
#    redistributing that specific file isn't safe just because the
#    repo as a whole shows a GPL badge. Instead, this plays
#    desktop-login.oga from pearos-sounds (already packaged in this
#    project from pearOS's own settings/sounds tarball, see
#    packaging/pearos-settings.spec) — a real asset already accepted
#    into the project, avoiding a new asset with an explicit
#    rights-reservation claim.
#
# 2. Upstream's own install.sh installs its unit as a plain SYSTEM
#    service (`/etc/systemd/system/`, `systemctl enable` with no
#    --user) running as root. That can't reliably reach a real user's
#    PipeWire/PulseAudio session (no XDG_RUNTIME_DIR/session bus
#    access from a system-level unit on a normal Fedora desktop, which
#    has no system-wide PipeWire instance) — likely why this feature
#    is such a minor/rarely-mentioned one even in real pearOS. This
#    packages it correctly instead: a systemd --user unit
#    (/usr/lib/systemd/user/), so it runs inside the logging-in user's
#    own session with real audio access, using paplay (from
#    pipewire-pulseaudio, already a baseline dependency of the KDE
#    Plasma desktop stack — confirmed present on a real Fedora 44 KDE
#    Spin box) instead of upstream's mpv. Zero new Requires beyond
#    pearos-sounds itself.
#
# Like pearos-calamares-config/parchaos-tmog, this is a small
# ParchaOS-original integration with no upstream release tarball --
# Source0 is a local tarball built from this directory's checked-in
# files/ tree:
#   tar czf parchaos-boot-sound-files.tar.gz -C files .
# into ~/rpmbuild/SOURCES/ before `rpmbuild -bs`.
# ==============================================================================

Name:           parchaos-boot-sound
Version:        1.0.0
Release:        1%{?dist}
Summary:        Plays a startup sound on login (macOS-style boot chime)

License:        NOASSERTION
URL:            https://github.com/Pear-Project/pearos-boot-sound
Source0:        parchaos-boot-sound-files.tar.gz
BuildArch:      noarch

Requires:       pearos-sounds
Requires:       pipewire-pulseaudio
%{?systemd_requires}
BuildRequires:  systemd-rpm-macros

%description
Plays desktop-login.oga (from pearos-sounds) once per login session via a
systemd --user oneshot service, matching real pearOS's own boot-chime
feature -- reimplemented as a proper user unit (see this spec's banner
comment) so it actually reaches the logging-in user's real audio
session, unlike upstream's own system-level unit.

%prep
%setup -q -c -n %{name}-%{version}

%install
mkdir -p %{buildroot}
cp -a usr %{buildroot}/

%post
%systemd_user_post parchaos-boot-sound.service

%preun
%systemd_user_preun parchaos-boot-sound.service

%files
%{_prefix}/lib/systemd/user/parchaos-boot-sound.service
%{_prefix}/lib/systemd/user-preset/90-parchaos-boot-sound.preset

%changelog
* Tue Sep 22 2026 ParchaOS packaging - 1.0.0-1
- Initial package. Verified the service file's target path
  (/usr/share/sounds/pearOS-sounds/stereo/desktop-login.oga) exists in
  the real pearos-sounds package build output, and that paplay is
  present by default on a real Fedora 44 KDE Spin box (from
  pipewire-pulseaudio, a transitive dependency of the desktop stack
  already).
