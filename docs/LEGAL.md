# ParchaOS legal and privacy information

ParchaOS is published by Spanglish Enterprises LLC. It is free software,
built on Fedora Linux and GNOME. This file is installed on every ParchaOS
system at `/usr/share/doc/parchaos/LEGAL.md`.

## No warranty

ParchaOS is provided "as is", without warranty of any kind, express or
implied, including the warranties of merchantability, fitness for a
particular purpose and non-infringement. The individual licenses of the
components (below) contain the full terms. Back up your data before
installing.

## Licenses

- ParchaOS's own code, packaging and documentation: GPL-3.0-or-later.
- Original ParchaOS artwork: CC BY-SA 4.0.
- Every other component keeps its own license. Each installed package's
  license text is in `/usr/share/licenses/<package>/`, and
  `rpm -q --qf '%{LICENSE}\n' <package>` shows its license.

The complete corresponding source code for ParchaOS, and the written
offer for it, are described in `/usr/share/doc/parchaos/SOURCES.md`.

## Trademarks and affiliation

ParchaOS is an independent project. It is not affiliated with or
endorsed by the Fedora Project, Red Hat, the GNOME Foundation, Apple,
Google, Microsoft, Cisco, Flathub, Inled (Pulsar OS) or pearOS. Fedora is
a trademark of Red Hat, LLC; GNOME is a trademark of the GNOME
Foundation; Chromium is a trademark of Google LLC. Other names belong to
their owners and are used only to identify those projects and services.

## Credits

- **The ParchaOS logo** is based on "Passion Fruit" by LUTFI GANI AL
  ACHMAD, from the Noun Project, licensed CC BY 3.0
  (https://creativecommons.org/licenses/by/3.0/).
- **Themes:** the GTK and icon themes are based on MacTahoe by
  vinceliuice (https://github.com/vinceliuice), with ParchaOS's own icons
  and changes.
- **Parcha Dock** is based on Pulsar Dock by Inled (Pulsar OS), a fork of
  Dash to Dock by Michele Gaio and contributors.
- **Parcher** is based on the Pulsar OS file manager by Inled, a
  derivative of GNOME Files (Nautilus).
- **Keyboard remapping** uses xremap by Takashi Kokubun (MIT) and the
  xremap-gnome extension (GPL-2.0-or-later).
- **Ad blocking** uses hBlock by Héctor Molinero Fernández (MIT) and the
  lists it downloads, each under its own terms.
- **Weather data** comes from the Norwegian Meteorological Institute
  (MET Norway, CC BY 4.0) and, for current conditions, aviationweather.gov,
  through GNOME's libgweather.
- The GNOME Shell extensions ParchaOS ships are credited in their own
  metadata and in each package's license directory.

## Network connections

ParchaOS contacts these services. None of them receives an account or
personal profile from ParchaOS.

- **Software updates:** Fedora's mirrors and the ParchaOS package
  repository on Fedora COPR (copr.fedorainfracloud.org). Fedora's
  repositories count installed systems anonymously once a week
  ("countme"; set `countme=0` in `/etc/yum.repos.d/fedora*.repo` to opt
  out). H.264 support is downloaded from Cisco's openh264 repository.
- **Parcha Store:** app catalogs from Fedora and Flathub, and ratings and
  reviews from GNOME's review service (odrs.gnome.org).
- **Connectivity check:** NetworkManager loads
  http://fedoraproject.org/static/hotspot.txt to detect captive portals.
  It can be turned off in Settings, under Privacy & Security.
- **Location (only when Location Services are on):** GNOME's geoclue
  sends the identifiers of nearby Wi-Fi networks to BeaconDB
  (api.beacondb.net), and may look up your approximate location from your
  IP address (reallyfreegeoip.org). ParchaOS Welcome asks before turning
  Location Services on, and you can turn them off in Settings, under
  Privacy & Security.
  ParchaOS doesn't submit Wi-Fi data to BeaconDB.
- **Weather (menu bar and Weather app):** your approximate location is
  sent to MET Norway (api.met.no) and aviationweather.gov to get the
  forecast.
- **Ad blocking:** once a day, hBlock downloads blocklists (from
  raw.githubusercontent.com). Turn it off with
  `sudo systemctl disable --now hblock.timer`.
- **Parcha Browser** is Fedora's Chromium. It connects to the sites you
  visit and to the services in its own settings (for example Safe
  Browsing); see the browser's privacy settings.
- **Help and bug reports:** the Help menu opens parchaos.org. The bug
  report form there is covered by the website's privacy policy
  (https://parchaos.org/privacy).

## Export

ParchaOS contains cryptographic software. It may be subject to the U.S.
Export Administration Regulations and other export laws. You may not
export, re-export or transfer it to a country or person subject to U.S.
embargo or export restrictions, or for use in weapons of mass
destruction or missile programs. You are responsible for complying with
the laws that apply to you.

## Security

Report security problems privately, as described in `SECURITY.md` in the
project repository.
