# ParchaOS (GNOME variant) — pearOS/Pulsar OS on Fedora

**Status as of 2026-09-25**: a real disk install, reboot, and login has
happened on the actual physical machine this variant ships to (MSI B650
GAMING PLUS WIFI / AM5 desktop). This profile (`profiles/pulsaros/`) now
ships 25 real custom packages plus the full Fedora base — dock, global
menu, Finder (Nautilus fork), GTK/icon/Plymouth/wallpaper theming
(light + dark), a Chromium-based browser alongside the WebKitGTK one,
macOS keyboard remap, cloud drives, focus schedule, auto light/dark,
TMOG, a hosts-file ad-blocker, a real live/video wallpaper, Desktop
Icons NG, and 12 of Pulsar OS's own real GNOME Shell extensions for
macOS-style polish (traffic-light window buttons, genie minimize
effect, top-right notification banners, blur, and more). The KDE-only
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
- `docs/gnome-phase2-findings.md` — a full licensing audit of Pulsar
  OS's remaining from-scratch ports. Real finding: most of Inled's own
  original work (not their forks of established GPL projects) has no
  actual LICENSE file anywhere, a systemic gap, not a one-off. A single
  outreach email to Inled covering everything blocked is drafted but
  **not yet sent** — that's the single highest-leverage next step if
  you're picking this up fresh.
- `docs/gnome-phase3-findings.md` — scoping and shipping the three
  "bigger feature" gaps that don't depend on Inled's answer
  (`gnome-software`, a real hosts-file ad-blocker, a real Wayland-native
  live wallpaper) and closing the last extension gap (Desktop Icons
  NG). Also documents a real five-bug dependency chain found in the
  existing `pafari` package while adding `gnome-software` — worth
  reading before touching RPM `Epoch`/`Provides`/`Obsoletes` on any
  package in this repo.

## What this repo is

