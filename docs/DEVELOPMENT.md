# Developing ParchaOS

Notes for contributors and coding agents. The project overview for users
is in the top-level [README](../README.md).

**Status as of 2026-09-26**: a real disk install, reboot, and login has
happened on the actual physical machine this variant ships to (MSI B650
GAMING PLUS WIFI / AM5 desktop). This profile (`profiles/parchaos/`) now
ships 31 custom packages plus the full Fedora base — dock, global menu
bar, a full-screen app launcher, Parcha Controls (control center),
Parcher (the Nautilus-based file manager), ParchaOS Settings (plus a
panel in GNOME Settings), session restore, live Clock and Calendar
icons, two visual styles (Glass and Classic), GTK/icon/Plymouth/wallpaper
theming (light + dark) with original ParchaOS icons, a Chromium-based
browser, a Super-as-Ctrl keyboard remap, scheduled Do Not Disturb, auto
light/dark, a hosts-file ad-blocker, a live/video wallpaper,
Desktop Icons NG, and GNOME Shell extensions from Pulsar OS's own list
for desktop polish (traffic-light window buttons, magic-lamp minimize effect,
top-right notification banners, blur, and more). The KDE-only
cruft this repo inherited from its original fork (`profiles/pearos/`
and its packaging) has been fully removed.

**If you're an agent picking this up, read the phase docs before
touching code** — they are the authoritative, chronological record of
what's real, what's verified, and what's still open, and this README's
job is now just to orient you to them, not to duplicate their detail:
- `docs/gnome-phase0-findings.md` — the original GRUB/boot/disk-install
  saga and early packaging work.
- `docs/gnome-phase1-findings.md` — the real-hardware crisis (boot,
  locale, fonts, WiFi/Bluetooth firmware, a clock/signature-verification
  bug) plus everything from the theming/extension-polish pass: traffic
  lights, light mode, the browser, app renames, the GDM logo, and a
  full extension-parity pass against Pulsar OS's own real config.
- `docs/gnome-phase2-findings.md` — a licensing audit of Pulsar OS's
  remaining ports: several components have no LICENSE file, so they
  aren't packaged until licensing is clarified with the Inled team.
- `docs/gnome-phase4-findings.md` — the ParchaOS-original desktop pieces
  (launcher, Parcha Controls, settings, session restore, live icons,
  styles, original icons) and the September 2026 audits.
- `docs/gnome-phase3-findings.md` — scoping and shipping the three
  "bigger feature" gaps that don't depend on Inled's answer
  (`gnome-software`, a real hosts-file ad-blocker, a real Wayland-native
  live wallpaper) and closing the last extension gap (Desktop Icons
  NG). Also documents a real five-bug dependency chain found in the
  since-removed `pafari` package while adding `gnome-software` — worth
  reading before touching RPM `Epoch`/`Provides`/`Obsoletes` on any
  package in this repo.

## What this repo is

