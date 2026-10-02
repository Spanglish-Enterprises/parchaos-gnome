# ParchaOS weather app: spec

Status: 2026-10-02, owner request: "The current weather app is very limited and lacking. I want
something better, prettier, more dynamic, alive, hyperlocal, quirky even (possibly play with the
Parcha theme a bit). Design it with the glass effect in mind; at minimum compatible with it."
Ticket: #. Replaces GNOME Weather as the default weather app.

Working name: **Parcha Weather** (fits Parcha Keys, Parcha Browser, Parcha Backup). Owner to pick;
alternatives with a local flavour: *Cielito*, *Parcha Sky*. Original name either way.

## 1. What it must feel like

- **Alive:** the window *is* the sky outside, right now: a living background driven by real data
  (sun and moon position for this place and time, cloud cover, wind speed and direction, rain or
  snow intensity, fog, lightning), moving gently, never busy.
- **Hyperlocal:** "rain starts in about 12 minutes here", not "60% chance today"; local alerts
  (hurricanes, floods, heat) first; sea and waves on the coast; air quality and UV.
- **Quirky, with Parcha personality:** a small passion-fruit character (working name *Parchita*,
  original artwork, consistent with the halved-passion-fruit logo) that dresses for the weather
  (umbrella, sunglasses, scarf, hiding from thunder) and one-line plain-talk summaries in English or
  Spanish ("Calorón hasta las 4, después aguacero."). A Personality switch: Playful / Plain.
- **Calm and readable:** the information always wins over the decoration; reduced-motion users get
  a still sky.

## 2. Layout (glass first)

One window, sky behind, content as glass cards on top:

1. **Now:** place name, big temperature, condition, high/low, feels-like; Parchita next to it; the
   plain-talk line.
2. **Alerts banner** (only when there is one): coloured by severity, tap for details and the
   official text; hurricanes show the forecast cone on the map card.
3. **Next hour** (where minute-level data exists): a small precipitation curve with "starts in /
   stops in" wording.
4. **Hourly strip:** 24-48 h, temperature line with symbols, rain chance, wind arrows.
5. **10 days:** rows with symbol, rain chance, and a low-to-high temperature bar (the bar's colour
   follows temperature).
6. **Cards** (rearrangeable, like Control Center): wind (compass, gusts), UV, humidity and dew
   point, air quality, sunrise/sunset arc with daylight length, moon phase, pressure trend,
   visibility, sea (waves, sea temperature, tides) on the coast, pollen where available.
7. **Map card:** radar / precipitation, temperature and wind layers; storm tracks.

Several places: a sidebar or swipe between places; each place keeps its own sky.

### Glass and styles
- The app draws its own sky, so its cards can be *real* frosted glass in-app: GTK's blur render
  node over the sky (`Gtk.Snapshot.push_blur`) with our tint, rim highlight and the measured
  continuous corners (same parameters as the shell's `parchaos-glass`).
- Follows `org.parchaos.desktop style`: Glass = translucent cards; Classic = solid cards, same
  layout. Follows the glass clarity setting once #171 exists. Light/dark from the system, but the
  sky itself follows real day and night.
- Window chrome as the rest of ParchaOS (libadwaita, our theme).

## 3. Data (no accounts, no keys, private)

Only coarse coordinates (rounded to about 1 km) go to weather services; nothing else about the
user. Results cached; refresh every 10-15 minutes while open, slower in the background.

| Need | Default source | Licence / terms (to confirm before shipping) |
|---|---|---|
| Global forecast (hourly, 10 days) | MET Norway Locationforecast (what GWeather uses today) | Free, attribution required, identifying User-Agent, rate limits |
| US and Puerto Rico forecasts and **alerts** | US National Weather Service API (api.weather.gov) | US public domain, User-Agent required |
| Hurricanes (cone, track) | US National Hurricane Center feeds | US public domain |
| Minute-level rain (next hour) | MET Norway Nowcast (Nordic only) / radar extrapolation elsewhere | as above |
| Radar tiles | NOAA radar (US/PR); a global provider to be chosen | NOAA public domain; others: check terms |
| Air quality, UV, pollen, marine | candidates: Open-Meteo (Air quality, Marine), CAMS | **Open-Meteo's free API is for non-commercial use**; Spanglish Enterprises is a company: needs their paid plan, self-hosting (AGPL server) or another source. **Owner decision.** |
| Place search | GWeather's offline location database, then OpenStreetMap Nominatim for anything else | Nominatim: usage policy, attribution |
| Your location | GeoClue, with the existing consent | local |

Every source shown in an About/Sources sheet with its attribution, as the menu's weather item
does today.

## 4. Built how

- GTK 4 + libadwaita app (Python like our Settings app, or Rust if the sky needs the speed; to
  decide after a prototype). The sky is a `Gtk.GLArea` shader: gradient from sun elevation,
  procedural clouds moved by real wind, particle rain/snow by intensity, fog layer, lightning
  flashes. Capped at 30 fps, paused when the window is hidden or unfocused for a minute,
  still image with reduced motion.
- A small D-Bus service shares the current data so the menu-bar popover (#173), the desktop widget
  (#165), the Control Center Weather control (#172) and ongoing activity (#179, e.g. "rain in 10
  min", active hurricane warning) all show the same numbers without fetching twice.
- Search provider, so typing a place or "weather" in the search overlay (#150) shows it.
- Notifications for official alerts and "rain starting soon" (opt-in, per place).
- Spanish and English from day one (#146).

## 5. Originality and licences

Ideas only: no artwork, animations, icons, symbols or wording taken from any other weather app
(the reference desktop's weather app's animated backgrounds in particular are its own; ours must
look clearly different). Weather symbols: our own set (or Adwaita's, CC BY-SA). Parchita: original
artwork, owner-approved, never a bitten fruit or stem-and-leaf silhouette (logo rule). See
`docs/feature-roadmap-2026.md`, "Originality and licences".

## 6. Phases

1. **Core:** data from MET Norway + NWS, Now / hourly / 10 days / basic cards, living sky (sun,
   clouds, rain, snow), glass cards, Classic, light/dark, several places, ES/EN.
2. **Hyperlocal:** alerts and hurricanes, next-hour rain, map card with radar, sea card, air
   quality (after the data-source decision).
3. **Personality and system:** Parchita and playful summaries, D-Bus service feeding #173, #165,
   #172, #179, search provider, notifications.

Done when (phase 1): it replaces GNOME Weather on the ISO; side by side against the owner's
references it reads as clearly better; it runs under 3% CPU while open on the test desktop; and
Glass and Classic both look intentional.