This is a **GNOME-based** sibling of [`alexgalicea/parchaos`](https://github.com/alexgalicea/parchaos)
(the original, working, KDE Plasma–based ParchaOS — a Fedora port of
[pearOS](https://github.com/pearOS-archlinux), a macOS-styled Linux distro).

**Why a second repo instead of continuing the KDE one**: pearOS's own
macOS-mimicry is itself downstream of a much larger, more mature, more
complete project called **Pulsar OS "Bitten Fruit"**
(https://bittenfruit.inled.es/, source at
[`Inled-Pulsar-OS/PKG`](https://github.com/Inled-Pulsar-OS/PKG),
GNOME-based). Pulsar OS already has working, polished,
actively-maintained implementations of nearly everything on this
project's roadmap. All of it is GNOME Shell-extension-based, so **none
of it runs under KDE Plasma** — hence a separate repo rather than
trying to bolt GNOME Shell extensions onto the existing KDE build.

**The KDE repo (`alexgalicea/parchaos`) is being kept as-is, working,
untouched** — a real, verified-working, installable OS in its own
right. Do not assume this GNOME repo supersedes it; they are parallel
products until/unless the user decides otherwise. If you're unsure
which repo a task belongs in, ask.

**A real, important caveat on Pulsar OS's own licensing** (see
`docs/gnome-phase2-findings.md` for the full audit): their own
project's license claims don't hold up against the real repos in most
places. Their fork of Nautilus (used as this project's own Finder) has
a real, confirmed license. Almost everything else original to Inled —
Sayri, Time Machine, Welcome, Cloud, the keyboard remapper, the
Plymouth/Calamares/sound themes, Spotlight, Circle-to-Search, Control
Center, Dynamic Island, the app store, the driver manager — has **no
LICENSE file anywhere**, regardless of what a PKGBUILD or
`DEBIAN/control` claims. Don't take any license field in their repos at
face value; check for a real LICENSE file the way this project's own
audit did, and don't package anything from that list until Inled
responds to the outreach email.

## Layout

```
engine/            Reusable Fedora ISO build engine (dracut, GRUB,
                    xorriso/El Torito, Secure Boot shim signing) —
                    desktop-environment-agnostic, shared with the KDE
                    repo's own history.
profiles/pulsaros/  This variant's only profile. packages.list (stock
                    Fedora packages), packages.sh (this project's own
                    25 custom packages, PROFILE_REPO_PACKAGES),
                    customize.sh (branding + dconf defaults),
                    repo.sh, profile.conf.
packaging/          One directory per custom package, each with a
                    real .spec and (where the source isn't fetched
                    from a pinned upstream commit) a files/ tree.
                    Every package's own spec has a banner comment
                    explaining what it is, why it exists, and the
                    real bugs found building/shipping it — read the
                    spec before assuming what a package does.
docs/               gnome-phase{0,1,2,3}-findings.md — see above.
                    pearos-ui-reference/ — historical KDE-era design
                    reference, not this repo's own history.
```

## What's actually shipped (see the phase docs for the "why" and the real bugs behind each)

**Desktop shell**: `parchaos-dock` (Dash-to-Dock fork, genie minimize
effect via `parchaos-magic-lamp-effect`), `parchaos-global-menu` (real
macOS-style menu bar), `parchaos-gtk-theme`/`parchaos-icon-theme`
(MacTahoe, both light and dark), `parchaos-gnome-wallpaper`,
`parchaos-gnome-plymouth-theme` (currently a safe no-op guard, see
"Still deferred" below), `parchaos-gdm-logo`, `parchaos-desktop-icons`
(DING), `parchaos-hanabi` (real video wallpaper), plus 8 more
independently-licensed GNOME Shell extensions for polish
(`blur-my-shell`, Just Perfection, No Overview, AppIndicator,
`parchaos-notification-position`, `parchaos-wiggle`,
`parchaos-ui-tune`) — 12 of Pulsar OS's own real ~15-extension list in
total.

**Apps**: `parchaos-finder` (real Nautilus fork, GPL-3.0, genuinely
clear to redistribute), `pafari` (WebKitGTK/Epiphany fork), `parchaos-browser`
(thin Chromium rebrand for full Google-service compatibility),
`parchaos-app-renames` (Loupe → Preview, Clocks → Clock, Geary → Mail),
`parchaos-tmog`, `parchaos-cloud` (rclone wrapper — **deprioritized**,
see phase2/phase3 docs; already shipped before this project's own
licensing-audit habit started, same missing-LICENSE gap as the rest of
Inled's work, being replaced with ParchaOS's own implementation rather
than maintained further), `parchaos-focus-schedule`, `parchaos-yin-yang`
(auto light/dark), `parchaos-keyboard-remap` (Cmd↔Ctrl via xremap),
`parchaos-hblock` (real hosts-file ad-blocker).

**Installer**: `parchaos-gnome-calamares-config` — a real disk install
that boots, with the real partitioning/kernel-install/EFI fixes this
took (see phase0/phase1 docs for the full saga: BIOS boot partitions,
kernel-install-on-target, EFI System Partition population, a Calamares
app-removal cascade-removal regression caught and fixed twice).

**OTA mechanism**: `parchaos-desktop`, a no-content meta-package whose
`Requires:` list names every package above — installing/updating it is
what makes a plain `sudo dnf update` on an already-installed system
pick up packages added to this profile after the user's own install,
not just upgrade ones already present. **Must be kept in sync by hand**
whenever `packages.sh`'s `PROFILE_REPO_PACKAGES` changes — bump its
`Release` and add the new `Requires:` line, or a real user's `dnf
update` silently won't pick up the new package. This has bitten this
project's own real hardware more than once; see phase1/phase3 docs.

## Still deferred (explicit user calls, not forgotten)

- Deeper Calamares macOS-esque installer skinning (real QML/UI work,
  not started — could be done as this project's own original work,
  doesn't need Pulsar's blocked `calamares-themes`).
- A real Plymouth boot-splash theme (`parcha-plymouth` doesn't exist
  yet; the theme-switch step is a safe no-op in the meantime).
- A "Liquid Glass" blur/glass GNOME Shell extension equivalent (real
  source already identified: `ryohsuke1231/liquid-glass`, not started).
- `parchaos-cloud`'s replacement (see above).

## Blocked on Inled (one email would unblock all of it)

Sayri, `pulsaros-timemachine`, `pulsaros-welcome`, `pulsaros-cloud`,
`gnome-macos-remap-wayland`, `plymouth-macoslike`, `calamares-themes`,
`pulsar-pear-sound-theme`, `pulsaros-spotlight-launcher`,
`pulsar-circle-to-search`, a Control Center replica, a Dynamic
Island-style notification UI, an app store, a driver manager. See
`docs/gnome-phase2-findings.md` and `docs/gnome-phase3-findings.md` for
the full audit and the drafted (unsent) outreach email.

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
