# ==============================================================================
# Ambient Sounds for ParchaOS (ticket #183). Every sound is generated while it
# plays (noise, tones, filters and slow random swells); no recordings, so no
# third-party sound licences. Original code for ParchaOS.
# ==============================================================================

Name:           parchaos-ambient
Version:        1.0.0
Release:        1%{?dist}
Summary:        Ambient Sounds: rain, ocean, stream, night and noise, with a timer
License:        GPL-3.0-or-later
URL:            https://github.com/Spanglish-Enterprises/parchaos-gnome
Source0:        parchaos-ambient
Source1:        org.parchaos.Ambient.service
Source2:        README.md
Source90:       LICENSE
BuildArch:      noarch

BuildRequires:  python3
Requires:       python3-gobject
Requires:       gstreamer1
# audiotestsrc, audiomixer, volume, audioconvert, autoaudiosink
Requires:       gstreamer1-plugins-base
# audiocheblimit and audiochebband (audiofx), pulsesink
Requires:       gstreamer1-plugins-good
# Settings: the ambient-* keys of org.parchaos.desktop.
Requires:       parchaos-desktop-schemas >= 2026.09.23-82

%description
Calm background sound for ParchaOS: rain, ocean, stream, night, and white,
pink or brown noise, at its own volume under everything else, with a tone
control (warmer or brighter) and a timer from 15 minutes to 8 hours. All of
it is generated while it plays; nothing is recorded. Controlled from Parcha
Controls (Ambient Sounds) and ParchaOS Settings > Sound.

%prep
cp -p %{SOURCE90} %{SOURCE2} .

%build

%install
install -Dm0755 %{SOURCE0} %{buildroot}%{_bindir}/parchaos-ambient
install -Dm0644 %{SOURCE1} %{buildroot}%{_datadir}/dbus-1/services/org.parchaos.Ambient.service

%check
python3 -m py_compile %{SOURCE0}

%files
%license LICENSE
%doc README.md
%{_bindir}/parchaos-ambient
%{_datadir}/dbus-1/services/org.parchaos.Ambient.service

%changelog
* Mon Nov 09 2026 ParchaOS packaging - 1.0.0-1
- Ticket #183: first version. Rain, ocean, stream, night, white, pink and brown noise, all generated (no recordings), levelled to the same loudness; volume, tone and a 15 min to 8 h timer from org.parchaos.desktop; a D-Bus service (org.parchaos.Ambient) that only runs while a sound plays.
