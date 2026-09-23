# ParchaOS (GNOME variant) — pearOS/Pulsar OS on Fedora

**Status as of 2026-09-23: no longer "just forked" — a real, installable, end-to-end verified GNOME live ISO exists (theme, icons, dock, Parcher/Nautilus, global menu, Calamares branding + install, Plymouth, wallpaper, macOS-style keyboard remap), and a real disk install + reboot + login has been confirmed working. See `docs/gnome-phase0-findings.md` for the full story — this file's roadmap sections below are the ORIGINAL plan from the fork and are now partly stale; the phase doc has the current, accurate picture. If you are an agent picking this up, read both before touching code.**

## What this repo is

This is a **GNOME-based** sibling of [`alexgalicea/parchaos`](https://github.com/alexgalicea/parchaos)
(the original, working, KDE Plasma–based ParchaOS — a Fedora port of
[pearOS](https://github.com/pearOS-archlinux), a macOS-styled Linux distro).

**Why a second repo instead of continuing the KDE one**: mid-session
investigation (2026-09-22) discovered that pearOS's own macOS-mimicry is
itself downstream of a much larger, more mature, more complete project
called **Pulsar OS "Bitten Fruit"** (https://bittenfruit.inled.es/,
source at [`Inled-Pulsar-OS/PKG`](https://github.com/Inled-Pulsar-OS/PKG),
GNOME-based, MIT-INLED + GPL-3.0). Pulsar OS already has working, polished,
actively-maintained implementations of nearly everything on this project's
remaining roadmap: a real macOS-style global menu, a real Dash-to-Dock fork
with Liquid Glass blur, a heavily patched Nautilus ("Finder" — real traffic
lights, Tags sidebar, iCloud-style cloud drive integration), Spotlight
search, Time Machine-style backups, a Siri-like AI assistant ("Sayri"),
Circle-to-Search, and full theme/SDDM/GRUB/Plymouth/rEFInd macOS asset
packs. All of it is GNOME Shell-extension-based, so **none of it runs
under KDE Plasma** — hence a separate repo rather than trying to bolt GNOME
Shell extensions onto the existing KDE build.

**The KDE repo (`alexgalicea/parchaos`) is being kept as-is, working,
untouched** — it is a real, verified-working, installable OS (live boot,
disk install, full branding, all confirmed on real hardware/VMs this
project has access to). Do not assume this GNOME repo supersedes it; they
are parallel products until/unless the user decides otherwise. If you're
unsure which repo a task belongs in, ask.

## What carries over from the KDE repo vs. what doesn't

This repo was created via `git push --mirror`-equivalent from the KDE
repo's `claude/new-session-eqcw68` branch (pushed to this repo's `main`),
so **all of the KDE repo's history and files are currently present here
unchanged**. Most of it needs to be replaced or removed as this repo
diverges. Concretely:

**Carries over almost unchanged (desktop-environment-agnostic):**
- `engine/build-iso.sh` — the whole live-ISO build pipeline (dracut, GRUB,
  xorriso/El Torito assembly, Secure Boot shim signing). This was the
  hardest, highest-risk part of the original project (see
  `docs/phase1-findings.md` and `docs/phase4-findings.md` in the KDE repo
  for the full saga: GRUB relocator bugs, dmsquash-live, kernel-install-on-target,
  BIOS boot partition flags). None of it is KDE-specific.
- `packaging/pearos-calamares-config` — the Calamares installer branding +
  the real partitioning/kernel-install fixes that got a real disk install
  booting end-to-end. Only the visual branding assets (splash/logo) need
  re-pointing to new theme assets.
- Ploader / UEFI Secure Boot signing chain.
- `packaging/parchaos-focus-schedule` (D-Bus `Notifications.Inhibit`, works
  under any desktop implementing the freedesktop.org notifications spec).
- Likely `packaging/parchaos-yin-yang` (already has a `gtk` plugin
  upstream; may need less adaptation than it did for KDE, where a
  `parchaos-appmenu-gtk-module` bridge was needed just to get GTK apps'
  menus to show up at all — under GNOME that whole problem disappears).

**Needs full replacement (KDE/KWin/Plasma-specific — will not run under GNOME):**
- `packaging/pearos-dock` (Plasma 6 QML applet) → replace with Pulsar OS's
  `pulsar-dock@inled.es` (their Dash-to-Dock fork,
  [`Inled-Pulsar-OS/dash-to-dock`](https://github.com/Inled-Pulsar-OS/dash-to-dock)),
  packaged as part of `pulsaros-gnome`.
- `packaging/pearos-liquidgel` (KWin blur effect) → replace with Pulsar
  OS's "Liquid Glass" GNOME Shell extension
  ([`ryohsuke1231/liquid-glass`](https://github.com/ryohsuke1231/liquid-glass),
  bundled via `pulsaros-gnome`).
- The Aurorae window-decoration theme, the Plasma SVG desktop theme, and
  all `Pear*` plasmoids (`PearAppTitle`, `PearClock`, `PearPrivacy`,
  `PearControlCentre`, `PearWeather`, `PearCalendar`) → GNOME doesn't have
  a direct equivalent to Plasma's desktop-widget system; the global menu
  and top-bar experience come from `pulsaros-global-menu` (a GNOME Shell
  extension with a real Apple-menu + File/Edit/View/Window/Help bar and
  power-off dialogs) instead. Desktop calendar/weather widgets may need a
  separate solution or may just not exist in the GNOME variant — not yet
  investigated.
- `packaging/parchaos-appmenu-gtk-module` → becomes unnecessary entirely
  once everything is GTK-native under GNOME.
- `packaging/parchaos-whitesur-lookandfeel` (KDE Plasma look-and-feel
  KPackage) → not applicable; GNOME theming comes from `pulsaros-theme`
  (MacTahoe GTK + icon theme).
- Most of `packaging/pearos-settings` (skel `kdeglobals`/`kwinrc`/
  `plasma-org.kde.plasma.desktop-appletsrc`, Kvantum theme) → all
  KDE-config-format specific, meaningless under GNOME. The panel-layout
  bugs fixed there this session (see the KDE repo's own commit history,
  2026-09-22: broken icon-theme reference, non-expanding panel spacer,
  dead-code idle-menu-text path) are KDE-repo-only fixes and do **not**
  need porting here.
- `packaging/pearos-icon-theme`, `pearos-gtk-theme`, `pearos-sddm-theme`,
  `pearos-grub-theme`, `pearos-wallpapers` → replace wholesale with Pulsar
  OS's own theme packages (`pulsaros-theme`, `pulsaros-sddm` [Apple Tahoe
  SDDM theme], `pulsaros-grub`, `pulsaros-refind`, `pulsaros-plymouth`,
  `pulsaros-live-wallpaper`), all already built and working — this is
  **repackaging already-proven software for Fedora**, not inventing new
  themes from scratch.

**Real, substantial from-scratch ports** (Pulsar OS has these built, but
they're full standalone apps, not "install-and-go" — expect multi-day
effort each, same shape as the KDE repo's `liquid-gel`/`pearos-dock`
ports):
- [`Inled-Pulsar-OS/finder`](https://github.com/Inled-Pulsar-OS/finder) —
  the patched Nautilus ("Finder"). GPL-3.0. Meson/ninja build, depends on
  GTK4/libadwaita/gexiv2/tinysparql — check Fedora's package versions
  match what the PKGBUILD expects (it already needed one sed patch for a
  `gexiv2` pkgconfig naming difference between distros, see
  `arch/pkgbuilds/nautilus/PKGBUILD` in the `Inled-Pulsar-OS/PKG` repo).
  **This was approved and in-progress investigation when this repo was
  created — pick this up first.**
- `sayri` — Siri-like AI assistant, Python/GTK4, whisper.cpp + Piper.
- `pulsaros-timemachine` — Btrfs snapshots + restic, GTK4/Libadwaita.
- `pulsaros-welcome` — Tauri (Rust+React) first-boot app.
- `pulsaros-cloud` — rclone wrapper for Finder's cloud-drives sidebar.
- `gnome-macos-remap-wayland` — built on `xremap`, genuinely
  DE-agnostic key remapper; likely the easiest of this group.

**Full Pulsar OS package reference**: see
[`Inled-Pulsar-OS/PKG`](https://github.com/Inled-Pulsar-OS/PKG)'s own
README — it has a complete table of every package, what it does, and
exactly which upstream project it derives from (important for license
tracking: most original Inled work is MIT-INLED, forks of GPL projects
like Nautilus/Nautilus stay GPL-3.0). Their `arch/pkgbuilds/` directory has
real, working `PKGBUILD`s for every component — use these as the reference
for dependencies and build steps the way this project always has (verify
against the real upstream source, don't assume).

## Layout (inherited from the KDE repo, to be reorganized)

```
engine/                     Reusable Fedora build engine — keep as-is
profiles/pearos/            KDE-specific profile — needs a new
                             profiles/<gnome-flavor-name>/ alongside or
                             instead of this
packaging/                  Mix of reusable (Calamares, focus-schedule)
                             and KDE-only (dock, liquidgel, plasmoids,
                             settings) packages — needs to be sorted
docs/                       KDE repo's phase-history docs — historical
                             reference only, doesn't describe this repo's
                             own (not-yet-started) history
```

## Next steps for whoever picks this up

1. Decide on a profile name (`profiles/pearos/` is KDE-branded; this
   variant should probably be its own name, matching whatever product
   identity gets chosen — "ParchaOS" itself, or something distinguishing
   it from the KDE line).
2. Finish the Finder/Nautilus port (in progress — real upstream source
   identified, license confirmed GPL-3.0, build system is meson/ninja,
   dependencies listed above).
3. Get a minimal GNOME session booting via `engine/build-iso.sh` first
   (swap `livesys_session="kde"` → `"gnome"` in the engine, add GNOME
   packages to a new profile's `packages.list`) before layering on any
   Pulsar OS branding — establish the same "unbranded baseline" checkpoint
   the KDE repo used in its own Phase 1.
4. Work through the "needs full replacement" list above roughly in order
   of user-visible impact: theme/icon/SDDM assets first (highest
   visual-impact-to-effort ratio, since Pulsar OS already built and tested
   all of them), then dock + global menu (the two biggest "does this
   actually feel like macOS" pieces), then the standalone apps
   (Finder → Sayri → Time Machine → Welcome, in roughly that priority
   order based on what the user has asked about so far).
5. Write real phase-findings docs as you go (`docs/phase0-findings.md`
   etc., following the KDE repo's own convention) — that repo's docs are
   what let this session's work restart cleanly after context resets, and
   this repo needs the same for whichever agent works on it next.

## A note on working style, for any agent picking this up

The KDE repo's whole history (see its `docs/*.md` and commit log) is a
useful model for how this project expects work to happen: **verify against
real hands-on results, not assumptions** — every "should work" claim in
this project's history that wasn't actually tested turned out to hide a
real bug (a missing RPM `Release` bump silently no-op'ing a fix, a
dead-code QML path, a non-expanding panel spacer, a wrong git tag, wrong
dependency pins, ambiguous shebangs, and more, all listed in the KDE
repo's commit history from 2026-09-22 alone). Build it, install it, run
it, and look at a real screenshot before calling something done.