This is a **GNOME-based** sibling of `parchaos` (KDE, private)
(the original, working, KDE Plasma–based ParchaOS — a Fedora port of
[pearOS](https://github.com/pearOS-archlinux), a macOS-styled Linux distro).

**Why a second repo instead of continuing the KDE one**: pearOS's own
desktop look is itself downstream of a much larger, more mature, more
complete project called **Pulsar OS "Bitten Fruit"**
(https://bittenfruit.inled.es/, source at
[`Inled-Pulsar-OS/PKG`](https://github.com/Inled-Pulsar-OS/PKG),
GNOME-based). Pulsar OS already has working, polished,
actively-maintained implementations of nearly everything on this
project's roadmap. All of it is GNOME Shell-extension-based, so **none
of it runs under KDE Plasma** — hence a separate repo rather than
trying to bolt GNOME Shell extensions onto the existing KDE build.

The KDE variant is kept as a separate, working project; this repo
doesn't replace it.

**Licensing of upstream components**: only package code with a real
LICENSE file behind it. Several Pulsar OS components have none (see
`docs/gnome-phase2-findings.md`), so they aren't packaged until that is
clarified with the Inled team. Don't rely on a license field in a
PKGBUILD or `DEBIAN/control` alone.

## Layout

```
engine/            Reusable Fedora ISO build engine (dracut, GRUB,
                    xorriso/El Torito, Secure Boot shim signing) —
                    desktop-environment-agnostic, shared with the KDE
                    repo's own history.
profiles/parchaos/  This variant's only profile. packages.list (stock
                    Fedora packages), packages.sh (this project's own
                    31 custom packages, PROFILE_REPO_PACKAGES),
                    customize.sh (branding + dconf defaults),
                    repo.sh, profile.conf.
packaging/          One directory per custom package, each with a
                    real .spec and (where the source isn't fetched
                    from a pinned upstream commit) a files/ tree.
                    Every package's own spec has a banner comment
                    explaining what it is, why it exists, and the
                    real bugs found building/shipping it — read the
                    spec before assuming what a package does.
docs/               gnome-phase{0,1,2,3,4}-findings.md — see above.
scripts/lint.sh     The static checks CI runs on every push.
                    pearos-ui-reference/ — historical KDE-era design
                    reference, not this repo's own history.
```

## What's actually shipped (see the phase docs for the "why" and the real bugs behind each)

**Desktop shell**: `parchaos-dock` (Dash-to-Dock fork, magic-lamp minimize
effect via `parchaos-magic-lamp-effect`), `parchaos-global-menu` (global
menu bar with the About ParchaOS card and weather), `parchaos-launcher`
(full-screen app launcher with folders, search and uninstall),
`parchaos-controls` (Parcha Controls, the control center),
`parchaos-session` (reopens the last session's apps and windows),
`parchaos-live-icons` (live Clock and Calendar icons),
`parchaos-gtk-theme`/`parchaos-icon-theme` (MacTahoe, light and dark,
with original ParchaOS icons replacing the Apple-look ones),
`parchaos-gnome-wallpaper`, `parchaos-gnome-plymouth-theme`
(parcha-plymouth boot splash), `parchaos-gdm-logo`, `parchaos-desktop-icons`
(DING), `parchaos-hanabi` (real video wallpaper), plus 8 more
independently-licensed GNOME Shell extensions for polish
(`blur-my-shell`, Just Perfection, No Overview, AppIndicator,
`parchaos-notification-position`, `parchaos-wiggle`,
`parchaos-ui-tune`) — 12 of Pulsar OS's own real ~15-extension list in
total.

**Apps and settings**: `parcher` (Parcher, a Nautilus fork,
GPL-3.0), `parchaos-settings` (ParchaOS Settings: style, session
restore, Focus schedule, keyboard; also reachable from a ParchaOS panel
in GNOME Settings, `packaging/gnome-control-center/`, a patched Fedora
build the ParchaOS repository is preferred for), `parchaos-browser` ("Parcha Browser": thin Chromium
rebrand and the default web browser; it replaced and Obsoletes `pafari`, the
old WebKitGTK/Epiphany fork), `parchaos-app-renames` (Loupe → Preview,
Clocks → Clock, Geary → Mail, Software → Parcha Store),
`parchaos-cloud` (rclone wrapper — **deprioritized**,
see phase2/phase3 docs; already shipped before this project's own
licensing-audit habit started, same missing-LICENSE gap as the rest of
Inled's work, being replaced with ParchaOS's own implementation rather
than maintained further), `parchaos-focus-schedule`, `parchaos-yin-yang`
(auto light/dark), `parchaos-keyboard-remap` (Super↔Ctrl via xremap),
`parchaos-hblock` (real hosts-file ad-blocker).

**Installer**: `parchaos-gnome-calamares-config` — a real disk install
that boots, with the real partitioning/kernel-install/EFI fixes this
took (see phase0/phase1 docs for the full saga: BIOS boot partitions,
kernel-install-on-target, EFI System Partition population, a Calamares
app-removal cascade-removal regression caught and fixed twice).

**System**: `parchaos-release` keeps the ParchaOS name, logo and links
in `/etc/os-release` across Fedora updates. `parchaos-welcome` is the
first-login assistant (style, light/dark, Super key, location consent,
a short tour).

**OTA mechanism**: `parchaos-desktop`, a meta-package whose `Requires:`
list names every package above (it also ships the desktop-wide dconf
defaults, the `org.parchaos.desktop` settings schema, the Flathub
remote and the per-user extension migration) — installing/updating it is
what makes a plain `sudo dnf update` on an already-installed system
pick up packages added to this profile after the user's own install,
not just upgrade ones already present. **Must be kept in sync by hand**
whenever `packages.sh`'s `PROFILE_REPO_PACKAGES` changes — bump its
`Release` and add the new `Requires:` line, or a real user's `dnf
update` silently won't pick up the new package. This has bitten this
project's own real hardware more than once; see phase1/phase3 docs.

## Still deferred (explicit user calls, not forgotten)

- Deeper Calamares installer skinning to match the desktop's look (real QML/UI work,
  not started — could be done as this project's own original work,
  doesn't need Pulsar's blocked `calamares-themes`).
- Deeper glass effects (refraction, highlights) beyond the blur the
  Glass style uses today (a candidate source: `ryohsuke1231/liquid-glass`).
- `parchaos-cloud`'s replacement (see above).

## Waiting on upstream licensing

Sayri, Time Machine, Welcome, Cloud, the keyboard remapper, the Plymouth,
Calamares and sound themes, Spotlight, Circle-to-Search, a control center,
a notification island, an app store and a driver manager from Pulsar OS
have no LICENSE file. ParchaOS writes its own versions instead where it
needs them (Parcha Controls, the launcher, Welcome).

## Release image gate

`engine/build-iso.sh` runs `scripts/check-image.sh` on the finished
rootfs, just before compressing it. The script writes every installed
package (name, license, vendor) to `build/<iso>.packages.tsv`, which is
published with the ISO, and fails the build if the image contains
something ParchaOS can't redistribute or no longer ships: `openh264`
(Cisco's license only covers downloads from Cisco), `fedora-logos`
(Fedora's logos are for official Fedora media), any package built by RPM
Fusion other than its repo definitions, or `pafari`, `pearos-*`,
`parchaos-finder`, `parchaos-macos-remap`, `parchaos-tmog`. It also fails
if `noopenh264` or `generic-logos` is missing. `--skip-branding` test
builds skip it.

The swap itself is in `profiles/parchaos/customize.sh`. Cisco's
`openh264` obsoletes `noopenh264`, and dnf honors that for the installed
package too, so the profile removes `openh264` with `rpm -e --nodeps`
and then installs `noopenh264` with the Cisco repo disabled, in a single
container call.

## Release source code (GPL)

Every release publishes the complete corresponding source of its ISO as
GitHub release assets (owner decision, 2026-09-26). On the build host,
after the ISO build:

    scripts/collect-sources.py build/rootfs-parchaos-44 build/sources --prefix <iso-name>

It reads each installed package's source RPM from the rootfs, downloads
Fedora's from Koji (which keeps every build) and ParchaOS's from the
matching COPR build, and writes `<iso-name>-sources-NN.tar` archives
(under 2 GiB each) plus `<iso-name>-sources.sha256`. Upload those with
the ISO. `docs/SOURCES.md` (installed as /usr/share/doc/parchaos/SOURCES.md)
and `docs/release-notes-template.md` carry the written offer; source
requests come in through the parchaos.org/support form ("Question",
titled "Source code request").

## Public surface audit

`scripts/public-surface-audit.sh` (read-only) lists the COPR projects,
their packages and what the repo metadata actually serves, plus the
GitHub repositories, releases and release assets of the owner accounts.
It flags removed or third-party material (pearOS, Pafari, Finder,
macOS-remap, TMOG, pre-rewrite global-menu and cloud builds) and
ParchaOS-related repositories that are public by mistake. Run it before
every release.

## License

- **Code, packaging and docs** written for ParchaOS: **GPL-3.0-or-later**
  (`LICENSE`). Chosen to match the GPL code this project forks and ships
  (Nautilus/Parcher, Dash-to-Dock/Parcha Dock, several GNOME Shell
  extensions), so everything combines cleanly.
- **Original ParchaOS artwork** (e.g. the app icons in
  `packaging/parchaos-icon-theme/parchaos-icons/`): **CC BY-SA 4.0**
  (`LICENSE-ARTWORK`).
- **Third-party components keep their own licenses**, declared in each
  package's spec `License:` field (for example the MacTahoe-based themes
  and xremap). The ParchaOS logo is original artwork, generated by
  `branding/logo/make-brand.py` (see `branding/logo/CREDITS.md`).

## Naming policy (trademark caution)

ParchaOS is meant to ship publicly, so Apple's names stay out of anything
we name or write ourselves: package names, app/feature names, package
summaries/descriptions, and docs prose. Describe the feature instead (dock,
global menu bar, traffic-light window controls, hover magnification,
Super-as-Ctrl) or say "the reference desktop". Its key names and symbols
count too: the remapped key is Super, never "Cmd" or the command symbol.
Renamed so far:
`parchaos-macos-remap` -> `parchaos-keyboard-remap`, "Finder" -> "Parcher",
Software -> "Parcha Store" ("App Store" is itself a trademark). Approved names for
upcoming features: Parcha Time (backups), Parcha Controls (control center),
ParchaOS Recovery.
Still needing a ParchaOS name before it's built: system-wide search.

Deliberately kept: upstream project names and URLs (e.g. `MacTahoe` --
confirmed by the project owner 2026-09-25 to stay as-is, credited, not renamed;
`gnome-macos-remap-wayland`, Pulsar OS's own "Finder"), because renaming
them would misstate where the code came from; old names that
`Obsoletes:`/changelogs need; and direct quotes. This is risk reduction,
not legal clearance -- get a real legal review before a public launch.

## A note on working style, for any agent picking this up

**Verify against real hands-on results, not assumptions.** This
project's whole history (this repo's own phase docs, and the KDE
repo's before it) is one long demonstration that "should work" claims
hide real bugs: a missing RPM `Release` bump silently no-op'ing a fix,
an RPM `Epoch` mismatch quietly defeating a `Provides`/`Obsoletes`
declaration, a build-time macro getting expanded inside what was meant
to be a plain shell comment, a package's own install script silently
skipping a step because a build sandbox lacked a binary it assumed was
present, a license field in a PKGBUILD with no real LICENSE file behind
it. Every one of these was caught by actually building it, installing
it on real hardware, and reading the real output — not by asking
whether it should work. Do the same. Check licenses against a real
LICENSE file, not a claim. Check real package/service state with real
commands, not memory. Build it, install it, run it, and look at a real
screenshot (or a real `dnf`/`systemctl`/`gsettings` result) before
calling something done.
