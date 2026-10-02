# ==============================================================================
# Parcha Sky -- ParchaOS's weather app (ticket #192, spec docs/weather-app-spec.md).
# The window is the sky outside right now: a living background drawn from real
# data (sun height, clouds moved by the real wind, rain, snow, fog, thunder),
# with the forecast on frosted glass cards. MET Norway forecasts (attribution
# shown), US National Weather Service alerts for the US and Puerto Rico. No
# accounts or keys; only coordinates rounded to about 1 km are sent.
# Original code for ParchaOS.
# ==============================================================================

Name:           parchaos-sky
Version:        0.3.2
Release:        1%{?dist}
Summary:        Parcha Sky, the ParchaOS weather app

License:        GPL-3.0-or-later
URL:            https://github.com/Spanglish-Enterprises/parchaos-gnome
Source0:        parchaos-sky
Source1:        org.parchaos.Sky.desktop
Source2:        org.parchaos.Sky.svg
Source3:        parchaos-sky-map.json.gz
Source4:        org.parchaos.Sky.metainfo.xml
Source5:        es.po
Source6:        parchi-front.svgz
Source7:        parchi-waving.svgz
Source8:        parchi-sunny.svgz
Source9:        parchi-sunset.svgz
Source10:       parchi-rain.svgz
Source11:       parchi-cloudy.svgz
Source12:       parchi-foggy.svgz
Source13:       parchi-storm.svgz
Source14:       parchi-snowy.svgz
Source15:       parchi-cold.svgz
Source16:       parchi-windy.svgz
Source17:       parchi-night.svgz
Source90:       LICENSE

BuildArch:      noarch
BuildRequires:  desktop-file-utils
BuildRequires:  gettext
BuildRequires:  libappstream-glib

Requires:       python3-gobject
Requires:       gtk4
Requires:       libadwaita
Requires:       libsoup3
Requires:       python3-cairo
# Parchi's artwork (SVG); without it the hand-drawn Parchi stands in
Requires:       librsvg2
# Offline city search and the location the user allows.
Requires:       libgweather >= 4
Requires:       geoclue2-libs

%description
Parcha Sky shows the weather as the sky outside right now: the background
follows the real sun, clouds, wind, rain and snow for the place, and the
forecast sits on frosted glass cards (solid cards in the Classic style).
Hourly and 10-day forecasts, official alerts in the US and Puerto Rico,
wind, UV, humidity, sun and moon, in English and Spanish.

%prep
cp -p %{SOURCE90} .

%build

%install
install -Dm0755 %{SOURCE0} %{buildroot}%{_bindir}/parchaos-sky
install -Dm0644 %{SOURCE1} %{buildroot}%{_datadir}/applications/org.parchaos.Sky.desktop
install -Dm0644 %{SOURCE2} %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/org.parchaos.Sky.svg
install -Dm0644 %{SOURCE3} %{buildroot}%{_datadir}/parchaos-sky/parchaos-sky-map.json.gz
install -Dm0644 %{SOURCE4} %{buildroot}%{_metainfodir}/org.parchaos.Sky.metainfo.xml
install -m0644 %{SOURCE6} %{SOURCE7} %{SOURCE8} %{SOURCE9} %{SOURCE10} %{SOURCE11} %{SOURCE12} %{SOURCE13} %{SOURCE14} %{SOURCE15} %{SOURCE16} %{SOURCE17} %{buildroot}%{_datadir}/parchaos-sky/
# Spanish (es_PR falls back to es). Another language: a Source line and one more msgfmt line.
install -d %{buildroot}%{_datadir}/locale/es/LC_MESSAGES
msgfmt --check -o %{buildroot}%{_datadir}/locale/es/LC_MESSAGES/parchaos-sky.mo %{SOURCE5}

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/org.parchaos.Sky.desktop
appstream-util validate-relax --nonet %{buildroot}%{_metainfodir}/org.parchaos.Sky.metainfo.xml

%files
%license LICENSE
%{_bindir}/parchaos-sky
%{_datadir}/applications/org.parchaos.Sky.desktop
%{_datadir}/icons/hicolor/scalable/apps/org.parchaos.Sky.svg
%{_datadir}/parchaos-sky/
%{_metainfodir}/org.parchaos.Sky.metainfo.xml
%{_datadir}/locale/es/LC_MESSAGES/parchaos-sky.mo

%changelog
* Fri Oct 02 2026 ParchaOS packaging - 0.3.2-1
- Ticket #192: six more poses from the owner's second character kit: waving (happy), night (gazing at the moon), cold (beanie, scarf, shivering), snowy (parka), foggy, sunset (sunglasses, beach drink). New moods for fog and for a clear sunset; the round scenes stay level and breathe; the cold pose shivers; eyelids take the face's own colour.

* Fri Oct 02 2026 ParchaOS packaging - 0.3.1-2
- Ticket #192: the place and temperature sit dead centre; Parchi keeps them company off to one side instead of sharing the centre.

* Fri Oct 02 2026 ParchaOS packaging - 0.3.1-1
- Ticket #192: Parchi uses the owner's own character art, traced to vectors (one SVG per pose: front, sunny, rain, partly cloudy, storm, snow, windy, with their scenery). Parchi bobs, sways in the wind, nods to the music in storms, floats with the cloud and blinks now and then; at night the front pose gets sleepy lids and drifting z's. The hand-drawn Parchi stays as the fallback.

* Fri Oct 02 2026 ParchaOS packaging - 0.3.0-2
- Ticket #192: the character is Parchi the Parchita, redrawn after the owner's character kit: maroon rind, pink rim, golden pulp with radiating seeds, big eyes, stubby limbs; poses for sunny (sunglasses, drink), rain (hooded raincoat, leaf umbrella, boots), partly cloudy (sitting in a cloud), storm (headphones), snow and cold (beanie, scarf), wind (leafy branch, squinting), night (nightcap); expressions happy, neutral, concerned, surprised, sleepy, sad.

* Fri Oct 02 2026 ParchaOS packaging - 0.3.0-1
- Ticket #192: next hour reads drizzle as well as rain from the radar (graded none / drizzle / rain); every string goes through gettext (po/parchaos-sky.pot, Spanish in po/es.po, day names translated in-app so they work without a system language pack); AppStream metainfo with screenshots; the hourly strip keeps the scrubbed hour in view; drizzle bars visible; placeholders named for translators.

* Fri Oct 02 2026 ParchaOS packaging - 0.2.0-1
- Ticket #192: lenses (temperature, rain, wind, comfort), heads-up for the next 48 hours, time scrubber and 24-hour time-lapse of the sky, best time to be outside with your own comfort range, comfort in plain words, two columns on wide windows, trips from your calendar (opt-in, local), hurricane season card (US National Hurricane Center), coquí nights in Puerto Rico (opt-in, synthesised), Parchita character (preview), radar map (LibreWXR, CC BY 4.0 data) over a Natural Earth map, next-hour rain from the radar nowcast. Puerto Rico uses Fahrenheit and mph.

* Fri Oct 02 2026 ParchaOS packaging - 0.1.0-1
- Ticket #192: first version of Parcha Sky. Living sky from real data (sun elevation and day position, stars and moon phase, clouds drifting with the wind, rain and snow by intensity, fog, thunder flashes), frosted glass cards over it (solid in Classic), now / alerts / 24 hours / 10 days / wind, UV, humidity, sun, pressure, moon; MET Norway data with attribution and its Expires caching, US NWS alerts; places from GNOME Weather, GeoClue or an offline city search; playful or plain summaries; English and Spanish; units follow the locale.
